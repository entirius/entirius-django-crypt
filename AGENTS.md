# AGENTS.md

`entirius-django-crypt` (Django app `django_crypt`) — symmetric encryption helper (Fernet) for Entirius Django modules.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_crypt` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.
- No AI attribution in commits or PR descriptions.

## Architecture

```
src/django_crypt/
├── __init__.py             # Crypt class (encrypt/decrypt/generate_salt)
├── fields.py               # CryptedTextField — transparently-encrypted model field
├── apps.py                 # DjangoCryptConfig (is_volkanos=True)
├── settings.py             # CRYPT_SALT (loaded from django.conf.settings)
└── management/commands/
    ├── encrypt.py          # ./manage.py encrypt "<text>"
    ├── decrypt.py          # ./manage.py decrypt "<ciphertext>"
    └── generate_salt.py    # ./manage.py generate_salt
```

No models, no migrations — a helper, a model field, and management commands.

Public API:

```python
from django_crypt import Crypt

class Crypt:
    salt: str

    def __init__(self, salt: str | None = None)
        # If salt is None, loads from settings.CRYPT_SALT
        # Raises ValueError if both salt and CRYPT_SALT are None

    @staticmethod
    def generate_salt() -> str
        # Returns Fernet-compatible base64 key (32 bytes encoded)

    def encrypt(self, text: str | None) -> str | None
        # Returns Fernet ciphertext (non-deterministic)
        # Returns None if input is None

    def decrypt(self, text: str | None) -> str | None
        # Returns plaintext from Fernet ciphertext
        # Returns None if input is None
        # Raises cryptography.fernet.InvalidToken on bad input
```

```python
from django_crypt.fields import CryptedTextField

class CryptedTextField(models.TextField):
    # Encrypts on write (get_prep_value) via Crypt, decrypts on read (from_db_value).
    # __init__ raises ValueError on db_index=True / unique=True / primary_key=True
    #   (Fernet ciphertext is non-deterministic — an index/unique/PK could never match).
    # from_db_value: on InvalidToken logs (field + model name only, never the ciphertext)
    #   and returns "". A missing/malformed CRYPT_SALT raises (config error, not row damage).
```

| Topic | Where |
|---|---|
| Fernet format and guarantees | https://cryptography.io/en/latest/fernet/ |
| Usage and installation | `README.md` |

## Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `CRYPT_SALT` | None | Fernet key (base64). Generate via `python manage.py generate_salt` |

## Gotchas

- **Non-deterministic ciphertext** — `encrypt(x)` and `encrypt(x)` produce **different** ciphertexts.
  Don't use `Crypt.encrypt` for lookup-key hashing. Use HMAC-SHA256 (or similar deterministic hash)
  for unique-indexed lookup columns.
- **CRYPT_SALT must be Fernet-compatible** — 32 url-safe base64-encoded bytes. Generate via
  `Crypt.generate_salt()` or `Fernet.generate_key()`. Random strings will fail at runtime.
- **Salt rotation requires re-encrypt** — if you change `CRYPT_SALT`, all existing ciphertexts
  become undecryptable. Plan migration: dual-key window with `Crypt(salt=old)` for read +
  `Crypt(salt=new)` for write, then bulk re-encrypt.
- **Errors leak structure** — `decrypt()` on garbage raises `cryptography.fernet.InvalidToken`.
  Don't surface raw exception in HTTP responses (info leak).
- **`CryptedTextField` can't be filtered or searched** — `filter(secret=x)` never matches, and the field refuses
  `db_index`/`unique`/`primary_key`. `dumpdata` exports the decrypted plaintext and `loaddata` re-encrypts it, so
  fixtures and dumps carry secrets in clear text.
- **A row read as `""` is overwritten on the next save** — `CryptedTextField` returns `""` for a value that no longer
  decrypts, and saving that instance writes `""` over the old ciphertext.
