# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_vlan import (
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["interfaces", "ethernet"]


class TestVyOSVlanGetRunning(unittest.TestCase):

    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("vlan_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)

    def test_parses_vlans(self):
        result = get_running_config(self.mock_vyos)
        vlan_ids = [v["vlan_id"] for v in result]
        self.assertIn(10, vlan_ids)
        self.assertIn(20, vlan_ids)

    def test_parses_description(self):
        result = get_running_config(self.mock_vyos)
        v10 = next(v for v in result if v["vlan_id"] == 10)
        self.assertEqual(v10["description"], "VLAN10")

    def test_parses_address(self):
        result = get_running_config(self.mock_vyos)
        v10 = next(v for v in result if v["vlan_id"] == 10)
        self.assertEqual(v10["address"], "192.168.10.1/24")

    def test_parses_multiple_interfaces(self):
        result = get_running_config(self.mock_vyos)
        v10 = next(v for v in result if v["vlan_id"] == 10)
        self.assertIn("eth1", v10["interfaces"])
        self.assertIn("eth2", v10["interfaces"])

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSVlanBuildCommands(unittest.TestCase):

    def _have(self):
        return [
            {
                "vlan_id": 10,
                "interfaces": ["eth1"],
                "description": "VLAN10",
                "address": "192.168.10.1/24",
            },
            {"vlan_id": 20, "interfaces": ["eth1"], "description": "VLAN20"},
        ]

    def test_present_new_vlan(self):
        config = [{"vlan_id": 30, "description": "VLAN30", "interfaces": ["eth1"]}]
        cmds = build_commands(config, [], "present")
        self.assertIn(
            ("set", _BASE + ["eth1", "vif", "30", "description", "VLAN30"]),
            cmds,
        )

    def test_present_idempotent(self):
        config = [
            {
                "vlan_id": 10,
                "description": "VLAN10",
                "address": "192.168.10.1/24",
                "interfaces": ["eth1"],
            },
            {"vlan_id": 20, "description": "VLAN20", "interfaces": ["eth1"]},
        ]
        cmds = build_commands(config, self._have(), "present")
        self.assertEqual(cmds, [])

    def test_present_update_description(self):
        config = [{"vlan_id": 10, "description": "VLAN10-new", "interfaces": ["eth1"]}]
        cmds = build_commands(config, self._have(), "present")
        self.assertIn(
            ("set", _BASE + ["eth1", "vif", "10", "description", "VLAN10-new"]),
            cmds,
        )

    def test_absent_existing(self):
        config = [{"vlan_id": 10, "interfaces": ["eth1"]}]
        cmds = build_commands(config, self._have(), "absent")
        self.assertIn(("delete", _BASE + ["eth1", "vif", "10"]), cmds)

    def test_absent_nonexistent(self):
        config = [{"vlan_id": 99, "interfaces": ["eth1"]}]
        cmds = build_commands(config, self._have(), "absent")
        self.assertEqual(cmds, [])

    def test_present_bare_vif(self):
        config = [{"vlan_id": 30, "interfaces": ["eth1"]}]
        cmds = build_commands(config, [], "present")
        self.assertIn(("set", _BASE + ["eth1", "vif", "30"]), cmds)


if __name__ == "__main__":
    unittest.main()
