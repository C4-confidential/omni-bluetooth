# /Users/cidiacowalker/Zsoon app/omnilock/protocol.py
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

# Protocol Constants
STX = bytes([0xAB, 0xDE])  # Start of packet marker

class Command(IntEnum):
    """OmniLock protocol commands."""
    # Basic commands
    VERIFY_KEY = 0x01    # Pairing/authentication
    ERASE_KEY = 0x02     # Unpairing
    OPERATIONAL = 0x05   # Lock/unlock control
    CONFIG = 0x06        # Device configuration
    HEARTBEAT = 0x07     # Keep-alive

class Status(IntEnum):
    """Response status codes."""
    SUCCESS = 0x00
    FAILURE = 0x01
    INVALID_COMMAND = 0x02
    INVALID_PARAM = 0x03
    NOT_PAIRED = 0x04
    TIMEOUT = 0x05
    BUSY = 0x06

@dataclass
class LockResponse:
    """Response from the lock device."""
    command: int
    status: int
    data: bytes = bytes()

class OmniLockProtocol:
    """Handles packet building and parsing for OmniLock protocol."""
    
    @staticmethod
    def build_packet(cmd: int, data: bytes = None) -> bytes:
        """Build a protocol packet according to the OmniLock spec."""
        if data is None:
            data = bytes()
        
        # Packet: [STX0][STX1][LEN][RAND][CMD][DATA...][SUM]
        rand_byte = random.randint(0, 255)
        packet = bytearray([0xAB, 0xDE, len(data) + 4, rand_byte, cmd])
        packet.extend(data)
        
        # Calculate checksum (XOR of RAND + CMD + DATA)
        checksum = 0
        for b in packet[3:]:
            checksum ^= b
        packet.append(checksum)
        
        return bytes(packet)

    @staticmethod
    def parse_packet(data: bytes) -> Optional[LockResponse]:
        """Parse a response packet from the lock."""
        if len(data) < 6:  # Minimum packet size
            return None
        
        # Verify STX
        if data[0] != 0xAB or data[1] != 0xDE:
            return None
        
        # Verify length
        length = data[2]
        if len(data) != length + 3:  # +3 for STX0, STX1, LEN
            return None
        
        # Verify checksum
        checksum = 0
        for b in data[3:]:
            checksum ^= b
        if checksum != 0:
            return None
        
        # Extract fields
        cmd = data[4]
        status = data[5] if len(data) > 5 else 0
        payload = data[6:-1] if len(data) > 7 else bytes()
        
        return LockResponse(command=cmd, status=status, data=payload)