"""Abstract base client for social media platform integrations."""

from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseClient(ABC):
    """Abstract base class for platform clients with retry and rate limiting support."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the client connection is healthy.

        Returns:
            bool: True if healthy, False otherwise.
        """
        pass

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the platform."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the platform."""
        pass
