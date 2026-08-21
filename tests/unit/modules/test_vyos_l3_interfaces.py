# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_l3_interfaces import (
    _addr_cmds,
    _addr_list,
    _normalize,
    _parse_iface,
    _split_addresses,
    build_commands,
    get_running_config,
)


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    path = os.path.join(fixtures_dir, filename)
    with open(path) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.mock_vyos.get_config = MagicMock(return_value={})

    def set_running_config(self, data):
        self.mock_vyos.get_config.return_value = data


class TestVyOSL3InterfacesAddrList(unittest.TestCase):

    def test_string_returns_list(self):
        self.assertEqual(_addr_list("dhcp"), ["dhcp"])

    def test_list_returned_sorted(self):
        result = _addr_list(["10.0.0.2/32", "10.0.0.1/32"])
        self.assertEqual(result, ["10.0.0.1/32", "10.0.0.2/32"])

    def test_none_returns_empty(self):
        self.assertEqual(_addr_list(None), [])

    def test_empty_list_returns_empty(self):
        self.assertEqual(_addr_list([]), [])


class TestVyOSL3InterfacesSplitAddresses(unittest.TestCase):

    def test_dhcp_goes_to_ipv4(self):
        ipv4, ipv6 = _split_addresses(["dhcp"])
        self.assertIn("dhcp", ipv4)
        self.assertEqual(ipv6, [])

    def test_dhcpv6_goes_to_ipv6(self):
        ipv4, ipv6 = _split_addresses(["dhcpv6"])
        self.assertEqual(ipv4, [])
        self.assertIn("dhcpv6", ipv6)

    def test_ipv4_cidr(self):
        ipv4, ipv6 = _split_addresses(["192.0.2.1/24"])
        self.assertIn("192.0.2.1/24", ipv4)
        self.assertEqual(ipv6, [])

    def test_ipv6_cidr(self):
        ipv4, ipv6 = _split_addresses(["2001:db8::1/128"])
        self.assertEqual(ipv4, [])
        self.assertIn("2001:db8::1/128", ipv6)

    def test_mixed(self):
        ipv4, ipv6 = _split_addresses(["dhcp", "192.0.2.1/24", "2001:db8::1/128"])
        self.assertIn("dhcp", ipv4)
        self.assertIn("192.0.2.1/24", ipv4)
        self.assertIn("2001:db8::1/128", ipv6)


class TestVyOSL3InterfacesParseIface(unittest.TestCase):

    def test_parse_dhcp(self):
        result = _parse_iface("eth0", {"address": "dhcp"})
        self.assertEqual(result["name"], "eth0")
        self.assertEqual(result["ipv4"], [{"address": "dhcp"}])

    def test_parse_multiple_addresses(self):
        result = _parse_iface("lo", {"address": ["10.0.0.1/32", "10.0.0.2/32"]})
        addrs = [a["address"] for a in result["ipv4"]]
        self.assertIn("10.0.0.1/32", addrs)
        self.assertIn("10.0.0.2/32", addrs)

    def test_parse_vif(self):
        result = _parse_iface(
            "eth0",
            {
                "address": "dhcp",
                "vif": {"100": {"address": "192.0.2.100/24"}},
            },
        )
        self.assertIn("vifs", result)
        self.assertEqual(result["vifs"][0]["vlan_id"], 100)
        self.assertEqual(result["vifs"][0]["ipv4"][0]["address"], "192.0.2.100/24")

    def test_parse_no_address(self):
        result = _parse_iface("lo", {})
        self.assertNotIn("ipv4", result)
        self.assertNotIn("ipv6", result)

    def test_hw_id_ignored(self):
        result = _parse_iface("eth0", {"hw-id": "52:54:00:65:5a:24"})
        self.assertNotIn("hw_id", result)
        self.assertNotIn("hw-id", result)


