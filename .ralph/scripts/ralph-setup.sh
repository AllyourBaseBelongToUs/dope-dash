#!/bin/bash
# ralph-setup.sh - Interaktiv setup för Ralph
#
# Konfigurerar cloud provider och VM-inställningar

set -e

CONFIG_FILE="$HOME/.ralph-vm"

# Färger
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "LOGO"
  ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗
  ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║
  ██████╔╝███████║██║     ██████╔╝███████║
  ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║
  ██║  ██║██║  ██║███████╗██║     ██║  ██║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝
LOGO
echo -e "${NC}"
echo "Ralph Setup"
echo "==========="
echo ""

# Kolla om redan konfigurerad
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Befintlig konfiguration hittad:${NC}"
    cat "$CONFIG_FILE"
    echo ""
    read -p "Vill du skriva över? [y/N] " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo "Avbryter."
        exit 0
    fi
    echo ""
fi

# Välj cloud provider
echo "Välj cloud provider:"
echo "  1) Hetzner"
echo "  2) GCP (Google Cloud)"
echo "  3) Lokal (ingen VM)"
echo ""
read -p "Val [1]: " provider_choice
provider_choice="${provider_choice:-1}"

case "$provider_choice" in
    1)
        CLOUD="hetzner"
        echo ""
        echo -e "${CYAN}=== Hetzner Setup ===${NC}"

        # VM IP
        read -p "VM IP-adress: " vm_ip
        if [ -z "$vm_ip" ]; then
            echo -e "${RED}IP-adress krävs${NC}"
            exit 1
        fi

        # SSH User
        read -p "SSH-användare [root]: " ssh_user
        ssh_user="${ssh_user:-root}"

        # SSH Key
        default_key="$HOME/.ssh/id_rsa"
        if [ ! -f "$default_key" ]; then
            default_key="$HOME/.ssh/id_ed25519"
        fi
        read -p "SSH-nyckel [$default_key]: " ssh_key
        ssh_key="${ssh_key:-$default_key}"

        # VM Name
        read -p "VM-namn [ralph-sandbox]: " vm_name
        vm_name="${vm_name:-ralph-sandbox}"

        # Skriv config
        cat > "$CONFIG_FILE" << CONF
# Ralph VM Config - Hetzner
RALPH_CLOUD=hetzner

HETZNER_VM_NAME=$vm_name
HETZNER_VM_IP=$vm_ip
HETZNER_VM_USER=$ssh_user
HETZNER_SSH_KEY=$ssh_key
CONF
        ;;

    2)
        CLOUD="gcp"
        echo ""
        echo -e "${CYAN}=== GCP Setup ===${NC}"

        # Project ID
        read -p "GCP Project ID: " project_id
        if [ -z "$project_id" ]; then
            echo -e "${RED}Project ID krävs${NC}"
            exit 1
        fi

        # Zone
        read -p "Zone [europe-north1-a]: " zone
        zone="${zone:-europe-north1-a}"

        # VM Name
        read -p "VM-namn [ralph-sandbox]: " vm_name
        vm_name="${vm_name:-ralph-sandbox}"

        # User
        read -p "SSH-användare [$(whoami)]: " ssh_user
        ssh_user="${ssh_user:-$(whoami)}"

        # Skriv config
        cat > "$CONFIG_FILE" << CONF
# Ralph VM Config - GCP
RALPH_CLOUD=gcp

GCP_VM_PROJECT=$project_id
GCP_VM_ZONE=$zone
GCP_VM_NAME=$vm_name
GCP_VM_USER=$ssh_user
CONF
        ;;

    3)
        CLOUD="local"
        echo ""
        echo -e "${YELLOW}Lokal mode - ingen VM${NC}"

        cat > "$CONFIG_FILE" << CONF
# Ralph VM Config - Local
RALPH_CLOUD=local
CONF
        ;;

    *)
        echo -e "${RED}Ogiltigt val${NC}"
        exit 1
        ;;
