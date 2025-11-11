import ipaddress
import re
from vpcctl_lib.state import log

class Validators:
    
    @staticmethod
    def validate_vpc_name(name):
        """Validate VPC name format"""
        if not name:
            log('ERROR', "VPC name cannot be empty")
            return False
        
        if len(name) > 32:
            log('ERROR', "VPC name too long (max 32 characters)")
            return False
        
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            log('ERROR', "VPC name can only contain letters, numbers, and hyphens")
            return False
        
        return True
    
    @staticmethod
    def validate_subnet_name(name):
        """Validate subnet name format"""
        if not name:
            log('ERROR', "Subnet name cannot be empty")
            return False
        
        if len(name) > 16:
            log('ERROR', "Subnet name too long (max 16 characters)")
            return False
        
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            log('ERROR', "Subnet name can only contain letters, numbers, and hyphens")
            return False
        
        return True
    
    @staticmethod
    def validate_cidr(cidr):
        """Validate CIDR notation"""
        try:
            network = ipaddress.ip_network(cidr)
            
            # Check if it's a reasonable network size
            if network.prefixlen < 8:
                log('WARNING', f"Very large network /{network.prefixlen}, are you sure?")
            
            if network.prefixlen > 28:
                log('WARNING', f"Very small network /{network.prefixlen}, limited hosts available")
            
            return True
        except ValueError as e:
            log('ERROR', f"Invalid CIDR format: {e}")
            return False
    
    @staticmethod
    def validate_port(port):
        """Validate port number"""
        try:
            port = int(port)
            if port < 1 or port > 65535:
                log('ERROR', f"Port must be between 1 and 65535")
                return False
            return True
        except ValueError:
            log('ERROR', f"Invalid port number: {port}")
            return False
    
    @staticmethod
    def validate_subnet_within_vpc(vpc_cidr, subnet_cidr):
        """Validate that subnet is within VPC CIDR"""
        try:
            vpc_network = ipaddress.ip_network(vpc_cidr)
            subnet_network = ipaddress.ip_network(subnet_cidr)
            
            if not subnet_network.subnet_of(vpc_network):
                log('ERROR', f"Subnet {subnet_cidr} is not within VPC CIDR {vpc_cidr}")
                return False
            
            return True
        except Exception as e:
            log('ERROR', f"CIDR validation error: {e}")
            return False
    
    @staticmethod
    def check_subnet_overlap(existing_subnets, new_subnet_cidr):
        """Check if new subnet overlaps with existing subnets"""
        try:
            new_network = ipaddress.ip_network(new_subnet_cidr)
            
            for subnet_name, subnet_data in existing_subnets.items():
                existing_network = ipaddress.ip_network(subnet_data['cidr'])
                
                if new_network.overlaps(existing_network):
                    log('ERROR', f"Subnet {new_subnet_cidr} overlaps with existing subnet {subnet_name} ({subnet_data['cidr']})")
                    return False
            
            return True
        except Exception as e:
            log('ERROR', f"Overlap check error: {e}")
            return False