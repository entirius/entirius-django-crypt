# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management import BaseCommand

from django_crypt import Crypt


class Command(BaseCommand):
    help = "Decrypt a Fernet-encrypted string using settings.CRYPT_SALT"

    def add_arguments(self, parser):
        parser.add_argument("text", type=str)

    def handle(self, *args, **options):
        text = options["text"]
        result = Crypt().decrypt(text)
        self.stdout.write(self.style.SUCCESS(f"{result}"))
