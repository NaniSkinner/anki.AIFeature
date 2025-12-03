# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Simple obfuscation for API keys stored in profile.

This provides basic obfuscation to prevent casual viewing of API keys
in profile files. It is NOT cryptographically secure - the key can be
recovered by anyone with access to the source code and the obfuscated value.

For truly secure storage, consider using OS-level keychains in the future:
- macOS: Keychain
- Windows: Credential Manager
- Linux: Secret Service API
"""

from __future__ import annotations

import base64
import hashlib
import platform


def _get_machine_id() -> bytes:
    """Get a machine-specific identifier for key derivation."""
    # Use a combination of platform info as a simple machine identifier
    # This means the obfuscated key won't work if copied to another machine
    machine_info = f"{platform.node()}-{platform.machine()}-anki-ai"
    return hashlib.sha256(machine_info.encode()).digest()[:16]


def obfuscate_api_key(api_key: str) -> str:
    """Obfuscate an API key for storage.

    Args:
        api_key: The plain text API key

    Returns:
        An obfuscated string safe for storage
    """
    if not api_key:
        return ""

    key_bytes = api_key.encode("utf-8")
    machine_id = _get_machine_id()

    # XOR with machine ID (repeated to match length)
    obfuscated = bytearray(len(key_bytes))
    for i, byte in enumerate(key_bytes):
        obfuscated[i] = byte ^ machine_id[i % len(machine_id)]

    # Base64 encode for safe storage
    return "v1:" + base64.b64encode(obfuscated).decode("ascii")


def deobfuscate_api_key(obfuscated: str) -> str:
    """Deobfuscate a stored API key.

    Args:
        obfuscated: The obfuscated string from storage

    Returns:
        The original API key, or empty string if invalid
    """
    if not obfuscated:
        return ""

    # Check version prefix
    if not obfuscated.startswith("v1:"):
        # Legacy unobfuscated key - return as-is for migration
        return obfuscated

    try:
        encoded = obfuscated[3:]  # Remove "v1:" prefix
        obfuscated_bytes = base64.b64decode(encoded)
        machine_id = _get_machine_id()

        # XOR again to recover original
        original = bytearray(len(obfuscated_bytes))
        for i, byte in enumerate(obfuscated_bytes):
            original[i] = byte ^ machine_id[i % len(machine_id)]

        return original.decode("utf-8")
    except Exception:
        # If anything goes wrong, return empty string
        return ""
