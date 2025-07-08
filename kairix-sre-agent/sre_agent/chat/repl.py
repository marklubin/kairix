"""Interactive REPL for SRE Agent chat interface."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from openai import AsyncOpenAI
import structlog

from ..config import Config
from ..health.checker import HealthChecker
from ..health.tools import get_all_functions
from ..recovery.actions import RecoveryActions
from ..memory.store import MemoryStore
from ..logs.analyzer import LogAnalyzer

logger = structlog.get_logger()
console = Console()


class ChatREPL:
    """Interactive chat interface for the SRE agent."""
    
    COMMANDS = {
        "/help": "Show available commands",
        "/status": "Show current system status",
        "/history": "Show recent agent runs",
        "/services": "List all monitored services",
        "/check": "Run a health check on all services",
        "/check <service>": "Run a health check on specific service",
        "/logs": "Analyze recent logs",
        "/logs <service>": "Analyze logs for specific service",
        "/clear": "Clear the screen",
        "/exit": "Exit the chat interface"
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.memory = MemoryStore(config.memory_db_path)
        self.health_checker = None
        self.recovery_actions = RecoveryActions(config)
        self.log_analyzer = LogAnalyzer(config)
        self.session = PromptSession(
            history=FileHistory(str(config.memory_db_path.parent / "chat_history.txt")),
            auto_suggest=AutoSuggestFromHistory(),
            completer=WordCompleter(list(self.COMMANDS.keys()) + 
                                  [s.name for s in config.services])
        )
        self.messages = []
    
    async def __aenter__(self):
        self.health_checker = await HealthChecker(self.config).__aenter__()
        self._load_context()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.health_checker:
            await self.health_checker.__aexit__(exc_type, exc_val, exc_tb)
    
    def _load_context(self):
        """Load initial context from memory."""
        # Get recent history
        recent_runs = self.memory.get_recent_runs(hours=24)
        health_summary = self.memory.get_service_health_summary(hours=24)
        
        # Load previous chat history
        chat_history = self.memory.get_chat_history(limit=20)
        
        # Build system message
        system_message = f"""You are an interactive SRE assistant for Kairix infrastructure.
        
Current time: {datetime.utcnow().isoformat()}

Recent System Status (24h):
- Total runs: {len(recent_runs)}
- Last run: {recent_runs[0]['timestamp'] if recent_runs else 'Never'}
- Service health: {json.dumps(health_summary, indent=2)}

You can:
1. Answer questions about the system state
2. Perform health checks on services
3. Analyze logs and identify issues
4. Suggest and execute recovery actions
5. Provide insights from historical data

Available services: {[s.name for s in self.config.services]}

