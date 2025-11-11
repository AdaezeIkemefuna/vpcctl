#!/bin/bash

echo "╔════════════════════════════════════════╗"
echo "║   VPCctl Complete Cleanup Script      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/6] Cleaning up VPCs via vpcctl...${NC}"
vpcctl cleanup-all 2>/dev/null || echo "No VPCs found via vpcctl"

echo -e "${YELLOW}[2/6] Removing all network namespaces...${NC}"
for ns in $(ip netns list | awk '{print $1}'); do
    if [[ $ns == ns-* ]]; then
        echo "  Deleting namespace: $ns"
        ip netns del "$ns" 2>/dev/null
    fi
done

echo -e "${YELLOW}[3/6] Removing veth interfaces...${NC}"
for iface in $(ip link show | grep -E "vb|vn|peer-|veth-" | awk -F: '{print $2}' | awk '{print $1}'); do
    echo "  Deleting interface: $iface"
    ip link del "$iface" 2>/dev/null
done

echo -e "${YELLOW}[4/6] Removing VPC bridges...${NC}"
# Only remove bridges from our state files
if [ -d "/var/lib/vpcctl" ]; then
    for statefile in /var/lib/vpcctl/*.json; do
        if [ -f "$statefile" ]; then
            bridge=$(grep -oP '"bridge":\s*"\K[^"]+' "$statefile")
            if [ -n "$bridge" ]; then
                echo "  Deleting bridge: $bridge"
                ip link del "$bridge" 2>/dev/null
            fi
        fi
    done
fi

#check for any orphaned br-vpc* bridges
for bridge in $(ip link show type bridge | grep "br-vpc" | awk -F: '{print $2}' | awk '{print $1}'); do
    echo "  Deleting orphaned bridge: $bridge"
    ip link del "$bridge" 2>/dev/null
done

echo -e "${YELLOW}[5/6] Cleaning iptables rules...${NC}"
# Remove vpcctl-related FORWARD rules
iptables -S FORWARD | grep -E "br-|MASQUERADE" | sed 's/-A/-D/' | while read rule; do
    iptables $rule 2>/dev/null
done

# Remove NAT rules
iptables -t nat -S POSTROUTING | grep MASQUERADE | sed 's/-A/-D/' | while read rule; do
    iptables -t nat $rule 2>/dev/null
done

echo -e "${YELLOW}[6/6] Cleaning state files...${NC}"
if [ -d "/var/lib/vpcctl" ]; then
    rm -rf /var/lib/vpcctl/*.json
    echo "  State files removed"
fi

# Clean up temporary web server files
rm -rf /tmp/webserver-* 2>/dev/null
rm -rf /etc/netns/ns-* 2>/dev/null

echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""
echo "Verification:"
echo "  Namespaces: $(ip netns list | wc -l)"
echo "  Bridges: $(ip link show type bridge | grep br- | wc -l)"
echo "  VPCs: $(ls /var/lib/vpcctl/*.json 2>/dev/null | wc -l)"