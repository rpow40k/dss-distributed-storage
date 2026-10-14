"""Utility functions for DSS"""
import socket
import json
import logging
from datetime import datetime
from config.constants import MESSAGE_ENCODING, MAX_MESSAGE_SIZE

def setup_logging(name):
    """Setup logging for a process"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def get_local_ip():
    """Get local IP address"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def generate_message_id():
    """Generate unique message ID"""
    return f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def is_power_of_two(n):
    """Check if a number is a power of two"""
    return (n & (n - 1) == 0) and n != 0

def validate_port(port, used_ports):
    """Validate port number"""
    return (1500 <= port <= 1999) and (port not in used_ports)

def send_message(sock, message, address):
    """Send JSON message over socket"""
    try:
        if not sock:
            logging.error("Socket is None in send_message")
            return False
            
        message_str = json.dumps(message)
        sock.sendto(message_str.encode(MESSAGE_ENCODING), address)
        logging.debug(f"Sent message to {address}: {message['command']}")
        return True
    except Exception as e:
        logging.error(f"Error sending message to {address}: {e}")
        return False

def receive_message(sock, timeout=None):
    """Receive JSON message from socket"""
    if not sock:
        logging.error("Socket is None in receive_message")
        return None, None
        
    try:
        if timeout:
            sock.settimeout(timeout)
        data, addr = sock.recvfrom(MAX_MESSAGE_SIZE)
        message = json.loads(data.decode(MESSAGE_ENCODING))
        logging.debug(f"Received message from {addr}: {message.get('command', 'unknown')}")
        return message, addr
    except socket.timeout:
        return None, None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Error receiving message: {e}")
        return None, None