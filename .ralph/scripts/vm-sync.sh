#!/bin/bash
# vm-sync.sh - Synka projekt till/från VM
#
# Läser config från .ralph/config.json
# Stödjer: hcloud, gcloud, doctl, aws, ssh
#
# Användning:
#   ./vm-sync.sh push [path]     # Skicka till VM
#   ./vm-sync.sh pull [path]     # Hämta från VM
#   ./vm-sync.sh ssh             # SSH till VM
#   ./vm-sync.sh start           # Starta VM
#   ./vm-sync.sh stop            # Stoppa VM
#   ./vm-sync.sh status          # Visa status
#   ./vm-sync.sh run <spec>      # Kör Ralph på VM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")/lib"

# Load VM functions
source "$LIB_DIR/vm.sh"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Config not found: $CONFIG_FILE${NC}"
    echo "Run '/discover' to set up VM configuration."
    exit 1
fi

# Default workspace on VM
VM_WORKDIR="/home/$(vm_user)/workspace"

case "$1" in
    push)
        PROJECT_PATH="${2:-.}"
        echo -e "${YELLOW}Pushing $PROJECT_PATH to VM...${NC}"
        vm_ssh "mkdir -p $VM_WORKDIR"
        vm_scp_to "$PROJECT_PATH/" "$VM_WORKDIR/"
        echo -e "${GREEN}Done! Files on VM in $VM_WORKDIR${NC}"
        ;;

    pull)
        PROJECT_PATH="${2:-.}"
        echo -e "${YELLOW}Pulling from VM to $PROJECT_PATH...${NC}"
        vm_scp_from "$VM_WORKDIR/" "$PROJECT_PATH/"
        echo -e "${GREEN}Done! Files synced back${NC}"
        ;;

    ssh)
        echo -e "${YELLOW}Connecting to VM...${NC}"
        vm_ssh
        ;;

    start)
        vm_start
        ;;

    stop)
        vm_stop
        ;;

    status)
        local status=$(vm_status)
        echo -e "VM: $(vm_name)"
        echo -e "Provider: $(vm_provider)"
        echo -e "Status: $status"
        ;;

    run)
        SPEC_FILE="$2"
        if [ -z "$SPEC_FILE" ]; then
            echo "Usage: $0 run <spec-file>"
            exit 1
        fi
        echo -e "${YELLOW}Running Ralph with spec: $SPEC_FILE${NC}"
        vm_ssh "cd $VM_WORKDIR && ./scripts/ralph.sh $SPEC_FILE"
        ;;

    create)
        vm_create
        ;;

    init)
        echo -e "${YELLOW}Initializing VM with Ralph dependencies...${NC}"
        vm_scp_to "$SCRIPT_DIR/vm-init.sh" "/tmp/vm-init.sh"
        vm_ssh "chmod +x /tmp/vm-init.sh && /tmp/vm-init.sh"
        echo -e "${GREEN}VM initialized!${NC}"
        ;;

    *)
        echo "Ralph VM Sync (multi-provider)"
        echo ""
        echo "Config: $CONFIG_FILE"
        echo "Provider: $(vm_provider)"
        echo "VM: $(vm_name)"
        echo ""
        echo "Commands:"
        echo "  $0 push [path]    Push project to VM"
        echo "  $0 pull [path]    Pull changes from VM"
        echo "  $0 ssh            SSH to VM"
        echo "  $0 start          Start VM"
        echo "  $0 stop           Stop VM (saves money)"
        echo "  $0 status         Show VM status"
        echo "  $0 run <spec>     Run Ralph with spec file"
        echo "  $0 create         Show create command"
        echo "  $0 init           Initialize VM with dependencies"
        ;;
esac
