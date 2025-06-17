#!/usr/bin/env python
"""
Launch script for the Gradio interface with log streaming.

Usage:
    # Basic log streaming demo
    python launch_gradio.py
    
    # Kairix integration with logs
    python launch_gradio.py --kairix
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Launch Gradio interface")
    parser.add_argument(
        "--kairix",
        action="store_true",
        help="Launch Kairix integration interface instead of basic demo"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the server on (default: 7860)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public shareable link"
    )
    
    args = parser.parse_args()
    
    if args.kairix:
        print("Launching Kairix Gradio Interface...")
        from src.kairix_engine.gradio_kairix_integration import main as launch_kairix
        launch_kairix()
    else:
        print("Launching Basic Log Streaming Demo...")
        from src.kairix_engine.gradio_log_streamer import main as launch_demo
        launch_demo()


if __name__ == "__main__":
    main()