# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospf_interfaces import (
    _parse_ipv4_iface,
    _parse_ipv6_iface,
    build_commands,
    get_running_config,
)


_BASE4 = ["protocols", "ospf", "interface"]
_BASE6 = ["protocols", "ospfv3", "interface"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.ipv4_fixture = load_fixture("ospf_interfaces_ipv4.json")
        self.ipv6_fixture = load_fixture("ospf_interfaces_ipv6.json")
        self.mock_vyos.get_config = MagicMock(
            side_effect=lambda path: (self.ipv4_fixture if path == _BASE4 else self.ipv6_fixture),
        )


class TestVyOSOspfInterfacesParse(VyOSModuleTestCase):

    def test_parse_ipv4_scalars(self):
        raw = {"cost": "100", "transmit-delay": "50", "priority": "26"}
        result = _parse_ipv4_iface(raw)
        self.assertEqual(result["afi"], "ipv4")
        self.assertEqual(result["cost"], 100)
        self.assertEqual(result["transmit_delay"], 50)
        self.assertEqual(result["priority"], 26)

    def test_parse_ipv4_md5_auth(self):
        raw = {"authentication": {"md5": {"key-id": {"10": {"md5-key": "secret"}}}}}
        result = _parse_ipv4_iface(raw)
        self.assertEqual(result["authentication"]["md5_key"]["key_id"], 10)
        self.assertEqual(result["authentication"]["md5_key"]["key"], "secret")

    def test_parse_ipv6_scalars(self):
        raw = {"dead-interval": "39", "passive": {}}
        result = _parse_ipv6_iface(raw)
        self.assertEqual(result["afi"], "ipv6")
        self.assertEqual(result["dead_interval"], 39)
        self.assertTrue(result["passive"])

    def test_get_running_config(self):
        result = get_running_config(self.mock_vyos)
        names = [e["name"] for e in result]
        self.assertIn("eth1", names)
        self.assertIn("eth2", names)
        eth1 = next(e for e in result if e["name"] == "eth1")
        afis = {af["afi"] for af in eth1["address_family"]}
        self.assertIn("ipv4", afis)
        self.assertIn("ipv6", afis)

    def test_get_running_config_empty(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSOspfInterfacesBuildCommands(unittest.TestCase):

    def test_deleted_all(self):
        have = [
            {
                "name": "eth1",
                "address_family": [{"afi": "ipv4", "cost": 100}, {"afi": "ipv6", "passive": True}],
            },
        ]
        cmds = build_commands([], have, "deleted")
        self.assertIn(("delete", _BASE4 + ["eth1"]), cmds)
        self.assertIn(("delete", _BASE6 + ["eth1"]), cmds)

    def test_deleted_specific(self):
        have = [
            {"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]},
            {"name": "eth2", "address_family": [{"afi": "ipv4", "cost": 200}]},
        ]
        cmds = build_commands([{"name": "eth1"}], have, "deleted")
        self.assertIn(("delete", _BASE4 + ["eth1"]), cmds)
        paths = [c[1] for c in cmds]
        self.assertNotIn(_BASE4 + ["eth2"], paths)

    def test_merged_adds_cost(self):
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, [], "merged")
        self.assertIn(("set", _BASE4 + ["eth1", "cost", "100"]), cmds)

    def test_merged_idempotent(self):
        have = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_merged_ipv6_passive(self):
        config = [{"name": "eth1", "address_family": [{"afi": "ipv6", "passive": True}]}]
        cmds = build_commands(config, [], "merged")
        self.assertIn(("set", _BASE6 + ["eth1", "passive"]), cmds)

    def test_overridden_removes_extra_interface(self):
        have = [
            {"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]},
            {"name": "eth2", "address_family": [{"afi": "ipv4", "cost": 200}]},
        ]
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, have, "overridden")
        self.assertIn(("delete", _BASE4 + ["eth2"]), cmds)

    def test_replaced_idempotent(self):
        have = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 200}]}]
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 200}]}]
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_rebuilds_on_change(self):
        have = [
            {
                "name": "eth1",
                "address_family": [{"afi": "ipv4", "cost": 100, "transmit_delay": 50}],
            },
        ]
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 200}]}]
        cmds = build_commands(config, have, "replaced")
        self.assertIn(("delete", _BASE4 + ["eth1"]), cmds)
        self.assertIn(("set", _BASE4 + ["eth1", "cost", "200"]), cmds)


if __name__ == "__main__":
    unittest.main()
