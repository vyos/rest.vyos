# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_bgp_address_family import (
    build_commands,
    get_running_config,
)


_BASE = ["protocols", "bgp"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("bgp_af_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestVyOSBgpAFGetRunning(VyOSModuleTestCase):

    def test_parses_as_number(self):
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["as_number"], 65000)

    def test_parses_global_af_networks(self):
        result = get_running_config(self.mock_vyos)
        ipv4 = next(af for af in result["address_family"] if af["afi"] == "ipv4")
        prefixes = [n["prefix"] for n in ipv4["networks"]]
        self.assertIn("192.0.2.0/24", prefixes)
        self.assertIn("192.0.3.0/24", prefixes)

    def test_parses_global_af_redistribute(self):
        result = get_running_config(self.mock_vyos)
        ipv4 = next(af for af in result["address_family"] if af["afi"] == "ipv4")
        protos = [r["protocol"] for r in ipv4["redistribute"]]
        self.assertIn("connected", protos)
        connected = next(r for r in ipv4["redistribute"] if r["protocol"] == "connected")
        self.assertEqual(connected["metric"], 10)

    def test_parses_neighbor_af(self):
        result = get_running_config(self.mock_vyos)
        nb = next(n for n in result["neighbors"] if n["neighbor_address"] == "192.0.2.1")
        afis = [af["afi"] for af in nb["address_family"]]
        self.assertIn("ipv4", afis)
        self.assertIn("ipv6", afis)
        ipv4 = next(af for af in nb["address_family"] if af["afi"] == "ipv4")
        self.assertTrue(ipv4["nexthop_self"])
        self.assertTrue(ipv4["soft_reconfiguration"])

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {})


class TestVyOSBgpAFBuildCommands(unittest.TestCase):

    def _have(self):
        return {
            "as_number": 65000,
            "address_family": [
                {
                    "afi": "ipv4",
                    "networks": [{"prefix": "192.0.2.0/24"}],
                    "redistribute": [{"protocol": "connected", "metric": 10}],
                },
            ],
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "address_family": [
                        {"afi": "ipv4", "soft_reconfiguration": True, "nexthop_self": True},
                    ],
                },
            ],
        }

    def test_deleted_removes_global_af(self):
        cmds = build_commands({"as_number": 65000}, self._have(), "deleted")
        self.assertIn(("delete", _BASE + ["address-family"]), cmds)

    def test_deleted_removes_neighbor_af(self):
        cmds = build_commands({"as_number": 65000}, self._have(), "deleted")
        self.assertIn(
            ("delete", _BASE + ["neighbor", "192.0.2.1", "address-family"]),
            cmds,
        )

    def test_merged_network(self):
        config = {
            "as_number": 65000,
            "address_family": [
                {"afi": "ipv4", "networks": [{"prefix": "192.0.5.0/24"}]},
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["address-family", "ipv4-unicast", "network", "192.0.5.0/24"]),
            cmds,
        )

    def test_merged_redistribute(self):
        config = {
            "as_number": 65000,
            "address_family": [
                {"afi": "ipv4", "redistribute": [{"protocol": "connected", "metric": 10}]},
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["address-family", "ipv4-unicast", "redistribute", "connected"]),
            cmds,
        )
        self.assertIn(
            (
                "set",
                _BASE
                + [
                    "address-family",
                    "ipv4-unicast",
                    "redistribute",
                    "connected",
                    "metric",
                    "10",
                ],
            ),
            cmds,
        )

    def test_merged_neighbor_soft_reconfig(self):
        config = {
            "as_number": 65000,
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "address_family": [
                        {"afi": "ipv4", "soft_reconfiguration": True},
                    ],
                },
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            (
                "set",
                _BASE
                + [
                    "neighbor",
                    "192.0.2.1",
                    "address-family",
                    "ipv4-unicast",
                    "soft-reconfiguration",
                    "inbound",
                ],
            ),
            cmds,
        )

    def test_merged_idempotent(self):
        have = self._have()
        config = {
            "as_number": 65000,
            "address_family": [
                {
                    "afi": "ipv4",
                    "networks": [{"prefix": "192.0.2.0/24"}],
                    "redistribute": [{"protocol": "connected", "metric": 10}],
                },
            ],
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "address_family": [
                        {"afi": "ipv4", "soft_reconfiguration": True, "nexthop_self": True},
                    ],
                },
            ],
        }
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        have = self._have()
        config = {
            "as_number": 65000,
            "address_family": [
                {
                    "afi": "ipv4",
                    "networks": [{"prefix": "192.0.2.0/24"}],
                    "redistribute": [{"protocol": "connected", "metric": 10}],
                },
            ],
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "address_family": [
                        {"afi": "ipv4", "soft_reconfiguration": True, "nexthop_self": True},
                    ],
                },
            ],
        }
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_rebuilds_on_change(self):
        have = self._have()
        config = {
            "as_number": 65000,
            "address_family": [
                {"afi": "ipv4", "networks": [{"prefix": "192.0.9.0/24"}]},
            ],
        }
        cmds = build_commands(config, have, "replaced")
        self.assertIn(("delete", _BASE + ["address-family"]), cmds)
        self.assertIn(
            ("set", _BASE + ["address-family", "ipv4-unicast", "network", "192.0.9.0/24"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
