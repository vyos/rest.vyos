# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_global import (
    build_commands,
    get_running_config,
)


_BASE = ["firewall", "group"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("firewall_global_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestVyOSFirewallGlobalGetRunning(VyOSModuleTestCase):

    def test_parses_address_groups(self):
        result = get_running_config(self.mock_vyos)
        groups = result["group"]["address_group"]
        names = [g["name"] for g in groups]
        self.assertIn("SERVERS", names)
        self.assertIn("DNS", names)
        servers = next(g for g in groups if g["name"] == "SERVERS")
        self.assertEqual(servers["description"], "Web servers")
        self.assertIn("192.168.1.10", servers["address"])
        self.assertIn("192.168.1.11", servers["address"])

    def test_parses_network_groups(self):
        result = get_running_config(self.mock_vyos)
        groups = result["group"]["network_group"]
        dmz = next(g for g in groups if g["name"] == "DMZ")
        self.assertIn("10.0.0.0/8", dmz["network"])
        self.assertIn("172.16.0.0/12", dmz["network"])

    def test_parses_port_groups(self):
        result = get_running_config(self.mock_vyos)
        groups = result["group"]["port_group"]
        web = next(g for g in groups if g["name"] == "WEB-PORTS")
        self.assertIn("80", web["port"])
        self.assertIn("443", web["port"])

    def test_parses_interface_groups(self):
        result = get_running_config(self.mock_vyos)
        groups = result["group"]["interface_group"]
        lan = next(g for g in groups if g["name"] == "LAN-IFACES")
        self.assertIn("eth1", lan["interface"])

    def test_parses_ipv6_network_groups(self):
        result = get_running_config(self.mock_vyos)
        groups = result["group"]["ipv6_network_group"]
        ipv6 = next(g for g in groups if g["name"] == "IPV6-LAN")
        self.assertIn("2001:db8::/32", ipv6["network"])

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {})


class TestVyOSFirewallGlobalBuildCommands(unittest.TestCase):

    def _have(self):
        return {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "address": ["192.168.1.10", "192.168.1.11"]},
                ],
                "network_group": [
                    {"name": "LAN", "network": ["192.168.0.0/16"]},
                ],
            },
        }

    def test_deleted_with_have(self):
        cmds = build_commands({}, self._have(), "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_without_have(self):
        cmds = build_commands({}, {}, "deleted")
        self.assertEqual(cmds, [])

    def test_merged_address_group(self):
        config = {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "address": ["192.168.1.10"]},
                ],
            },
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["address-group", "SERVERS", "address", "192.168.1.10"]),
            cmds,
        )

    def test_merged_network_group(self):
        config = {
            "group": {
                "network_group": [
                    {"name": "LAN", "network": ["192.168.0.0/16"]},
                ],
            },
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["network-group", "LAN", "network", "192.168.0.0/16"]),
            cmds,
        )

    def test_merged_port_group(self):
        config = {
            "group": {
                "port_group": [
                    {"name": "WEB", "port": ["80", "443"]},
                ],
            },
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["port-group", "WEB", "port", "80"]),
            cmds,
        )

    def test_merged_idempotent(self):
        have = self._have()
        config = {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "address": ["192.168.1.10", "192.168.1.11"]},
                ],
                "network_group": [
                    {"name": "LAN", "network": ["192.168.0.0/16"]},
                ],
            },
        }
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_replaced_removes_extra_group(self):
        have = self._have()
        config = {
            "group": {
                "network_group": [
                    {"name": "DMZ", "network": ["10.0.0.0/8"]},
                ],
            },
        }
        cmds = build_commands(config, have, "replaced")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["address-group", "SERVERS"], paths)
        self.assertIn(_BASE + ["network-group", "LAN"], paths)

    def test_replaced_idempotent(self):
        have = self._have()
        config = {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "address": ["192.168.1.10", "192.168.1.11"]},
                ],
                "network_group": [
                    {"name": "LAN", "network": ["192.168.0.0/16"]},
                ],
            },
        }
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])


if __name__ == "__main__":
    unittest.main()
