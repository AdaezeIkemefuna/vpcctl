.PHONY: install uninstall test clean help

SCRIPT_NAME = vpcctl
INSTALL_DIR = /usr/local/bin
LIB_DIR = /usr/local/lib/python-vpcctl
STATE_DIR = /var/lib/vpcctl

help:
	@echo "VPCctl Installation & Management"
	@echo "================================"
	@echo "make install    - Install vpcctl system-wide"
	@echo "make uninstall  - Remove vpcctl from system"
	@echo "make test       - Run basic functionality tests"
	@echo "make clean      - Remove all VPCs and cleanup"
	@echo "make demo       - Run full demo scenario"

install:
	@echo "Installing vpcctl..."
	sudo cp $(SCRIPT_NAME) $(INSTALL_DIR)/$(SCRIPT_NAME)
	sudo chmod +x $(INSTALL_DIR)/$(SCRIPT_NAME)
	sudo mkdir -p $(LIB_DIR)
	sudo cp -r vpcctl_lib $(LIB_DIR)/
	sudo mkdir -p $(STATE_DIR)
	@echo "✓ vpcctl installed successfully!"
	@echo "Run 'vpcctl --help' to get started"

uninstall:
	@echo "Uninstalling vpcctl..."
	sudo rm -f $(INSTALL_DIR)/$(SCRIPT_NAME)
	sudo rm -rf $(LIB_DIR)
	@echo "✓ vpcctl uninstalled"
	@echo "Note: State directory $(STATE_DIR) preserved"

test:
	@echo "Running basic tests..."
	sudo vpcctl create test-vpc 10.100.0.0/16
	sudo vpcctl subnet-add test-vpc public 10.100.1.0/24 --type public
	sudo vpcctl show test-vpc
	sudo vpcctl del test-vpc
	@echo "✓ Basic tests passed"

clean:
	@echo "Cleaning up all VPCs..."
	sudo vpcctl cleanup-all
	@echo "✓ All VPCs removed"

demo:
	@echo "Running full demo scenario..."
	@bash demo.sh