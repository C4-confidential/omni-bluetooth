# /Users/cidiacowalker/Zsoon app/omnilock/errors.py

class OmniLockError(Exception):
    """Base exception for all OmniLock errors."""
    pass

class ConnectionError(OmniLockError):
    """Raised when there's a connection-related error."""
    pass

class AuthenticationError(OmniLockError):
    """Raised when authentication fails."""
    pass

class ProtocolError(OmniLockError):
    """Raised when there's a protocol violation."""
    pass

class TimeoutError(OmniLockError):
    """Raised when an operation times out."""
    pass

class DeviceNotFoundError(OmniLockError):
    """Raised when the specified device is not found."""
    pass

class CommandError(OmniLockError):
    """Raised when a command fails."""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        if status_code is not None:
            message = f"{message} (status: 0x{status_code:02X})"
        super().__init__(message)