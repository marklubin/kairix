"""
Wrapper to safely import knowledge_db_demo for testing
"""
import asyncio
from unittest.mock import Mock, patch

# Mock the async run at module level
with patch('asyncio.run'):
    import sys
    sys.path.append('/Users/mark/kairix/kairix-offline/scripts')
    
    # Import after patching
    from knowledge_db_demo import *