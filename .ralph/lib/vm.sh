#!/bin/bash
# vm.sh - Multi-provider VM management
# Source this file: source lib/vm.sh
#
# Supports: hcloud (Hetzner), gcloud (Google), doctl (DigitalOcean), aws (AWS), ssh (generic)
# Config stored in .ralph/config.json

CONFIG_FILE="${RALPH_CONFIG:-.ralph/config.json}"

# Read config value
_vm_config() {
    local key="$1"
    jq -r ".$key // empty" "$CONFIG_FILE" 2>/dev/null
}

# Get provider from config
vm_provider() {
    _vm_config "provider"
}

# Get VM name from config
vm_name() {
    _vm_config "vm_name"
}

# Get VM IP from config
vm_ip() {
    _vm_config "vm_ip"
}

# Get VM user from config
vm_user() {
    _vm_config "user" || echo "$USER"
}

# Check if provider CLI is installed
vm_check_cli() {
    local provider="${1:-$(vm_provider)}"
    case "$provider" in
        hcloud)   which hcloud >/dev/null 2>&1 ;;
        gcloud)   which gcloud >/dev/null 2>&1 ;;
        doctl)    which doctl >/dev/null 2>&1 ;;
        aws)      which aws >/dev/null 2>&1 ;;
        ssh)      which ssh >/dev/null 2>&1 ;;
        *)        return 1 ;;
    esac
}

# SSH to VM
vm_ssh() {
    local cmd="$1"
    local provider=$(vm_provider)
    local name=$(vm_name)
    local ip=$(vm_ip)
    local user=$(vm_user)

    case "$provider" in
        hcloud)
            if [ -n "$cmd" ]; then
                ssh "$user@$ip" "$cmd"
            else
                ssh "$user@$ip"
            fi
            ;;
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            if [ -n "$cmd" ]; then
                gcloud compute ssh "$user@$name" --zone="$zone" --project="$project" --command="$cmd"
            else
                gcloud compute ssh "$user@$name" --zone="$zone" --project="$project"
            fi
            ;;
        doctl)
            if [ -n "$cmd" ]; then
                ssh "$user@$ip" "$cmd"
            else
                ssh "$user@$ip"
            fi
            ;;
        aws)
            local key=$(_vm_config "key_file")
            if [ -n "$cmd" ]; then
                ssh -i "$key" "$user@$ip" "$cmd"
            else
                ssh -i "$key" "$user@$ip"
            fi
            ;;
        ssh)
            if [ -n "$cmd" ]; then
                ssh "$user@$ip" "$cmd"
            else
                ssh "$user@$ip"
            fi
            ;;
    esac
}

# SCP to VM
vm_scp_to() {
    local src="$1"
    local dest="$2"
    local provider=$(vm_provider)
    local name=$(vm_name)
    local ip=$(vm_ip)
    local user=$(vm_user)

    case "$provider" in
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            gcloud compute scp --recurse "$src" "$user@$name:$dest" --zone="$zone" --project="$project"
            ;;
        aws)
            local key=$(_vm_config "key_file")
            scp -i "$key" -r "$src" "$user@$ip:$dest"
            ;;
        *)
            scp -r "$src" "$user@$ip:$dest"
            ;;
    esac
}

# SCP from VM
vm_scp_from() {
    local src="$1"
    local dest="$2"
    local provider=$(vm_provider)
    local name=$(vm_name)
    local ip=$(vm_ip)
    local user=$(vm_user)

    case "$provider" in
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            gcloud compute scp --recurse "$user@$name:$src" "$dest" --zone="$zone" --project="$project"
            ;;
        aws)
            local key=$(_vm_config "key_file")
            scp -i "$key" -r "$user@$ip:$src" "$dest"
            ;;
        *)
            scp -r "$user@$ip:$src" "$dest"
            ;;
    esac
}

# Start VM
vm_start() {
    local provider=$(vm_provider)
    local name=$(vm_name)

    echo "[vm] Starting $name..."

    case "$provider" in
        hcloud)
            hcloud server poweron "$name"
            ;;
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            gcloud compute instances start "$name" --zone="$zone" --project="$project"
            ;;
        doctl)
            local id=$(doctl compute droplet list --format ID,Name --no-header | grep "$name" | awk '{print $1}')
            doctl compute droplet-action power-on "$id"
            ;;
        aws)
            local id=$(_vm_config "instance_id")
            aws ec2 start-instances --instance-ids "$id"
            ;;
        ssh)
            echo "[vm] Generic SSH - start manually"
            return 1
            ;;
    esac
}

# Stop VM
vm_stop() {
    local provider=$(vm_provider)
    local name=$(vm_name)

    echo "[vm] Stopping $name..."

    case "$provider" in
        hcloud)
            hcloud server poweroff "$name"
            ;;
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            gcloud compute instances stop "$name" --zone="$zone" --project="$project"
            ;;
        doctl)
            local id=$(doctl compute droplet list --format ID,Name --no-header | grep "$name" | awk '{print $1}')
            doctl compute droplet-action power-off "$id"
            ;;
        aws)
            local id=$(_vm_config "instance_id")
            aws ec2 stop-instances --instance-ids "$id"
            ;;
        ssh)
            echo "[vm] Generic SSH - stop manually"
            return 1
            ;;
    esac

    echo "[vm] Stopped (saves money!)"
}

# Get VM status
vm_status() {
    local provider=$(vm_provider)
    local name=$(vm_name)

    case "$provider" in
        hcloud)
            hcloud server describe "$name" -o format='{{.Status}}'
            ;;
        gcloud)
            local zone=$(_vm_config "region")
            local project=$(_vm_config "project")
            gcloud compute instances describe "$name" --zone="$zone" --project="$project" --format="value(status)"
            ;;
        doctl)
            doctl compute droplet list --format Name,Status --no-header | grep "$name" | awk '{print $2}'
            ;;
        aws)
            local id=$(_vm_config "instance_id")
            aws ec2 describe-instances --instance-ids "$id" --query 'Reservations[0].Instances[0].State.Name' --output text
            ;;
        ssh)
            # Try to ping
            if vm_ssh "echo ok" >/dev/null 2>&1; then
                echo "running"
            else
                echo "unknown"
            fi
            ;;
    esac
}

# Create VM (interactive - shows command)
vm_create() {
    local provider=$(vm_provider)
    local name=$(vm_name)
    local region=$(_vm_config "region")
    local size=$(_vm_config "size")

    echo "[vm] Create command for $provider:"
    echo ""

    case "$provider" in
        hcloud)
            echo "hcloud server create --name $name --type ${size:-cx22} --image ubuntu-24.04 --location ${region:-fsn1}"
            ;;
        gcloud)
            local project=$(_vm_config "project")
            echo "gcloud compute instances create $name --zone=$region --machine-type=${size:-e2-small} --image-family=ubuntu-2404-lts --image-project=ubuntu-os-cloud --project=$project"
            ;;
        doctl)
            echo "doctl compute droplet create $name --region ${region:-nyc1} --size ${size:-s-1vcpu-1gb} --image ubuntu-24-04-x64"
            ;;
        aws)
            echo "aws ec2 run-instances --image-id ami-0c55b159cbfafe1f0 --instance-type ${size:-t3.micro} --key-name ${name}-key"
            ;;
    esac

    echo ""
    echo "Run this command to create the VM, then update .ralph/config.json with the IP."
}
