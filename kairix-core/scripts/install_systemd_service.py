#!/usr/bin/env python3
import sys
import os
import subprocess


K_DIR = os.getenv("K_DIR")
K_USR = os.getenv("K_USR")


if not K_DIR or not K_USR
    print("Missing required env vars.")
    sys.exit(1)


def service_file_contents(name, command, wd):
    return f""""
    [Unit]
    Description=Kairix™ - Component Service Unit v.0.0.1 [kairix-component-identifier={name}]
    After=network.target

    [Service]
    Type=simple
    ExecStart={command}
    WorkingDirectory={wd}
    Restart=always
    User=kairix

    [Install]
    WantedBy=multi-user.target
    """

def file_path(name):
    return f"/etc/systemd/system/kairix-{name}.service"


def create_service_and_load(name, command, dir):
    service_file = service_file_contents(name, command, dir)
    service_file_path = file_path(name)

    with open(service_file_path, "w") as f:
        f.write(service_file)
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", name])
    print(f"Service {name} installed and enabled.")

create_service_and_load(f"Kairix-Server-{K_USR}", f"/usr/bin/just run-server {K_USR}", K_DIR)
create_service_and_load(f"Kairix-Website-{K_USR}", f"/usr/bin/just run-website {K_USR}", K_DIR)
