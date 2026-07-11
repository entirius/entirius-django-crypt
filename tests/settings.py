# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Standalone Django settings for django-crypt tests."""

SECRET_KEY = "not so secret test secret"  # noqa: S105
DEBUG = True

# Fernet-compatible test salt (generated via Crypt.generate_salt)
CRYPT_SALT = "gqebfjpTxP3J6aie-xB3RKcJOdojZyARou9K-R--wXI="

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_crypt",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
