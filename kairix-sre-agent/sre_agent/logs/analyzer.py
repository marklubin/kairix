"""Log analysis implementation."""

import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()


class LogAnalyzer:
    """Analyzes logs for patterns and anomalies."""
    
    # Common error patterns
    ERROR_PATTERNS = [
        (re.compile(r'ERROR|CRITICAL|FATAL', re.I), 'error'),
        (re.compile(r'WARN|WARNING', re.I), 'warning'),
        (re.compile(r'Exception|Traceback', re.I), 'exception'),
        (re.compile(r'timeout|timed out', re.I), 'timeout'),
        (re.compile(r'connection refused|connection error', re.I), 'connection'),
        (re.compile(r'out of memory|OOM', re.I), 'memory'),
        (re.compile(r'disk full|no space left', re.I), 'disk'),
        (re.compile(r'permission denied|access denied', re.I), 'permission'),
        (re.compile(r'404|not found', re.I), 'not_found'),
        (re.compile(r'500|internal server error', re.I), 'server_error'),
    ]
    
    def __init__(self, config):
        self.config = config
    
    def analyze_logs(
        self,
        service_name: str,
        user: Optional[str] = None,
        minutes: int = 30
    ) -> Dict[str, Any]:
        """Analyze logs for a service over a time window."""
        # Get log path
        if user:
            log_path = self.config.log_base_path / user / f"{service_name}.log"
        else:
            log_path = self.config.log_base_path / f"{service_name}.log"
        
        if not log_path.exists():
            return {
                "service": service_name,
                "user": user,
                "status": "no_logs",
                "error": "Log file not found"
            }
        
        # Get log lines for time window
        lines = self._get_recent_lines(log_path, minutes)
        
        if not lines:
            return {
                "service": service_name,
                "user": user,
                "status": "empty",
                "total_lines": 0,
                "time_window_minutes": minutes
            }
        
        # Analyze patterns
        analysis = self._analyze_patterns(lines)
        
        # Extract user activity
        user_activity = self._extract_user_activity(lines)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(lines, analysis)
        
        return {
            "service": service_name,
            "user": user,
            "status": "analyzed",
            "time_window_minutes": minutes,
            "total_lines": len(lines),
            "patterns": analysis,
            "user_activity": user_activity,
            "anomalies": anomalies,
            "health_score": self._calculate_health_score(analysis, anomalies)
        }
    
    def _get_recent_lines(self, log_path: Path, minutes: int) -> List[str]:
        """Get log lines from the recent time window."""
        try:
            # Use tail to get approximate lines
            estimated_lines = minutes * 100  # Assume ~100 logs/minute max
            
            result = subprocess.run(
                ["tail", "-n", str(estimated_lines), str(log_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error("Failed to read logs", path=log_path, error=result.stderr)
                return []
            
            lines = result.stdout.strip().split('\n')
            
            # Filter by timestamp if logs have them
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            filtered_lines = []
            
            for line in lines:
                # Try to extract timestamp (common formats)
                timestamp = self._extract_timestamp(line)
                if timestamp:
                    if timestamp >= cutoff_time:
                        filtered_lines.append(line)
                else:
                    # If no timestamp, include all recent lines
                    filtered_lines.append(line)
            
            return filtered_lines
            
        except Exception as e:
            logger.error("Error reading logs", path=log_path, error=str(e))
            return []
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from a log line."""
        # Common timestamp patterns
        patterns = [
            # ISO format: 2023-12-01T10:30:45
            (r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', '%Y-%m-%dT%H:%M:%S'),
            # Standard format: 2023-12-01 10:30:45
            (r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', '%Y-%m-%d %H:%M:%S'),
            # Syslog format: Dec 01 10:30:45
            (r'([A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2})', '%b %d %H:%M:%S'),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    # For syslog format, add current year
                    if '%Y' not in fmt:
                        timestamp_str = f"{datetime.utcnow().year} {match.group(1)}"
                        fmt = '%Y ' + fmt
                    else:
                        timestamp_str = match.group(1)
                    
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _analyze_patterns(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze log lines for patterns."""
        pattern_counts = defaultdict(int)
        error_samples = defaultdict(list)
        
        for line in lines:
            for pattern, category in self.ERROR_PATTERNS:
                if pattern.search(line):
                    pattern_counts[category] += 1
                    if len(error_samples[category]) < 3:  # Keep up to 3 samples
                        error_samples[category].append(line.strip()[:200])  # Truncate long lines
        
        # Calculate request rate if applicable
        request_pattern = re.compile(r'(GET|POST|PUT|DELETE|PATCH)\s+/\S+')
        requests = [line for line in lines if request_pattern.search(line)]
        
        return {
            "error_counts": dict(pattern_counts),
            "error_samples": dict(error_samples),
            "request_count": len(requests),
            "requests_per_minute": len(requests) / (len(lines) / 100) if lines else 0,  # Rough estimate
            "error_rate": sum(pattern_counts.values()) / len(lines) if lines else 0
        }
    
    def _extract_user_activity(self, lines: List[str]) -> Dict[str, Any]:
        """Extract user activity from logs."""
        # Look for user identifiers (common patterns)
        user_pattern = re.compile(r'user[_-]?(?:id|name)?[:\s]+([^\s,]+)', re.I)
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        users = Counter()
        ips = Counter()
        
        for line in lines:
            # Extract users
            user_match = user_pattern.search(line)
            if user_match:
                users[user_match.group(1)] += 1
            
            # Extract IPs
            ip_matches = ip_pattern.findall(line)
            for ip in ip_matches:
                # Filter out common local IPs
                if not ip.startswith(('127.', '0.', '255.')):
                    ips[ip] += 1
        
        return {
            "unique_users": len(users),
            "top_users": users.most_common(5),
            "unique_ips": len(ips),
            "top_ips": ips.most_common(5),
            "total_user_actions": sum(users.values())
        }
    
    def _detect_anomalies(self, lines: List[str], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns."""
        anomalies = []
        
        # High error rate
        if analysis["error_rate"] > 0.1:  # More than 10% errors
            anomalies.append({
                "type": "high_error_rate",
                "severity": "high",
                "details": f"Error rate is {analysis['error_rate']:.1%}",
                "value": analysis["error_rate"]
            })
        
        # Spike in specific error types
        for error_type, count in analysis["error_counts"].items():
            if count > 50:  # More than 50 occurrences
                anomalies.append({
                    "type": f"high_{error_type}_count",
                    "severity": "medium" if count < 100 else "high",
                    "details": f"{count} {error_type} errors detected",
                    "value": count,
                    "samples": analysis["error_samples"].get(error_type, [])
                })
        
        # Repeated error patterns (same error multiple times)
        error_lines = [line for line in lines if any(p[0].search(line) for p in self.ERROR_PATTERNS)]
        if error_lines:
            # Group similar errors
            error_groups = defaultdict(list)
            for line in error_lines:
                # Simple grouping by removing timestamps and numbers
                key = re.sub(r'\d+', 'N', line)
                key = re.sub(r'\b[0-9a-f]{8,}\b', 'ID', key)  # Remove hex IDs
                error_groups[key].append(line)
            
            # Find repeated errors
            for key, group in error_groups.items():
                if len(group) > 10:
                    anomalies.append({
                        "type": "repeated_error",
                        "severity": "medium",
                        "details": f"Error repeated {len(group)} times",
                        "value": len(group),
                        "sample": group[0][:200]
                    })
        
        return anomalies
    
    def _calculate_health_score(self, analysis: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> float:
        """Calculate a health score from 0-100."""
        score = 100.0
        
        # Deduct for error rate
        score -= analysis["error_rate"] * 100
        
        # Deduct for anomalies
        for anomaly in anomalies:
            if anomaly["severity"] == "high":
                score -= 20
            elif anomaly["severity"] == "medium":
                score -= 10
            else:
                score -= 5
        
        # Ensure score is in valid range
        return max(0.0, min(100.0, score))
    
    def summarize_all_logs(self, minutes: int = 30) -> Dict[str, Any]:
        """Summarize logs across all services."""
        all_analyses = {}
        overall_health = 100.0
        total_errors = 0
        total_requests = 0
        all_anomalies = []
        
        # Analyze each service
        for service in self.config.services:
            analysis = self.analyze_logs(service.name, service.user, minutes)
            all_analyses[service.name] = analysis
            
            if analysis["status"] == "analyzed":
                overall_health = min(overall_health, analysis["health_score"])
                total_errors += sum(analysis["patterns"]["error_counts"].values())
                total_requests += analysis["patterns"]["request_count"]
                
                for anomaly in analysis["anomalies"]:
                    anomaly["service"] = service.name
                    all_anomalies.append(anomaly)
        
        # Sort anomalies by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_anomalies.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return {
            "time_window_minutes": minutes,
            "services_analyzed": len(all_analyses),
            "overall_health_score": overall_health,
            "total_errors": total_errors,
            "total_requests": total_requests,
            "top_anomalies": all_anomalies[:10],
            "service_details": all_analyses
        }