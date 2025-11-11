# vpcctl

A simple VPC management tool using native Linux networking.

## What it does

Creates and manages Virtual Private Clouds (VPCs) on Linux using bridges and network namespaces. Each VPC gets its own isolated network with configurable CIDR blocks.

## Installation

```bash
# Clone the repository
git clone https://github.com/AdaezeIkemefuna/vpcctl.git
cd vpcctl
```

### Quick run (from repo directory)

```bash
sudo python3 ./vpcctl create my-vpc 10.0.0.0/16
```

### Recommended: Install system-wide

```bash
# Copy script to system binaries
sudo cp vpcctl /usr/local/bin/vpcctl
sudo chmod +x /usr/local/bin/vpcctl

# Create state directory
sudo mkdir -p /var/lib/vpcctl
```

**Why these locations?**

- `/usr/local/bin` - Makes `vpcctl` available from anywhere in your terminal (it's in your `$PATH`)
- `/var/lib/vpcctl` - Stores VPC state persistently. This is where vpcctl remembers your VPC configurations across reboots.

## Usage

```bash
# Create a VPC
sudo vpcctl create demo-vpc 10.0.0.0/16

# List all VPCs
sudo vpcctl list

# Show VPC details
sudo vpcctl show demo-vpc

# Delete a VPC
sudo vpcctl del demo-vpc
```

## Requirements

- Linux with `ip` command (iproute2)
- Python 3.6+
- Root privileges (sudo)

## State Storage

VPC configurations are stored as JSON files in `/var/lib/vpcctl/`. Each VPC gets its own state file containing bridge name, CIDR, gateway IP, and subnet information.
