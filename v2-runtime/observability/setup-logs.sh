#!/bin/bash
# =============================================================================
# Fluent Bit Host Setup for Kairix
# =============================================================================
# Installs Fluent Bit and configures it to collect container logs from journald
# and send them to OpenObserve.
#
# Usage: ./setup-logs.sh [install|uninstall|status]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

install_fluent_bit() {
    print_header "Installing Fluent Bit"

    # Check if already installed
    if [[ -f /opt/fluent-bit/bin/fluent-bit ]]; then
        echo -e "${GREEN}Fluent Bit already installed at /opt/fluent-bit${NC}"
    else
        echo "Downloading and installing Fluent Bit..."

        # Detect OS
        if [[ -f /etc/debian_version ]]; then
            # Debian/Ubuntu
            curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | sh
        elif [[ -f /etc/redhat-release ]]; then
            # RHEL/Fedora
            curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | sh
        else
            echo -e "${RED}Unsupported OS. Please install Fluent Bit manually.${NC}"
            echo "See: https://docs.fluentbit.io/manual/installation/linux"
            exit 1
        fi
    fi

    # Verify installation
    if ! /opt/fluent-bit/bin/fluent-bit --version; then
        echo -e "${RED}Fluent Bit installation failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}Fluent Bit installed successfully${NC}"
}

setup_systemd_service() {
    print_header "Setting up Systemd User Service"

    # Create user systemd directory
    mkdir -p ~/.config/systemd/user

    # Copy service file
    cp "$SCRIPT_DIR/fluent-bit.service" ~/.config/systemd/user/fluent-bit.service

    # Reload systemd
    systemctl --user daemon-reload

    echo -e "${GREEN}Systemd service installed${NC}"
}

start_service() {
    print_header "Starting Fluent Bit Service"

    systemctl --user enable fluent-bit
    systemctl --user start fluent-bit

    sleep 2

    if systemctl --user is-active --quiet fluent-bit; then
        echo -e "${GREEN}Fluent Bit is running${NC}"
    else
        echo -e "${RED}Fluent Bit failed to start${NC}"
        echo "Check logs with: journalctl --user -u fluent-bit -f"
        exit 1
    fi
}

show_status() {
    print_header "Fluent Bit Status"

    echo -e "\n${CYAN}Binary:${NC}"
    if [[ -f /opt/fluent-bit/bin/fluent-bit ]]; then
        /opt/fluent-bit/bin/fluent-bit --version
    else
        echo -e "${YELLOW}Not installed${NC}"
    fi

    echo -e "\n${CYAN}Service:${NC}"
    if systemctl --user is-active --quiet fluent-bit 2>/dev/null; then
        echo -e "${GREEN}Running${NC}"
        systemctl --user status fluent-bit --no-pager | head -10
    else
        echo -e "${YELLOW}Not running${NC}"
    fi

    echo -e "\n${CYAN}Recent logs:${NC}"
    journalctl --user -u fluent-bit -n 5 --no-pager 2>/dev/null || echo "No logs available"

    echo -e "\n${CYAN}OpenObserve log streams:${NC}"
    curl -s "http://localhost:5080/api/default/streams" \
        -u "admin@kairix.local:kairix123" 2>/dev/null | \
        jq -r '.list[] | select(.stream_type=="logs") | .name' 2>/dev/null || \
        echo "Unable to connect to OpenObserve"
}

uninstall() {
    print_header "Uninstalling Fluent Bit Service"

    # Stop and disable service
    systemctl --user stop fluent-bit 2>/dev/null || true
    systemctl --user disable fluent-bit 2>/dev/null || true

    # Remove service file
    rm -f ~/.config/systemd/user/fluent-bit.service
    systemctl --user daemon-reload

    echo -e "${GREEN}Service removed${NC}"
    echo -e "${YELLOW}Note: Fluent Bit binary at /opt/fluent-bit was not removed${NC}"
}

# Main
case "${1:-install}" in
    install)
        install_fluent_bit
        setup_systemd_service
        start_service
        echo
        show_status
        echo
        echo -e "${GREEN}Setup complete!${NC}"
        echo "View logs: journalctl --user -u fluent-bit -f"
        echo "Check OpenObserve: http://localhost:5080 (Logs tab)"
        ;;
    uninstall)
        uninstall
        ;;
    status)
        show_status
        ;;
    restart)
        print_header "Restarting Fluent Bit"
        systemctl --user restart fluent-bit
        sleep 2
        show_status
        ;;
    *)
        echo "Usage: $0 [install|uninstall|status|restart]"
        exit 1
        ;;
esac
