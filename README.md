# entirius-django-crypt

A Django helper for symmetric encryption in Entirius, the open-source modular ecommerce platform: Fernet encrypt and decrypt with one key from settings.
It wraps `cryptography.fernet` in a small `Crypt` class and ships management commands for the same operations.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-crypt.svg)](https://pypi.org/project/entirius-django-crypt/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-crypt.svg)](https://pypi.org/project/entirius-django-crypt/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-crypt/blob/develop/LICENSE)

## What it does

- Encrypts and decrypts strings with Fernet, using the key in `settings.CRYPT_SALT` or one passed to `Crypt(salt=...)`.
- Generates a Fernet-compatible key with `Crypt.generate_salt()`.
- Passes `None` through unchanged, so nullable fields need no guard.
- Ships the management commands `generate_salt`, `encrypt` and `decrypt`.
- Produces non-deterministic ciphertext: the same plaintext encrypts to a different value each time, so use a
  separate deterministic hash (for example HMAC-SHA256) for unique or lookup columns.

## Installation

```shell
uv add entirius-django-crypt
pip install entirius-django-crypt
```

```python
INSTALLED_APPS = [
    ...
    "django_crypt",
]

CRYPT_SALT = "<output of generate_salt>"
```

```shell
python manage.py generate_salt           # print a fresh key
python manage.py encrypt "plain text"    # encrypt a string
python manage.py decrypt "<ciphertext>"  # decrypt a string
```

Required setting: `CRYPT_SALT`; reference in
https://github.com/entirius/entirius-django-crypt/blob/develop/AGENTS.md (section Settings).

## Quick start

```python
from django_crypt import Crypt

crypt = Crypt()                            # uses settings.CRYPT_SALT
encrypted = crypt.encrypt("secret value")
assert crypt.decrypt(encrypted) == "secret value"

salt = Crypt.generate_salt()               # a fresh key for first-time setup
```

## Requirements

- Python 3.11 or newer, Django 4.0 or newer.
- `cryptography` 42.0 or newer.
- No database tables and no other Entirius packages.

## Documentation

- Entirius documentation: https://docs.entirius.com/
- Releases: https://github.com/entirius/entirius-django-crypt/releases
- Fernet specification: https://cryptography.io/en/latest/fernet/

## Part of Entirius

This module installs into the Entirius backend service (Volkanos) as a standalone helper with no database tables.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-utils

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django)
```

Development and agent instructions: https://github.com/entirius/entirius-django-crypt/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-crypt/blob/develop/LICENSE.
