"""Manager process implementation - Simplified version"""
import socket
import json
import threading
import logging
from datetime import datetime

SOCKET_TIMEOUT = 5.0
MESSAGE_ENCODING = 'utf-8'
MAX_NAME_LENGTH = 15
MIN_DISKS = 3
PORT_RANGE_START = 1500
PORT_RANGE_END = 1999

class DiskState:
    FREE = "FREE"
    IN_DSS = "IN_DSS"

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

class UserInfo:
    def __init__(self, user_name, ip_address, m_port, c_port):
        self.user_name = user_name
        self.ip_address = ip_address
        self.m_port = m_port
        self.c_port = c_port

class DiskInfo:
    def __init__(self, disk_name, ip_address, m_port, c_port):
        self.disk_name = disk_name
        self.ip_address = ip_address
        self.m_port = m_port
        self.c_port = c_port
        self.state = DiskState.FREE
        self.dss_name = None

class FileInfo:
    def __init__(self, file_name, file_size, owner, dss_name):
        self.file_name = file_name
        self.file_size = file_size
        self.owner = owner
        self.dss_name = dss_name
        self.stored_at = datetime.now()
    
    def to_dict(self):
        return {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "owner": self.owner,
            "dss_name": self.dss_name,
            "stored_at": self.stored_at.isoformat()
        }
    
class CopyOperation:
    def __init__(self, user_name, file_name, file_size, dss_name):
        self.user_name = user_name
        self.file_name = file_name
        self.file_size = file_size
        self.dss_name = dss_name
        self.started_at = datetime.now()

class ReadOperation:
    def __init__(self, user_name, file_name, dss_name):
        self.user_name = user_name
        self.file_name = file_name
        self.dss_name = dss_name
        self.started_at = datetime.now()

class DSSConfig:
    def __init__(self, dss_name, n, striping_unit):
        self.dss_name = dss_name
        self.n = n
        self.striping_unit = striping_unit
        self.disks = []

class ManagerState:
    def __init__(self):
        self.users = {}
        self.disks = {}
        self.dss_configs = {}
        self.files = {}
        self.copy_operations = {}
        self.read_operations = {}
        self.disk_failure_operations = {}
        self.used_ports = set()
    
    def is_valid_name(self, name):
        return len(name) <= MAX_NAME_LENGTH and name.isalnum() and len(name) > 0
    
    def validate_user_registration(self, user_name, ip_address, m_port, c_port):
        errors = []
        if not self.is_valid_name(user_name):
            errors.append(f"User name must be alphanumeric and <= {MAX_NAME_LENGTH} chars")
        if user_name in self.users:
            errors.append(f"User '{user_name}' already registered")
        errors.extend(self.validate_ports(m_port, c_port))
        return errors

    def validate_ports(self, m_port, c_port):
        """Ports must be integers in the allowed range, unused, and distinct"""
        errors = []
        for port in (m_port, c_port):
            if not isinstance(port, int) or not PORT_RANGE_START <= port <= PORT_RANGE_END:
                errors.append(f"Port {port} must be between {PORT_RANGE_START} and {PORT_RANGE_END}")
            elif port in self.used_ports:
                errors.append(f"Port {port} already used")
        if m_port == c_port:
            errors.append("Management and command ports must differ")
        return errors
    
    def validate_disk_registration(self, disk_name, ip_address, m_port, c_port):
        errors = []
        if not self.is_valid_name(disk_name):
            errors.append(f"Disk name must be alphanumeric and <= {MAX_NAME_LENGTH} chars")
        if disk_name in self.disks:
            errors.append(f"Disk '{disk_name}' already registered")
        errors.extend(self.validate_ports(m_port, c_port))
        return errors

class DiskFailureOperation:
    def __init__(self, user_name, dss_name, failed_disk_name):
        self.user = user_name
        self.dss_name = dss_name
        self.failed_disk_name = failed_disk_name
        self.started_at = datetime.now()

