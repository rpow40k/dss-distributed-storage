"""Script to start the manager process"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.manager import ManagerProcess

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python start_manager.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    manager = ManagerProcess(port)
    
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nShutting down manager...")
    finally:
        manager.stop()