#!/usr/bin/env python3
import sys
import os
import subprocess

if len(sys.argv) != 2:
    print("Usage: install_systemd_service.py <ENV>")
    sys.exit(1)

env = sys.argv[1]
service_content = f"""[Unit]
Description=Kairix Server ({env})
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/just run-server {env}
WorkingDirectory={os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}
Restart=always
User={os.environ.get('USER', 'kairix')}

[Install]
WantedBy=multi-user.target
"""

service_path = f"/etc/systemd/system/kairix-{env}.service"
with open(service_path, 'w') as f:
    f.write(service_content)

subprocess.run(["systemctl", "daemon-reload"])
subprocess.run(["systemctl", "enable", f"kairix-{env}.service"])
print(f"Service kairix-{env} installed and enabled")