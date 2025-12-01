"""Module to provide the TextEnum classes"""
import enum


class EnumFriendly(enum.Enum):
    """Enum with the ablity to return a friendly name."""

    @property
    def friendly_name(self):
        """Return the "friendly" display name of the value."""
        return self.name.title().replace("_", " ")


class IntEnumFriendly(enum.IntEnum, EnumFriendly):
    """IntEnum with the ablity to return a friendly name."""
