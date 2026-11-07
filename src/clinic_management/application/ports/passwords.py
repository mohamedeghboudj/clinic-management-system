"""PasswordHasher port: interface for secure password hashing operations."""

from __future__ import annotations

import abc


class PasswordHasher(abc.ABC):
    """Abstract port for encoding and verifying password hashes.

    Concrete implementations (e.g. Argon2) belong to the infrastructure layer
    and are provided during Week 2.  No cryptographic implementation is
    included here.

    The port is intentionally thin: the application layer must never handle
    raw passwords beyond forwarding them to this interface.
    """

    @abc.abstractmethod
    def hash(self, password: str) -> str:
        """Produce an encoded password hash from a plaintext password.

        The returned string is suitable for storage in ``UserAccount.password_hash``.
        The plaintext password must not be stored or logged after this call.

        Args:
            password: Plaintext password supplied by the user.

        Returns:
            An encoded hash string (algorithm, parameters, and hash combined).
        """

    @abc.abstractmethod
    def verify(self, password: str, encoded_hash: str) -> bool:
        """Verify a plaintext password against a stored encoded hash.

        Args:
            password: Plaintext password to verify.
            encoded_hash: Encoded hash previously produced by ``hash``.

        Returns:
            True if the password matches the hash, False otherwise.
        """

    @abc.abstractmethod
    def needs_rehash(self, encoded_hash: str) -> bool:
        """Return whether the encoded hash should be upgraded.

        This is True when the stored hash was produced with weaker parameters
        than the current policy (e.g. lower memory cost or iteration count).
        The application must re-hash and save the new hash after a successful
        login when this returns True.

        Args:
            encoded_hash: Encoded hash to inspect.

        Returns:
            True if the hash parameters are outdated and the account should be
            rehashed on next successful login.
        """

