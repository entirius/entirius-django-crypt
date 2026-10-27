# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for CryptedTextField — constructor guards, prep/read hooks, ORM round-trip, fail-loud read, log redaction."""

import contextlib
import logging

import pytest
from cryptography.fernet import InvalidToken
from django.db import connection, models
from django.test.utils import isolate_apps

from django_crypt import Crypt
from django_crypt.fields import CryptedTextField, DecryptionError


class TestConstructorGuards:
    def test_rejects_db_index(self):
        with pytest.raises(ValueError, match="db_index"):
            CryptedTextField(db_index=True)

    def test_rejects_unique(self):
        with pytest.raises(ValueError, match="unique"):
            CryptedTextField(unique=True)

    def test_rejects_primary_key(self):
        with pytest.raises(ValueError, match="primary_key"):
            CryptedTextField(primary_key=True)

    def test_plain_declaration_is_allowed(self):
        assert isinstance(CryptedTextField(default=""), CryptedTextField)

    def test_allows_the_guarded_kwargs_when_explicitly_false(self):
        field = CryptedTextField(db_index=False, unique=False, primary_key=False)
        assert (field.db_index, field.unique, field.primary_key) == (False, False, False)


class TestHooks:
    """get_prep_value / from_db_value are the whole field — testable without a table."""

    def test_none_and_empty_pass_through(self):
        field = CryptedTextField()
        assert field.get_prep_value(None) is None
        assert field.get_prep_value("") == ""
        assert field.from_db_value(None, None, None) is None
        assert field.from_db_value("", None, None) == ""

    def test_encrypt_then_decrypt_roundtrip(self):
        field = CryptedTextField()
        ciphertext = field.get_prep_value("s3cr3t")
        assert ciphertext != "s3cr3t"
        assert Crypt().decrypt(ciphertext) == "s3cr3t"
        assert field.from_db_value(ciphertext, None, None) == "s3cr3t"

    def test_decrypt_failure_raises_without_echoing_the_value(self):
        field = CryptedTextField()
        field.set_attributes_from_name("secret")
        with pytest.raises(DecryptionError, match=r"\?\.secret") as excinfo:
            field.from_db_value("not-a-fernet-token", None, None)
        assert "not-a-fernet-token" not in str(excinfo.value)

    def test_missing_salt_raises_instead_of_reading_empty(self, settings):
        ciphertext = CryptedTextField().get_prep_value("s3cr3t")
        settings.CRYPT_SALT = None
        with pytest.raises(ValueError, match="CRYPT_SALT"):
            CryptedTextField().from_db_value(ciphertext, None, None)

    def test_malformed_salt_raises_instead_of_reading_empty(self, settings):
        ciphertext = CryptedTextField().get_prep_value("s3cr3t")
        settings.CRYPT_SALT = "not-a-fernet-key"
        with pytest.raises(ValueError):
            CryptedTextField().from_db_value(ciphertext, None, None)


@contextlib.contextmanager
def _temp_model():
    with isolate_apps("django_crypt"):

        class SecretHolder(models.Model):
            secret = CryptedTextField(default="")

            class Meta:
                app_label = "django_crypt"

            def __str__(self) -> str:
                return "SecretHolder"

        with connection.schema_editor() as editor:
            editor.create_model(SecretHolder)
        try:
            yield SecretHolder
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(SecretHolder)


def _raw_secret(model, pk) -> str:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT secret FROM {model._meta.db_table} WHERE id = %s", [pk])  # noqa: S608
        return cursor.fetchone()[0]


@pytest.mark.django_db(transaction=True)
class TestOrmRoundTrip:
    def test_column_holds_ciphertext_and_orm_reads_plaintext(self):
        with _temp_model() as model:
            obj = model.objects.create(secret="client-secret-123")  # noqa: S106 - field name, not a credential

            with connection.cursor() as cursor:
                cursor.execute(f"SELECT secret FROM {model._meta.db_table} WHERE id = %s", [obj.pk])  # noqa: S608
                raw = cursor.fetchone()[0]
            assert raw != "client-secret-123"
            assert Crypt().decrypt(raw) == "client-secret-123"

            assert model.objects.get(pk=obj.pk).secret == "client-secret-123"

    def test_corrupted_row_raises_and_keeps_the_stored_value(self):
        with _temp_model() as model:
            obj = model.objects.create(secret="value")  # noqa: S106 - field name, not a credential
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {model._meta.db_table} SET secret = %s WHERE id = %s",  # noqa: S608
                    ["not-a-fernet-token", obj.pk],
                )
            with pytest.raises(DecryptionError, match=r"SecretHolder\.secret") as excinfo:
                model.objects.get(pk=obj.pk)
            assert isinstance(excinfo.value.__cause__, InvalidToken)
            assert "not-a-fernet-token" not in str(excinfo.value)
            assert _raw_secret(model, obj.pk) == "not-a-fernet-token"

    def test_queryset_update_blanks_an_unreadable_row(self):
        with _temp_model() as model:
            obj = model.objects.create(secret="value")  # noqa: S106 - field name, not a credential
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {model._meta.db_table} SET secret = %s WHERE id = %s",  # noqa: S608
                    ["not-a-fernet-token", obj.pk],
                )
            model.objects.filter(pk=obj.pk).update(secret="")
            assert model.objects.get(pk=obj.pk).secret == ""


@pytest.mark.django_db(transaction=True)
class TestFailureLogging:
    """The stored ciphertext is still a secret — a failed read may name the column, never the value."""

    def test_failure_log_names_the_column_without_echoing_the_ciphertext(self, caplog, settings):
        with _temp_model() as model:
            obj = model.objects.create(secret="novatrade-api-token")  # noqa: S106 - field name, not a credential
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT secret FROM {model._meta.db_table} WHERE id = %s", [obj.pk])  # noqa: S608
                ciphertext = cursor.fetchone()[0]

            settings.CRYPT_SALT = Crypt.generate_salt()  # rotated key — the stored row no longer decrypts
            with caplog.at_level(logging.ERROR, logger="process"), pytest.raises(DecryptionError) as excinfo:
                model.objects.get(pk=obj.pk)

            logged = [record.getMessage() for record in caplog.records if record.name == "process"]
            assert logged, "the failure must be logged on the 'process' channel"
            assert "SecretHolder.secret" in logged[0]
            assert ciphertext not in caplog.text
            assert ciphertext not in str(excinfo.value)
            assert "novatrade-api-token" not in str(excinfo.value)


@pytest.mark.django_db(transaction=True)
class TestQueryability:
    """A fresh IV per write means a lookup value never matches the stored ciphertext."""

    def test_filtering_by_plaintext_never_matches(self):
        stored = "ENT-4471-recovery-code"
        with _temp_model() as model:
            model.objects.create(secret=stored)
            assert not model.objects.filter(secret=stored).exists()
