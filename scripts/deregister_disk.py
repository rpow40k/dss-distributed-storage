"""Script to manually deregister a disk"""
import socket
import json
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from datetime import datetime

def deregister_disk(disk_name, manager_ip, manager_port):
    """Send deregister command for a disk"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        
        message = {
            "command": "deregister-disk",
            "params": {
                "disk_name": disk_name
            },
            "timestamp": datetime.now().isoformat(),
            "message_id": f"manual_dereg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        }
        
        print(f"Sending deregister command for disk: {disk_name}")
        sock.sendto(json.dumps(message).encode('utf-8'), (manager_ip, manager_port))
        
        data, addr = sock.recvfrom(4096)
        response = json.loads(data.decode('utf-8'))
        sock.close()
        
        if response.get('status') == 'SUCCESS':
            print(f"Successfully deregistered disk: {disk_name}")
        else:
            print(f"Failed: {response.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python deregister_disk.py <disk_name> <manager_ip> <manager_port>")
        print("Example: python deregister_disk.py disk1 127.0.0.1 1500")
        sys.exit(1)
    
    disk_name = sys.argv[1]
    manager_ip = sys.argv[2]
    manager_port = int(sys.argv[3])
    
    deregister_disk(disk_name, manager_ip, manager_port)