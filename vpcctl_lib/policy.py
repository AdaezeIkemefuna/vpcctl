import json
import subprocess
from vpcctl_lib.state import StateManager, log

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

class PolicyManager:
    
    @staticmethod
    def apply_policy(vpc_name, subnet_name, policy_file):
        """Apply security policy from JSON file to a subnet"""
        manager = StateManager()
        state = manager.load(vpc_name)
        
        if not state:
            log('ERROR', f"VPC {vpc_name} not found")
            return False
        
        if subnet_name not in state['subnets']:
            log('ERROR', f"Subnet {subnet_name} not found in VPC {vpc_name}")
            return False
        
        try:
            with open(policy_file, 'r') as f:
                policy = json.load(f)
        except Exception as e:
            log('ERROR', f"Failed to load policy file: {e}")
            return False
        
        subnet = state['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        log('INFO', f"Applying security policy to {vpc_name}/{subnet_name}")
        
        try:
            log('INFO', "Setting default policies to DROP")
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'INPUT', 'DROP'], check=False)
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'FORWARD', 'DROP'], check=False)
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'OUTPUT', 'ACCEPT'], check=False)
            
            log('INFO', "Allowing established/related connections")
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-A', 'INPUT',
                    '-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'], check=False)
            
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-A', 'INPUT',
                    '-i', 'lo', '-j', 'ACCEPT'], check=False)
            
            if 'ingress' in policy:
                for rule in policy['ingress']:
                    PolicyManager._apply_ingress_rule(ns_name, rule)
            
            if 'egress' in policy:
                for rule in policy['egress']:
                    PolicyManager._apply_egress_rule(ns_name, rule)
            
            if 'policies' not in state['subnets'][subnet_name]:
                state['subnets'][subnet_name]['policies'] = []
            state['subnets'][subnet_name]['policies'].append(policy_file)
            manager.save(vpc_name, state)
            
            log('SUCCESS', f"Policy applied to {vpc_name}/{subnet_name}")
            return True
            
        except Exception as e:
            log('ERROR', f"Failed to apply policy: {e}")
            return False
    
    @staticmethod
    def _apply_ingress_rule(ns_name, rule):
        """Apply a single ingress rule"""
        port = rule.get('port')
        protocol = rule.get('protocol', 'tcp')
        source = rule.get('source', '0.0.0.0/0')
        action = rule.get('action', 'deny')
        
        iptables_action = 'ACCEPT' if action == 'allow' else 'DROP'
        
        log('INFO', f"  Ingress: {action} {protocol}/{port} from {source}")
        
        cmd = ['ip', 'netns', 'exec', ns_name, 'iptables', '-A', 'INPUT',
               '-p', protocol, '-s', source]
        
        if port:
            cmd.extend(['--dport', str(port)])
        
        cmd.extend(['-j', iptables_action])
        run_cmd(cmd, check=False)
    
    @staticmethod
    def _apply_egress_rule(ns_name, rule):
        """Apply a single egress rule"""
        port = rule.get('port')
        protocol = rule.get('protocol', 'tcp')
        destination = rule.get('destination', '0.0.0.0/0')
        action = rule.get('action', 'deny')
        
        iptables_action = 'ACCEPT' if action == 'allow' else 'DROP'
        
        log('INFO', f"  Egress: {action} {protocol}/{port} to {destination}")
        
        cmd = ['ip', 'netns', 'exec', ns_name, 'iptables', '-A', 'OUTPUT',
               '-p', protocol, '-d', destination]
        
        if port:
            cmd.extend(['--dport', str(port)])
        
        cmd.extend(['-j', iptables_action])
        run_cmd(cmd, check=False)
    
    @staticmethod
    def clear_policy(vpc_name, subnet_name):
        """Clear all firewall rules from a subnet"""
        manager = StateManager()
        state = manager.load(vpc_name)
        
        if not state:
            log('ERROR', f"VPC {vpc_name} not found")
            return False
        
        if subnet_name not in state['subnets']:
            log('ERROR', f"Subnet {subnet_name} not found in VPC {vpc_name}")
            return False
        
        subnet = state['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        log('INFO', f"Clearing security policy from {vpc_name}/{subnet_name}")
        
        try:
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-F'], check=False)
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'INPUT', 'ACCEPT'], check=False)
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'FORWARD', 'ACCEPT'], check=False)
            run_cmd(['ip', 'netns', 'exec', ns_name, 'iptables', '-P', 'OUTPUT', 'ACCEPT'], check=False)
            
            if 'policies' in state['subnets'][subnet_name]:
                del state['subnets'][subnet_name]['policies']
            manager.save(vpc_name, state)
            
            log('SUCCESS', f"Policy cleared from {vpc_name}/{subnet_name}")
            return True
            
        except Exception as e:
            log('ERROR', f"Failed to clear policy: {e}")
            return False
    
    @staticmethod
    def show_policy(vpc_name, subnet_name):
        """Show current firewall rules for a subnet"""
        manager = StateManager()
        state = manager.load(vpc_name)
        
        if not state:
            log('ERROR', f"VPC {vpc_name} not found")
            return
        
        if subnet_name not in state['subnets']:
            log('ERROR', f"Subnet {subnet_name} not found in VPC {vpc_name}")
            return
        
        subnet = state['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        print(f"\n{'='*60}")
        print(f"Firewall Rules: {vpc_name}/{subnet_name}")
        print(f"{'='*60}")
        
        result = subprocess.run(
            ['ip', 'netns', 'exec', ns_name, 'iptables', '-L', '-v', '-n'],
            capture_output=True, text=True
        )
        print(result.stdout)