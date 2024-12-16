"""Exceptions for the AMPECO EV Charger integration."""


class AmpecoEVChargerError(Exception):
    """Base exception for AMPECO EV Charger."""


class AuthenticationError(AmpecoEVChargerError):
    """Exception raised for authentication failures."""


class ConnectionError(AmpecoEVChargerError):
    """Exception raised for connection failures."""


class NoActiveSessionError(AmpecoEVChargerError):
    """Exception raised when no active charging session is found."""


class InvalidResponse(AmpecoEVChargerError):
    """Exception raised when the API response is invalid."""


class RateLimitError(AmpecoEVChargerError):
    """Exception raised when API rate limit is exceeded."""


class ApiError(AmpecoEVChargerError):
    """Exception raised for general API errors."""
