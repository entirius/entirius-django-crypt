# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Transparently-encrypted model field, backed by `Crypt` (Fernet).

Encrypt on write, decrypt on read — call sites use plaintext and never see ciphertext.

Fernet ciphertext is non-deterministic (a fresh IV per save), so an indexed / unique /
primary-key encrypted column would never match. Those are refused at declaration time so the
mistake surfaces at `manage.py check`, not in production.

On decryption failure (`InvalidToken`: salt rotation, row corruption) the field logs a generic message —
model + field name only, never the ciphertext — and raises `DecryptionError`. It never returns a value
for such a row: the raw ciphertext would flow into consuming code and get re-encrypted on the next save,
and `""` would be written over the ciphertext by the next `save()`, losing the secret for good. Loading
the row fails loud until an operator restores the right `CRYPT_SALT` or blanks the column with
`QuerySet.update()`, which never reads it. A missing or malformed `CRYPT_SALT` is a configuration error,
not row damage: it raises `ValueError` from `Crypt` as before.
"""

import logging

from cryptography.fernet import InvalidToken
from django.db import models

from django_crypt import Crypt

logger = logging.getLogger("process")

_FORBIDDEN_KWARGS = ("db_index", "unique", "primary_key")


class DecryptionError(Exception):
    """A stored `CryptedTextField` value doesn't decrypt with the current `CRYPT_SALT`.

    Raised instead of returning a value, so the row can't be silently overwritten on the next save.
    The message names model and field only — never the ciphertext or the plaintext.
    """


class CryptedTextField(models.TextField):
    """A `TextField` whose value is encrypted at rest via `Crypt` (Fernet / `CRYPT_SALT`)."""

    def __init__(self, *args, **kwargs) -> None:
        for forbidden in _FORBIDDEN_KWARGS:
            if kwargs.get(forbidden):
                raise ValueError(
                    f"CryptedTextField does not support {forbidden}=True — Fernet ciphertext is "
                    "non-deterministic and cannot be indexed, made unique, or used as a primary key."
                )
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        return Crypt().encrypt(str(value))

    def from_db_value(self, value: str | None, expression, connection) -> str | None:
        if value is None or value == "":
            return value
        try:
            return Crypt().decrypt(value)
        except InvalidToken as exc:  # row-level damage; a missing/malformed CRYPT_SALT raises ValueError in Crypt
            model_name = getattr(getattr(self, "model", None), "__name__", "?")
            logger.error("CryptedTextField decryption failed (field=%s.%s)", model_name, self.name)
            raise DecryptionError(
                f"{model_name}.{self.name} does not decrypt with the current CRYPT_SALT (salt rotated or row corrupted)"
            ) from exc
