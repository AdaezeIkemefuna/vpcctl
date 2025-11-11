# vpcctl

A powerful Linux-native **VPC management tool** that lets you build isolated, cloud-style virtual networks locally — using only bridges, namespaces, and iptables.

---

## 🧭 Overview

`vpcctl` creates and manages **Virtual Private Clouds (VPCs)** on Linux using:

- Linux **bridges** for Layer 2 isolation
- **network namespaces** for subnet environments
- **iptables** for routing, NAT, and peering
- **JSON-based persistent state** for VPC configuration

It behaves much like AWS VPCs — but entirely locally.

---

## ✨ Features

✅ Create isolated VPCs with custom CIDR blocks  
✅ Add **private** or **public** subnets (with NAT)  
✅ Persistent **state management** across reboots  
✅ **Peering** between VPCs for inter-VPC communication  
✅ Auto-recovery of bridges if missing  
✅ Deploy simple **HTTP workloads** into namespaces  
✅ Built-in **connectivity tests** (ping between subnets)  
✅ Colored logging for readability  
✅ Modular codebase (`vpcctl_lib` for state, policy, and peering logic)

---

## ⚙️ Installation

### 1. Clone and install

```bash
git clone https://github.com/AdaezeIkemefuna/vpcctl.git
cd vpcctl

sudo cp vpcctl /usr/local/bin/vpcctl
sudo chmod +x /usr/local/bin/vpcctl

# Copy supporting libraries
sudo mkdir -p /usr/local/lib/python-vpcctl
sudo cp -r vpcctl_lib /usr/local/lib/python-vpcctl/

# Create persistent state directory
sudo mkdir -p /var/lib/vpcctl
```

**Why these locations?**

| Path                           | Purpose                                |
| ------------------------------ | -------------------------------------- |
| `/usr/local/bin`               | Allows running `vpcctl` from anywhere  |
| `/usr/local/lib/python-vpcctl` | Houses internal Python library modules |
| `/var/lib/vpcctl`              | Stores VPC state as JSON files         |

## Usage

### 🏗️ Create a VPC

```bash
sudo vpcctl create my-vpc 10.0.0.0/16
```

### ➕ Add a Subnet

```bash
sudo vpcctl subnet-add my-vpc subnet-a 10.0.1.0/24 private
sudo vpcctl subnet-add my-vpc public-subnet 10.0.2.0/24 public
```

- Private subnets are isolated.
- Public subnets get NAT to the internet automatically.

### 🌐 List All VPCs

```bash
sudo vpcctl list
```

### 🔍 Show VPC Details

```bash
sudo vpcctl show my-vpc
```

### 🧹 Delete a VPC

```bash
sudo vpcctl del my-vpc
```

- Cleans up namespaces, bridges, NAT, and peerings automatically.

### 🔄 Test Connectivity

Run built-in connectivity tests inside VPC namespaces:

```bash
sudo vpcctl test my-vpc
```

You can also test a specific subnet:

```bash
sudo vpcctl test my-vpc subnet-a
```

## 🚀 Deploy Workload (Demo Web Server)

Start a simple HTTP server inside a subnet namespace:

```bash
sudo vpcctl deploy-workload my-vpc subnet-a --port 8080
```

Then test it from the host:

```bash
curl http://10.0.1.2:8080
```

## 🔗 Peering Between VPCs

Connect two VPCs so their subnets can communicate:

```bash
sudo vpcctl peer vpc-a vpc-b
```

This:

- Creates a veth pair between both bridges
- Sets up forwarding rules in iptables
- Adds routes in all subnet namespaces

## 🧩 Example Workflow

# Create two VPCs

```bash
sudo vpcctl create vpc-a 10.0.0.0/16
sudo vpcctl create vpc-b 10.1.0.0/16
```

# Add subnets

```bash
sudo vpcctl subnet-add vpc-a subnet-a1 10.0.1.0/24 private
sudo vpcctl subnet-add vpc-b subnet-b1 10.1.1.0/24 public
```

# Peer them

```bash
sudo vpcctl peer vpc-a vpc-b
```

# Test connectivity between namespaces

```bash
sudo vpcctl test vpc-a
sudo vpcctl test vpc-b
```

# Deploy workloads

```bash
sudo vpcctl deploy-workload vpc-a subnet-a1
sudo vpcctl deploy-workload vpc-b subnet-b1
```

