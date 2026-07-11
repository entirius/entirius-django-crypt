# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for django_crypt.Crypt — round-trip, salt generation, edge cases."""

import pytest
from cryptography.fernet import InvalidToken

from django_crypt import Crypt


class TestGenerateSalt:
    def test_returns_string(self):
        salt = Crypt.generate_salt()
        assert isinstance(salt, str)

    def test_two_calls_return_different_salts(self):
        salt1 = Crypt.generate_salt()
        salt2 = Crypt.generate_salt()
        assert salt1 != salt2

    def test_generated_salt_is_fernet_compatible(self):
        salt = Crypt.generate_salt()
        # Should not raise — fernet accepts the generated salt
        Crypt(salt=salt).encrypt("test")


class TestInit:
    def test_loads_salt_from_settings_when_not_provided(self, settings):
        # tests/settings.py sets CRYPT_SALT
        crypt = Crypt()
        assert crypt.salt == settings.CRYPT_SALT

    def test_uses_explicit_salt_when_provided(self):
        explicit = Crypt.generate_salt()
        crypt = Crypt(salt=explicit)
        assert crypt.salt == explicit

    def test_raises_value_error_when_salt_and_settings_missing(self, settings):
        settings.CRYPT_SALT = None
        with pytest.raises(ValueError, match="CRYPT_SALT is not set"):
            Crypt()


class TestEncryptDecryptRoundTrip:
    def test_encrypts_and_decrypts_simple_text(self):
        crypt = Crypt()
        assert crypt.decrypt(crypt.encrypt("hello")) == "hello"

    def test_encrypts_and_decrypts_unicode(self):
        crypt = Crypt()
        original = "zażółć gęślą jaźń · 日本語"
        assert crypt.decrypt(crypt.encrypt(original)) == original

    def test_encrypts_and_decrypts_empty_string(self):
        crypt = Crypt()
        assert crypt.decrypt(crypt.encrypt("")) == ""

    def test_encrypts_long_text(self):
        crypt = Crypt()
        original = "x" * 10_000
        assert crypt.decrypt(crypt.encrypt(original)) == original


class TestNonDeterminism:
    """Fernet ciphertexts include random IV — same plaintext yields different ciphertexts."""

    def test_two_encrypts_of_same_text_differ(self):
        crypt = Crypt()
        c1 = crypt.encrypt("same value")
        c2 = crypt.encrypt("same value")
        assert c1 != c2

    def test_both_decrypt_to_same_plaintext(self):
        crypt = Crypt()
        c1 = crypt.encrypt("same value")
        c2 = crypt.encrypt("same value")
        assert crypt.decrypt(c1) == crypt.decrypt(c2) == "same value"


class TestNonePassthrough:
    def test_encrypt_none_returns_none(self):
        assert Crypt().encrypt(None) is None

    def test_decrypt_none_returns_none(self):
        assert Crypt().decrypt(None) is None


class TestCrossSaltIsolation:
    def test_ciphertext_from_salt_a_cannot_decrypt_with_salt_b(self):
        salt_a = Crypt.generate_salt()
        salt_b = Crypt.generate_salt()
        ciphertext = Crypt(salt=salt_a).encrypt("secret")
        with pytest.raises(InvalidToken):
            Crypt(salt=salt_b).decrypt(ciphertext)


class TestInvalidInput:
    def test_decrypt_garbage_raises_invalid_token(self):
        with pytest.raises(InvalidToken):
            Crypt().decrypt("not-a-fernet-ciphertext")
