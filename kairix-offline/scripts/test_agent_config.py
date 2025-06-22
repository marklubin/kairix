#!/usr/bin/env python3
"""Test script to debug agent configuration issues."""

import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check environment variables
print("=== Environment Variables ===")
env_vars = [
    "KAIRIX_AGENT_CONFIGURATION_SET_KEY",
    "KAIRIX_AGENT_CONFIG_SET",
    "NEO4J_URL",
    "OPENAI_API_KEY"
]

for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f"{var}: {value[:20]}..." if len(value) > 20 else f"{var}: {value}")
    else:
        print(f"{var}: NOT SET")

print("\n=== Testing Configuration Loading ===")

try:
    from kairix_core.configuration.agent import configuration_sets
    print(f"Available configuration sets: {list(configuration_sets.keys())}")
    
    # Try to get the environment configuration key
    config_key = os.environ.get("KAIRIX_AGENT_CONFIGURATION_SET_KEY")
    if not config_key:
        print("ERROR: KAIRIX_AGENT_CONFIGURATION_SET_KEY not set!")
        print("Trying alternative: KAIRIX_AGENT_CONFIG_SET...")
        config_key = os.environ.get("KAIRIX_AGENT_CONFIG_SET")
        
    if config_key:
        print(f"\nUsing configuration set: {config_key}")
        if config_key in configuration_sets:
            config = configuration_sets[config_key]
            print(f"Configuration name: {config.name}")
            print(f"Default provider: {config.default_provider}")
            print(f"Agent configs: {list(config.agent_configs.keys())}")
        else:
            print(f"ERROR: Configuration set '{config_key}' not found in available sets!")
    else:
        print("ERROR: No configuration key found in environment!")
        
except Exception as e:
    print(f"ERROR loading configuration: {e}")
    import traceback
    traceback.print_exc()