esac

# Claude Code mode
echo ""
echo -e "${CYAN}=== Claude Code Inställningar ===${NC}"
echo ""
echo "Hur kör du Claude Code lokalt?"
echo "  1) MAX subscription (flat rate)"
echo "  2) API-nyckel (pay-per-token)"
echo ""
read -p "Val [1]: " local_mode
local_mode="${local_mode:-1}"

if [ "$local_mode" = "1" ]; then
    echo "CLAUDE_LOCAL_MODE=max" >> "$CONFIG_FILE"
else
    echo "CLAUDE_LOCAL_MODE=api" >> "$CONFIG_FILE"
fi

# VM Claude mode (om inte lokal)
if [ "$CLOUD" != "local" ]; then
    echo ""
    echo "Hur kör du Claude Code på VM?"
    echo "  1) MAX subscription (flat rate)"
    echo "  2) API-nyckel (pay-per-token)"
    echo ""
    read -p "Val [1]: " vm_mode
    vm_mode="${vm_mode:-1}"

    if [ "$vm_mode" = "1" ]; then
        echo "CLAUDE_VM_MODE=max" >> "$CONFIG_FILE"
        echo ""
        echo -e "${YELLOW}Tips för MAX på VM:${NC}"
        echo "  - Timeout kan behöva ökas (supervisor checks)"
        echo "  - Begränsa parallella worktrees till 2-3"
        echo "  - Logga in med: ssh VM && claude login"
    else
        echo "CLAUDE_VM_MODE=api" >> "$CONFIG_FILE"
        echo ""
        echo -e "${YELLOW}Tips för API på VM:${NC}"
        echo "  - Sätt ANTHROPIC_API_KEY i VM:s miljö"
        echo "  - Snabbare svar, men kostar per token"
    fi
fi

# ntfy topic
echo ""
read -p "ntfy.sh topic för notifikationer (valfritt): " ntfy_topic
echo "NTFY_TOPIC=$ntfy_topic" >> "$CONFIG_FILE"

echo ""
echo -e "${GREEN}✅ Konfiguration sparad till $CONFIG_FILE${NC}"
echo ""
cat "$CONFIG_FILE"
echo ""

# Testa anslutning
if [ "$CLOUD" != "local" ]; then
    echo -e "${YELLOW}Testar anslutning...${NC}"

    if [ "$CLOUD" = "hetzner" ]; then
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "$ssh_user@$vm_ip" "echo 'OK'" 2>/dev/null; then
            echo -e "${GREEN}✅ SSH-anslutning OK${NC}"

            # Kolla om Claude Code finns
            if ssh -o StrictHostKeyChecking=no -i "$ssh_key" "$ssh_user@$vm_ip" "which claude" 2>/dev/null; then
                echo -e "${GREEN}✅ Claude Code installerad på VM${NC}"
            else
                echo -e "${YELLOW}⚠ Claude Code ej hittad på VM${NC}"
                echo "  Installera med: npm install -g @anthropic-ai/claude-code"
            fi
        else
            echo -e "${RED}❌ Kunde inte ansluta till VM${NC}"
            echo "  Kontrollera IP, användare och SSH-nyckel"
        fi
    elif [ "$CLOUD" = "gcp" ]; then
        if gcloud compute ssh "$ssh_user@$vm_name" --zone="$zone" --project="$project_id" --command="echo OK" 2>/dev/null; then
            echo -e "${GREEN}✅ GCP-anslutning OK${NC}"
        else
            echo -e "${RED}❌ Kunde inte ansluta till VM${NC}"
            echo "  Kontrollera gcloud auth och projektinställningar"
        fi
    fi
fi

echo ""
echo -e "${GREEN}Ralph setup klar!${NC}"
echo ""
echo "Nästa steg:"
echo "  ralph discover my-app    # Skapa PRD"
echo "  ralph plan               # Skapa implementation plan"
echo "  ralph handoff            # Kör på VM"
