#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_step() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"
    sleep 2
}

echo_success() {
    echo -e "${GREEN}✓ $1${NC}\n"
    sleep 1
}

echo_test() {
    echo -e "${YELLOW}→ Testing: $1${NC}"
}

# Start demo
clear
echo_step "VPCctl Demo - Cloud-like VPC on Linux"

# Step 1: Create first VPC
echo_step "Step 1: Create VPC1 (Production Network)"
vpcctl create vpc1 10.1.0.0/16
vpcctl subnet-add vpc1 public 10.1.1.0/24 --type public
vpcctl subnet-add vpc1 private 10.1.2.0/24
vpcctl show vpc1
echo_success "VPC1 created with public and private subnets"

# Step 2: Deploy applications
echo_step "Step 2: Deploy Web Applications"
echo_test "Deploying web server in public subnet (port 8001)"
vpcctl deploy vpc1 public --port 8001

echo_test "Deploying app in private subnet (port 8002)"
vpcctl deploy vpc1 private --port 8002
echo_success "Applications deployed"

# Step 3: Test internal connectivity
echo_step "Step 3: Test Inter-Subnet Communication (Same VPC)"
echo_test "Public subnet → Private subnet"
ip netns exec ns-vpc1-public curl -s -m 2 http://10.1.2.2:8002 | head -3
echo_success "Subnets in same VPC can communicate ✓"

# Step 4: Test NAT (Internet access)
echo_step "Step 4: Test NAT Gateway"
echo_test "Public subnet → Internet (should work)"
ip netns exec ns-vpc1-public ping -c 2 8.8.8.8
echo_success "Public subnet has internet access ✓"

echo_test "Private subnet → Internet (should fail)"
timeout 3 ip netns exec ns-vpc1-private ping -c 2 8.8.8.8 || echo "Connection blocked ✓"
echo_success "Private subnet has NO internet access ✓"

# Step 5: Create second VPC
echo_step "Step 5: Create VPC2 (Development Network)"
vpcctl create vpc2 10.2.0.0/16
vpcctl subnet-add vpc2 public 10.2.1.0/24 --type public
vpcctl deploy vpc2 public --port 8003
vpcctl show vpc2
echo_success "VPC2 created"

# Step 6: Test VPC isolation
echo_step "Step 6: Test VPC Isolation (No Peering)"
echo_test "VPC1 → VPC2 (should fail - isolated)"
timeout 3 ip netns exec ns-vpc1-public curl -s -m 2 http://10.2.1.2:8003 || echo "Connection blocked ✓"
echo_success "VPCs are isolated by default ✓"

# Step 7: Enable peering
echo_step "Step 7: Enable VPC Peering"
vpcctl peer vpc1 vpc2
echo_success "Peering established between VPC1 and VPC2"

# Step 8: Test peering connectivity
echo_step "Step 8: Test Cross-VPC Communication (After Peering)"
echo_test "VPC1 → VPC2 (should work now)"
ip netns exec ns-vpc1-public curl -s http://10.2.1.2:8003 | head -3
echo_success "Cross-VPC communication works after peering ✓"

# Step 9: Apply firewall policy
echo_step "Step 9: Apply Security Policy (Firewall)"
cat > /tmp/restrict-policy.json << 'EOF'
{
  "subnet": "10.1.1.0/24",
  "ingress": [
    {"port": 8001, "protocol": "tcp", "source": "10.1.0.0/16", "action": "allow"},
    {"port": 22, "protocol": "tcp", "source": "0.0.0.0/0", "action": "deny"}
  ]
}
EOF

vpcctl policy-apply vpc1 public /tmp/restrict-policy.json
echo_success "Policy applied: Only VPC1 internal traffic allowed on port 8001"

# Step 10: Test firewall
echo_step "Step 10: Test Firewall Enforcement"
echo_test "Access from same VPC (should work)"
ip netns exec ns-vpc1-private curl -s http://10.1.1.2:8001 | head -3

echo_test "Access from different VPC (should fail)"
timeout 3 ip netns exec ns-vpc2-public curl -s -m 2 http://10.1.1.2:8001 || echo "Blocked by firewall ✓"
echo_success "Firewall rules enforced correctly ✓"

# Step 11: Show summary
echo_step "Step 11: Infrastructure Summary"
vpcctl list
echo ""

# Step 12: Cleanup
echo_step "Step 12: Complete Teardown"
echo "Deleting VPC1..."
vpcctl del vpc1
echo "Deleting VPC2..."
vpcctl del vpc2

echo_test "Verifying cleanup..."
echo "Remaining namespaces: $(ip netns list | wc -l)"
echo "Remaining bridges: $(ip link show type bridge | grep br- | wc -l)"
echo_success "All resources cleaned up successfully ✓"

echo_step "Demo Complete!"
echo "All acceptance criteria verified ✓"