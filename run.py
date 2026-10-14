"""Main entry point for DSS project"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main function to run different components"""
    if len(sys.argv) < 2:
        print("Usage: python run.py <component> [args...]")
        return
    
    component = sys.argv[1]
    
    if component == "manager":
        from src.manager import ManagerProcess
        if len(sys.argv) != 3:
            print("Usage: python run.py manager <port>")
            return
        port = int(sys.argv[2])
        manager = ManagerProcess(port)
        try:
            manager.start()
        except KeyboardInterrupt:
            print("\nShutting down manager...")
        finally:
            manager.stop()
    
    elif component == "disk":
        from src.disk import DiskProcess
        if len(sys.argv) != 7:
            print("Usage: python run.py disk <disk_name> <manager_ip> <manager_port> <m_port> <c_port>")
            return
        disk_name = sys.argv[2]
        manager_ip = sys.argv[3]
        manager_port = int(sys.argv[4])
        m_port = int(sys.argv[5])
        c_port = int(sys.argv[6])
        
        disk = DiskProcess(disk_name, manager_ip, manager_port, m_port, c_port)
        try:
            disk.start()
        except KeyboardInterrupt:
            print("\nShutting down disk...")
        finally:
            disk.stop()
    
    elif component == "user":
        from src.user import UserProcess
        if len(sys.argv) != 7:
            print("Usage: python run.py user <user_name> <manager_ip> <manager_port> <m_port> <c_port>")
            return
        user_name = sys.argv[2]
        manager_ip = sys.argv[3]
        manager_port = int(sys.argv[4])
        m_port = int(sys.argv[5])
        c_port = int(sys.argv[6])
        
        user = UserProcess(user_name, manager_ip, manager_port, m_port, c_port)
        try:
            user.start()
        except KeyboardInterrupt:
            print("\nShutting down user...")
        finally:
            user.stop()
    
    else:
        print(f"Unknown component: {component}")
        print("Available components: manager, disk, user")

if __name__ == "__main__":
    main()