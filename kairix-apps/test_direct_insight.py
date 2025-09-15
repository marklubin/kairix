#!/usr/bin/env python3
"""Direct test to find the k=0 issue"""

import os
import sys
import logging
from kairix_core.runtime.logging import LoggingRuntime

# Set up proper logging
logger = LoggingRuntime().logger
logger.setLevel(logging.DEBUG)

# Add file/line handler to root logger too
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    fmt="[%(filename)s:%(funcName)s:L%(lineno)d][%(levelname)s] %(message)s"
))
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)

print("=" * 60)
print("TESTING SUMMARY INSIGHT PERCEPTOR")
print("=" * 60)

# Check environment
print(f"KAIRIX_N_SUMMARIES_PER_MESSAGE: {os.getenv('KAIRIX_N_SUMMARIES_PER_MESSAGE')}")
print(f"KAIRIX_AGENT_CONFIGURATION_SET_KEY: {os.getenv('KAIRIX_AGENT_CONFIGURATION_SET_KEY')}")

try:
    # Import and test
    from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
    from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
    from kairix_core.runtime.agent import AgentRuntime
    
    print("\nCreating runtime...")
    runtime = AgentRuntime()
    
    print("\nCreating embedded store...")
    store = SQLiteEmbeddedDataStore()
    
    n_summaries = int(os.getenv('KAIRIX_N_SUMMARIES_PER_MESSAGE', '20'))
    print(f"\nCreating perceptor with k_memories={n_summaries}...")
    perceptor = SummaryInsightPerceptor(
        runtime=runtime,
        embedded_sumary_store=store,
        k_memories=n_summaries
    )
    
    print(f"\nPerceptor created successfully!")
    print(f"perceptor.k_memories = {perceptor.k_memories}")
    print(f"Type: {type(perceptor.k_memories)}")
    
    # Check the _gather_memories method
    import inspect
    print(f"\n_gather_memories signature: {inspect.signature(perceptor._gather_memories)}")
    
    # Try to trace where k might become 0
    print("\nChecking for k value in code...")
    import dis
    dis.dis(perceptor._gather_memories)
    
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    sys.exit(1)