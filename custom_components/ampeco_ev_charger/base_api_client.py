"""Base API client for AMPECO EV Charger."""

from abc import ABC, abstractmethod
import logging
import async_timeout
from typing import Any

from .exceptions import AuthenticationError, ConnectionError, AlreadyChargingError


class BaseApiClient(ABC):
    """Base API client implementation."""

    def __init__(self, host: str, session, timeout: int = 10):
        """Initialize the base client."""
        self._host = host.rstrip("/")
        self._session = session
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._logger.debug(
            "Initializing BaseApiClient with host: %s, timeout: %d",
            self._host,
            self._timeout,
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: dict = None,
        json_data: dict = None,
    ) -> dict[str, Any]:
        """Make authenticated request to the API."""
        url = f"{self._host}/api/v1/{endpoint}"
        self._logger.debug(
            "Making %s request to %s with data: %s",
            method,
            url,
            json_data if json_data else "None",
        )

        try:
            async with async_timeout.timeout(self._timeout):
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                )
                self._logger.debug(
                    "Response status: %d, headers: %s",
                    response.status,
                    response.headers,
                )

                if response.status == 401:
                    self._logger.debug("Authentication failed")
                    raise AuthenticationError("Invalid authentication")
                if response.status == 404:
                    self._logger.debug("Resource not found, returning empty dict")
                    return {}

                # Special handling for 406 errors when trying to start a charging session
                if response.status == 406 and "session/start" in endpoint:
                    self._logger.info(
                        "Received 406 when starting session - likely already charging"
                    )
                    raise AlreadyChargingError(
                        "Cannot start charging: A session is already active"
                    )

                response.raise_for_status()
                data = await response.json()
                self._logger.debug("Response data: %s", data)
                return data

        except AlreadyChargingError:
            # Re-raise without wrapping in ConnectionError
            raise
        except Exception as err:
            self._logger.error("API request failed: %s", str(err))
            raise ConnectionError(f"Failed to connect: {err}") from err
