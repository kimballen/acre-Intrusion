"""Storage handling for acre Intrusion."""
from homeassistant.helpers.storage import Store
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import hashlib
import base64
import os

from .const import STORAGE_KEY, STORAGE_VERSION

class PinStorage:
    """Class to handle PIN storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data = {}

    async def async_load(self) -> None:
        """Load pins."""
        self._data = await self.store.async_load() or {}

    async def async_save(self) -> None:
        """Save pins."""
        await self.store.async_save(self._data)

    def _hash_pin(self, pin: str, salt: str = None) -> tuple[str, str]:
        """Hash a PIN with salt."""
        if salt is None:
            salt = base64.b64encode(os.urandom(16)).decode('utf-8')
        pin_bytes = pin.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hash_obj = hashlib.pbkdf2_hmac('sha256', pin_bytes, salt_bytes, 100000)
        pin_hash = base64.b64encode(hash_obj).decode('utf-8')
        return pin_hash, salt

    def verify_pin(self, pin: str, username: str = None) -> bool:
        """Verify if a PIN is valid."""
        if not username:
            # Verify against all stored PINs
            for user_data in self._data.values():
                stored_hash = user_data.get('pin_hash')
                salt = user_data.get('salt')
                if stored_hash and salt:
                    test_hash, _ = self._hash_pin(pin, salt)
                    if test_hash == stored_hash:
                        return True
            return False
        else:
            # Verify against specific user's PIN
            user_data = self._data.get(username, {})
            stored_hash = user_data.get('pin_hash')
            salt = user_data.get('salt')
            if stored_hash and salt:
                test_hash, _ = self._hash_pin(pin, salt)
                return test_hash == stored_hash
            return False

    async def async_store_pin(self, username: str, pin: str) -> None:
        """Store a PIN for a user."""
        pin_hash, salt = self._hash_pin(pin)
        self._data[username] = {
            'pin_hash': pin_hash,
            'salt': salt
        }
        await self.async_save()

    async def async_remove_user(self, username: str) -> None:
        """Remove a user's PIN."""
        if username in self._data and username != 'admin':
            self._data.pop(username)
            await self.async_save()

    def get_users(self) -> list[str]:
        """Get list of users with stored PINs."""
        return list(self._data.keys())

    def has_admin_pin(self) -> bool:
        """Check if admin PIN is configured."""
        return 'admin' in self._data

    def verify_admin_pin(self, pin: str) -> bool:
        """Verify admin PIN."""
        if not self.has_admin_pin():
            return False
        admin_data = self._data.get('admin', {})
        stored_hash = admin_data.get('pin_hash')
        salt = admin_data.get('salt')
        if stored_hash and salt:
            test_hash, _ = self._hash_pin(pin, salt)
            return test_hash == stored_hash
        return False

    async def async_store_admin_pin(self, pin: str) -> None:
        """Store admin PIN."""
        pin_hash, salt = self._hash_pin(pin)
        self._data['admin'] = {
            'pin_hash': pin_hash,
            'salt': salt
        }
        await self.async_save()

    def get_user_pins(self) -> dict[str, dict]:
        """Get all user PINs except admin."""
        return {k: v for k, v in self._data.items() if k != 'admin'}
