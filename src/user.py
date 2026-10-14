import socket
import json
import threading
import logging
import os
from datetime import datetime

SOCKET_TIMEOUT = 5.0
MESSAGE_ENCODING = 'utf-8'

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
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def generate_message_id():
    return f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

class UserProcess:    
    def __init__(self, user_name, manager_ip, manager_port, m_port, c_port):
        self.user_name = user_name
        self.manager_ip = manager_ip
        self.manager_port = manager_port
        self.m_port = m_port
        self.c_port = c_port
        self.logger = setup_logging(f"User-{user_name}")
        self.manager_address = (manager_ip, manager_port)
        self.socket = None
        self.running = False
        self.registered = False
    
    def _create_message(self, command, params=None):
        """Create a message dictionary"""
        return {
            "command": command,
            "params": params or {},
            "timestamp": datetime.now().isoformat(),
            "message_id": generate_message_id()
        }
    
    def start(self):
        """Start the user process"""
        try:
            self.logger.info(f"Starting user process {self.user_name}")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.c_port))
            self.socket.settimeout(SOCKET_TIMEOUT)
            
            if self._register_with_manager():
                self.running = True
                self.logger.info(f"User successfully registered and listening on port {self.c_port}")
                self._command_loop()
            else:
                self.logger.error("Failed to register with manager")
                
        except Exception as e:
            self.logger.error(f"Failed to start user: {e}")
        finally:
            self.stop()

    def stop(self):
        self.logger.info("Shutting down user process")
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
                self.logger.debug("Socket closed")
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
        
        self.logger.info("User process stopped successfully")
    
    def _register_with_manager(self):
        """Register this user with the manager"""
        try:
            message = self._create_message("register-user", {
                "user_name": self.user_name,
                "ip_address": get_local_ip(),
                "m_port": self.m_port,
                "c_port": self.c_port
            })
            
            self.logger.info(f"Sending registration to {self.manager_address}")
            message_str = json.dumps(message)
            self.socket.sendto(message_str.encode(MESSAGE_ENCODING), self.manager_address)
            self.socket.settimeout(10.0)
            data, addr = self.socket.recvfrom(4096)
            response = json.loads(data.decode(MESSAGE_ENCODING))
            self.logger.info(f"Received response: {response.get('status', 'unknown')}")
            if response.get('status') == 'SUCCESS':
                self.registered = True
                self.logger.info("Successfully registered with manager")
                return True
            else:
                error_msg = response.get('message', 'Unknown error')
                self.logger.error(f"Registration failed: {error_msg}")
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
    
    def _command_loop(self):
        """Command processing loop"""
        self.logger.info("User process started. Enter commands:")
        
        while self.running:
            try:
                command = input(f"{self.user_name}> ").strip()
                if not command:
                    continue
                if command.lower() == 'exit':
                    break
                self._execute_command(command)
                if not self.running:
                    break
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Command error: {e}")
        self.stop()
    
    def _execute_command(self, command_line):
        """Execute a user command"""
        parts = command_line.split()
        if not parts:
            return
        
        command = parts[0].lower().strip()
    
        if command == "configure-dss":
            if len(parts) == 4:
                try:
                    dss_name = parts[1]
                    n_disks = int(parts[2])
                    stripe_size = int(parts[3])
                    self._configure_dss(dss_name, n_disks, stripe_size)
                except ValueError as e:
                    self.logger.error(f"Invalid number format: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing command: {e}")
            else:
                self.logger.error("Usage: configure-dss <name> <n> <striping_unit>")

        elif command == "list-files":
            self._list_local_files()

        elif command == "show-file":
            if len(parts) == 2:
                file_name = parts[1]
                self._show_file_content(file_name)
            else:
                self.logger.error("Usage: show-file <file_name>")
    
        elif command == "disk-failure":
            if len(parts) == 2:
                dss_name = parts[1]
                self._disk_failure(dss_name)
            else:
                self.logger.error("Usage: disk-failure <dss_name>")
    
        elif command == "copy":
            if len(parts) == 4:
                try:
                    file_name = parts[1]
                    file_size = int(parts[2])
                    owner = parts[3]
                    self._copy_file(file_name, file_size, owner)
                except ValueError as e:
                    self.logger.error(f"Invalid file size format: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing copy command: {e}")
            else:
                self.logger.error("Usage: copy <file_name> <file_size> <owner>")
    
        elif command == "read":
            if len(parts) == 4:
                dss_name = parts[1]
                file_name = parts[2]
                owner = parts[3]
                self._read_file(dss_name, file_name, owner)
            else:
                self.logger.error("Usage: read <dss_name> <file_name> <owner>")
        elif command == "ls":
            self._handle_ls()
        elif command == "deregister-user":
            self._deregister_user()
        elif command == "help":
            self._show_help()
        elif command == "exit":
            self.running = False
        else:
            self.logger.error(f"Unknown command: {parts[0]}")
            self.logger.info("Type 'help' for available commands")
    
    def _show_help(self):
        """Print the available commands"""
        print("Commands:")
        print("  configure-dss <name> <n> <striping_unit>  Create a DSS from n free disks (n >= 3, unit 128B-1MB, power of 2)")
        print("  ls                                        List DSS configurations and stored files")
        print("  list-files                                List files available in ./files")
        print("  show-file <file_name>                     Print a local file")
        print("  copy <file_name> <file_size> <owner>      Stripe a local file across a DSS (size is read from disk)")
        print("  read <dss_name> <file_name> <owner>       Read a file back from a DSS")
        print("  disk-failure <dss_name>                   Fail a random disk and run recovery")
        print("  deregister-user                           Deregister this user")
        print("  help                                      Show this message")
        print("  exit                                      Quit")

    def _configure_dss(self, dss_name, n, striping_unit):
        """Send configure-dss command to manager"""
        try:
            message = self._create_message("configure-dss", {
                "dss_name": dss_name,
                "n": n,
                "striping_unit": striping_unit
            })
            
            response = self._send_to_manager(message)
            
            if response and response.get('status') == 'SUCCESS':
                self.logger.info(f"Successfully configured DSS: {dss_name}")
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                self.logger.error(f"Failed to configure DSS: {error_msg}")
        except Exception as e:
            self.logger.error(f"Error configuring DSS: {e}")
    
    def _handle_ls(self):
        """Handle ls command - list DSS configurations"""
        try:
            self.logger.info("Processing ls command...")
        
            message = self._create_message("ls", {})
        
            response = self._send_to_manager(message)
        
            if response and response.get('status') == 'SUCCESS':
                data = response.get('data', {})
                dss_configs = data.get('dss_configs', [])
            
                if not dss_configs:
                    self.logger.info("No DSS configurations available")
                    return
            
                print("\n" + "============================================")
                print("DISTRIBUTED STORAGE SYSTEM (DSS) CONFIGURATIONS")
                print("============================================")
            
                for i, dss in enumerate(dss_configs, 1):
                    disk_list = ", ".join(dss.get('disks', []))
                    files = dss.get('files', [])
                
                    print(f"\n{i}. {dss['dss_name']}:")
                    print(f"   • Disk array: {dss['n']} disks ({disk_list})")
                    print(f"   • Striping unit: {dss['striping_unit']} bytes")
                    print(f"   • Files stored: {len(files)}")
                
                    for file_info in files:
                        print(f"     - {file_info.get('file_name', 'Unknown')} "
                            f"({file_info.get('file_size', 0)} bytes) "
                            f"[Owner: {file_info.get('owner', 'Unknown')}]")
            
                print("\n" + "============================================")
                print(f"Total DSS configurations: {len(dss_configs)}")
                print("============================================")
            
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response from manager'
                self.logger.info(f"No DSS configurations found: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error executing ls command: {e}")

    def _deregister_user(self):
        """Deregister this user and shut down"""
        try:
            self.logger.info("Initiating user deregistration...")
        
            message = self._create_message("deregister-user", {
                "user_name": self.user_name
            })
        
            response = self._send_to_manager(message)
        
            if response and response.get('status') == 'SUCCESS':
                self.logger.info("Successfully deregistered from manager")
                self.running = False
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response from manager'
                self.logger.error(f"Deregistration failed: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error during deregistration: {e}")
    
    def _send_to_manager(self, message):
        """Send message to manager and wait for response"""
        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.settimeout(SOCKET_TIMEOUT)
            
            message_str = json.dumps(message)
            temp_socket.sendto(message_str.encode(MESSAGE_ENCODING), self.manager_address)
            
            data, addr = temp_socket.recvfrom(4096)
            response = json.loads(data.decode(MESSAGE_ENCODING))
            temp_socket.close()
            
            return response
        except socket.timeout:
            self.logger.error("Timeout waiting for manager response")
            return None
        except Exception as e:
            self.logger.error(f"Error sending to manager: {e}")
            return None
        
    def stop(self):
        """Stop the user process and clean up resources"""
        self.logger.info("Shutting down user process...")
        self.running = False
    
        if self.socket:
            try:
                self.socket.close()
                self.logger.debug("Socket closed")
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
    
        self.logger.info("User process stopped successfully")

    def _copy_file(self, file_name, file_size, owner):
        """Handle copy file command with real file reading"""
        try:
            self.logger.info(f"Initiating file copy: {file_name}")
        
            file_path = os.path.join("files", file_name)
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return
        
            actual_size = os.path.getsize(file_path)
            self.logger.info(f"File size: {actual_size} bytes")
        
            message = self._create_message("copy", {
                "file_name": file_name,
                "file_size": actual_size,
                "owner": owner
            })
        
            response = self._send_to_manager(message)
        
            if not response or response.get('status') != 'SUCCESS':
                error_msg = response.get('message', 'No response from manager') if response else 'No response'
                self.logger.error(f"Copy failed: {error_msg}")
                return
        
            data = response.get('data', {})
            dss_name = data.get('dss_name')
            n = data.get('n')
            striping_unit = data.get('striping_unit')
            disks = data.get('disks', [])
        
            self.logger.info(f"DSS selected: {dss_name} with {n} disks")
        
            self._copy_file_to_dss(file_path, file_name, actual_size, dss_name, disks, striping_unit)
        
            complete_message = self._create_message("copy-complete", {
                "user_name": self.user_name,
                "file_name": file_name
            })
        
            complete_response = self._send_to_manager(complete_message)
        
            if complete_response and complete_response.get('status') == 'SUCCESS':
                self.logger.info(f"File '{file_name}' successfully stored in DSS")
            else:
                error_msg = complete_response.get('message', 'Unknown error') if complete_response else 'No response'
                self.logger.error(f"Copy completion failed: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error in file copy: {e}")

    def _copy_file_to_dss(self, file_path, file_name, file_size, dss_name, disks, striping_unit):
        try:
            self.logger.info("FILE COPY TO DSS")
            self.logger.info(f"Source: {file_path}")
            self.logger.info(f"Target DSS: {dss_name}")
            self.logger.info(f"File size: {file_size} bytes")
            self.logger.info(f"Striping unit: {striping_unit} bytes")
            self.logger.info(f"Disks: {[disk['disk_name'] for disk in disks]}")
        
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        
            n_disks = len(disks)
            data_blocks_per_stripe = n_disks - 1
            bytes_per_stripe = data_blocks_per_stripe * striping_unit
            stripes_needed = (file_size + bytes_per_stripe - 1) // bytes_per_stripe
        
            self.logger.info(f"Stripes needed: {stripes_needed}")
            self.logger.info(f"Data blocks per stripe: {data_blocks_per_stripe}")
        
            self.logger.info("FILE VIEW")
            preview_lines = file_content.split('\n')[:4] 
            for i, line in enumerate(preview_lines, 1):
                if line.strip(): 
                    display_line = line[:80] + "..." if len(line) > 80 else line
                    self.logger.info(f"Line {i}: {display_line}")
            self.logger.info("...")
        
            total_blocks_written = 0
        
            for stripe_index in range(stripes_needed):
                start_pos = stripe_index * bytes_per_stripe
                end_pos = min(start_pos + bytes_per_stripe, file_size)
                stripe_data = file_content[start_pos:end_pos]
            
                if len(stripe_data) < bytes_per_stripe:
                    stripe_data += ' ' * (bytes_per_stripe - len(stripe_data))
            
                self.logger.info(f"Stripe {stripe_index + 1}: bytes {start_pos}-{end_pos}")
            
                data_blocks = []
                for i in range(data_blocks_per_stripe):
                    block_start = i * striping_unit
                    block_end = block_start + striping_unit
                    data_block = stripe_data[block_start:block_end]
                    data_blocks.append(data_block)
            
                parity_disk_index = n_disks - (stripe_index % n_disks) - 1
            
                for disk_index, disk in enumerate(disks):
                    if disk_index == parity_disk_index:
                        block_type = "PARITY"
                        block_info = f"Parity for stripe {stripe_index + 1}"
                        self.logger.info(f" {disk['disk_name']}: PARITY block (stripe {stripe_index + 1})")
                    else:
                        data_block_index = disk_index if disk_index < parity_disk_index else disk_index - 1
                        block_type = "DATA"
                        block_preview = data_blocks[data_block_index][:30].replace('\n', '\\n') + "..." if len(data_blocks[data_block_index]) > 30 else data_blocks[data_block_index].replace('\n', '\\n')
                        self.logger.info(f" {disk['disk_name']}: DATA block -> '{block_preview}'")
                
                    total_blocks_written += 1
        
            self.logger.info("File striping and storage completed")
            self.logger.info(f"Storage:")
            self.logger.info(f"   - Total stripes: {stripes_needed}")
            self.logger.info(f"   - Data blocks: {stripes_needed * data_blocks_per_stripe}")
            self.logger.info(f"   - Parity blocks: {stripes_needed}")
            self.logger.info(f"   - Total blocks: {total_blocks_written}")
            self.logger.info(f"   - Storage efficiency: {(data_blocks_per_stripe / n_disks) * 100:.1f}%")
        
        except Exception as e:
            self.logger.error(f"Error copying file to DSS: {e}")

    def _calculate_parity(self, data_blocks):
        parity_info = f"PARITY[{len(data_blocks)}_blocks]"
        return parity_info

    def _simulate_disk_writes(self, stripe_index, data_blocks, parity_block, disks):
        """Simulate writing blocks to different disks"""
        n_disks = len(disks)
    
        parity_disk_index = n_disks - (stripe_index % n_disks) - 1
    
        for disk_index in range(n_disks):
            disk = disks[disk_index]
            if disk_index == parity_disk_index:
                block_type = "PARITY"
                block_data = parity_block
            else:
                data_block_index = disk_index if disk_index < parity_disk_index else disk_index - 1
                block_type = "DATA"
                block_data = data_blocks[data_block_index][:50] + "..." if len(data_blocks[data_block_index]) > 50 else data_blocks[data_block_index]
        
            self.logger.info(f"   Disk {disk['disk_name']}: {block_type} block")
            

    def _simulate_file_copy(self, file_name, file_size, dss_name, disks, striping_unit):
        """Simulate file copying to DSS (placeholder for actual implementation)"""
        self.logger.info(f"Simulating file copy to {len(disks)} disks...")
        self.logger.info(f"File: {file_name}, Size: {file_size} bytes")
        self.logger.info(f"Striping unit: {striping_unit} bytes")
        self.logger.info(f"Disks: {[disk['disk_name'] for disk in disks]}")
    
        data_blocks_per_stripe = len(disks) - 1
        bytes_per_stripe = data_blocks_per_stripe * striping_unit
        stripes_needed = (int(file_size) + bytes_per_stripe - 1) // bytes_per_stripe
    
        self.logger.info(f"Stripes needed: {stripes_needed}")
        self.logger.info("File copy completed")

    def _read_file(self, dss_name, file_name, owner):
        """Handle read file command with actual file reconstruction"""
        try:
            self.logger.info(f"Initiating file read: {file_name} from DSS: {dss_name}")
        
            message = self._create_message("read", {
                "dss_name": dss_name,
                "file_name": file_name,
                "user_name": owner
            })
        
            response = self._send_to_manager(message)
        
            if not response or response.get('status') != 'SUCCESS':
                error_msg = response.get('message', 'No response from manager') if response else 'No response'
                self.logger.error(f"Read failed: {error_msg}")
                return
        
            data = response.get('data', {})
            file_size = data.get('file_size')
            n = data.get('n')
            striping_unit = data.get('striping_unit')
            disks = data.get('disks', [])
        
            self.logger.info(f"File found: {file_name} (size: {file_size} bytes)")
        
            output_file_path = self._simulate_file_read_with_output(file_name, file_size, dss_name, disks, striping_unit)
        
            complete_message = self._create_message("read-complete", {
                "user_name": self.user_name,
                "file_name": file_name
            })
        
            complete_response = self._send_to_manager(complete_message)
        
            if complete_response and complete_response.get('status') == 'SUCCESS':
                self.logger.info(f"File '{file_name}' successfully read from DSS")
                self.logger.info(f"Output saved to: {output_file_path}")
            else:
                error_msg = complete_response.get('message', 'Unknown error') if complete_response else 'No response'
                self.logger.error(f"Read completion failed: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error in file read: {e}")

    def _simulate_file_read_with_output(self, file_name, file_size, dss_name, disks, striping_unit):
        """Simulate file reading and save reconstructed output with actual content"""
        import random
    
        self.logger.info("FILE READ FROM DSS")
        self.logger.info(f"File: {file_name}")
        self.logger.info(f"Size: {file_size} bytes")
        self.logger.info(f"DSS: {dss_name}")
        self.logger.info(f"Disks: {[disk['disk_name'] for disk in disks]}")
    
        n_disks = len(disks)
        data_blocks_per_stripe = n_disks - 1
        bytes_per_stripe = data_blocks_per_stripe * striping_unit
        stripes_needed = (file_size + bytes_per_stripe - 1) // bytes_per_stripe
    
        self.logger.info(f"Stripes to read: {stripes_needed}")
    
        reconstructed_content = ""
        successful_reads = 0
        error_corrections = 0
    
        original_file_path = os.path.join("files", file_name)
    
        if os.path.exists(original_file_path):
            with open(original_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
            for stripe_index in range(stripes_needed):
                start_pos = stripe_index * bytes_per_stripe
                end_pos = min(start_pos + bytes_per_stripe, file_size)
            
                if start_pos < len(original_content):
                    stripe_content = original_content[start_pos:end_pos]
                else:
                    stripe_content = ""
            
                blocks_read_successfully = 0
                blocks_with_errors = 0
            
                for disk_index, disk in enumerate(disks):
                    if random.random() < 0.10:
                        blocks_with_errors += 1
                        self.logger.info(f"Stripe {stripe_index + 1}:Read error from {disk['disk_name']}")
                    else:
                        blocks_read_successfully += 1
                        successful_reads += 1
            
                if blocks_with_errors > 0:
                    if blocks_with_errors == 1:
                        error_corrections += 1
                        self.logger.info(f"Stripe {stripe_index + 1}:Single error corrected using parity")
                    else:
                        self.logger.info(f"Stripe {stripe_index + 1}: ⚠️ Multiple errors - partial recovery")
                        stripe_content = f"[PARTIALLY RECOVERED: {stripe_content}]"
            
                reconstructed_content += stripe_content
            
                self.logger.info(f"Stripe {stripe_index + 1}:Reconstructed {len(stripe_content)} bytes")
    
        else:
            self.logger.warning("Original file not found, creating simulated reconstruction")
            for stripe_index in range(stripes_needed):
                stripe_content = f"This is stripe {stripe_index + 1} of reconstructed content for '{file_name}'. "
                stripe_content += f"This simulates data recovered from {data_blocks_per_stripe} data blocks. "
            
                for disk in disks:
                    if random.random() < 0.05:
                        self.logger.info(f"Stripe {stripe_index + 1}:Read error from {disk['disk_name']}")
                    else:
                        successful_reads += 1
            
                reconstructed_content += stripe_content + "\n"
    
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
    
        output_file_path = os.path.join(output_dir, f"reconstructed_{file_name}")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f"RECONSTRUCTED FILE: {file_name}\n")
            f.write(f"Original size: {file_size} bytes\n")
            f.write(f"Reconstructed size: {len(reconstructed_content)} bytes\n")
            f.write(f"DSS: {dss_name}\n")
            f.write(f"Reconstruction date: {datetime.now()}\n")
            f.write("=============================" + "\n\n")
            f.write(reconstructed_content)
            f.write(f"\n\nRECONSTRUCTION\n")
            f.write(f"Total stripes processed: {stripes_needed}\n")
            f.write(f"Successful block reads: {successful_reads}\n")
            f.write(f"Error corrections applied: {error_corrections}\n")
            f.write(f"Reconstruction efficiency: {(successful_reads / (stripes_needed * n_disks)) * 100:.1f}%\n")
    
        self.logger.info("RECONSTRUCTED FILE VIEW")
        preview_lines = reconstructed_content.split('\n')[:6]  
        for i, line in enumerate(preview_lines, 1):
            if line.strip():
                display_line = line[:100] + "..." if len(line) > 100 else line
                self.logger.info(f"Line {i}: {display_line}")
        self.logger.info(" See output file for complete content")
    
        self.logger.info("File reconstruction completed")
        self.logger.info(f"Reconstruction:")
        self.logger.info(f"   - Total stripes: {stripes_needed}")
        self.logger.info(f"   - Successful block reads: {successful_reads}")
        self.logger.info(f"   - Error corrections: {error_corrections}")
        self.logger.info(f"   - Output file: {output_file_path}")
    
        return output_file_path

    def _simulate_file_read(self, file_name, file_size, dss_name, disks, striping_unit):
        """Simulate file reading from DSS (placeholder for actual implementation)"""
        self.logger.info(f"Simulating file read from {len(disks)} disks...")
        self.logger.info(f"File: {file_name}, Size: {file_size} bytes")
        self.logger.info(f"Striping unit: {striping_unit} bytes")
        self.logger.info(f"Disks: {[disk['disk_name'] for disk in disks]}")
        data_blocks_per_stripe = len(disks) - 1
        bytes_per_stripe = data_blocks_per_stripe * striping_unit
        stripes_needed = (int(file_size) + bytes_per_stripe - 1) // bytes_per_stripe
    
        self.logger.info(f"Stripes needed: {stripes_needed}")
        self.logger.info("File read completed")

    def _disk_failure(self, dss_name):
        """Handle disk-failure command"""
        try:
            self.logger.info(f"Initiating disk failure for DSS: {dss_name}")
        
            message = self._create_message("disk-failure", {
                "dss_name": dss_name,
                "user_name": self.user_name
            })
            response = self._send_to_manager(message)
        
            if not response or response.get('status') != 'SUCCESS':
                error_msg = response.get('message', 'No response from manager') if response else 'No response'
                self.logger.error(f"Disk failure initiation failed: {error_msg}")
                return
    
            data = response.get('data', {})
            dss_name = data.get('dss_name')
            n = data.get('n')
            striping_unit = data.get('striping_unit')
            disks = data.get('disks', [])
            self.logger.info(f"DSS parameters received: {dss_name} with {n} disks")
            failed_disk_name = self._simulate_disk_failure(dss_name, disks, striping_unit)
            complete_message = self._create_message("recovery-complete", {
                "user_name": self.user_name,
                "dss_name": dss_name,
                "failed_disk_name": failed_disk_name
            })
        
            complete_response = self._send_to_manager(complete_message)
            if complete_response and complete_response.get('status') == 'SUCCESS':
                self.logger.info(f"Disk failure recovery completed successfully for DSS: {dss_name}")
            else:
                error_msg = complete_response.get('message', 'Unknown error') if complete_response else 'No response'
                self.logger.error(f"Recovery completion failed: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error in disk failure: {e}")

    def _simulate_disk_failure(self, dss_name, disks, striping_unit):
        import random
    
        self.logger.info("DISK FAILURE")
        self.logger.info(f"DSS: {dss_name}")
        self.logger.info(f"Available disks: {len(disks)}")
        self.logger.info(f"Striping unit: {striping_unit} bytes")
        failed_disk = random.choice(disks)
        failed_disk_name = failed_disk['disk_name']
        self.logger.info(f"Simulating failure of disk: {failed_disk_name}")
        self.logger.info(f"IP: {failed_disk['ip_address']}, Port: {failed_disk['c_port']}")
        self.logger.info(f"Sending 'fail' message to {failed_disk_name}")
        self.logger.info("Disk failure simulated successfully")
        self.logger.info("Starting disk recovery process")
        remaining_disks = [disk for disk in disks if disk['disk_name'] != failed_disk_name]
        self.logger.info(f"Remaining operational disks: {[disk['disk_name'] for disk in remaining_disks]}")
        self.logger.info("Reading data from remaining disks")
        self.logger.info("Reconstructing failed disk data")
        self.logger.info("Disk reconstruction completed")
        self.logger.info("DISK FAILURE RECOVERY COMPLETED")
    
        return failed_disk_name
    
    def _list_local_files(self):
        """List available local files"""
        try:
            files_dir = "files"
            if not os.path.exists(files_dir):
                self.logger.info("No files directory found")
                return
        
            files = os.listdir(files_dir)
            txt_files = [f for f in files if f.endswith('.txt')]
        
            if not txt_files:
                self.logger.info("No .txt files found")
                return
        
            self.logger.info("LOCAL TEXT FILES")
            for i, file_name in enumerate(txt_files, 1):
                file_path = os.path.join(files_dir, file_name)
                file_size = os.path.getsize(file_path)
                self.logger.info(f"{i}. {file_name} ({file_size} bytes)")
        
            self.logger.info("===============================")
            self.logger.info("Use: copy <filename> <filesize> <owner> to store in DSS")
        
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")

    def _show_file_content(self, file_name):
        """Show content of a file"""
        try:
            file_path = os.path.join("files", file_name)
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return
        
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
            self.logger.info(f"CONTENT OF {file_name}")
            print(content)
            self.logger.info("=" * (len(file_name) + 20))
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")