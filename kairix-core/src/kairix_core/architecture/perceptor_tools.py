"""
Perceptor-based Tool Configuration Architecture
==============================================

This module defines a unified architecture for tool and MCP configuration
that leverages perceptors as the fundamental abstraction for both
external tools and internal cognitive capabilities.

Key Concepts:
- Tools are specialized perceptors that interact with external systems
- MCP servers become perceptor providers
- Self-modification through versioned code perceptors
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Type, Union
import inspect
import importlib.util
import hashlib
import json
from pathlib import Path
from datetime import datetime

from kairix_core.types.cognition import Perception, Stimulus, StimulusType
from kairix_core.cognition.perceptor import Perceptor


class ToolCapability(Enum):
    """Defines what a tool can do"""
    READ = auto()          # Can read/observe
    WRITE = auto()         # Can modify external state
    EXECUTE = auto()       # Can run code/commands
    COMMUNICATE = auto()   # Can send/receive messages
    REFLECT = auto()       # Can introspect/modify self


@dataclass
class ToolSchema:
    """Dynamic schema for tool parameters"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    capabilities: List[ToolCapability]
    version: str = "1.0.0"

    def validate(self, params: Dict[str, Any]) -> bool:
        """Validate parameters against schema"""
        # TODO: Implement JSON schema validation
        return True


@dataclass
class ToolRegistration:
    """Registration metadata for a tool perceptor"""
    name: str
    schema: ToolSchema
    perceptor_class: Type['ToolPerceptor']
    mcp_server: Optional[str] = None
    auto_discover: bool = True
    security_level: int = 0  # 0=safe, 1=needs confirmation, 2=dangerous


