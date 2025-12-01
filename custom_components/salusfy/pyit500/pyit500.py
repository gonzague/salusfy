"""Module provising Main API Class"""
# from typing import List

from typing import List
from .auth import Auth
from .user import User
from .devicelistitem import DeviceListItem
from .device import Device

# from .light import Light


class PyIt500:
    """Class to communicate with the ExampleHub API."""

    def __init__(self, auth: Auth):
        """Inialize the API and store the auth so we can make requests."""
        self.auth = auth

    async def refresh_session(self) -> None:
        """Refresh the Auth session"""
        await self.auth.refresh_token()

    async def async_get_user(self) -> User:
        """Return the user."""
        return await User.async_get_user(self.auth)

    async def async_get_device_list(self) -> List[DeviceListItem]:
        """Return a list of devices (in summary)"""
        return await DeviceListItem.async_get_device_list(self.auth)

    async def async_get_device(self, device_id) -> Device:
        """Return a device"""
        return await Device.async_get_device(self.auth, device_id)
