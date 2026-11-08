"""Exceptions for aioeltako_ip."""

class EltakoError(Exception):
    """Base exception for all Eltako errors."""

class AuthenticationError(EltakoError):
    """Raised when authentication fails (invalid PoP or expired token)."""

class EltakoConnectionError(EltakoError):
    """Raised when unable to communicate with the Eltako device."""

class DeviceNotFoundError(EltakoError):
    """Raised when a requested device is not found."""

class UnsupportedCommandError(EltakoError):
    """Raised when an operation or command is invalid or unsupported."""
