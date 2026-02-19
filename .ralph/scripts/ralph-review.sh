#!/bin/bash
# ralph-review.sh - Öppna portar för manuell verifiering
#
# Användning: ./ralph review
#
# Skapar SSH-tunnlar så att du kan testa appen i din browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ladda config
RALPH_CONFIG="$HOME/.ralph-vm"
if [ -f "$RALPH_CONFIG" ]; then
    source "$RALPH_CONFIG"
fi

VM_IP="${VM_IP:-}"
VM_USER="${VM_USER:-ralph}"

# Färger
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ██████╗ ███████╗██╗   ██╗██╗███████╗██╗    ██╗"
echo "  ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║    ██║"
echo "  ██████╔╝█████╗  ██║   ██║██║█████╗  ██║ █╗ ██║"
echo "  ██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║"
echo "  ██║  ██║███████╗ ╚████╔╝ ██║███████╗╚███╔███╔╝"
echo "  ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝ "
echo -e "${NC}"

if [ -z "$VM_IP" ]; then
    echo "❌ VM_IP ej konfigurerad"
    echo "   Kör 'ralph setup' först"
    exit 1
fi

echo "🔗 Öppnar tunnlar till $VM_IP..."
echo ""

# Stäng eventuella gamla tunnlar
pkill -f "ssh.*-L 5173:localhost:5173.*$VM_IP" 2>/dev/null || true
pkill -f "ssh.*-L 54321:localhost:54321.*$VM_IP" 2>/dev/null || true
pkill -f "ssh.*-L 54324:localhost:54324.*$VM_IP" 2>/dev/null || true

# Öppna nya tunnlar
echo "📦 Dev-server (5173)..."
ssh -f -N -L 5173:localhost:5173 "$VM_USER@$VM_IP" && echo "   ✅ localhost:5173 → VM"

echo "📦 Supabase API (54321)..."
ssh -f -N -L 54321:localhost:54321 "$VM_USER@$VM_IP" && echo "   ✅ localhost:54321 → VM"

echo "📦 Mailpit (54324)..."
ssh -f -N -L 54324:localhost:54324 "$VM_USER@$VM_IP" && echo "   ✅ localhost:54324 → VM"

echo ""
echo -e "${GREEN}✅ Tunnlar öppna!${NC}"
echo ""
echo "🌐 Öppna i browser:"
echo "   App:     http://localhost:5173"
echo "   Mailpit: http://localhost:54324"
echo ""
echo "💡 Stäng tunnlar med: pkill -f 'ssh.*-L.*$VM_IP'"