class ManagerProcess:
    def __init__(self, port):
        self.port = port
        self.logger = setup_logging("Manager")
        self.state = ManagerState()
        self.socket = None
        self.running = False
        self.lock = threading.Lock()
        
        self.copy_in_progress = False
        self.copy_operations = {}
        self.files = {}
        self.read_operations = {}
    
    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(SOCKET_TIMEOUT)
            self.running = True
            self.logger.info(f"Manager started on port {self.port}")
            self._main_loop()
        except Exception as e:
            self.logger.error(f"Failed to start manager: {e}")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("Manager stopped")
    
    def _main_loop(self):
        while self.running:
            try:
                data, address = self.socket.recvfrom(4096)
                self.logger.info(f"Received data from {address}")
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._handle_message(message, address)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON error: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error: {e}")
    
    def _handle_message(self, message, address):
        command = message.get('command', 'unknown')
        self.logger.info(f"Handling command: {command}")
        
        handler_name = f"_handle_{command.replace('-', '_')}"
        handler = getattr(self, handler_name, self._handle_unknown)
        
        with self.lock:
            response = handler(message, address)
        
        if response:
            self.socket.sendto(json.dumps(response).encode('utf-8'), address)
    
    def _handle_unknown(self, message, address):
        self.logger.warning(f"Unknown command: {message.get('command', 'unknown')}")
        return {
        "status": "FAILURE", 
            "message": f"Unknown command: {message.get('command', 'unknown')}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_register_user(self, message, address):
        params = message.get('params', {})
        user_name = params.get('user_name')
        ip_address = params.get('ip_address')
        m_port = params.get('m_port')
        c_port = params.get('c_port')
        
        errors = self.state.validate_user_registration(user_name, ip_address, m_port, c_port)
        if errors:
            return {
            "status": "FAILURE", 
                "message": "; ".join(errors),
                "timestamp": datetime.now().isoformat()
            }
        
        self.state.users[user_name] = UserInfo(user_name, ip_address, m_port, c_port)
        self.state.used_ports.add(m_port)
        self.state.used_ports.add(c_port)
        self.logger.info(f"Registered user: {user_name}")
        return {
        "status": "SUCCESS", 
            "message": "User registered successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_register_disk(self, message, address):
        params = message.get('params', {})
        disk_name = params.get('disk_name')
        ip_address = params.get('ip_address')
        m_port = params.get('m_port')
        c_port = params.get('c_port')
        
        errors = self.state.validate_disk_registration(disk_name, ip_address, m_port, c_port)
        if errors:
            return {
            "status": "FAILURE", 
                "message": " ".join(errors),
                "timestamp": datetime.now().isoformat()
            }
        
        self.state.disks[disk_name] = DiskInfo(disk_name, ip_address, m_port, c_port)
        self.state.used_ports.add(m_port)
        self.state.used_ports.add(c_port)
        self.logger.info(f"Registered disk: {disk_name}")
        return {
        "status": "SUCCESS", 
            "message": "Disk registered successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_configure_dss(self, message, address):
        params = message.get('params', {})
        dss_name = params.get('dss_name')
        n = params.get('n')
        striping_unit = params.get('striping_unit')
        
        self.logger.info(f"Configuring DSS: {dss_name} with {n} disks")
        
        if not dss_name or not n or not striping_unit:
            return {
            "status": "FAILURE", 
                "message": "Missing required parameters",
                "timestamp": datetime.now().isoformat()
            }
        
        if n < 3:
            return {
            "status": "FAILURE",
                "message": "Number of disks must be at least 3",
                "timestamp": datetime.now().isoformat()
            }
        
        if dss_name in self.state.dss_configs:
            return {
            "status": "FAILURE",
                "message": f"DSS '{dss_name}' already exists",
                "timestamp": datetime.now().isoformat()
            }
        
        free_disks = [disk for disk in self.state.disks.values() if disk.state == "FREE"]
        
        if len(free_disks) < n:
            return {
            "status": "FAILURE",
                "message": f"Not enough free disks. Required: {n}, Available: {len(free_disks)}",
                "timestamp": datetime.now().isoformat()
            }
        
        if not (striping_unit & (striping_unit - 1) == 0) and striping_unit != 0:
            return {
            "status": "FAILURE",
                "message": "Striping unit must be a power of 2",
                "timestamp": datetime.now().isoformat()
            }
        
        if striping_unit < 128 or striping_unit > 1048576:
            return {
            "status": "FAILURE", 
                "message": "Striping unit must be between 128B and 1MB",
                "timestamp": datetime.now().isoformat()
            }
        
        selected_disks = free_disks[:n]
        
        dss_config = DSSConfig(dss_name, n, striping_unit)
        dss_config.disks = selected_disks
        
        for disk in selected_disks:
            disk.state = "IN_DSS"
            disk.dss_name = dss_name
        
        self.state.dss_configs[dss_name] = dss_config
        
        self.logger.info(f"Successfully configured DSS: {dss_name} with {n} disks")
        return {
            "status": "SUCCESS",
            "message": "DSS configured successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_ls(self, message, address):
        """Handle ls command - list all DSS configurations and files"""
        try:
            self.logger.info(f"Processing ls command from {address}")
        
            if not self.state.dss_configs and not self.state.files:
                return {
                    "status": "FAILURE",
                    "message": "No DSS configurations or files available",
                    "timestamp": datetime.now().isoformat()
                }
        
            dss_info = []
            for dss_name, dss_config in self.state.dss_configs.items():
                disk_names = [disk.disk_name for disk in dss_config.disks]
            
                dss_files = []
                for file_name, file_info in self.state.files.items():
                    if file_info.dss_name == dss_name:
                        dss_files.append({
                            "file_name": file_info.file_name,
                            "file_size": file_info.file_size,
                            "owner": file_info.owner
                        })
            
                dss_info.append({
                    "dss_name": dss_name,
                    "n": dss_config.n,
                    "striping_unit": dss_config.striping_unit,
                    "disks": disk_names,
                    "files": dss_files
                })
        
            self.logger.info(f"Returning information for {len(dss_info)} DSS configurations")
        
            return {
                "status": "SUCCESS",
                "message": f"Found {len(dss_info)} DSS configuration(s) and {len(self.state.files)} file(s)",
                "data": {
                    "dss_configs": dss_info,
                    "total_files": len(self.state.files)
                },
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in ls command: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
    def _handle_copy(self, message, address):
        """Handle copy command - Phase 1: Select DSS and return parameters"""
        try:
            if self.copy_operations:
                return {
                    "status": "FAILURE",
                    "message": "Another copy operation is in progress",
                    "timestamp": datetime.now().isoformat()
            }

            params = message.get('params', {})
            file_name = params.get('file_name')
            file_size = params.get('file_size')
            owner = params.get('owner')
        
            self.logger.info(f"Processing copy command for file: {file_name} from user: {owner}")
        
            if not file_name or not file_size or not owner:
                return {
                "status": "FAILURE",
                "message": "Missing required parameters: file_name, file_size, owner",
                "timestamp": datetime.now().isoformat()
            }
        
            if file_name in self.files:
                return {
                "status": "FAILURE", 
                    "message": f"File '{file_name}' already exists",
                    "timestamp": datetime.now().isoformat()
            }
        
            if not self.state.dss_configs:
                return {
                "status": "FAILURE",
                    "message": "No DSS configurations available",
                    "timestamp": datetime.now().isoformat()
            }
        
            dss_name = list(self.state.dss_configs.keys())[0]
            dss_config = self.state.dss_configs[dss_name]
        
            self.state.copy_operations[owner] = CopyOperation(owner, file_name, file_size, dss_name)
        
            disks_info = []
            for disk in dss_config.disks:
                disks_info.append({
                "disk_name": disk.disk_name,
                "ip_address": disk.ip_address,
                "c_port": disk.c_port
                })
        
            self.logger.info(f"Selected DSS '{dss_name}' for file copy. Waiting for copy-complete...")
        
            return {
                "status": "SUCCESS",
                "message": "DSS selected for file copy",
                "data": {
                "dss_name": dss_name,
                "n": dss_config.n,
                "striping_unit": dss_config.striping_unit,
                "disks": disks_info
            },
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in copy command: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_copy_complete(self, message, address):
        """Handle copy-complete command"""
        try:
            params = message.get('params', {})
            user_name = params.get('user_name')
            file_name = params.get('file_name')
        
            self.logger.info(f"Processing copy-complete for file: {file_name} from user: {user_name}")
        
            if user_name not in self.state.copy_operations:
                return {
                    "status": "FAILURE",
                    "message": "No active copy operation found for user",
                    "timestamp": datetime.now().isoformat()
                }
        
            copy_op = self.state.copy_operations[user_name]
        
            if copy_op.file_name != file_name:
                return {
                    "status": "FAILURE",
                    "message": "File name does not match active copy operation",
                    "timestamp": datetime.now().isoformat()
                }
        
            self.state.files[file_name] = FileInfo(
                file_name=file_name,
                file_size=copy_op.file_size,
                owner=user_name,
                dss_name=copy_op.dss_name
            )
        
            del self.state.copy_operations[user_name]
        
            self.logger.info(f"Successfully stored file: {file_name} in DSS: {copy_op.dss_name}")
        
            return {
                "status": "SUCCESS",
                "message": f"File '{file_name}' successfully stored",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in copy-complete: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
    def _handle_read(self, message, address):
        """Handle read command"""
        try:
            params = message.get('params', {})
            dss_name = params.get('dss_name')
            file_name = params.get('file_name')
            user_name = params.get('user_name')
        
            self.logger.info(f"Processing read command for file: {file_name} from user: {user_name}")
        
            if not dss_name or not file_name or not user_name:
                return {
                    "status": "FAILURE",
                    "message": "Missing required parameters: dss_name, file_name, user_name",
                    "timestamp": datetime.now().isoformat()
                }
        
            if file_name not in self.state.files:
                return {
                    "status": "FAILURE",
                    "message": f"File '{file_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
        
            file_info = self.state.files[file_name]
        
            if file_info.owner != user_name:
                return {
                    "status": "FAILURE",
                    "message": f"User '{user_name}' is not the owner of file '{file_name}'",
                    "timestamp": datetime.now().isoformat()
                }
        
            if file_info.dss_name != dss_name:
                return {
                    "status": "FAILURE",
                    "message": f"File '{file_name}' is not stored in DSS '{dss_name}'",
                    "timestamp": datetime.now().isoformat()
                }
        
            if dss_name not in self.state.dss_configs:
                return {
                    "status": "FAILURE",
                    "message": f"DSS '{dss_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
        
            dss_config = self.state.dss_configs[dss_name]
        
            self.state.read_operations[user_name] = ReadOperation(user_name, file_name, dss_name)
        
            disks_info = []
            for disk in dss_config.disks:
                disks_info.append({
                    "disk_name": disk.disk_name,
                    "ip_address": disk.ip_address,
                    "c_port": disk.c_port
                })
        
            self.logger.info(f"Preparing read operation for file: {file_name}")
        
            return {
                "status": "SUCCESS",
                "message": "File found and ready for reading",
                "data": {
                    "file_size": file_info.file_size,
                    "dss_name": dss_name,
                    "n": dss_config.n,
                    "striping_unit": dss_config.striping_unit,
                    "disks": disks_info
                },
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in read command: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_read_complete(self, message, address):
        try:
            params = message.get('params', {})
            user_name = params.get('user_name')
            file_name = params.get('file_name')
        
            self.logger.info(f"Processing read-complete for file: {file_name} from user: {user_name}")
        
            if user_name not in self.state.read_operations:
                return {
                    "status": "FAILURE",
                    "message": "No active read operation found for user",
                    "timestamp": datetime.now().isoformat()
                }
        
            read_op = self.state.read_operations[user_name]
        
            if read_op.file_name != file_name:
                return {
                    "status": "FAILURE",
                    "message": "File name does not match active read operation",
                    "timestamp": datetime.now().isoformat()
                }
        
            del self.state.read_operations[user_name]
        
            self.logger.info(f"Successfully completed read operation for file: {file_name}")
        
            return {
                "status": "SUCCESS",
                "message": f"Read operation for '{file_name}' completed successfully",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in read-complete: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_deregister_user(self, message, address):
        try:
            params = message.get('params', {})
            user_name = params.get('user_name')
        
            self.logger.info(f"Processing deregister-user for: {user_name}")
        
            if not user_name:
                return {
                    "status": "FAILURE",
                    "message": "User name is required",
                    "timestamp": datetime.now().isoformat()
                }
        
            if user_name not in self.state.users:
                return {
                    "status": "FAILURE",
                    "message": f"User '{user_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
        
            user_info = self.state.users[user_name]
        
            del self.state.users[user_name]
        
            self.state.used_ports.discard(user_info.m_port)
            self.state.used_ports.discard(user_info.c_port)
        
            self.logger.info(f"Successfully deregistered user: {user_name}")
            return {
                "status": "SUCCESS",
                "message": f"User '{user_name}' deregistered successfully",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in deregister-user: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_deregister_disk(self, message, address):
        try:
            params = message.get('params', {})
            disk_name = params.get('disk_name')
        
            self.logger.info(f"Processing deregister-disk for: {disk_name}")
        
            if not disk_name:
                return {
                "status": "FAILURE",
                    "message": "Disk name is required",
                    "timestamp": datetime.now().isoformat()
                }
        
            if disk_name not in self.state.disks:
                return {
                "status": "FAILURE",
                    "mesage": f"Disk '{disk_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
        
            disk_info = self.state.disks[disk_name]
        
            if disk_info.state != "FREE":
                dss_name = disk_info.dss_name
                self.logger.warning(f"Disk '{disk_name}' is in use by DSS '{dss_name}'. Removing from DSS")
            
                if dss_name in self.state.dss_configs:
                    dss_config = self.state.dss_configs[dss_name]
                
                    dss_config.disks = [disk for disk in dss_config.disks if disk.disk_name != disk_name]
                    dss_config.n = len(dss_config.disks)
                
                    if dss_config.n < 3:
                        self.logger.warning(f"DSS '{dss_name}' now has only {dss_config.n} disks. Auto-decommissioning")
                    
                        for remaining_disk in dss_config.disks:
                            remaining_disk.state = "FREE"
                            remaining_disk.dss_name = None
                            self.logger.info(f"Freed disk: {remaining_disk.disk_name}")
                    
                        del self.state.dss_configs[dss_name]
                        self.logger.info(f"Auto-decommissioned DSS: {dss_name}")
                    else:
                        self.logger.info(f"Updated DSS '{dss_name}' now has {dss_config.n} disks")
        
            del self.state.disks[disk_name]
        
            self.state.used_ports.discard(disk_info.m_port)
            self.state.used_ports.discard(disk_info.c_port)
        
            self.logger.info(f"Successfully deregistered disk: {disk_name}")
            return {
            "status": "SUCCESS",
                "message": f"Disk '{disk_name}' deregistered successfully",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in deregister-disk: {e}")
            return {
            "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }
    def _handle_disk_failure(self, message, address):
        try:
            params = message.get('params', {})
            dss_name = params.get('dss_name')
            user_name = params.get('user_name')
        
            self.logger.info(f"Processing disk-failure for DSS: {dss_name} from user: {user_name}")
        
            if not dss_name or not user_name:
                return {
                "status": "FAILURE",
                "mesage": "Missing required parameters: dss_name, user_name",
                "timestamp": datetime.now().isoformat()
                }
        
            if dss_name not in self.state.dss_configs:
                return {
                "status": "FAILURE",
                    "message": f"DSS '{dss_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
        
            if self.state.read_operations:
                return {
                "status": "FAILURE",
                    "message": "Cannot initiate disk failure while read operations are in progress",
                    "timestamp": datetime.now().isoformat()
                }
        
            if user_name in self.state.disk_failure_operations:
                return {
                "status": "FAILURE",
                    "message": "User already has an active disk failure operation",
                    "timestamp": datetime.now().isoformat()
                }
        
            dss_config = self.state.dss_configs[dss_name]
        
            disks_info = []
            for disk in dss_config.disks:
                disks_info.append({
                "disk_name": disk.disk_name,
                "ip_address": disk.ip_address,
                "c_port": disk.c_port
                })
        
            self.state.disk_failure_operations[user_name] = DiskFailureOperation(
                user_name = user_name,
                dss_name = dss_name,
                failed_disk_name = None
            )
        
            self.logger.info(f"Prepared disk failure operation for DSS: {dss_name}. Waiting for recovery-complete...")
        
            return {
                "status": "SUCCESS",
                "message": "DSS parameters ready for disk failure simulation",
                "data": {
                 "dss_name": dss_name,
                   "n": dss_config.n,
                "striping_unit": dss_config.striping_unit,
                "disks": disks_info
                },
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in disk-failure: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_recovery_complete(self, message, address):
        try:
            params = message.get('params', {})
            user_name = params.get('user_name')
            dss_name = params.get('dss_name')
            failed_disk_name = params.get('failed_disk_name')
        
            self.logger.info(f"Processing recovery-complete for DSS: {dss_name} from user: {user_name}")
        
            if user_name not in self.state.disk_failure_operations:
                return {
                    "status": "FAILURE",
                    "message": "No active disk failure operation found for user",
                    "timestamp": datetime.now().isoformat()
                }
        
            disk_failure_op = self.state.disk_failure_operations[user_name]
        
            if disk_failure_op.dss_name != dss_name:
                return {
                    "status": "FAILURE",
                    "message": "DSS name does not match active disk failure operation",
                    "timestamp": datetime.now().isoformat()
                }
        
            disk_failure_op.failed_disk_name = failed_disk_name
        
            self.logger.info(f"Disk failure recovery completed for DSS: {dss_name}")
            self.logger.info(f"Failed disk: {failed_disk_name}")
            self.logger.info(f"Recovery performed by user: {user_name}")
        
            del self.state.disk_failure_operations[user_name]
        
            return {
                "status": "SUCCESS",
                "message": f"Disk failure recovery completed successfully for DSS '{dss_name}'. Failed disk: {failed_disk_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error in recovery-complete: {e}")
            return {
                "status": "FAILURE",
                "message": f"Internal error: {e}",
                "timestamp": datetime.now().isoformat()
            }
    
            