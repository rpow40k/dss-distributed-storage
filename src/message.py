"""Message format definitions"""
import json
import logging
from datetime import datetime
from src.utils import generate_message_id

logger = logging.getLogger(__name__)

class Message:
    """Base message class"""
    
    @staticmethod
    def create(command, params=None):
        """Create a new message"""
        message = {
            "command": command,
            "params": params or {},
            "timestamp": datetime.now().isoformat(),
            "message_id": generate_message_id()
        }
        logger.debug(f"Created message: {message}")
        return message
    
    @staticmethod
    def create_response(request_message, status, message="", data=None):
        """Create a response message"""
        response = {
            "status": status,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
            "message_id": request_message.get("message_id", "unknown")
        }
        logger.debug(f"Created response: {response}")
        return response
    
    @staticmethod
    def validate_message(message):
        """Validate message structure"""
        required = ["command", "params", "timestamp", "message_id"]
        if not all(key in message for key in required):
            logger.debug(f"Message validation failed. Message: {message}")
            return False
        return True

class MessageFactory:
    """Factory for creating specific command messages"""
    
    @staticmethod
    def register_user(user_name, ip_address, m_port, c_port):
        return Message.create("register-user", {
            "user_name": user_name,
            "ip_address": ip_address,
            "m_port": m_port,
            "c_port": c_port
        })
    
    @staticmethod
    def register_disk(disk_name, ip_address, m_port, c_port):
        return Message.create("register-disk", {
            "disk_name": disk_name,
            "ip_address": ip_address,
            "m_port": m_port,
            "c_port": c_port
        })
    
    @staticmethod
    def configure_dss(dss_name, n, striping_unit):
        return Message.create("configure-dss", {
            "dss_name": dss_name,
            "n": n,
            "striping_unit": striping_unit
        })
    
    @staticmethod
    def deregister_user(user_name):
        return Message.create("deregister-user", {
            "user_name": user_name
        })
    
    @staticmethod
    def deregister_disk(disk_name):
        return Message.create("deregister-disk", {
            "disk_name": disk_name
        })