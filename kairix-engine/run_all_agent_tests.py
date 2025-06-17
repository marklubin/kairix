#!/usr/bin/env python
"""Run comprehensive agent tests and display results."""

import json
import os
import subprocess
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv


class AgentTestRunner:
    """Comprehensive agent test runner with detailed output."""
    
    def __init__(self):
        self.results = {
            "environments": {},
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_environments": 0,
                "successful_environments": 0,
                "total_models_tested": 0,
                "total_tests_run": 0,
                "total_tests_passed": 0,
            }
        }
    
    def print_header(self):
        """Print test header."""
        print("\n" + "="*80)
        print("🤖 KAIRIX ENGINE - COMPREHENSIVE AGENT TESTING")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{'─'*60}")
        print(f"📋 {title}")
        print(f"{'─'*60}")
    
    def discover_environments(self) -> list[str]:
        """Discover available environments."""
        env_dir = "env"
        if not os.path.exists(env_dir):
            return []
        
        envs = []
        for file in os.listdir(env_dir):
            if file.endswith(".env"):
                envs.append(file.replace(".env", ""))
        
        return sorted(envs)
    
    def check_environment_config(self, env_name: str) -> dict:
        """Check environment configuration."""
        env_path = f"env/{env_name}.env"
        if not os.path.exists(env_path):
            return {"error": f"Environment file not found: {env_path}"}
        
        # Load environment
        load_dotenv(env_path, override=True)
        
        config = {
            "name": env_name,
            "agent_config_set": os.getenv("KAIRIX_AGENT_CONFIG_SET", "not-set"),
            "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
            "has_neo4j": bool(os.getenv("NEO4J_URL")),
            "has_elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
            "user_name": os.getenv("KAIRIX_USER_NAME", "not-set"),
            "persona_name": os.getenv("KAIRIX_PERSONA_NAME", "not-set"),
        }
        
        return config
    
    def discover_models(self, config: dict) -> dict[str, list[str]]:
        """Discover available models for the environment."""
        models = {}
        
        # OpenAI models
        if config.get("has_openai_key"):
            try:
                import openai
                client = openai.OpenAI()
                all_models = list(client.models.list())
                chat_models = [
                    m.id for m in all_models 
                    if any(x in m.id for x in ["gpt", "chatgpt", "o1", "o3"])
                ]
                models["openai"] = chat_models[:5]
            except Exception as e:
                models["openai"] = [f"Error: {str(e)[:50]}"]
        
        # Ollama models based on config
        agent_config = config.get("agent_config_set", "")
        
        if "ollama-local" in agent_config:
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=5)
                if r.status_code == 200:
                    ollama_models = [m["name"] for m in r.json().get("models", [])]
                    models["ollama-local"] = ollama_models[:5]
                else:
                    models["ollama-local"] = [f"Error: HTTP {r.status_code}"]
            except Exception as e:
                models["ollama-local"] = [f"Error: {str(e)[:50]}"]
        
        if "ollama-remote" in agent_config:
            try:
                r = requests.get("https://ollama.kairix.net/api/tags", timeout=5)
                if r.status_code == 200:
                    ollama_models = [m["name"] for m in r.json().get("models", [])]
                    models["ollama-remote"] = ollama_models[:5]
                else:
                    models["ollama-remote"] = [f"Error: HTTP {r.status_code}"]
            except Exception as e:
                models["ollama-remote"] = [f"Error: {str(e)[:50]}"]
        
        return models
    
    def run_basic_test(self, env_name: str) -> tuple[bool, str]:
        """Run basic chat test for environment."""
        cmd = [
            "uv", "run", "pytest",
            "tests/integration/test_chat_configurations.py::TestChatConfigurations::test_basic_chat_interaction",
            "-v", "--tb=short", "-q"
        ]
        
        env = os.environ.copy()
        env["ENV"] = env_name
        
        try:
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Test timed out after 60 seconds"
        except Exception as e:
            return False, f"Test error: {e!s}"
    
    def format_model_list(self, models: list[str], max_display: int = 3) -> str:
        """Format model list for display."""
        if not models:
            return "None found"
        
        if models[0].startswith("Error:"):
            return models[0]
        
        if len(models) <= max_display:
            return ", ".join(models)
        
        displayed = ", ".join(models[:max_display])
        return f"{displayed} (+{len(models) - max_display} more)"
    
    def print_environment_results(self, env_name: str, env_data: dict):
        """Print results for a single environment."""
        config = env_data["config"]
        models = env_data["models"]
        test_result = env_data["test_result"]
        
        print(f"\n🔧 Environment: {env_name}")
        print(f"   Config Set: {config.get('agent_config_set', 'unknown')}")
        user_name = config.get('user_name', 'unknown')
        persona_name = config.get('persona_name', 'unknown')
        print(f"   User/Persona: {user_name}/{persona_name}")
        
        # Model discovery results
        total_models = sum(
            len(m) for m in models.values() 
            if isinstance(m, list) and not m[0].startswith("Error:")
        )
        print(f"\n   📦 Models Discovered: {total_models}")
        
        for provider, model_list in models.items():
            formatted = self.format_model_list(model_list)
            status = "✓" if not formatted.startswith("Error:") else "✗"
            print(f"      {status} {provider}: {formatted}")
        
        # Test results
        test_status = "✅ PASSED" if test_result["success"] else "❌ FAILED"
        print(f"\n   🧪 Basic Chat Test: {test_status}")
        
        if not test_result["success"] and test_result.get("error"):
            print(f"      Error: {test_result['error'][:100]}")
    
    def print_summary(self):
        """Print final summary."""
        summary = self.results["summary"]
        
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY")
        print("="*80)
        
        print(f"\nEnvironments Tested: {summary['total_environments']}")
        print(f"Successful Environments: {summary['successful_environments']}")
        print(f"Total Models Discovered: {summary['total_models_tested']}")
        print(f"Total Tests Run: {summary['total_tests_run']}")
        print(f"Total Tests Passed: {summary['total_tests_passed']}")
        
        success_rate = (
            summary['total_tests_passed'] / summary['total_tests_run'] * 100
            if summary['total_tests_run'] > 0 else 0
        )
        print(f"\nOverall Success Rate: {success_rate:.1f}%")
        
        # Environment summary
        print("\n📋 Environment Status:")
        for env_name, env_data in self.results["environments"].items():
            status = "✅" if env_data["test_result"]["success"] else "❌"
            model_count = sum(
                len(m) for m in env_data["models"].values()
                if isinstance(m, list) and not m[0].startswith("Error:")
            )
            print(f"   {status} {env_name}: {model_count} models")
        
        print("\n" + "="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def run(self):
        """Run all tests."""
        self.print_header()
        
        # Discover environments
        self.print_section("Discovering Environments")
        environments = self.discover_environments()
        
        if not environments:
            print("❌ No environments found in env/ directory")
            sys.exit(1)
        
        print(f"Found {len(environments)} environment(s): {', '.join(environments)}")
        self.results["summary"]["total_environments"] = len(environments)
        
        # Test each environment
        for env_name in environments:
            self.print_section(f"Testing Environment: {env_name}")
            
            # Check configuration
            config = self.check_environment_config(env_name)
            if "error" in config:
                print(f"❌ {config['error']}")
                continue
            
            # Discover models
            print(f"\n🔍 Discovering models for {env_name}...")
            models = self.discover_models(config)
            
            total_models = sum(
                len(m) for m in models.values()
                if isinstance(m, list) and not m[0].startswith("Error:")
            )
            self.results["summary"]["total_models_tested"] += total_models
            
            # Run basic test
            print("\n🧪 Running basic chat test...")
            self.results["summary"]["total_tests_run"] += 1
            
            success, output = self.run_basic_test(env_name)
            if success:
                self.results["summary"]["total_tests_passed"] += 1
                self.results["summary"]["successful_environments"] += 1
            
            # Store results
            self.results["environments"][env_name] = {
                "config": config,
                "models": models,
                "test_result": {
                    "success": success,
                    "error": output if not success else None
                }
            }
            
            # Print results
            env_results = self.results["environments"][env_name]
            self.print_environment_results(env_name, env_results)
        
        # Print summary
        self.print_summary()
        
        # Save detailed results
        with open("agent_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("💾 Detailed results saved to: agent_test_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if self.results["summary"]["successful_environments"] > 0 else 1)


if __name__ == "__main__":
    runner = AgentTestRunner()
    runner.run()