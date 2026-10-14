"""Disk process implementation"""
import socket
import json
import threading
import logging
from datetime import datetime

from src.utils import setup_logging, get_local_ip
from src.message import MessageFactory
from config.constants import SOCKET_TIMEOUT, MESSAGE_ENCODING

class DiskProcess:
    """Disk process that simulates a physical disk"""
    
    def __init__(self, disk_name, manager_ip, manager_port, m_port, c_port):
        self.disk_name = disk_name
        self.manager_ip = manager_ip
        self.manager_port = manager_port
        self.m_port = m_port
        self.c_port = c_port
        self.logger = setup_logging(f"Disk-{disk_name}")
        self.manager_address = (manager_ip, manager_port)
        self.socket = None
        self.running = False
        self.registered = False
        
        self.storage = {}
    
    def start(self):
        """Start the disk process"""
        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.settimeout(SOCKET_TIMEOUT)
            
            if self._register_with_manager(temp_socket):
                temp_socket.close()
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.bind(('0.0.0.0', self.c_port))
                self.socket.settimeout(SOCKET_TIMEOUT)
                
                self.running = True
                self.logger.info(f"Disk successfully started on port {self.c_port}")
                self._main_loop()
            else:
                self.logger.error("Failed to register with manager")
                temp_socket.close()
                
        except Exception as e:
            self.logger.error(f"Failed to start disk: {e}")
        finally:
            self.stop()
    
    def _register_with_manager(self, sock):
        """Register this disk with the manager"""
        try:
            message = MessageFactory.register_disk(
                self.disk_name, get_local_ip(), self.m_port, self.c_port
            )
            
            self.logger.info(f"Sending registration to {self.manager_address}")
            
            message_str = json.dumps(message)
            sock.sendto(message_str.encode(MESSAGE_ENCODING), self.manager_address)
            self.logger.info(f"Sent registration message")
            
            sock.settimeout(10.0)
            data, addr = sock.recvfrom(4096)
            
            response = json.loads(data.decode(MESSAGE_ENCODING))
            self.logger.info(f"Received response: {response}")
            
            if response.get('status') == 'SUCCESS':
                self.registered = True
                self.logger.info("Successfully registered with manager")
                return True
            else:
                self.logger.error(f"Registration failed: {response.get('message', 'Unknown error')}")
                return False
                
        except socket.timeout:
            self.logger.error("Timeout waiting for manager response")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in response: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error during registration: {e}")
            return False
    
    def _main_loop(self):
        """Main processing loop for command handling"""
        self.logger.info("Disk main loop started - waiting for commands...")
    
        while self.running:
            try:
                data, address = self.socket.recvfrom(4096)
                if data:
                    try:
                        message = json.loads(data.decode(MESSAGE_ENCODING))
                        command = message.get('command', 'unknown')
                    
                        if command == "fail":
                            self._handle_fail_message(message, address)
                        else:
                            self.logger.info(f"Received command: {command}")
                        
                    except json.JSONDecodeError:
                        self.logger.error(f"Received invalid JSON from {address}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                break
    
    def stop(self):
        """Stop the disk process and clean up resources"""
        self.logger.info("Shutting down disk process...")
        self.running = False
    
        if self.socket:
            try:
                self.socket.close()
                self.logger.debug("Socket closed")
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
    
        self.logger.info("Disk process stopped successfully")

    def _handle_deregister_disk(self):
        """Deregister this disk and shut down"""
        try:
            self.logger.info("Initiating disk deregistration...")
        
            message = {
                "command": "deregister-disk",
                "params": {
                    "disk_name": self.disk_name
                },
                "timestamp": datetime.now().isoformat(),
                "message_id": f"dereg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            }
        
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.settimeout(SOCKET_TIMEOUT)
        
            message_str = json.dumps(message)
            temp_socket.sendto(message_str.encode(MESSAGE_ENCODING), self.manager_address)
        
            data, addr = temp_socket.recvfrom(4096)
            response = json.loads(data.decode(MESSAGE_ENCODING))
            temp_socket.close()
        
            if response and response.get('status') == 'SUCCESS':
                self.logger.info("Successfully deregistered from manager")
                self.running = False
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                self.logger.error(f"Deregistration failed: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error during deregistration: {e}")

    def _handle_fail_message(self, message, address):
        """Handle fail message from user to simulate disk failure"""
        try:
            self.logger.warning("Received FAIL message - simulating disk failure")
        
            files_deleted = len(self.storage)
            self.storage.clear()
        
            self.logger.warning(f"Disk failure simulated - deleted {files_deleted} files from storage")
        
            response = {
                "status": "SUCCESS",
                "message": f"Disk failure simulated successfully on {self.disk_name}",
                "files_deleted": files_deleted,
                "timestamp": datetime.now().isoformat()
            }
        
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.sendto(json.dumps(response).encode(MESSAGE_ENCODING), address)
            temp_socket.close()
        
            self.logger.info("Fail-complete response sent")
        
        except Exception as e:
            self.logger.error(f"Error handling fail message: {e}")