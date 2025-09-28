"""Mode management service for auto/text/voice reply logic."""

from typing import Dict, Literal
from app.schemas import UserMode


class ModeManager:
    """Manager for user reply modes."""

    def __init__(self):
        # In-memory storage for MVP (use Redis in production)
        self._user_modes: Dict[int, UserMode] = {}

    def get_user_mode(self, user_id: int) -> UserMode:
        """
        Get user reply mode.

        Args:
            user_id: Telegram user ID

        Returns:
            User mode (defaults to AUTO)
        """
        return self._user_modes.get(user_id, UserMode.AUTO)

    def set_user_mode(self, user_id: int, mode: UserMode) -> None:
        """
        Set user reply mode.

        Args:
            user_id: Telegram user ID
            mode: New mode to set
        """
        self._user_modes[user_id] = mode

    def determine_response_mode(
        self,
        user_id: int,
        input_type: Literal["text", "voice"],
        text_content: str = None
    ) -> Literal["text", "voice"]:
        """
        Determine response mode based on user settings and input.

        Args:
            user_id: Telegram user ID
            input_type: Type of input ("text" or "voice")
            text_content: Text content if input_type is "text"

        Returns:
            Response mode ("text" or "voice")
        """
        user_mode = self.get_user_mode(user_id)

        # If user mode is explicit, use it
        if user_mode == UserMode.TEXT:
            return "text"
        elif user_mode == UserMode.VOICE:
            return "voice"

        # Auto mode logic
        if input_type == "voice":
            return "voice"

        # Check for voice markers in text
        if text_content and any(marker in text_content.lower() for marker in ["🔊", "voice", "/voice"]):
            return "voice"

        return "text"

    def get_mode_description(self, mode: UserMode) -> str:
        """
        Get human-readable description of a mode.

        Args:
            mode: Mode to describe

        Returns:
            Description string
        """
        descriptions = {
            UserMode.AUTO: "Автоматический режим: текст → текст, голос → голос, 🔊 → голос",
            UserMode.TEXT: "Всегда отвечать текстом",
            UserMode.VOICE: "Всегда отвечать голосом",
        }
        return descriptions.get(mode, "Неизвестный режим")


# Global instance for easy access
mode_manager = ModeManager()


def get_user_mode(user_id: int) -> UserMode:
    """Get user mode (convenience function)."""
    return mode_manager.get_user_mode(user_id)


def set_user_mode(user_id: int, mode: UserMode) -> None:
    """Set user mode (convenience function)."""
    mode_manager.set_user_mode(user_id, mode)


def determine_response_mode(
    user_id: int,
    input_type: Literal["text", "voice"],
    text_content: str = None
) -> Literal["text", "voice"]:
    """Determine response mode (convenience function)."""
    return mode_manager.determine_response_mode(user_id, input_type, text_content)


def get_mode_description(mode: UserMode) -> str:
    """Get mode description (convenience function)."""
    return mode_manager.get_mode_description(mode)