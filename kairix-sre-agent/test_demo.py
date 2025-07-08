#!/usr/bin/env python3
"""Demo script to test SRE agent functionality without OpenAI."""

import asyncio
from datetime import datetime
from sre_agent.config import get_default_config
from sre_agent.health.checker import HealthChecker
from sre_agent.logs.analyzer import LogAnalyzer
from sre_agent.memory.store import MemoryStore, RunRecord, ServiceEvent
from sre_agent.recovery.actions import RecoveryActions
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def demo_run():
    """Run a demo of the SRE agent functionality."""
    config = get_default_config()
    memory = MemoryStore(config.memory_db_path)
    log_analyzer = LogAnalyzer(config)
    recovery = RecoveryActions(config)
    
    console.print(Panel("🤖 SRE Agent Demo - Testing Core Functionality", style="bold blue"))
    
    # Start a run
    run = RunRecord(
        timestamp=datetime.utcnow().isoformat(),
        run_type="demo",
        status="running"
    )
    run_id = memory.add_run(run)
    
    async with HealthChecker(config) as checker:
        # 1. Health Checks
        console.print("\n[bold]1. Running Health Checks[/bold]")
        services_checked = 0
        issues_found = 0
        
        # Check some example services
        test_services = [
            ("test_ui", 6000, "/"),
            ("test_api", 7000, "/api/status"),
            ("test_tools", 8000, "/health")
        ]
        
        table = Table(title="Service Health Status")
        table.add_column("Service", style="cyan")
        table.add_column("Port")
        table.add_column("Status")
        table.add_column("Response Time")
        
        for name, port, endpoint in test_services:
            result = await checker.check_service_health(name, port, endpoint)
            services_checked += 1
            
            if result["status"] != "healthy":
                issues_found += 1
                # Record the issue
                event = ServiceEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    service_name=name,
                    event_type=result["status"],
                    details=result
                )
                memory.add_event(event)
            
            status_color = "green" if result["status"] == "healthy" else "red"
            response_time = f"{result.get('response_time_ms', 0):.1f}ms" if result.get('response_time_ms') else "N/A"
            
            table.add_row(
                name,
                str(port),
                f"[{status_color}]{result['status']}[/{status_color}]",
                response_time
            )
        
        console.print(table)
        
        # 2. Process Checks
        console.print("\n[bold]2. Checking Running Processes[/bold]")
        processes = ["python", "node", "java"]
        for proc_name in processes:
            result = checker.check_process_status(proc_name)
            if result["found"]:
                console.print(f"✅ {proc_name}: {result['count']} instances running")
            else:
                console.print(f"❌ {proc_name}: No instances found")
        
        # 3. Log Analysis
        console.print("\n[bold]3. Analyzing Logs[/bold]")
        log_result = log_analyzer.analyze_logs("mark_api", user="mark", minutes=30)
        
        if log_result["status"] == "analyzed":
            console.print(f"📊 Health Score: {log_result['health_score']:.1f}/100")
            console.print(f"📝 Lines Analyzed: {log_result['total_lines']}")
            console.print(f"❌ Errors Found: {sum(log_result['patterns']['error_counts'].values())}")
            console.print(f"👥 Active Users: {log_result['user_activity']['unique_users']}")
            
            if log_result["anomalies"]:
                console.print("\n⚠️  Anomalies Detected:")
                for anomaly in log_result["anomalies"][:3]:
                    console.print(f"   - {anomaly['type']}: {anomaly['details']}")
        
        # 4. Recovery Actions (simulated)
        console.print("\n[bold]4. Recovery Actions[/bold]")
        if issues_found > 0:
            console.print("🔧 Attempting recovery actions...")
            
            # Simulate alert
            alert_result = await recovery.send_alert(
                severity="warning",
                message=f"Demo run found {issues_found} issues with services",
                attempted_fixes=["Service health check", "Log analysis"]
            )
            console.print(f"📢 Alert sent: {alert_result['alert_sent']}")
        
        # 5. Summary
        console.print("\n[bold]5. Run Summary[/bold]")
        
        # Update run record
        memory.update_run(
            run_id,
            status="completed",
            services_checked=services_checked,
            issues_found=issues_found,
            fixes_attempted=0,
            fixes_successful=0,
            summary=f"Demo run completed. Checked {services_checked} services, found {issues_found} issues.",
            duration_seconds=5.0
        )
        
        # Get system health summary
        health_summary = memory.get_service_health_summary(hours=1)
        
        summary_panel = Panel(f"""
[bold green]Demo Run Complete![/bold green]

Services Checked: {services_checked}
Issues Found: {issues_found}
Log Health Score: {log_result.get('health_score', 0):.1f}/100

Recent Activity (1h):
- Total Events: {sum(s['total_events'] for s in health_summary['services'].values())}
- Recovery Attempts: {health_summary['recovery']['total_attempts']}
""", title="📊 Summary")
        
        console.print(summary_panel)
    
    memory.close()

if __name__ == "__main__":
    console.print("Starting SRE Agent Demo...")
    asyncio.run(demo_run())