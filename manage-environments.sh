#!/bin/bash

# Kairix Environment Management Script
# Manages multiple user environments with state transitions

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

KAIRIX_ENV_BASE="/kairix-env"

# State definitions
# Lifecycle states: Creating -> Created -> InProgress -> Completed
# Service states: Disabled, Activated, Staydown

print_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list                    List all environments"
    echo "  create <username>       Create new environment (runs setup)"
    echo "  activate <username>     Activate environment services"
    echo "  disable <username>      Disable environment services"
    echo "  staydown <username>     Mark environment to stay down"
    echo "  status [username]       Show environment status"
    echo "  restart <username>      Restart environment services"
    echo "  remove <username>       Remove environment (with confirmation)"
    echo ""
}

get_state() {
    local user=$1
    local state_file="${KAIRIX_ENV_BASE}/${user}/.state"
    if [ -f "$state_file" ]; then
        cat "$state_file"
    else
        echo "Unknown"
    fi
}

get_service_state() {
    local user=$1
    local env_file="${KAIRIX_ENV_BASE}/${user}/.env"
    if [ -f "$env_file" ]; then
        grep "^SERVICE_STATE=" "$env_file" | cut -d'=' -f2 || echo "Created"
    else
        echo "Unknown"
    fi
}

set_state() {
    local user=$1
    local state=$2
    echo "$state" > "${KAIRIX_ENV_BASE}/${user}/.state"
}

set_service_state() {
    local user=$1
    local state=$2
    local env_file="${KAIRIX_ENV_BASE}/${user}/.env"
    if [ -f "$env_file" ]; then
        sed -i.bak "s/^SERVICE_STATE=.*/SERVICE_STATE=${state}/" "$env_file"
    fi
}

list_environments() {
    echo -e "${BLUE}=== Kairix Environments ===${NC}"
    echo ""
    printf "%-15s %-12s %-15s %-6s\n" "Username" "State" "Service State" "Port"
    printf "%-15s %-12s %-15s %-6s\n" "--------" "-----" "-------------" "----"
    
    for user_dir in "${KAIRIX_ENV_BASE}"/*; do
        if [ -d "$user_dir" ]; then
            username=$(basename "$user_dir")
            state=$(get_state "$username")
            service_state=$(get_service_state "$username")
            
            # Get port from .env
            port=""
            if [ -f "${user_dir}/.env" ]; then
                port=$(grep "^PORT=" "${user_dir}/.env" | cut -d'=' -f2)
            fi
            
            # Color code based on state
            case "$service_state" in
                "Activated")
                    color=$GREEN
                    ;;
                "Disabled"|"Staydown")
                    color=$RED
                    ;;
                *)
                    color=$YELLOW
                    ;;
            esac
            
            printf "${color}%-15s${NC} %-12s %-15s %-6s\n" "$username" "$state" "$service_state" "$port"
        fi
    done
}

create_environment() {
    local username=$1
    
    if [ -d "${KAIRIX_ENV_BASE}/${username}" ]; then
        echo -e "${RED}Error: Environment for ${username} already exists${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Creating environment for: ${username}${NC}"
    set_state "$username" "Creating"
    
    # Run the setup script
    ./setup-user-env.sh
}

activate_environment() {
    local username=$1
    local user_dir="${KAIRIX_ENV_BASE}/${username}"
    
    if [ ! -d "$user_dir" ]; then
        echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
        exit 1
    fi
    
    local service_state=$(get_service_state "$username")
    
    if [ "$service_state" == "Staydown" ]; then
        echo -e "${YELLOW}Warning: Environment is marked to stay down. Remove staydown first.${NC}"
        return
    fi
    
    echo -e "${BLUE}Activating environment: ${username}${NC}"
    set_service_state "$username" "Activated"
    
    # Start services
    "${user_dir}/run.sh" start
}

disable_environment() {
    local username=$1
    local user_dir="${KAIRIX_ENV_BASE}/${username}"
    
    if [ ! -d "$user_dir" ]; then
        echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Disabling environment: ${username}${NC}"
    set_service_state "$username" "Disabled"
    
    # Stop services
    "${user_dir}/run.sh" stop
}

staydown_environment() {
    local username=$1
    local user_dir="${KAIRIX_ENV_BASE}/${username}"
    
    if [ ! -d "$user_dir" ]; then
        echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Marking environment to stay down: ${username}${NC}"
    set_service_state "$username" "Staydown"
    
    # Stop services if running
    "${user_dir}/run.sh" stop
}

show_status() {
    local username=$1
    
    if [ -z "$username" ]; then
        list_environments
    else
        local user_dir="${KAIRIX_ENV_BASE}/${username}"
        
        if [ ! -d "$user_dir" ]; then
            echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
            exit 1
        fi
        
        echo -e "${BLUE}=== Environment Status: ${username} ===${NC}"
        "${user_dir}/run.sh" status
        echo ""
        echo "Service State: $(get_service_state "$username")"
    fi
}

restart_environment() {
    local username=$1
    local user_dir="${KAIRIX_ENV_BASE}/${username}"
    
    if [ ! -d "$user_dir" ]; then
        echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Restarting environment: ${username}${NC}"
    "${user_dir}/run.sh" stop
    sleep 2
    "${user_dir}/run.sh" start
}

remove_environment() {
    local username=$1
    local user_dir="${KAIRIX_ENV_BASE}/${username}"
    
    if [ ! -d "$user_dir" ]; then
        echo -e "${RED}Error: Environment for ${username} does not exist${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Warning: This will permanently remove the environment for ${username}${NC}"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" == "yes" ]; then
        # Stop services first
        "${user_dir}/run.sh" stop 2>/dev/null || true
        
        # Remove directory
        rm -rf "$user_dir"
        echo -e "${GREEN}Environment removed: ${username}${NC}"
    else
        echo "Cancelled"
    fi
}

# Main command handling
case "$1" in
    list)
        list_environments
        ;;
    create)
        create_environment "$2"
        ;;
    activate)
        activate_environment "$2"
        ;;
    disable)
        disable_environment "$2"
        ;;
    staydown)
        staydown_environment "$2"
        ;;
    status)
        show_status "$2"
        ;;
    restart)
        restart_environment "$2"
        ;;
    remove)
        remove_environment "$2"
        ;;
    *)
        print_usage
        exit 1
        ;;
esac