import subprocess
from vpcctl_lib.state import log

def run_cmd(cmd, check=True):
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return False

class CleanupManager:
    
    @staticmethod
    def verify_cleanup(vpc_name, state):
        """Verify all resources are cleaned up"""
        log('INFO', f"Verifying cleanup for {vpc_name}")
        
        issues = []
        
        # Check if bridge still exists
        result = subprocess.run(['ip', 'link', 'show', state['bridge']], 
                              capture_output=True, check=False)
        if result.returncode == 0:
            issues.append(f"Bridge {state['bridge']} still exists")
        
        # Check if namespaces still exist
        for subnet_name, subnet_data in state['subnets'].items():
            ns_name = subnet_data['namespace']
            result = subprocess.run(['ip', 'netns', 'list'], 
                                  capture_output=True, text=True)
            if ns_name in result.stdout:
                issues.append(f"Namespace {ns_name} still exists")
        
        # Check for leftover veth interfaces
        result = subprocess.run(['ip', 'link', 'show'], 
                              capture_output=True, text=True)
        for subnet_name, subnet_data in state['subnets'].items():
            veth_br = subnet_data['veth_br']
            if veth_br in result.stdout:
                issues.append(f"Veth interface {veth_br} still exists")
        
        # Check for peering interfaces
        if 'peerings' in state:
            for peer_vpc, peer_data in state['peerings'].items():
                if peer_data['veth'] in result.stdout:
                    issues.append(f"Peering interface {peer_data['veth']} still exists")
        
        if issues:
            log('WARNING', "Cleanup verification found issues:")
            for issue in issues:
                log('WARNING', f"  - {issue}")
            return False
        
        log('SUCCESS', "Cleanup verification passed")
        return True
    
    @staticmethod
    def force_cleanup(vpc_name, state):
        """Force cleanup of all resources related to a VPC"""
        log('INFO', f"Force cleaning up {vpc_name}")
        
        # Kill any processes in namespaces
        for subnet_name, subnet_data in state['subnets'].items():
            ns_name = subnet_data['namespace']
            log('INFO', f"Killing processes in {ns_name}")
            run_cmd(['ip', 'netns', 'pids', ns_name], check=False)
            result = subprocess.run(['ip', 'netns', 'pids', ns_name], 
                                  capture_output=True, text=True, check=False)
            for pid in result.stdout.split():
                run_cmd(['kill', '-9', pid], check=False)
        
        # Delete namespaces
        for subnet_name, subnet_data in state['subnets'].items():
            ns_name = subnet_data['namespace']
            log('INFO', f"Deleting namespace {ns_name}")
            run_cmd(['ip', 'netns', 'del', ns_name], check=False)
        
        # Delete veth interfaces
        for subnet_name, subnet_data in state['subnets'].items():
            veth_br = subnet_data['veth_br']
            log('INFO', f"Deleting veth {veth_br}")
            run_cmd(['ip', 'link', 'del', veth_br], check=False)
        
        # Delete peering interfaces
        if 'peerings' in state:
            for peer_vpc, peer_data in state['peerings'].items():
                log('INFO', f"Deleting peering interface {peer_data['veth']}")
                run_cmd(['ip', 'link', 'del', peer_data['veth']], check=False)
        
        # Delete bridge
        log('INFO', f"Deleting bridge {state['bridge']}")
        run_cmd(['ip', 'link', 'del', state['bridge']], check=False)
        
        log('SUCCESS', f"Force cleanup completed for {vpc_name}")