## 🧱 Requirements

- Linux with `ip` command (iproute2)
- Python 3.6+
- Root privileges (sudo)

## 📦 State Storage

All persistent configuration is stored in `/var/lib/vpcctl/` as JSON files.

### Example

```bash

{
  "name": "demo-vpc",
  "cidr": "10.0.0.0/16",
  "bridge": "br-demo-vpc",
  "subnets": {
    "subnet-a": {
      "cidr": "10.0.1.0/24",
      "type": "private",
      "namespace": "ns-demo-vpc-subnet-a",
      "gateway_ip": "10.0.1.1",
      "namespace_ip": "10.0.1.2"
    },
  },
  "peerings": {}
}

```

## 🧩 Internal Structure

| Module                  | Purpose                                        |
| ----------------------- | ---------------------------------------------- |
| `vpcctl`                | CLI entrypoint and orchestration               |
| `vpcctl_lib/state.py`   | Handles persistent VPC state management        |
| `vpcctl_lib/policy.py`  | Policy and security rule management _(future)_ |
| `vpcctl_lib/peering.py` | VPC peering and routing setup                  |

## 🧰 Command Reference

| Command                                            | Description                            |     |
| -------------------------------------------------- | -------------------------------------- | --- |
| `vpcctl create <vpc-name> <cidr>`                  | Create a new VPC                       |     |
| `vpcctl subnet-add <vpc> <subnet-name> <cidr>`     | Add subnet to VPC                      |     |
| `vpcctl list`                                      | List all VPCs                          |     |
| `vpcctl show <vpc>`                                | Show details of a VPC                  |     |
| `vpcctl del <vpc>`                                 | Delete a VPC                           |     |
| `vpcctl test <vpc> [subnet]`                       | Test connectivity inside VPC or subnet |     |
| `vpcctl peer <vpc-a> <vpc-b>`                      | Create peering between VPCs            |     |
| `vpcctl deploy-workload <vpc> <subnet> [--port N]` | Deploy demo HTTP server in subnet      |     |
| `vpcctl --help`                                    | Show help message                      |     |

## 🎬 Quick Demo

Run the automated demo script to see all features in action:

```bash
sudo bash demo.sh
```

This demo:

- Creates two VPCs with public/private subnets
- Deploys web applications in each subnet
- Tests inter-subnet communication
- Demonstrates NAT gateway functionality
- Shows VPC isolation and peering
- Applies and tests security policies
- Performs complete cleanup

Perfect for presentations or verification!

🧪 Testing & Validation
Manual Testing

```bash
# Test inter-subnet communication
sudo ip netns exec ns-vpc1-public ping 10.1.2.2


# Test internet access (public subnet)
sudo ip netns exec ns-vpc1-public ping 8.8.8.8

# Test deployed application
curl http://10.1.1.2:8001
```

Automated Testing with Makefile

```bash
make test       # Run basic functionality tests
sudo make demo       # Run full demo scenario with root privileges
make clean      # Remove all VPCs
```

## 🔒 Security Policies

Apply firewall rules to subnets using JSON policy files:

```bash
# Create policy file
cat > web-policy.json << 'EOF'
{
  "subnet": "10.1.1.0/24",
  "ingress": [
    {"port": 80, "protocol": "tcp", "source": "0.0.0.0/0", "action": "allow"},
    {"port": 8001, "protocol": "tcp", "source": "10.1.0.0/16", "action": "allow"},
    {"port": 22, "protocol": "tcp", "source": "0.0.0.0/0", "action": "deny"}
  ]
}
EOF

# Apply policy
sudo vpcctl policy-apply vpc1 public web-policy.json

# View active rules
sudo vpcctl policy-show vpc1 public

# Clear policy
sudo vpcctl policy-clear vpc1 public
```

Policy features:

- Default deny with explicit allows
- Source IP/CIDR filtering
- Port and protocol-specific rules
- Supports both ingress and egress rules

## 🧹 Cleanup

Clean up specific VPC

```bash
sudo vpcctl del my-vpc
```

Clean up all VPCs

```bash
sudo vpcctl cleanup-all
```

## 🛠️ Makefile Commands

```bash
make install    # Install vpcctl system-wide
make uninstall  # Remove vpcctl from system
make test       # Run basic functionality tests
make clean      # Remove all VPCs
make demo       # Run full demo scenario
make help       # Show all available commands
```
