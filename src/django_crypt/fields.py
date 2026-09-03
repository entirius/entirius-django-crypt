# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Transparently-encrypted model field, backed by `Crypt` (Fernet).

Encrypt on write, decrypt on read — call sites use plaintext and never see ciphertext.

Fernet ciphertext is non-deterministic (a fresh IV per save), so an indexed / unique /
primary-key encrypted column would never match. Those are refused at declaration time so the
mistake surfaces at `manage.py check`, not in production.

On decryption failure (salt rotation, row corruption) the field logs a generic message —
field + model name only, never the ciphertext — and returns `""`. Returning the raw ciphertext
would (a) flow garbage into consuming code and (b) get re-encrypted on the next save,
permanently corrupting the row. Empty-string-on-failure lets the standard
`if not config.secret: skip` pattern degrade gracefully.
"""

import logging

from cryptography.fernet import InvalidToken
from django.db import models

from django_crypt import Crypt

logger = logging.getLogger("process")

_FORBIDDEN_KWARGS = ("db_index", "unique", "primary_key")


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
        except (InvalidToken, ValueError, TypeError):
            model_name = getattr(getattr(self, "model", None), "__name__", "?")
            logger.error("CryptedTextField decryption failed (field=%s.%s) — returning empty", model_name, self.name)
            return ""
