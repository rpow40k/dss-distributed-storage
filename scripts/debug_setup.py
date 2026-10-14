"""Debug script to test basic connectivity"""
import socket
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_port_availability():
    """Test if ports are available"""
    ports_to_test = list(range(1500, 1520))
    
    print("Testing port availability...")
    for port in ports_to_test:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
            print(f"Port {port} is available")
        except OSError:
            print(f"Port {port} is already in use")

def test_manager_connection(port=1500):
    """Test if manager is running on port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.sendto(b"ping", ('127.0.0.1', port))
        sock.close()
        print("Can send to manager port")
    except Exception as e:
        print(f"Cannot send to manager port: {e}")

if __name__ == "__main__":
    print("=== DSS Debug Setup ===\n")
    test_port_availability()
    print("\nTesting manager connection...")
    test_manager_connection()