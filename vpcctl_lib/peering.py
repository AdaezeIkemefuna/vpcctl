import subprocess
import ipaddress
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

class PeeringManager:
    
    @staticmethod
    def peer(vpc1_name, vpc2_name):
        """Create a peering connection between two VPCs"""
        manager = StateManager()
        
        state1 = manager.load(vpc1_name)
        state2 = manager.load(vpc2_name)
        
        if not state1:
            log('ERROR', f"VPC {vpc1_name} not found")
            return False
        
        if not state2:
            log('ERROR', f"VPC {vpc2_name} not found")
            return False
        
        # Check for CIDR overlap
        try:
            cidr1 = ipaddress.ip_network(state1['cidr'])
            cidr2 = ipaddress.ip_network(state2['cidr'])
            
            if cidr1.overlaps(cidr2):
                log('ERROR', f"VPC CIDRs overlap: {state1['cidr']} and {state2['cidr']}")
                return False
        except Exception as e:
            log('ERROR', f"Invalid CIDR: {e}")
            return False
        
        log('INFO', f"Creating peering between {vpc1_name} and {vpc2_name}")
        
        try:
            # Create veth pair to connect bridges
            veth1 = f"peer-{vpc1_name}-{vpc2_name}"
            veth2 = f"peer-{vpc2_name}-{vpc1_name}"
            
            log('INFO', f"Creating veth pair: {veth1} <-> {veth2}")
            run_cmd(['ip', 'link', 'add', veth1, 'type', 'veth', 'peer', 'name', veth2])
            
            # Attach each end to respective bridges
            log('INFO', f"Attaching {veth1} to {state1['bridge']}")
            run_cmd(['ip', 'link', 'set', veth1, 'master', state1['bridge']])
            run_cmd(['ip', 'link', 'set', veth1, 'up'])
            
            log('INFO', f"Attaching {veth2} to {state2['bridge']}")
            run_cmd(['ip', 'link', 'set', veth2, 'master', state2['bridge']])
            run_cmd(['ip', 'link', 'set', veth2, 'up'])

            # Allow forwarding between the two VPC bridges
            log('INFO', f"Enabling forwarding between {state1['bridge']} and {state2['bridge']}")
            run_cmd(['iptables', '-A', 'FORWARD', '-i', state1['bridge'], 
                    '-o', state2['bridge'], '-j', 'ACCEPT'], check=False)
            run_cmd(['iptables', '-A', 'FORWARD', '-i', state2['bridge'], 
                    '-o', state1['bridge'], '-j', 'ACCEPT'], check=False)
            
            # Add routes from VPC1 subnets to VPC2 CIDR (via their own local gateway)
            for subnet_name, subnet_data in state1['subnets'].items():
                ns_name = subnet_data['namespace']
                local_gateway = subnet_data['gateway_ip']
                log('INFO', f"Adding route from {vpc1_name}/{subnet_name} to {state2['cidr']} via {local_gateway}")
                run_cmd(['ip', 'netns', 'exec', ns_name, 'ip', 'route', 'add',
                        state2['cidr'], 'via', local_gateway], check=False)

            # Add routes from VPC2 subnets to VPC1 CIDR (via their own local gateway)
            for subnet_name, subnet_data in state2['subnets'].items():
                ns_name = subnet_data['namespace']
                local_gateway = subnet_data['gateway_ip']
                log('INFO', f"Adding route from {vpc2_name}/{subnet_name} to {state1['cidr']} via {local_gateway}")
                run_cmd(['ip', 'netns', 'exec', ns_name, 'ip', 'route', 'add',
                        state1['cidr'], 'via', local_gateway], check=False)
            
            # Save peering info to state
            if 'peerings' not in state1:
                state1['peerings'] = {}
            if 'peerings' not in state2:
                state2['peerings'] = {}
            
            state1['peerings'][vpc2_name] = {'veth': veth1, 'peer_veth': veth2}
            state2['peerings'][vpc1_name] = {'veth': veth2, 'peer_veth': veth1}
            
            manager.save(vpc1_name, state1)
            manager.save(vpc2_name, state2)
            
            log('SUCCESS', f"Peering established between {vpc1_name} and {vpc2_name}")
            return True
            
        except Exception as e:
            log('ERROR', f"Failed to create peering: {e}")
            # Cleanup
            run_cmd(['ip', 'link', 'del', veth1], check=False)
            return False