"""Module to provide the User class"""
import xmltodict
from .auth import Auth


class User:
    """Class that represents a User object in the Salus iT500 API."""

    # Constructor
    def __init__(self, user_id: int, raw_data: dict, auth: Auth):
        """Initialise a user object."""
        self._user_id = user_id
        self.raw_data = raw_data or {}
        self.auth = auth

    # User Class Methods
    @classmethod
    async def async_get_user(cls, auth: Auth, user_id: int = None) -> "User":
        """Returns the signed in user."""
        if user_id is None and auth.get_user_id():
            user_id = auth.get_user_id()
        if user_id:
            user = User(user_id, None, auth)
            await user.async_update()
            return user

    # Note: each property name maps the name in the returned data
    @property
    def user_id(self) -> int:
        """Return the ID of the user."""
        return self._user_id

    @property
    def customer_name(self) -> str:
        """Return the username of the user."""
        return self.raw_data["valist:customerName"]["value"]

    @property
    def full_name(self) -> str:
        """Return the full name of the user."""
        return self.raw_data["valist:full_name"]["value"]

    async def async_update(self):
        """Update the user data."""
        resp = await self.auth.request(
            "post", "getUserValueList", data={"userId": self._user_id}
        )
        resp.raise_for_status()
        self.raw_data = xmltodict.parse(
            await resp.text(),
            xml_attribs=False,
            force_list=("valist",),
            postprocessor=User.xml_postprocessor,
        )["ns1:getUserValueListResponse"]
        self._user_id = self.raw_data["userId"]

    @staticmethod
    def xml_postprocessor(_path, key, value) -> tuple:
        """Called by xmltodict. Extracts the valist key/value pairs."""
        if key == "valist":
            return "valist:" + value["name"], value
        return key, value
