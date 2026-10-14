"""Script to start a user process"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from src.user import UserProcess
    print("Successfully imported UserProcess")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python start_user.py <user_name> <manager_ip> <manager_port> <m_port> <c_port>")
        print("Example: python start_user.py user1 127.0.0.1 1500 1701 1702")
        sys.exit(1)
    
    user_name = sys.argv[1]
    manager_ip = sys.argv[2]
    manager_port = int(sys.argv[3])
    m_port = int(sys.argv[4])
    c_port = int(sys.argv[5])
    
    print(f"Starting user: {user_name}")
    user = UserProcess(user_name, manager_ip, manager_port, m_port, c_port)
    
    try:
        user.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        user.stop()
        print("User process has been terminated")