import json
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