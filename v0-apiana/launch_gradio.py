#!/usr/bin/env python3
"""
Launch script for the Apiana AI Gradio Pipeline Runner.

This script starts the web application with automatic pipeline discovery
and provides a user-friendly interface for pipeline execution.
"""

import argparse
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apiana.applications.gradio.app import create_app  # noqa: E402


def main():
    """Main entry point for the Gradio application."""
    parser = argparse.ArgumentParser(
        description="Apiana AI Pipeline Runner - Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_gradio.py                    # Start on localhost:7860
  python launch_gradio.py --host 0.0.0.0    # Start on all interfaces
  python launch_gradio.py --port 8080       # Start on custom port
  python launch_gradio.py --share           # Create public share link
  python launch_gradio.py --debug           # Enable debug mode
        """
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to bind to (default: 7860)"
    )
    
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link (useful for remote access)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    
    args = parser.parse_args()
    
    # Create and launch the application
    try:
        print("🚀 Starting Apiana AI Pipeline Runner...")
        print(f"📍 Host: {args.host}")
        print(f"🔌 Port: {args.port}")
        print(f"🌐 Share: {args.share}")
        print(f"🐛 Debug: {args.debug}")
        print("-" * 50)
        
        app = create_app(host=args.host, port=args.port)
        app.launch(share=args.share, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()