# Changelog

## Unreleased

- `CryptedTextField` (`django_crypt.fields`): a `TextField` encrypted at rest with `Crypt` — call sites read and write
  plaintext. Refuses `db_index`, `unique` and `primary_key` at declaration (Fernet ciphertext differs on every save).
- A stored value that no longer decrypts (salt rotated, row corrupted) raises `django_crypt.fields.DecryptionError`
  on load; it is never read as `""`, so a later `save()` can't overwrite the ciphertext. The error and the `process`
  log line name model and field only. Recover by restoring the original `CRYPT_SALT`, or blank the column on purpose
  with `QuerySet.update()`. A missing or malformed `CRYPT_SALT` raises `ValueError`.
