"""Simple disk starter with better error handling"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.disk import DiskProcess

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python start_disk_simple.py <disk_name> <manager_ip> <manager_port> <m_port> <c_port>")
        sys.exit(1)
    
    disk_name = sys.argv[1]
    manager_ip = sys.argv[2]
    manager_port = int(sys.argv[3])
    m_port = int(sys.argv[4])
    c_port = int(sys.argv[5])
    
    print(f"Starting disk: {disk_name}")
    print(f"Manager: {manager_ip}:{manager_port}")
    print(f"Disk ports: M={m_port}, C={c_port}")
    
    disk = DiskProcess(disk_name, manager_ip, manager_port, m_port, c_port)
    
    try:
        disk.start()
    except KeyboardInterrupt:
        print("\nShutting down disk...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        disk.stop()