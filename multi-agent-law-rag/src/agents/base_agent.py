"""
Abstract base agent class for multi-agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str):
        """
        Initialize base agent.

        Args:
            name: Agent name
        """
        self.name = name

    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic and update state.

        Args:
            state: Current state dict

        Returns:
            dict: Updated state

        Note: Must be implemented by subclasses
        """
        pass

    async def execute_with_timeout(self, state: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute agent with timeout.

        Args:
            state: Current state
            timeout: Timeout in seconds

        Returns:
            dict: Updated state
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.execute, state),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Return state with error
            state['error'] = f"{self.name} timed out after {timeout}s"
            return state
        except Exception as e:
            state['error'] = f"{self.name} failed: {str(e)}"
            return state

    def validate_input(self, state: Dict[str, Any]) -> bool:
        """
        Validate input state.

        Args:
            state: State to validate

        Returns:
            bool: True if valid
        """
        # Basic validation - subclasses can override
        if not isinstance(state, dict):
            return False
        if 'query' not in state:
            return False
        return True

    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"

    def __repr__(self):
        return self.__str__()
