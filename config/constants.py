"""Configuration constants for DSS"""

# Network constants
MAX_PACKET_SIZE = 65507  # Max UDP packet size
SOCKET_TIMEOUT = 5.0     # Socket timeout time
BUFFER_SIZE = 4096       # Buffer for socket

# Message constants
MESSAGE_ENCODING = 'utf-8'
MAX_MESSAGE_SIZE = 4096

# Validation constants
MAX_NAME_LENGTH = 15
MIN_DISKS = 3
MIN_STRIPE_SIZE = 128     
MAX_STRIPE_SIZE = 1048576

# Port range
PORT_RANGE_START = 1500
PORT_RANGE_END = 1999

# Response codes
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"

class DiskState:
    FREE = "FREE"
    IN_DSS = "IN_DSS"