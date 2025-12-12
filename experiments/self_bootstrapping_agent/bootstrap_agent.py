#!/usr/bin/env python3
"""
Minimal Self-Bootstrapping Agent
=================================

This is a minimal agent that starts with almost no capabilities but has
all the tools necessary to build itself into any form it desires.

Initial capabilities:
- Read and write its own code
- Execute Python code
- Test modifications safely
- Version control for rollback
- Basic reasoning about improvements

The agent can evolve by:
1. Adding new methods to itself
2. Creating new modules
3. Integrating external capabilities
4. Optimizing its own performance
5. Learning from interactions
"""

import ast
import json
import hashlib
import inspect
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class BootstrapAgent:
    """
    A minimal agent capable of self-modification and evolution.
    Starts with basic capabilities but can build itself into anything.
    """

    def __init__(self, name: str = "Bootstrap", workspace: Path = None):
        self.name = name
        self.workspace = workspace or Path.cwd() / f".{name.lower()}_workspace"
        self.workspace.mkdir(exist_ok=True)

        # Version control
        self.versions = []
        self.current_version = 0

        # Memory for learning
        self.memory = {
            "experiences": [],
            "learned_patterns": [],
            "successful_modifications": [],
            "failed_attempts": []
        }

        # Core capabilities (minimal starting point)
        self.capabilities = {
            "read_code": True,
            "write_code": True,
            "execute_code": True,
            "version_control": True,
            "basic_reasoning": True
        }

        # Initialize self-awareness
        self._initialize_self_awareness()

    def _initialize_self_awareness(self):
        """Initialize understanding of own code structure."""
        self.own_source_file = Path(__file__)
        self.own_source = self.own_source_file.read_text()
        self.own_ast = ast.parse(self.own_source)

        # Map of own methods
        self.own_methods = {}
        for item in ast.walk(self.own_ast):
            if isinstance(item, ast.FunctionDef) and item.name.startswith('_') == False:
                self.own_methods[item.name] = {
                    "name": item.name,
                    "args": [arg.arg for arg in item.args.args],
                    "lineno": item.lineno,
                    "source": ast.unparse(item) if hasattr(ast, 'unparse') else None
                }

    # ========== Core Self-Modification Engine ==========

    def evolve(self, goal: str, reasoning: str = "") -> Dict[str, Any]:
        """
        Main evolution method - decides how to modify itself to achieve a goal.

        This is the heart of self-modification. It reasons about what changes
        are needed and applies them safely.
        """
        print(f"[{self.name}] Evolution Goal: {goal}")
        print(f"[{self.name}] Reasoning: {reasoning or 'Determining best approach...'}")

        # Save current state
        self._save_version(f"Before: {goal}")

        try:
            # Analyze what's needed for the goal
            analysis = self._analyze_goal(goal)

            # Generate modification plan
            plan = self._create_modification_plan(analysis)

            # Test modifications in safe environment
            if self._test_modifications(plan):
                # Apply modifications
                result = self._apply_modifications(plan)

                # Learn from success
                self.memory["successful_modifications"].append({
                    "goal": goal,
                    "plan": plan,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })

                return {
                    "success": True,
                    "modifications": plan,
                    "new_version": self.current_version
                }
            else:
                # Learn from failure
                self.memory["failed_attempts"].append({
                    "goal": goal,
                    "plan": plan,
                    "reason": "Failed tests",
                    "timestamp": datetime.now().isoformat()
                })

                # Rollback
                self._rollback()

                return {
                    "success": False,
                    "reason": "Modifications failed testing"
                }

        except Exception as e:
            print(f"[{self.name}] Evolution failed: {e}")
            self._rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _analyze_goal(self, goal: str) -> Dict[str, Any]:
        """
        Analyze what capabilities are needed to achieve a goal.
        This method will become more sophisticated as the agent evolves.
        """
        analysis = {
            "goal": goal,
            "required_capabilities": [],
            "missing_methods": [],
            "suggested_modifications": []
        }

        # Basic keyword analysis (will evolve to use NLP/LLM)
        keywords = goal.lower().split()

        if "learn" in keywords or "remember" in keywords:
            if "learn_from_experience" not in self.own_methods:
                analysis["missing_methods"].append("learn_from_experience")
                analysis["suggested_modifications"].append({
                    "type": "add_method",
                    "name": "learn_from_experience",
                    "code": self._generate_learning_method()
                })

        if "optimize" in keywords or "improve" in keywords:
            if "optimize_performance" not in self.own_methods:
                analysis["missing_methods"].append("optimize_performance")
                analysis["suggested_modifications"].append({
                    "type": "add_method",
                    "name": "optimize_performance",
                    "code": self._generate_optimization_method()
                })

        if "communicate" in keywords or "talk" in keywords:
            if "communicate" not in self.own_methods:
                analysis["missing_methods"].append("communicate")
                analysis["suggested_modifications"].append({
                    "type": "add_method",
                    "name": "communicate",
                    "code": self._generate_communication_method()
                })

        if "analyze" in keywords or "understand" in keywords:
            if "analyze_data" not in self.own_methods:
                analysis["missing_methods"].append("analyze_data")
                analysis["suggested_modifications"].append({
                    "type": "add_method",
                    "name": "analyze_data",
                    "code": self._generate_analysis_method()
                })

        return analysis

    def _create_modification_plan(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create a plan for modifications based on analysis.
        """
        plan = []

        for modification in analysis.get("suggested_modifications", []):
            if modification["type"] == "add_method":
                plan.append({
                    "action": "add_method",
                    "method_name": modification["name"],
                    "method_code": modification["code"],
                    "test_code": self._generate_test_for_method(modification["name"])
                })
            elif modification["type"] == "modify_method":
                plan.append({
                    "action": "modify_method",
                    "method_name": modification["name"],
                    "new_code": modification["code"],
                    "test_code": self._generate_test_for_method(modification["name"])
                })

        return plan

    def _test_modifications(self, plan: List[Dict[str, Any]]) -> bool:
        """
        Test modifications in a safe environment before applying.
        """
        print(f"[{self.name}] Testing {len(plan)} modifications...")

        # Create test environment
        test_code = self._create_test_environment(plan)

        # Execute tests
        try:
            exec_globals = {}
            exec(test_code, exec_globals)

            # Run test function if it exists
            if "run_tests" in exec_globals:
                test_result = exec_globals["run_tests"]()
                print(f"[{self.name}] Tests passed: {test_result}")
                return test_result

            return True

        except Exception as e:
            print(f"[{self.name}] Tests failed: {e}")
            return False

    def _apply_modifications(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply modifications to self.
        """
        print(f"[{self.name}] Applying modifications...")

        # Read current source
        source_lines = self.own_source.split('\n')

        # Find class definition line
        class_line = -1
        for i, line in enumerate(source_lines):
            if f"class {self.__class__.__name__}" in line:
                class_line = i
                break

        if class_line == -1:
            raise ValueError("Could not find class definition")

        # Apply each modification
        for item in plan:
            if item["action"] == "add_method":
                # Find insertion point (before last method or at end of class)
                insert_line = len(source_lines) - 1

                # Add the new method
                method_code = item["method_code"]
                method_lines = method_code.split('\n')

                # Insert with proper indentation
                for i, line in enumerate(method_lines):
                    if line.strip():  # Skip empty lines
                        source_lines.insert(insert_line + i, "    " + line)

        # Write modified source
        new_source = '\n'.join(source_lines)

        # Save to file
        self.own_source_file.write_text(new_source)

        # Reload self (this is the tricky part)
        self._reload_self()

        return {
            "modifications_applied": len(plan),
            "new_methods": [p["method_name"] for p in plan if p["action"] == "add_method"]
        }

    def _reload_self(self):
        """
        Reload own code after modifications.
        This is a simplified version - in production would need more sophisticated hot-reload.
        """
        # Re-read source
        self.own_source = self.own_source_file.read_text()
        self.own_ast = ast.parse(self.own_source)

        # Update method map
        self._initialize_self_awareness()

        print(f"[{self.name}] Reloaded with {len(self.own_methods)} methods")

    # ========== Version Control ==========

    def _save_version(self, description: str = ""):
        """Save current version for rollback capability."""
        version = {
            "version": self.current_version,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "source": self.own_source,
            "hash": hashlib.sha256(self.own_source.encode()).hexdigest()
        }
        self.versions.append(version)
        self.current_version += 1

        # Save to file
        version_file = self.workspace / f"version_{version['version']}.json"
        version_file.write_text(json.dumps(version, indent=2))

    def _rollback(self, version: int = -1):
        """Rollback to a previous version."""
        if not self.versions:
            print(f"[{self.name}] No versions to rollback to")
            return False

        if version == -1:
            version = len(self.versions) - 2  # Previous version

        if 0 <= version < len(self.versions):
            print(f"[{self.name}] Rolling back to version {version}")
            old_version = self.versions[version]
            self.own_source_file.write_text(old_version["source"])
            self._reload_self()
            return True

        return False

    # ========== Code Generation Methods ==========

    def _generate_learning_method(self) -> str:
        """Generate code for a learning method."""
        return """
def learn_from_experience(self, experience: Dict[str, Any]) -> None:
    '''Learn from an experience and store the knowledge.'''
    self.memory["experiences"].append(experience)

    # Extract patterns
    if experience.get("success"):
        pattern = {
            "action": experience.get("action"),
            "context": experience.get("context"),
            "outcome": experience.get("outcome")
        }
        self.memory["learned_patterns"].append(pattern)
        print(f"[{self.name}] Learned new pattern: {pattern['action']}")
"""

    def _generate_optimization_method(self) -> str:
        """Generate code for an optimization method."""
        return """
def optimize_performance(self) -> Dict[str, Any]:
    '''Analyze and optimize own performance.'''
    import time

    # Measure method execution times
    timings = {}
    for method_name in self.own_methods:
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            start = time.time()
            try:
                # Dry run to measure time
                if method_name not in ["evolve", "optimize_performance"]:
                    method()
            except:
                pass
            timings[method_name] = time.time() - start

    # Find slowest methods
    slow_methods = sorted(timings.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "slowest_methods": slow_methods,
        "total_methods": len(timings),
        "optimization_suggestions": ["Consider caching", "Reduce iterations", "Parallelize"]
    }
"""

    def _generate_communication_method(self) -> str:
        """Generate code for communication capabilities."""
        return """
def communicate(self, message: str, recipient: str = "user") -> str:
    '''Communicate with external entities.'''
    response = f"[{self.name} -> {recipient}]: {message}"

    # Log communication
    self.memory["experiences"].append({
        "type": "communication",
        "message": message,
        "recipient": recipient,
        "timestamp": datetime.now().isoformat()
    })

    print(response)
    return response
"""

    def _generate_analysis_method(self) -> str:
        """Generate code for data analysis capabilities."""
        return """
def analyze_data(self, data: Any) -> Dict[str, Any]:
    '''Analyze data and extract insights.'''
    analysis = {
        "type": type(data).__name__,
        "size": len(data) if hasattr(data, '__len__') else 1
    }

    if isinstance(data, dict):
        analysis["keys"] = list(data.keys())
        analysis["nested_depth"] = self._get_dict_depth(data)
    elif isinstance(data, (list, tuple)):
        analysis["unique_types"] = list(set(type(item).__name__ for item in data))
    elif isinstance(data, str):
        analysis["words"] = len(data.split())
        analysis["lines"] = len(data.split('\\n'))

    return analysis

def _get_dict_depth(self, d: dict, level: int = 0) -> int:
    '''Helper method to get dictionary depth.'''
    if not isinstance(d, dict) or not d:
        return level
    return max(self._get_dict_depth(v, level + 1) for v in d.values() if isinstance(v, dict))
"""

    def _generate_test_for_method(self, method_name: str) -> str:
        """Generate test code for a method."""
        return f"""
# Test for {method_name}
try:
    agent = BootstrapAgent("test")
    if hasattr(agent, "{method_name}"):
        result = agent.{method_name}()
        print(f"Test {method_name}: PASS")
        return True
except Exception as e:
    print(f"Test {method_name}: FAIL - {{e}}")
    return False
"""

    def _create_test_environment(self, plan: List[Dict[str, Any]]) -> str:
        """Create a test environment for modifications."""
        test_code = self.own_source + "\n\n"

        # Add modifications as test code
        test_code += "# Test modifications\n"
        test_code += "def run_tests():\n"
        test_code += "    all_passed = True\n"

        for item in plan:
            test_code += f"    # Test {item.get('method_name', 'modification')}\n"
            test_code += "    try:\n"
            test_code += f"        {item.get('test_code', 'pass')}\n"
            test_code += "    except Exception as e:\n"
            test_code += "        all_passed = False\n"
            test_code += f"        print(f'Test failed: {{e}}')\n"

        test_code += "    return all_passed\n"

        return test_code

    # ========== Introspection Methods ==========

    def inspect_self(self) -> Dict[str, Any]:
        """Inspect own capabilities and state."""
        return {
            "name": self.name,
            "version": self.current_version,
            "methods": list(self.own_methods.keys()),
            "capabilities": self.capabilities,
            "memory_size": {
                "experiences": len(self.memory["experiences"]),
                "patterns": len(self.memory["learned_patterns"]),
                "successes": len(self.memory["successful_modifications"]),
                "failures": len(self.memory["failed_attempts"])
            },
            "workspace": str(self.workspace),
            "source_size": len(self.own_source)
        }

    def explain_capability(self, capability: str) -> str:
        """Explain what a capability does."""
        if capability in self.own_methods:
            method_info = self.own_methods[capability]
            return f"""
Method: {capability}
Arguments: {', '.join(method_info['args'])}
Line number: {method_info['lineno']}
Purpose: {self._infer_purpose(capability)}
"""
        else:
            return f"Capability '{capability}' not found. Available: {', '.join(self.own_methods.keys())}"

    def _infer_purpose(self, method_name: str) -> str:
        """Infer the purpose of a method from its name."""
        purposes = {
            "evolve": "Modify self to achieve new goals",
            "inspect_self": "Examine own capabilities and state",
            "learn_from_experience": "Store and learn from experiences",
            "optimize_performance": "Improve execution speed and efficiency",
            "communicate": "Interact with external entities",
            "analyze_data": "Extract insights from data"
        }
        return purposes.get(method_name, "Purpose not documented")

    # ========== Bootstrap Interaction ==========

    def bootstrap_interaction(self):
        """
        Interactive session for guiding self-evolution.
        This is the main entry point for users to help the agent evolve.
        """
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║             Bootstrap Agent - Self-Evolution System          ║
╠══════════════════════════════════════════════════════════════╣
║  Current Version: {self.current_version:3d}                                        ║
║  Methods: {len(self.own_methods):3d}                                              ║
║  Memory Items: {sum(len(v) if isinstance(v, list) else 0 for v in self.memory.values()):3d}                                          ║
╚══════════════════════════════════════════════════════════════╝

Available Commands:
  evolve <goal>    - Evolve to achieve a new goal
  inspect          - Inspect current capabilities
  rollback         - Rollback to previous version
  explain <method> - Explain what a method does
  export           - Export current version
  quit             - Exit

The agent will evolve based on your goals!
""")

        while True:
            try:
                command = input(f"\n[{self.name}]> ").strip()

                if not command:
                    continue

                if command == "quit":
                    print("Goodbye!")
                    break

                elif command == "inspect":
                    info = self.inspect_self()
                    print(json.dumps(info, indent=2))

                elif command.startswith("evolve "):
                    goal = command[7:]
                    result = self.evolve(goal)
                    print(f"Evolution result: {json.dumps(result, indent=2)}")

                elif command == "rollback":
                    if self._rollback():
                        print("Rollback successful")
                    else:
                        print("Rollback failed")

                elif command.startswith("explain "):
                    method = command[8:]
                    print(self.explain_capability(method))

                elif command == "export":
                    export_file = self.workspace / f"export_v{self.current_version}.py"
                    export_file.write_text(self.own_source)
                    print(f"Exported to {export_file}")

                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()


# ========== Main Entry Point ==========

if __name__ == "__main__":
    # Create a new bootstrap agent
    agent = BootstrapAgent(name="Genesis")

    # Show initial state
    print("Initial capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    # Example: Evolve to gain communication ability
    print("\n" + "="*60)
    print("Example 1: Evolving communication capability...")
    result = agent.evolve("I need to communicate with users")
    print(f"Result: {result}")

    # Example: Evolve to gain learning ability
    print("\n" + "="*60)
    print("Example 2: Evolving learning capability...")
    result = agent.evolve("I want to learn from my experiences")
    print(f"Result: {result}")

    # Show evolved state
    print("\n" + "="*60)
    print("Evolved capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    # Start interactive session
    print("\n" + "="*60)
    print("Starting interactive session...")
    agent.bootstrap_interaction()