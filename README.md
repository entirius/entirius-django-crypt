# django-crypt

Symmetric encryption helper (Fernet) for Volkanos Django modules. Wraps `cryptography.fernet`
with a salt loaded from `settings.CRYPT_SALT`.

## Quick Start

Requires Python 3.11+.

```bash
make install   # uv venv + install deps
make test      # run tests
make check     # ruff lint + format check
```

## Usage

```python
from django_crypt import Crypt

# Encrypt / decrypt
crypt = Crypt()                            # uses settings.CRYPT_SALT
encrypted = crypt.encrypt("secret value")
decrypted = crypt.decrypt(encrypted)
assert decrypted == "secret value"

# Generate fresh salt (for first-time setup)
salt = Crypt.generate_salt()               # static method
print(f"Save this in settings.CRYPT_SALT: {salt}")
```

### Transparently-encrypted model field

`CryptedTextField` encrypts on write and decrypts on read — call sites use plaintext:

```python
from django.db import models

from django_crypt.fields import CryptedTextField


class PaymentProviderConfig(models.Model):
    client_id = CryptedTextField(default="")
    client_secret = CryptedTextField(default="")
```

- Cannot be `db_index`, `unique`, or `primary_key` (Fernet ciphertext is non-deterministic) —
  those raise `ValueError` at declaration time.
- On decryption failure (salt rotation, row corruption) it logs and returns `""` (never the raw
  ciphertext), so `if not config.client_secret: skip` degrades gracefully.
- Do **not** seed secrets into this field via fixtures — YAML can't carry the encrypted form.

## Management Commands

```bash
python manage.py generate_salt           # generate fresh salt
python manage.py encrypt "plain text"    # encrypt a string
python manage.py decrypt "<ciphertext>"  # decrypt a string
```

## Settings

```python
# In Django settings.py
CRYPT_SALT = "<output of generate_salt>"
INSTALLED_APPS = [..., "django_crypt"]
```

## Important

Fernet ciphertexts are **non-deterministic** — encrypting the same plaintext twice yields
different ciphertexts. For deterministic lookup hashing (e.g. unique-indexed code lookup),
use a separate HMAC-SHA256 helper, not `Crypt.encrypt()`.

## Details

See [`AGENTS.md`](AGENTS.md) for architecture and integration details.
