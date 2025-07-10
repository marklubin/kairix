#!/usr/bin/env python3
import subprocess
import sys

def create_service_user(username="kairix-user"):
    """Create a service user account"""
    commands = [
        f"sudo useradd -r -s /bin/bash -m -d /home/{username} {username}",
        f"echo 'Service user {username} created'",
        f"echo 'Run commands as {username}: sudo -u {username} <command>'",
        f"echo 'Interactive shell: sudo -u {username} -i'"
    ]
    
    for cmd in commands:
        if cmd.startswith("sudo"):
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                sys.exit(1)
        else:
            print(cmd.replace("echo ", ""))

if __name__ == "__main__":
    create_service_user()