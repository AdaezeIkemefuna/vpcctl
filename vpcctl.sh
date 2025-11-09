#!/usr/bin/env python3

import subprocess
import json
import sys
import os
import argparse
from pathlib import Path

STATE_DIR = Path("/var/lib/vpcctl")

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def log(level, message):
    colors = {'INFO': Colors.BLUE, 'SUCCESS': Colors.GREEN, 
              'WARNING': Colors.YELLOW, 'ERROR': Colors.RED}
    color = colors.get(level, '')
    print(f"{color}[{level}]{Colors.RESET} {message}")

def run_cmd(cmd, check=True):
    try:
        log('INFO', f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        log('ERROR', f"Command failed: {e.stderr}")
        if check:
            raise
        return False

class StateManager:
    def __init__(self):
        self.state_dir = STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, vpc_name, data):
        state_file = self.state_dir / f"{vpc_name}.json"
        with open(state_file, 'w') as f:
            json.dump(data, f, indent=2)
        log('SUCCESS', f"State saved: {state_file}")
    
    def load(self, vpc_name):
        state_file = self.state_dir / f"{vpc_name}.json"
        if not state_file.exists():
            return None
        with open(state_file, 'r') as f:
            return json.load(f)
    
    def delete(self, vpc_name):
        state_file = self.state_dir / f"{vpc_name}.json"
        if state_file.exists():
            state_file.unlink()
            log('SUCCESS', f"State deleted: {state_file}")
    
    def exists(self, vpc_name):
        return (self.state_dir / f"{vpc_name}.json").exists()
    
    def list_all(self):
        return [f.stem for f in self.state_dir.glob("*.json")]

class VPC:
    def __init__(self, name, cidr):
        self.name = name
        self.cidr = cidr
        self.bridge_name = f"br-{name}"
        self.state_manager = StateManager()
    
    def create(self):
        log('INFO', f"Creating VPC: {self.name} ({self.cidr})")
        
        if self.state_manager.exists(self.name):
            log('ERROR', f"VPC {self.name} already exists")
            return False
        
        try:
            log('INFO', f"Creating bridge: {self.bridge_name}")
            run_cmd(['ip', 'link', 'add', 'name', self.bridge_name, 'type', 'bridge'])
            
            gateway_ip = self._get_gateway_ip()
            
            log('INFO', f"Assigning gateway IP: {gateway_ip}")
            run_cmd(['ip', 'addr', 'add', f"{gateway_ip}/{self._get_prefix()}", 
                    'dev', self.bridge_name])
            
            log('INFO', "Bringing bridge UP")
            run_cmd(['ip', 'link', 'set', self.bridge_name, 'up'])
            
            state_data = {
                'name': self.name,
                'cidr': self.cidr,
                'bridge': self.bridge_name,
                'gateway_ip': gateway_ip,
                'subnets': {}
            }
            self.state_manager.save(self.name, state_data)
            
            log('SUCCESS', f"VPC {self.name} created successfully!")
            log('INFO', f"  Bridge: {self.bridge_name}")
            log('INFO', f"  Gateway: {gateway_ip}")
            
            return True
            
        except Exception as e:
            log('ERROR', f"Failed to create VPC: {e}")
            run_cmd(['ip', 'link', 'del', self.bridge_name], check=False)
            return False
    
    def delete(self):
        log('INFO', f"Deleting VPC: {self.name}")
        
        state = self.state_manager.load(self.name)
        if not state:
            log('WARNING', f"VPC {self.name} does not exist")
            return False
        
        try:
            log('INFO', f"Deleting bridge: {state['bridge']}")
            run_cmd(['ip', 'link', 'del', state['bridge']], check=False)
            
            self.state_manager.delete(self.name)
            
            log('SUCCESS', f"VPC {self.name} deleted successfully!")
            return True
            
        except Exception as e:
            log('ERROR', f"Failed to delete VPC: {e}")
            return False
    
    def _get_gateway_ip(self):
        parts = self.cidr.split('/')[0].split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    
    def _get_prefix(self):
        return self.cidr.split('/')[1]
    
    @staticmethod
    def list_all():
        manager = StateManager()
        vpcs = manager.list_all()
        
        if not vpcs:
            log('INFO', "No VPCs found")
            return
        
        print(f"\n{'='*60}")
        print("Existing VPCs:")
        print(f"{'='*60}")
        
        for vpc_name in vpcs:
            state = manager.load(vpc_name)
            print(f"\n  {Colors.GREEN}•{Colors.RESET} {vpc_name}")
            print(f"    CIDR: {state['cidr']}")
            print(f"    Bridge: {state['bridge']}")
            print(f"    Gateway: {state['gateway_ip']}")
            print(f"    Subnets: {len(state['subnets'])}")
        
        print()
    
    @staticmethod
    def show(vpc_name):
        manager = StateManager()
        state = manager.load(vpc_name)
        
        if not state:
            log('ERROR', f"VPC {vpc_name} not found")
            return
        
        print(f"\n{'='*60}")
        print(f"VPC: {state['name']}")
        print(f"{'='*60}")
        print(f"CIDR:    {state['cidr']}")
        print(f"Bridge:  {state['bridge']}")
        print(f"Gateway: {state['gateway_ip']}")
        print(f"\nSubnets: {len(state['subnets'])}")
        
        if state['subnets']:
            for name, subnet in state['subnets'].items():
                print(f"  • {name} ({subnet['cidr']})")
        
        print()

def main():
    if os.geteuid() != 0:
        log('ERROR', "This tool requires root privileges. Run with sudo.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(prog='vpcctl', description='VPC Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    create_parser = subparsers.add_parser('create', help='Create a new VPC')
    create_parser.add_argument('name', help='VPC name')
    create_parser.add_argument('cidr', help='CIDR block (e.g., 10.0.0.0/16)')
    
    delete_parser = subparsers.add_parser('del', help='Delete a VPC')
    delete_parser.add_argument('name', help='VPC name')
    
    list_parser = subparsers.add_parser('list', help='List all VPCs')
    
    show_parser = subparsers.add_parser('show', help='Show VPC details')
    show_parser.add_argument('name', help='VPC name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    try:
        if args.command == 'create':
            vpc = VPC(args.name, args.cidr)
            success = vpc.create()
            sys.exit(0 if success else 1)
        
        elif args.command == 'del':
            vpc = VPC(args.name, '')
            success = vpc.delete()
            sys.exit(0 if success else 1)
        
        elif args.command == 'list':
            VPC.list_all()
        
        elif args.command == 'show':
            VPC.show(args.name)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        log('ERROR', f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()