class ToolPerceptor(Perceptor):
    """
    Base class for tool perceptors that bridge external capabilities
    into the cognitive architecture
    """

    def __init__(self, registration: ToolRegistration):
        self.registration = registration
        self.execution_history: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute_tool(self, params: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters"""
        pass

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """
        Process tool execution requests as stimuli
        """
        if stimulus.type != StimulusType.execution_attempt:
            return []

        try:
            # Parse tool invocation from stimulus
            invocation = json.loads(stimulus.content)
            if invocation.get("tool") != self.registration.name:
                return []

            # Validate parameters
            params = invocation.get("parameters", {})
            if not self.registration.schema.validate(params):
                return [Perception(
                    source=f"tool_{self.registration.name}",
                    content=f"Invalid parameters for tool {self.registration.name}",
                    confidence=0.0
                )]

            # Execute tool
            result = await self.execute_tool(params)

            # Record execution
            self.execution_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "params": params,
                "result": result
            })

            return [Perception(
                source=f"tool_{self.registration.name}",
                content=json.dumps(result),
                confidence=1.0
            )]

        except Exception as e:
            return [Perception(
                source=f"tool_{self.registration.name}",
                content=f"Tool execution error: {str(e)}",
                confidence=0.0
            )]


class MCPToolPerceptor(ToolPerceptor):
    """
    Tool perceptor that connects to MCP servers
    """

    def __init__(self, registration: ToolRegistration, mcp_client: Any):
        super().__init__(registration)
        self.mcp_client = mcp_client

    async def execute_tool(self, params: Dict[str, Any]) -> Any:
        """Execute tool via MCP protocol"""
        return await self.mcp_client.call_tool(
            self.registration.name,
            params
        )


class DynamicToolRegistry:
    """
    Registry for dynamically discovering and managing tool perceptors
    """

    def __init__(self, base_path: Path = Path("~/.kairix/tools")):
        self.base_path = base_path.expanduser()
        self.tools: Dict[str, ToolRegistration] = {}
        self.perceptors: Dict[str, ToolPerceptor] = {}
        self.base_path.mkdir(parents=True, exist_ok=True)

    def register_tool(self, registration: ToolRegistration) -> None:
        """Register a new tool"""
        self.tools[registration.name] = registration

    def discover_tools(self) -> None:
        """Auto-discover tools from filesystem"""
        tool_files = self.base_path.glob("*.tool.json")
        for tool_file in tool_files:
            try:
                with open(tool_file) as f:
                    tool_def = json.load(f)

                # Dynamically create tool perceptor class
                if "python_code" in tool_def:
                    perceptor_class = self._create_dynamic_perceptor(
                        tool_def["name"],
                        tool_def["python_code"]
                    )
                else:
                    perceptor_class = ToolPerceptor

                registration = ToolRegistration(
                    name=tool_def["name"],
                    schema=ToolSchema(**tool_def["schema"]),
                    perceptor_class=perceptor_class,
                    mcp_server=tool_def.get("mcp_server"),
                    auto_discover=tool_def.get("auto_discover", True),
                    security_level=tool_def.get("security_level", 0)
                )

                self.register_tool(registration)

            except Exception as e:
                print(f"Failed to load tool from {tool_file}: {e}")

    def _create_dynamic_perceptor(self, name: str, code: str) -> Type[ToolPerceptor]:
        """
        Dynamically create a perceptor class from code
        """
        # Create a unique module name
        module_name = f"dynamic_tool_{name}_{hashlib.md5(code.encode()).hexdigest()}"

        # Create module from code
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)

        # Execute code in module namespace
        exec(code, module.__dict__)

        # Find and return the perceptor class
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (inspect.isclass(item) and
                issubclass(item, ToolPerceptor) and
                item != ToolPerceptor):
                return item

        raise ValueError(f"No ToolPerceptor subclass found in code for {name}")

    def instantiate_perceptor(self, tool_name: str, **kwargs) -> ToolPerceptor:
        """Create an instance of a tool perceptor"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        registration = self.tools[tool_name]

        if registration.mcp_server:
            # Create MCP client and perceptor
            # TODO: Implement MCP client creation
            mcp_client = None  # Placeholder
            return MCPToolPerceptor(registration, mcp_client)
        else:
            return registration.perceptor_class(registration)


@dataclass
class PerceptorConfiguration:
    """
    Unified configuration for all perceptors and tools
    """
    perceptors: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)

    # Self-modification settings
    allow_self_modification: bool = False
    modification_security_level: int = 2  # Require explicit approval
    code_sandbox: bool = True  # Run modified code in sandbox first
    version_control: bool = True  # Track all modifications

    @classmethod
    def from_yaml(cls, path: Path) -> 'PerceptorConfiguration':
        """Load configuration from YAML file"""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file"""
        import yaml
        with open(path, 'w') as f:
            yaml.dump(self.__dict__, f)


class SelfModifyingPerceptor(Perceptor):
    """
    A perceptor that can safely modify its own code and behavior
    """

    def __init__(self, code_path: Path, version_control: bool = True):
        self.code_path = code_path
        self.version_control = version_control
        self.versions: List[Dict[str, Any]] = []
        self.current_version = 0

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """Process self-modification requests"""
        if stimulus.type != StimulusType.self_perception:
            return []

        try:
            modification = json.loads(stimulus.content)

            if modification.get("type") == "code_modification":
                result = await self.modify_code(
                    modification["code"],
                    modification.get("reason", "No reason provided")
                )

                return [Perception(
                    source="self_modification",
                    content=json.dumps(result),
                    confidence=0.8 if result["success"] else 0.2
                )]

        except Exception as e:
            return [Perception(
                source="self_modification",
                content=f"Self-modification failed: {str(e)}",
                confidence=0.0
            )]

    async def modify_code(self, new_code: str, reason: str) -> Dict[str, Any]:
        """
        Safely modify own code with versioning and validation
        """
        # Save current version
        if self.version_control:
            with open(self.code_path) as f:
                current_code = f.read()

            self.versions.append({
                "version": self.current_version,
                "timestamp": datetime.utcnow().isoformat(),
                "code": current_code,
                "reason": reason,
                "code_hash": hashlib.sha256(current_code.encode()).hexdigest()
            })

        # Validate new code
        validation_result = await self._validate_code(new_code)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "version": self.current_version
            }

        # Test in sandbox
        if hasattr(self, 'sandbox'):
            test_result = await self._test_in_sandbox(new_code)
            if not test_result["success"]:
                return {
                    "success": False,
                    "error": f"Sandbox test failed: {test_result['error']}",
                    "version": self.current_version
                }

        # Apply modification
        with open(self.code_path, 'w') as f:
            f.write(new_code)

        self.current_version += 1

        # Reload self
        await self._reload()

        return {
            "success": True,
            "version": self.current_version,
            "previous_version": self.current_version - 1,
            "reason": reason
        }

    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code for safety and correctness"""
        try:
            # Check syntax
            compile(code, '<string>', 'exec')

            # Check for dangerous operations
            dangerous_patterns = [
                'exec(', 'eval(', '__import__',
                'subprocess', 'os.system', 'open(',
                'requests.', 'urllib.'
            ]

            for pattern in dangerous_patterns:
                if pattern in code:
                    return {
                        "valid": False,
                        "error": f"Dangerous pattern detected: {pattern}"
                    }

            return {"valid": True}

        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"Syntax error: {str(e)}"
            }

    async def _test_in_sandbox(self, code: str) -> Dict[str, Any]:
        """Test code in isolated sandbox environment"""
        # TODO: Implement proper sandboxing (Docker, pypy-sandbox, etc.)
        return {"success": True}

    async def _reload(self) -> None:
        """Reload self with new code"""
        # TODO: Implement hot-reload mechanism
        pass

    def rollback(self, version: int) -> bool:
        """Rollback to a previous version"""
        if version >= self.current_version or version < 0:
            return False

        if version >= len(self.versions):
            return False

        previous = self.versions[version]
        with open(self.code_path, 'w') as f:
            f.write(previous["code"])

        self.current_version = version
        return True


# Example tool definition file (would be in ~/.kairix/tools/example.tool.json)
EXAMPLE_TOOL_DEFINITION = {
    "name": "web_search",
    "schema": {
        "name": "web_search",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        },
        "capabilities": ["READ", "COMMUNICATE"]
    },
    "python_code": '''
class WebSearchPerceptor(ToolPerceptor):
    async def execute_tool(self, params):
        query = params["query"]
        max_results = params.get("max_results", 5)

        # Simulated web search
        results = [
            {"title": f"Result {i}", "url": f"https://example.com/{i}"}
            for i in range(max_results)
        ]

        return {"query": query, "results": results}
    ''',
    "security_level": 0,
    "auto_discover": True
}