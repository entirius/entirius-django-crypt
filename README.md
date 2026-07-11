# django-crypt

Symmetric encryption helper (Fernet) for Volkanos Django modules. Wraps `cryptography.fernet`
with a salt loaded from `settings.CRYPT_SALT`.

## Quick Start

Requires Python 3.11+.

```bash
make install   # uv venv + install deps
make test      # run tests
make lint      # ruff check + format
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