Be conversational but concise. Use the available functions to gather real-time data when needed."""
        
        self.messages = [{"role": "system", "content": system_message}]
        
        # Add recent chat history
        for msg in chat_history[-10:]:  # Last 10 messages
            self.messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    async def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call."""
        if function_name in ["check_service_health", "check_process_status", 
                           "get_port_listeners", "analyze_service_logs"]:
            return await self.health_checker.execute_function(function_name, arguments)
        elif function_name in ["restart_service", "clear_cache", "send_alert"]:
            return await self.recovery_actions.execute_function(function_name, arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")
    
    async def _handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if handled."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/help":
            table = Table(title="Available Commands")
            table.add_column("Command", style="cyan")
            table.add_column("Description")
            
            for cmd, desc in self.COMMANDS.items():
                table.add_row(cmd, desc)
            
            console.print(table)
            return True
        
        elif cmd == "/status":
            # Show system status
            summary = self.memory.get_service_health_summary(hours=1)
            recent_runs = self.memory.get_recent_runs(hours=1)
            
            console.print(Panel(f"""
[bold]System Status[/bold]
Last check: {recent_runs[0]['timestamp'] if recent_runs else 'Never'}
Services monitored: {len(self.config.services)}
Recent issues: {sum(s['down_events'] + s['unhealthy_events'] for s in summary['services'].values())}
Recovery success rate: {summary['recovery']['successful']}/{summary['recovery']['total_attempts']}
""", title="📊 Current Status"))
            return True
        
        elif cmd == "/history":
            # Show recent runs
            runs = self.memory.get_recent_runs(hours=24)
            
            table = Table(title="Recent Agent Runs (24h)")
            table.add_column("Time", style="cyan")
            table.add_column("Status")
            table.add_column("Issues")
            table.add_column("Fixes")
            
            for run in runs[:10]:
                status_style = "green" if run["status"] == "completed" else "red"
                table.add_row(
                    run["timestamp"][:19],
                    f"[{status_style}]{run['status']}[/{status_style}]",
                    str(run["issues_found"]),
                    f"{run['fixes_successful']}/{run['fixes_attempted']}"
                )
            
            console.print(table)
            return True
        
        elif cmd == "/services":
            # List services
            table = Table(title="Monitored Services")
            table.add_column("Service", style="cyan")
            table.add_column("Port")
            table.add_column("User")
            table.add_column("Health Endpoint")
            
            for service in self.config.services:
                table.add_row(
                    service.name,
                    str(service.port),
                    service.user or "N/A",
                    service.health_endpoint
                )
            
            console.print(table)
            return True
        
        elif cmd == "/check":
            # Run health check
            if len(parts) > 1:
                # Check specific service
                service_name = parts[1]
                console.print(f"🔍 Checking {service_name}...")
                return False  # Let the AI handle it
            else:
                console.print("🔍 Running full health check...")
                return False  # Let the AI handle it
        
        elif cmd == "/logs":
            # Analyze logs
            if len(parts) > 1:
                service_name = parts[1]
                console.print(f"📄 Analyzing logs for {service_name}...")
            else:
                console.print("📄 Analyzing all service logs...")
            return False  # Let the AI handle it
        
        elif cmd == "/clear":
            console.clear()
            return True
        
        elif cmd == "/exit":
            console.print("👋 Goodbye!")
            raise KeyboardInterrupt
        
        return False
    
    async def chat_loop(self):
        """Main chat loop."""
        console.print(Panel("Welcome to the SRE Agent Chat Interface!\n"
                          "Type '/help' for commands or ask me anything about the system.",
                          title="🤖 SRE Agent"))
        
        while True:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.session.prompt,
                    "You> "
                )
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                if user_input.startswith("/"):
                    if await self._handle_command(user_input):
                        continue
                
                # Add user message
                self.messages.append({"role": "user", "content": user_input})
                self.memory.add_chat_message("user", user_input)
                
                # Get AI response
                console.print("[dim]Thinking...[/dim]")
                
                response = await self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=self.messages,
                    functions=get_all_functions(),
                    function_call="auto",
                    temperature=0.7
                )
                
                message = response.choices[0].message
                
                # Handle function calls
                function_results = []
                while message.function_call:
                    function_name = message.function_call.name
                    arguments = json.loads(message.function_call.arguments)
                    
                    console.print(f"[dim]Executing: {function_name}...[/dim]")
                    
                    # Execute function
                    result = await self._execute_function(function_name, arguments)
                    function_results.append({
                        "function": function_name,
                        "result": result
                    })
                    
                    # Add to messages
                    self.messages.append(message.model_dump())
                    self.messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(result)
                    })
                    
                    # Get next response
                    response = await self.client.chat.completions.create(
                        model=self.config.openai_model,
                        messages=self.messages,
                        functions=get_all_functions(),
                        function_call="auto",
                        temperature=0.7
                    )
                    
                    message = response.choices[0].message
                
                # Display final response
                if message.content:
                    self.messages.append(message.model_dump())
                    self.memory.add_chat_message("assistant", message.content, function_results)
                    
                    console.print()
                    console.print(Markdown(message.content))
                    console.print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                logger.error("Chat error", error=str(e))


async def start_chat_repl(config: Config):
    """Start the chat REPL."""
    async with ChatREPL(config) as repl:
        await repl.chat_loop()