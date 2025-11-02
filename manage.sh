#!/bin/bash

# Rantoo Management Script
# This script provides management functions for the deployed Rantoo application

set -e

# Configuration
ANSIBLE_DIR="ansible"
INVENTORY="hosts"
ANSIBLE_USER="ansible"
PRIVATE_KEY="~/.ssh/keys/nirdclub__id_ed25519"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if inventory file exists
check_inventory() {
    if [ ! -f "$INVENTORY" ]; then
        print_error "Inventory file '$INVENTORY' not found!"
        exit 1
    fi
}

# Status function
status() {
    print_header "Application Status"
    cd "$ANSIBLE_DIR"
    ansible -i "../$INVENTORY" -u "$ANSIBLE_USER" --private-key "$PRIVATE_KEY" pb_home -m systemd -a "name=rantoo"
}

# Logs function
logs() {
    print_header "Application Logs (last 50 lines)"
    cd "$ANSIBLE_DIR"
    ansible -i "../$INVENTORY" -u "$ANSIBLE_USER" --private-key "$PRIVATE_KEY" pb_home -m shell -a "journalctl -u rantoo -n 50 --no-pager"
}

# Restart function
restart() {
    print_header "Restarting Application"
    cd "$ANSIBLE_DIR"
    ansible -i "../$INVENTORY" -u "$ANSIBLE_USER" --private-key "$PRIVATE_KEY" pb_home -m systemd -a "name=rantoo state=restarted"
    print_status "Application restarted"
}

# Health check function
health() {
    print_header "Application Health Check"
    cd "$ANSIBLE_DIR"
    ansible -i "../$INVENTORY" -u "$ANSIBLE_USER" --private-key "$PRIVATE_KEY" pb_home -m uri -a "url=http://localhost:33080/health return_content=yes"
}

# Main execution
main() {
    check_inventory
    
    case "${1:-status}" in
        status)
            status
            ;;
        logs)
            logs
            ;;
        restart)
            restart
            ;;
        health)
            health
            ;;
        *)
            echo "Usage: $0 {status|logs|restart|health}"
            echo ""
            echo "Commands:"
            echo "  status  - Show application status"
            echo "  logs    - Show application logs"
            echo "  restart - Restart the application"
            echo "  health  - Check application health"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
