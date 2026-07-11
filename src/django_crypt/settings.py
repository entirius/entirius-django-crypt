# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Lazy accessors for django-crypt settings.

Reads from `django.conf.settings` on every access — required for tests
to override settings dynamically (e.g. via pytest's `settings` fixture or
`@override_settings`).
"""

from django.conf import settings as django_settings


def __getattr__(name: str) -> object:
    if name == "CRYPT_SALT":
        return getattr(django_settings, "CRYPT_SALT", None)
    raise AttributeError(f"module 'django_crypt.settings' has no attribute {name!r}")
