# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    dict_op,
    owned_config,
)
from ansible_collections.vyos.rest.plugins.modules.vyos_system import (
    _BASE,
    ARGUMENT_SPEC,
)

from .base import load_fixture


class TestOwnedConfig(unittest.TestCase):

    def setUp(self):
        self.fixture = load_fixture("system_running.json")

    def test_filters_to_owned_keys(self):
        result = owned_config(self.fixture, ARGUMENT_SPEC)
        self.assertIn("host-name", result)
        self.assertIn("domain-name", result)
        self.assertIn("name-server", result)

    def test_excludes_non_owned_keys(self):
        result = owned_config(self.fixture, ARGUMENT_SPEC)
        self.assertNotIn("config-management", result)
        self.assertNotIn("console", result)
        self.assertNotIn("login", result)
        self.assertNotIn("syslog", result)


class TestDictOp(unittest.TestCase):

    def _have(self):
        return {
            "host-name": "vyos150",
            "domain-name": "lab.example.com",
            "name-server": ["8.8.8.8", "8.8.4.4"],
        }

    def test_set_idempotent(self):
        want = {
            "host_name": "vyos150",
            "domain_name": "lab.example.com",
            "name_server": ["8.8.8.8", "8.8.4.4"],
        }
        cmds = dict_op(want, self._have(), _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_set_new_value(self):
        want = {"domain_name": "new.example.com"}
        cmds = dict_op(want, self._have(), _BASE, op="set")
        self.assertIn(("set", ["system", "domain-name", "new.example.com"]), cmds)

    def test_set_new_nameserver(self):
        want = {"name_server": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]}
        cmds = dict_op(want, self._have(), _BASE, op="set")
        self.assertIn(("set", ["system", "name-server", "1.1.1.1"]), cmds)
        self.assertNotIn(("set", ["system", "name-server", "8.8.8.8"]), cmds)

    def test_delete_scalar(self):
        want = {"domain_name": "lab.example.com"}
        cmds = dict_op(want, self._have(), _BASE, op="delete")
        self.assertIn(("delete", ["system", "domain-name"]), cmds)

    def test_delete_list_item(self):
        want = {"name_server": ["8.8.8.8"]}
        cmds = dict_op(want, self._have(), _BASE, op="delete")
        self.assertIn(("delete", ["system", "name-server", "8.8.8.8"]), cmds)
        self.assertNotIn(("delete", ["system", "name-server", "8.8.4.4"]), cmds)

    def test_delete_nonexistent(self):
        want = {"domain_name": "other.com"}
        have = {"host-name": "vyos150"}
        cmds = dict_op(want, have, _BASE, op="delete")
        self.assertEqual(cmds, [])

    def test_set_missing_key(self):
        want = {"host_name": "vyos150"}
        cmds = dict_op(want, {}, _BASE, op="set")
        self.assertIn(("set", ["system", "host-name", "vyos150"]), cmds)


if __name__ == "__main__":
    unittest.main()
