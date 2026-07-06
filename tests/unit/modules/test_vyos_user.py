# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_user import (
    _device_to_argspec,
    _public_keys_from_device,
    _public_keys_to_device,
    _user_from_device,
    _user_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["system", "login", "user"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        fixture = load_fixture("user_running.json")
        self.fixture = fixture.get("user", fixture)
        self.mock_vyos.get_config = MagicMock(return_value={"user": self.fixture})


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_unwraps_user_key(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("alice", result)
        self.assertIn("vyos", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestPublicKeysToDeviceFromDevice(unittest.TestCase):
    def test_to_device(self):
        result = _public_keys_to_device([{"name": "laptop", "key": "AAAA", "type": "ssh-rsa"}])
        self.assertEqual(result, {"laptop": {"key": "AAAA", "type": "ssh-rsa"}})

    def test_from_device(self):
        result = _public_keys_from_device({"laptop": {"key": "AAAA", "type": "ssh-rsa"}})
        self.assertEqual(result, [{"name": "laptop", "key": "AAAA", "type": "ssh-rsa"}])

    def test_empty(self):
        self.assertEqual(_public_keys_to_device([]), {})
        self.assertEqual(_public_keys_from_device({}), [])


class TestUserToDeviceFromDevice(unittest.TestCase):
    """Password is the critical case here: it must NEVER appear in
    _user_to_device's output (it's handled separately, outside dict_op,
    since it can't be compared against have's encrypted-password)."""

    def test_password_never_enters_dict_op_path(self):
        result = _user_to_device({"name": "alice", "password": "secret", "full_name": "Alice"})
        self.assertNotIn("password", result)
        self.assertNotIn("plaintext-password", str(result))
        self.assertEqual(result, {"full_name": "Alice"})

    def test_update_password_never_enters_dict_op_path(self):
        result = _user_to_device({"name": "alice", "update_password": "on_create"})
        self.assertEqual(result, {})

    def test_public_keys_wrapped_under_authentication(self):
        result = _user_to_device(
            {
                "name": "alice",
                "public_keys": [{"name": "laptop", "key": "AAAA", "type": "ssh-rsa"}],
            },
        )
        self.assertEqual(
            result,
            {"authentication": {"public_keys": {"laptop": {"key": "AAAA", "type": "ssh-rsa"}}}},
        )

    def test_from_device_encrypted_password_surfaces_as_fact_only(self):
        entry = _user_from_device("alice", {"authentication": {"encrypted-password": "hash1"}})
        self.assertEqual(entry["encrypted_password"], "hash1")
        self.assertNotIn("password", entry)

    def test_from_device_plaintext_password_placeholder_ignored(self):
        """VyOS's write-only placeholder (an empty plaintext-password
        marker) must never surface in the argspec-facing output."""
        entry = _user_from_device(
            "vyos",
            {"authentication": {"encrypted-password": "hash1", "plaintext-password": ""}},
        )
        self.assertNotIn("plaintext_password", entry)
        self.assertNotIn("password", entry)

    def test_from_device_with_public_keys(self):
        entry = _user_from_device(
            "alice",
            {"authentication": {"public-keys": {"laptop": {"key": "AAAA", "type": "ssh-rsa"}}}},
        )
        self.assertEqual(
            entry["public_keys"],
            [{"name": "laptop", "key": "AAAA", "type": "ssh-rsa"}],
        )


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_alice_full_name_and_keys(self):
        have = _device_to_argspec(self.fixture)
        alice = next(u for u in have if u["name"] == "alice")
        self.assertEqual(alice["full_name"], "Alice Smith")
        self.assertEqual(alice["encrypted_password"], "$6$def456")
        self.assertEqual(alice["public_keys"][0]["name"], "alice-laptop")

    def test_vyos_user_present_no_plaintext_leak(self):
        have = _device_to_argspec(self.fixture)
        vyos_user = next(u for u in have if u["name"] == "vyos")
        self.assertNotIn("password", vyos_user)
        self.assertEqual(vyos_user["encrypted_password"], "$6$abc123")

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), [])
        self.assertEqual(_device_to_argspec(None), [])


class TestBuildCommands(VyOSModuleTestCase):
    """Password policy is the module's core correctness risk -- covered
    heavily here since it can never be validated via idempotency
    (there's no way to compare plaintext to a hash)."""

    def test_present_idempotent_without_password(self):
        have = _device_to_argspec(self.fixture)
        # drop encrypted_password/keys not settable via argspec anyway;
        # use only what a user would actually pass back in
        users = [{"name": u["name"], "full_name": u.get("full_name")} for u in have]
        cmds = build_commands(users, self.fixture, "present")
        self.assertEqual(cmds, [])

    def test_update_password_always_resets_existing_user(self):
        cmds = build_commands(
            [{"name": "alice", "password": "newpass", "update_password": "always"}],
            self.fixture,
            "present",
        )
        self.assertIn(
            ("set", _BASE + ["alice", "authentication", "plaintext-password", "newpass"]),
            cmds,
        )

    def test_update_password_on_create_skips_existing_user(self):
        cmds = build_commands(
            [{"name": "alice", "password": "newpass", "update_password": "on_create"}],
            self.fixture,
            "present",
        )
        self.assertTrue(all("plaintext-password" not in c[1] for c in cmds))

    def test_update_password_on_create_sets_for_new_user(self):
        cmds = build_commands(
            [{"name": "bob", "password": "newpass", "update_password": "on_create"}],
            self.fixture,
            "present",
        )
        self.assertIn(
            ("set", _BASE + ["bob", "authentication", "plaintext-password", "newpass"]),
            cmds,
        )

    def test_default_update_password_is_always(self):
        """default of 'always' must re-set even without explicit
        update_password, matching the argspec default."""
        cmds = build_commands([{"name": "alice", "password": "newpass"}], self.fixture, "present")
        self.assertIn(
            ("set", _BASE + ["alice", "authentication", "plaintext-password", "newpass"]),
            cmds,
        )

    def test_no_password_never_sets_plaintext(self):
        cmds = build_commands(
            [{"name": "alice", "full_name": "Alice Smith"}],
            self.fixture,
            "present",
        )
        self.assertTrue(all("plaintext-password" not in c[1] for c in cmds))

    def test_vyos_user_never_deleted(self):
        cmds = build_commands([{"name": "vyos"}], self.fixture, "absent")
        self.assertEqual(cmds, [])

    def test_absent_deletes_named_existing_user(self):
        cmds = build_commands([{"name": "alice"}], self.fixture, "absent")
        self.assertEqual(cmds, [("delete", _BASE + ["alice"])])

    def test_absent_skips_nonexistent_user(self):
        cmds = build_commands([{"name": "nobody"}], self.fixture, "absent")
        self.assertEqual(cmds, [])

    def test_present_adds_new_public_key_without_removing_others(self):
        """present is additive-only: adding a key for an existing user
        must not touch other existing fields."""
        cmds = build_commands(
            [
                {
                    "name": "alice",
                    "public_keys": [
                        {"name": "alice-desktop", "key": "BBBB", "type": "ssh-ed25519"},
                    ],
                },
            ],
            self.fixture,
            "present",
        )
        self.assertIn(
            (
                "set",
                _BASE
                + [
                    "alice",
                    "authentication",
                    "public-keys",
                    "alice-desktop",
                    "key",
                    "BBBB",
                ],
            ),
            cmds,
        )

    def test_collapsed_single_public_key_no_char_iteration_bug(self):
        raw_have = {"alice": {"authentication": {"public-keys": "alice-laptop"}}}
        users = [{"name": "alice", "public_keys": [{"name": "alice-laptop"}]}]
        self.assertEqual(build_commands(users, raw_have, "present"), [])


if __name__ == "__main__":
    unittest.main()