class TestVyOSL3InterfacesGetRunningFixture(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("l3_interfaces_running.json")

    def test_fixture_parses_eth0_dhcp(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth0 = next((e for e in result if e["name"] == "eth0"), None)
        self.assertIsNotNone(eth0)
        addrs = [a["address"] for a in eth0.get("ipv4", [])]
        self.assertIn("dhcp", addrs)

    def test_fixture_parses_loopback_addresses(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        lo = next((e for e in result if e["name"] == "lo"), None)
        self.assertIsNotNone(lo)
        addrs = [a["address"] for a in lo.get("ipv4", [])]
        self.assertIn("10.0.0.1/32", addrs)
        self.assertIn("10.0.0.2/32", addrs)

    def test_fixture_parses_vif(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertIn("vifs", eth0)
        self.assertEqual(eth0["vifs"][0]["vlan_id"], 100)

    def test_empty_interface_not_included(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        names = [e["name"] for e in result]
        # loopback with no addresses should not appear
        self.assertNotIn("dummy0", names)


class TestVyOSL3InterfacesGetRunning(VyOSModuleTestCase):

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_interface_without_address_excluded(self):
        self.set_running_config(
            {
                "ethernet": {"eth0": {"hw-id": "52:54:00:65:5a:24"}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSL3InterfacesNormalize(unittest.TestCase):

    def test_normalize_ipv4(self):
        config = [
            {
                "name": "lo",
                "ipv4": [{"address": "10.0.0.1/32"}],
            },
        ]
        result = _normalize(config)
        self.assertIn("lo", result)
        self.assertIn("10.0.0.1/32", result["lo"]["ipv4"])

    def test_normalize_vif(self):
        config = [
            {
                "name": "eth0",
                "vifs": [{"vlan_id": 100, "ipv4": [{"address": "192.0.2.100/24"}]}],
            },
        ]
        result = _normalize(config)
        self.assertIn(100, result["eth0"]["vifs"])
        self.assertIn("192.0.2.100/24", result["eth0"]["vifs"][100]["ipv4"])

    def test_normalize_empty(self):
        result = _normalize([])
        self.assertEqual(result, {})


class TestVyOSL3InterfacesAddrCmds(unittest.TestCase):

    def test_adds_new_address(self):
        base = ["interfaces", "loopback", "lo"]
        cmds = _addr_cmds(base, ["10.0.0.1/32"], [], "merged")
        self.assertIn(("set", base + ["address", "10.0.0.1/32"]), cmds)

    def test_idempotent(self):
        base = ["interfaces", "loopback", "lo"]
        cmds = _addr_cmds(base, ["10.0.0.1/32"], ["10.0.0.1/32"], "merged")
        self.assertEqual(cmds, [])

    def test_merged_does_not_delete_extra(self):
        base = ["interfaces", "loopback", "lo"]
        cmds = _addr_cmds(base, ["10.0.0.1/32"], ["10.0.0.1/32", "10.0.0.2/32"], "merged")
        self.assertEqual(cmds, [])

    def test_replaced_deletes_extra(self):
        base = ["interfaces", "loopback", "lo"]
        cmds = _addr_cmds(base, ["10.0.0.1/32"], ["10.0.0.1/32", "10.0.0.2/32"], "replaced")
        self.assertIn(("delete", base + ["address", "10.0.0.2/32"]), cmds)


class TestVyOSL3InterfacesBuildCommands(unittest.TestCase):

    def _have_lo(self):
        return [
            {
                "name": "lo",
                "ipv4": [
                    {"address": "10.0.0.1/32"},
                    {"address": "10.0.0.2/32"},
                ],
            },
        ]

    def test_merged_adds_address(self):
        config = [{"name": "lo", "ipv4": [{"address": "10.0.0.3/32"}]}]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", ["interfaces", "loopback", "lo", "address", "10.0.0.3/32"]),
            cmds,
        )

    def test_merged_idempotent(self):
        cmds = build_commands(self._have_lo(), self._have_lo(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self._have_lo(), "deleted")
        paths = [c[1] for c in cmds]
        self.assertIn(["interfaces", "loopback", "lo", "address", "10.0.0.1/32"], paths)
        self.assertIn(["interfaces", "loopback", "lo", "address", "10.0.0.2/32"], paths)

    def test_deleted_with_config_removes_interface_addresses(self):
        config = [{"name": "lo"}]
        cmds = build_commands(config, self._have_lo(), "deleted")
        paths = [c[1] for c in cmds]
        self.assertIn(["interfaces", "loopback", "lo", "address", "10.0.0.1/32"], paths)

    def test_deleted_idempotent_when_empty(self):
        cmds = build_commands([], [], "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_removes_extra_address(self):
        config = [{"name": "lo", "ipv4": [{"address": "10.0.0.1/32"}]}]
        cmds = build_commands(config, self._have_lo(), "replaced")
        self.assertIn(
            ("delete", ["interfaces", "loopback", "lo", "address", "10.0.0.2/32"]),
            cmds,
        )

    def test_overridden_removes_unlisted_interface(self):
        config = [{"name": "lo", "ipv4": [{"address": "10.0.0.1/32"}]}]
        have = self._have_lo() + [
            {
                "name": "eth0",
                "ipv4": [{"address": "192.0.2.1/24"}],
            },
        ]
        cmds = build_commands(config, have, "overridden")
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "address", "192.0.2.1/24"]),
            cmds,
        )

    def test_vif_added(self):
        config = [
            {
                "name": "eth0",
                "vifs": [{"vlan_id": 100, "ipv4": [{"address": "192.0.2.100/24"}]}],
            },
        ]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "vif", "100", "address", "192.0.2.100/24"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
