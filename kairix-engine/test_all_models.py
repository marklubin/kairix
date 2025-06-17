#!/usr/bin/env python
"""Quick script to test and display all available models."""

import os
import sys

import requests
from dotenv import load_dotenv


def print_header():
    """Print header."""
    print("\n" + "="*60)
    print("🤖 MODEL VERIFICATION SUMMARY")
    print("="*60 + "\n")


def check_environment(env_name: str) -> dict:
    """Check environment and discover models."""
    env_path = f"env/{env_name}.env"
    if not os.path.exists(env_path):
        return {"error": "File not found"}
    
    # Load environment
    load_dotenv(env_path, override=True)
    
    result = {
        "name": env_name,
        "config_set": os.getenv("KAIRIX_AGENT_CONFIG_SET", "not-set"),
        "models": {}
    }
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            client = openai.OpenAI()
            models = list(client.models.list())
            chat_models = [m.id for m in models if "gpt" in m.id][:5]
            result["models"]["openai"] = chat_models
        except Exception as e:
            result["models"]["openai"] = [f"Error: {str(e)[:30]}"]
    
    # Check Ollama based on config
    config_set = result["config_set"]
    
    if "ollama-local" in config_set:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])][:5]
                result["models"]["ollama-local"] = models
            else:
                result["models"]["ollama-local"] = [f"HTTP {r.status_code}"]
        except Exception as e:
            result["models"]["ollama-local"] = [f"Error: {str(e)[:30]}"]
    
    if "ollama-remote" in config_set:
        try:
            r = requests.get("https://ollama.kairix.net/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])][:5]
                result["models"]["ollama-remote"] = models
            else:
                result["models"]["ollama-remote"] = [f"HTTP {r.status_code}"]
        except Exception as e:
            result["models"]["ollama-remote"] = [f"Error: {str(e)[:30]}"]
    
    return result


def main():
    """Main function."""
    print_header()
    
    # Find environments
    environments = []
    if os.path.exists("env"):
        for f in os.listdir("env"):
            if f.endswith(".env"):
                environments.append(f.replace(".env", ""))
    
    if not environments:
        print("❌ No environments found in env/")
        sys.exit(1)
    
    # Check each environment
    total_models = 0
    working_envs = 0
    
    for env in sorted(environments):
        print(f"📁 Environment: {env}")
        result = check_environment(env)
        
        if "error" in result:
            print(f"   ❌ {result['error']}")
            continue
        
        print(f"   Config: {result['config_set']}")
        
        env_models = 0
        env_working = False
        
        for provider, models in result["models"].items():
            if models and not models[0].startswith("Error"):
                print(f"   ✅ {provider}: {len(models)} models")
                print(f"      {', '.join(models[:3])}")
                if len(models) > 3:
                    print(f"      ... and {len(models) - 3} more")
                env_models += len(models)
                env_working = True
            else:
                error_msg = models[0] if models else "No response"
                print(f"   ❌ {provider}: {error_msg}")
        
        if env_working:
            working_envs += 1
            total_models += env_models
        
        print()
    
    # Summary
    print("="*60)
    print(f"✅ Working Environments: {working_envs}/{len(environments)}")
    print(f"📊 Total Models Available: {total_models}")
    print("="*60 + "\n")
    
    sys.exit(0 if working_envs > 0 else 1)


if __name__ == "__main__":
    main()