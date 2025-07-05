#!/bin/bash

# Management script for Kairix multi-tenant instances

set -e

DEPLOYMENTS_DIR="deployments"

function show_help() {
    echo "Kairix Multi-Tenant Management Script"
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  list                    List all deployed instances"
    echo "  stop <user_id>         Stop a user instance"
    echo "  start <user_id>        Start a stopped instance"
    echo "  remove <user_id>       Remove a user instance (with confirmation)"
    echo "  logs <user_id>         Show logs for a user instance"
    echo "  status <user_id>       Show status of a user instance"
    echo "  info <user_id>         Show deployment info for a user"
    echo ""
}

function list_instances() {
    echo "Deployed Kairix instances:"
    echo "=========================="
    
    if [ -d "$DEPLOYMENTS_DIR" ]; then
        for file in $DEPLOYMENTS_DIR/*.json; do
            if [ -f "$file" ]; then
                user_id=$(basename "$file" .json)
                status=$(docker compose -p "kairix-${user_id}" ps --format json 2>/dev/null | jq -r '.[0].State' 2>/dev/null || echo "unknown")
                echo "- ${user_id}: ${status}"
            fi
        done
    else
        echo "No deployments found."
    fi
}

function stop_instance() {
    local user_id=$1
    echo "Stopping instance for user: ${user_id}"
    docker compose -p "kairix-${user_id}" stop
    echo "Instance stopped."
}

function start_instance() {
    local user_id=$1
    local env_file=".env.${user_id}"
    
    if [ ! -f "$env_file" ]; then
        echo "Error: Environment file not found: $env_file"
        exit 1
    fi
    
    echo "Starting instance for user: ${user_id}"
    docker compose -f docker-compose.user.yml \
        --project-name "kairix-${user_id}" \
        --env-file "$env_file" \
        up -d
    echo "Instance started."
}

function remove_instance() {
    local user_id=$1
    
    echo "WARNING: This will remove all data for user ${user_id}!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
    
    echo "Removing instance for user: ${user_id}"
    
    # Stop and remove containers
    docker compose -p "kairix-${user_id}" down -v
    
    # Remove deployment info
    rm -f "$DEPLOYMENTS_DIR/${user_id}.json"
    rm -f ".env.${user_id}"
    
    echo "Instance removed."
}

function show_logs() {
    local user_id=$1
    docker compose -p "kairix-${user_id}" logs -f
}

function show_status() {
    local user_id=$1
    echo "Status for user ${user_id}:"
    echo "========================"
    docker compose -p "kairix-${user_id}" ps
}

function show_info() {
    local user_id=$1
    local info_file="$DEPLOYMENTS_DIR/${user_id}.json"
    
    if [ ! -f "$info_file" ]; then
        echo "No deployment info found for user: ${user_id}"
        exit 1
    fi
    
    echo "Deployment info for user ${user_id}:"
    echo "=================================="
    cat "$info_file" | jq .
}

# Main script logic
case "$1" in
    list)
        list_instances
        ;;
    stop)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        stop_instance "$2"
        ;;
    start)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        start_instance "$2"
        ;;
    remove)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        remove_instance "$2"
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        show_logs "$2"
        ;;
    status)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        show_status "$2"
        ;;
    info)
        if [ -z "$2" ]; then
            echo "Error: User ID required"
            show_help
            exit 1
        fi
        show_info "$2"
        ;;
    *)
        show_help
        ;;
esac