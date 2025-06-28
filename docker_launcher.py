#!/usr/bin/env python3
"""
Smart Docker Compose launcher for Kairix
Automatically determines whether to use local or remote Neo4j
"""

import os
import sys
import subprocess
import re
from urllib.parse import urlparse


def parse_neo4j_url(url):
    """Parse NEO4J_URL to determine if it's localhost"""
    if not url:
        return True  # Default to local if not specified
    
    # Check for localhost patterns
    localhost_patterns = ['localhost', '127.0.0.1', '0.0.0.0', 'neo4j:']
    
    for pattern in localhost_patterns:
        if pattern in url.lower():
            return True
    
    # Try to parse the URL
    try:
        # Handle bolt:// URLs
        if url.startswith('bolt://'):
            # Extract host from bolt URL format: bolt://user:pass@host:port
            match = re.search(r'@([^:]+):', url)
            if match:
                host = match.group(1)
                return host in localhost_patterns
    except:
        pass
    
    return False


def setup_environment():
    """Set up environment variables before launching containers"""
    neo4j_url = os.environ.get('NEO4J_URL', '')
    
    # Determine if we should use local Neo4j
    use_local_neo4j = parse_neo4j_url(neo4j_url)
    
    if use_local_neo4j:
        # Override NEO4J_URL to point to the container service
        os.environ['NEO4J_URL'] = 'bolt://neo4j:password@neo4j:7687'
        os.environ['USE_LOCAL_NEO4J'] = 'true'
    else:
        os.environ['USE_LOCAL_NEO4J'] = 'false'
    
    # Ensure MCP servers list is set
    if 'MCP_SERVERS_TO_INSTALL' not in os.environ:
        os.environ['MCP_SERVERS_TO_INSTALL'] = ''
    
    return use_local_neo4j


def launch_docker_compose(use_local_neo4j, extra_args):
    """Launch docker-compose with appropriate configuration"""
    cmd = ['docker-compose']
    
    if use_local_neo4j:
        cmd.extend(['--profile', 'with-neo4j'])
        print("Starting with local Neo4j...")
    else:
        print(f"Using remote Neo4j at: {os.environ.get('NEO4J_URL')}")
    
    cmd.extend(['up'] + extra_args)
    
    # Run docker-compose
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running docker-compose: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        subprocess.run(['docker-compose', 'down'], check=False)
        sys.exit(0)


def main():
    """Main entry point"""
    # Get any additional arguments passed to the script
    extra_args = sys.argv[1:]
    
    # Set up environment
    use_local_neo4j = setup_environment()
    
    # Launch docker-compose
    launch_docker_compose(use_local_neo4j, extra_args)


if __name__ == '__main__':
    main()