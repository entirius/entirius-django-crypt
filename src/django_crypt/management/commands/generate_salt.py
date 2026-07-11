# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management import BaseCommand

from django_crypt import Crypt


class Command(BaseCommand):
    help = "Generate a fresh Fernet salt for settings.CRYPT_SALT"

    def handle(self, *args, **options):
        salt = Crypt.generate_salt()
        self.stdout.write("Save this salt in settings.CRYPT_SALT:")
        self.stdout.write(self.style.SUCCESS(f"{salt}"))
