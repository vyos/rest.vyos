# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_user import (
    build_commands,
    get_running_config,
)


_BASE = ["system", "login", "user"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("user_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestVyOSUserGetRunning(VyOSModuleTestCase):

    def test_parses_users(self):
        result = get_running_config(self.mock_vyos)
        names = [u["name"] for u in result]
        self.assertIn("vyos", names)
        self.assertIn("alice", names)

    def test_parses_full_name(self):
        result = get_running_config(self.mock_vyos)
        alice = next(u for u in result if u["name"] == "alice")
        self.assertEqual(alice["full_name"], "Alice Smith")

    def test_parses_encrypted_password(self):
        result = get_running_config(self.mock_vyos)
        alice = next(u for u in result if u["name"] == "alice")
        self.assertEqual(alice["encrypted_password"], "$6$def456")

    def test_parses_public_keys(self):
        result = get_running_config(self.mock_vyos)
        alice = next(u for u in result if u["name"] == "alice")
        self.assertEqual(len(alice["public_keys"]), 1)
        key = alice["public_keys"][0]
        self.assertEqual(key["name"], "alice-laptop")
        self.assertEqual(key["type"], "ssh-rsa")
        self.assertEqual(key["key"], "AAAAB3NzaC1yc2EAAAA")

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSUserBuildCommands(unittest.TestCase):

    def _have(self):
        return [
            {"name": "vyos", "encrypted_password": "$6$abc123"},
            {
                "name": "alice",
                "full_name": "Alice Smith",
                "encrypted_password": "$6$def456",
            },
        ]

    def test_present_new_user_with_password(self):
        users = [
            {
                "name": "bob",
                "full_name": "Bob Jones",
                "password": "secret",
                "update_password": "always",
            },
        ]
        cmds = build_commands(users, self._have(), "present")
        self.assertIn(("set", _BASE + ["bob", "full-name", "Bob Jones"]), cmds)
        self.assertIn(
            ("set", _BASE + ["bob", "authentication", "plaintext-password", "secret"]),
            cmds,
        )

    def test_present_update_password_always(self):
        users = [{"name": "alice", "password": "newpass", "update_password": "always"}]
        cmds = build_commands(users, self._have(), "present")
        self.assertIn(
            ("set", _BASE + ["alice", "authentication", "plaintext-password", "newpass"]),
            cmds,
        )

    def test_present_update_password_on_create_existing(self):
        users = [{"name": "alice", "password": "newpass", "update_password": "on_create"}]
        cmds = build_commands(users, self._have(), "present")
        paths = [c[1] for c in cmds]
        self.assertNotIn(
            _BASE + ["alice", "authentication", "plaintext-password", "newpass"],
            paths,
        )

    def test_present_update_password_on_create_new(self):
        users = [{"name": "bob", "password": "secret", "update_password": "on_create"}]
        cmds = build_commands(users, self._have(), "present")
        self.assertIn(
            ("set", _BASE + ["bob", "authentication", "plaintext-password", "secret"]),
            cmds,
        )

    def test_present_idempotent_full_name(self):
        users = [{"name": "alice", "full_name": "Alice Smith"}]
        cmds = build_commands(users, self._have(), "present")
        self.assertEqual(cmds, [])

    def test_present_update_full_name(self):
        users = [{"name": "alice", "full_name": "Alice Updated"}]
        cmds = build_commands(users, self._have(), "present")
        self.assertIn(
            ("set", _BASE + ["alice", "full-name", "Alice Updated"]),
            cmds,
        )

    def test_absent_existing_user(self):
        users = [{"name": "alice"}]
        cmds = build_commands(users, self._have(), "absent")
        self.assertIn(("delete", _BASE + ["alice"]), cmds)

    def test_absent_nonexistent_user(self):
        users = [{"name": "bob"}]
        cmds = build_commands(users, self._have(), "absent")
        self.assertEqual(cmds, [])

    def test_present_public_key(self):
        users = [
            {
                "name": "alice",
                "public_keys": [
                    {"name": "new-key", "key": "AAAAB3...", "type": "ssh-ed25519"},
                ],
            },
        ]
        cmds = build_commands(users, self._have(), "present")
        self.assertIn(
            (
                "set",
                _BASE + ["alice", "authentication", "public-keys", "new-key", "key", "AAAAB3..."],
            ),
            cmds,
        )
        self.assertIn(
            (
                "set",
                _BASE
                + ["alice", "authentication", "public-keys", "new-key", "type", "ssh-ed25519"],
            ),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
