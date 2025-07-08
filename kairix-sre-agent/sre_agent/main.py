"""Main SRE Agent orchestrator."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import structlog
from openai import AsyncOpenAI

from .config import get_default_config, Config
from .health.checker import HealthChecker
from .health.tools import get_all_functions
from .recovery.actions import RecoveryActions
from .memory.store import MemoryStore, RunRecord, ServiceEvent
from .logs.analyzer import LogAnalyzer
from .chat.repl import start_chat_repl

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
console = Console()
app = typer.Typer()


class SREAgent:
    """Main SRE Agent class."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.memory = MemoryStore(config.memory_db_path)
        self.health_checker = None
        self.recovery_actions = RecoveryActions(config)
        self.log_analyzer = LogAnalyzer(config)
    
    async def __aenter__(self):
        self.health_checker = await HealthChecker(self.config).__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.health_checker:
            await self.health_checker.__aexit__(exc_type, exc_val, exc_tb)
        self.memory.close()
    
    def _get_system_prompt(self) -> str:
        """Generate system prompt with context."""
        # Get recent history
        recent_runs = self.memory.get_recent_runs(hours=24)
        health_summary = self.memory.get_service_health_summary(hours=24)
        
        context = f"""You are an SRE (Site Reliability Engineering) agent monitoring Kairix infrastructure.
        
Current time: {datetime.utcnow().isoformat()}

Recent History (last 24h):
- Total runs: {len(recent_runs)}
- Service health summary: {json.dumps(health_summary, indent=2)}

Your responsibilities:
1. Check health of all configured services
2. Analyze logs for errors and anomalies
3. Attempt basic recovery actions when issues are found
4. Escalate if unable to fix after one attempt
5. Maintain detailed logs of all actions

Guidelines:
- Be thorough but efficient in checking services
- Prioritize user-facing services (UI, API)
- Only attempt non-destructive recovery actions
- Always log actions before attempting them
- Escalate promptly if recovery fails

Available services to monitor:
{json.dumps([s.name for s in self.config.services], indent=2)}
"""
        return context
    
    async def _execute_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call from OpenAI."""
        logger.info("Executing function", function=function_name, args=arguments)
        
        # Route to appropriate handler
        if function_name in ["check_service_health", "check_process_status", 
                           "get_port_listeners", "analyze_service_logs"]:
            return await self.health_checker.execute_function(function_name, arguments)
        elif function_name in ["restart_service", "clear_cache", "send_alert"]:
            return await self.recovery_actions.execute_function(function_name, arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run a complete health check cycle."""
        run_start = datetime.utcnow()
        run = RunRecord(
            timestamp=run_start.isoformat(),
            run_type="scheduled",
            status="running"
        )
        run_id = self.memory.add_run(run)
        
        try:
            # Create initial prompt
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": """Please perform a comprehensive health check of all services. 
                    For each service:
                    1. Check if it's running and responding
                    2. Analyze recent logs for errors
                    3. If issues are found, attempt recovery
                    4. Report the final status
                    
                    Start with checking all configured services."""
                }
            ]
            
            # Track results
            all_results = {
                "services": {},
                "issues": [],
                "recoveries": [],
                "summary": ""
            }
            
            # Run conversation with function calls
            while True:
                response = await self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=messages,
                    functions=get_all_functions(),
                    function_call="auto",
                    temperature=0.1
                )
                
                message = response.choices[0].message
                messages.append(message.model_dump())
                
                # Handle function calls
                if message.function_call:
                    function_name = message.function_call.name
                    arguments = json.loads(message.function_call.arguments)
                    
                    # Execute function
                    result = await self._execute_function_call(function_name, arguments)
                    
                    # Track results
                    if function_name == "check_service_health":
                        service_name = arguments["service_name"]
                        all_results["services"][service_name] = result
                        
                        # Record event if issue found
                        if result["status"] != "healthy":
                            all_results["issues"].append(service_name)
                            event = ServiceEvent(
                                timestamp=datetime.utcnow().isoformat(),
                                service_name=service_name,
                                event_type=result["status"],
                                details=result
                            )
                            self.memory.add_event(event)
                    
                    elif function_name == "restart_service":
                        all_results["recoveries"].append(result)
                        
                        # Update event with recovery info
                        event = ServiceEvent(
                            timestamp=datetime.utcnow().isoformat(),
                            service_name=arguments["service_name"],
                            event_type="recovery_attempt",
                            details=result,
                            recovery_attempted=True,
                            recovery_successful=result.get("success", False)
                        )
                        self.memory.add_event(event)
                    
                    # Add function result to messages
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(result)
                    })
                
                # Check if we have a final response
                elif message.content and "health check complete" in message.content.lower():
                    all_results["summary"] = message.content
                    break
                
                # Safety limit
                if len(messages) > 50:
                    logger.warning("Conversation limit reached")
                    break
            
            # Calculate final stats
            duration = (datetime.utcnow() - run_start).total_seconds()
            
            # Update run record
            self.memory.update_run(
                run_id,
                status="completed",
                services_checked=len(all_results["services"]),
                issues_found=len(all_results["issues"]),
                fixes_attempted=len(all_results["recoveries"]),
                fixes_successful=sum(1 for r in all_results["recoveries"] if r.get("success")),
                summary=all_results["summary"],
                full_report=all_results,
                duration_seconds=duration
            )
            
            return all_results
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            self.memory.update_run(
                run_id,
                status="failed",
                summary=f"Error: {str(e)}",
                duration_seconds=(datetime.utcnow() - run_start).total_seconds()
            )
            raise
    
    def display_report(self, results: Dict[str, Any]):
        """Display results in a nice format."""
        # Create services table
        table = Table(title="Service Health Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Port")
        table.add_column("Response Time")
        table.add_column("Notes")
        
        for service_name, status in results["services"].items():
            status_style = "green" if status["status"] == "healthy" else "red"
            response_time = f"{status.get('response_time_ms', 0):.1f}ms" if status.get('response_time_ms') else "N/A"
            
            table.add_row(
                service_name,
                f"[{status_style}]{status['status']}[/{status_style}]",
                str(status.get("port", "N/A")),
                response_time,
                status.get("error", "")
            )
        
        console.print(table)
        
        # Show issues and recoveries
        if results["issues"]:
            console.print(Panel(f"[red]Issues found:[/red] {', '.join(results['issues'])}", 
                              title="⚠️  Issues"))
        
        if results["recoveries"]:
            recovery_summary = []
            for r in results["recoveries"]:
                status = "✅" if r.get("success") else "❌"
                recovery_summary.append(f"{status} {r['service']}")
            
            console.print(Panel("\n".join(recovery_summary), title="🔧 Recovery Attempts"))
        
        # Show summary
        if results.get("summary"):
            console.print(Panel(results["summary"], title="📝 Summary"))


@app.command()
def run(
    config_file: Optional[str] = typer.Option(None, "--config", "-c", 
                                             help="Path to configuration file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", 
                                help="Enable verbose logging")
):
    """Run a health check cycle."""
    if verbose:
        structlog.configure(
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    config = get_default_config()
    
    async def _run():
        async with SREAgent(config) as agent:
            console.print("[bold blue]🤖 Starting SRE Agent health check...[/bold blue]")
            results = await agent.run_health_check()
            agent.display_report(results)
    
    asyncio.run(_run())


@app.command()
def shell(
    config_file: Optional[str] = typer.Option(None, "--config", "-c",
                                             help="Path to configuration file")
):
    """Start interactive chat shell."""
    config = get_default_config()
    
    console.print("[bold blue]🤖 Starting SRE Agent interactive shell...[/bold blue]")
    console.print("Type 'help' for available commands or 'exit' to quit.\n")
    
    asyncio.run(start_chat_repl(config))


@app.command()
def services():
    """Show all monitored services."""
    config = get_default_config()
    
    # Group services by user
    users = {}
    for service in config.services:
        if service.user not in users:
            users[service.user] = []
        users[service.user].append(service)
    
    # Create table
    table = Table(title=f"Monitored Services ({len(config.services)} total)")
    table.add_column("User", style="cyan")
    table.add_column("Service", style="green")
    table.add_column("Port")
    table.add_column("Health Endpoint")
    
    for user, services in sorted(users.items()):
        for i, service in enumerate(services):
            table.add_row(
                user if i == 0 else "",  # Only show user on first row
                service.name,
                str(service.port),
                service.health_endpoint
            )
    
    console.print(table)


@app.command()
def status(
    hours: int = typer.Option(24, "--hours", "-h", 
                             help="Number of hours to look back")
):
    """Show agent status and recent history."""
    config = get_default_config()
    memory = MemoryStore(config.memory_db_path)
    
    # Get recent runs
    runs = memory.get_recent_runs(hours=hours)
    
    # Create runs table
    table = Table(title=f"Recent Runs (last {hours} hours)")
    table.add_column("Time", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Services")
    table.add_column("Issues")
    table.add_column("Fixes")
    table.add_column("Duration")
    
    for run in runs[:10]:  # Show last 10
        status_style = "green" if run["status"] == "completed" else "red"
        table.add_row(
            run["timestamp"][:19],
            run["run_type"],
            f"[{status_style}]{run['status']}[/{status_style}]",
            str(run["services_checked"]),
            str(run["issues_found"]),
            f"{run['fixes_successful']}/{run['fixes_attempted']}",
            f"{run['duration_seconds']:.1f}s"
        )
    
    console.print(table)
    
    # Get health summary
    summary = memory.get_service_health_summary(hours=hours)
    
    # Show problematic services
    problem_services = [
        (name, stats) for name, stats in summary["services"].items()
        if stats["down_events"] > 0 or stats["unhealthy_events"] > 0
    ]
    
    if problem_services:
        console.print("\n[bold red]⚠️  Problematic Services:[/bold red]")
        for name, stats in problem_services:
            console.print(f"  • {name}: {stats['down_events']} down, "
                         f"{stats['unhealthy_events']} unhealthy events")
    
    # Show recovery stats
    recovery = summary["recovery"]
    if recovery["total_attempts"] > 0:
        success_rate = (recovery["successful"] / recovery["total_attempts"]) * 100
        console.print(f"\n[bold]🔧 Recovery Stats:[/bold] "
                     f"{recovery['successful']}/{recovery['total_attempts']} "
                     f"successful ({success_rate:.1f}%)")
    
    memory.close()


if __name__ == "__main__":
    app()