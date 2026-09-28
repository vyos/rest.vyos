# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_l3_interfaces import (
    _addr_cmds,
    _device_to_argspec,
    _guess_iface_type,
    _iface_base,
    _resolve_iface_type,
    _split_addresses,
    _vif_addr_cmds,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["interfaces"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("l3_interfaces_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)

    def gather(self):
        return _device_to_argspec(self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("ethernet", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_collapsed_response_normalized(self):
        self.mock_vyos.get_config = MagicMock(return_value="eth0")
        self.assertEqual(get_running_config(self.mock_vyos), {"eth0": {}})


class TestTypeResolution(unittest.TestCase):
    def test_resolves_from_have_when_present(self):
        raw_have = {"loopback": {"lo": {}}}
        self.assertEqual(_resolve_iface_type("lo", raw_have), "loopback")

    def test_falls_back_to_guess_for_new_interface(self):
        self.assertEqual(_resolve_iface_type("eth5", {}), "ethernet")

    def test_guess_covers_all_11_types_aligned_with_vyos_interfaces(self):
        """Confirmed original inconsistency: this module's own type
        table was missing ppp/wlan compared to vyos_interfaces' table,
        despite both modules operating on the same interface
        namespace. Aligned here."""
        expected = {
            "eth0": "ethernet",
            "bond0": "bonding",
            "lo": "loopback",
            "tun0": "tunnel",
            "wg0": "wireguard",
            "vti0": "vti",
            "dum0": "dummy",
            "vtun0": "openvpn",
            "ppp0": "pppoe",
            "wlan0": "wireless",
            "br0": "bridge",
        }
        for name, itype in expected.items():
            self.assertEqual(_guess_iface_type(name), itype)

    def test_iface_base_uses_resolved_type(self):
        raw_have = {"bonding": {"bond0": {}}}
        self.assertEqual(_iface_base("bond0", raw_have), ["interfaces", "bonding", "bond0"])


class TestSplitAddresses(unittest.TestCase):
    def test_ipv4_ipv6_dhcp_dhcpv6(self):
        ipv4, ipv6 = _split_addresses(["192.0.2.1/24", "2001:db8::1/64", "dhcp", "dhcpv6"])
        self.assertEqual(ipv4, ["192.0.2.1/24", "dhcp"])
        self.assertEqual(ipv6, ["2001:db8::1/64", "dhcpv6"])

    def test_auto_config(self):
        ipv4, ipv6 = _split_addresses(["auto-config"])
        self.assertEqual(ipv6, ["auto-config"])


class TestAddrCmds(unittest.TestCase):
    """Confirmed scoped correctly: address commands only ever touch
    the "address" leaf under the given base, regardless of whether
    that base is an interface or a vif."""

    def test_set_new_address(self):
        cmds = _addr_cmds(["interfaces", "ethernet", "eth0"], ["192.0.2.1/24"], [], "merged")
        expected = ("set", ["interfaces", "ethernet", "eth0", "address", "192.0.2.1/24"])
        self.assertEqual(cmds, [expected])

    def test_merged_never_deletes(self):
        cmds = _addr_cmds(["interfaces", "ethernet", "eth0"], [], ["192.0.2.1/24"], "merged")
        self.assertEqual(cmds, [])

    def test_replaced_deletes_omitted(self):
        cmds = _addr_cmds(["interfaces", "ethernet", "eth0"], [], ["192.0.2.1/24"], "replaced")
        expected = ("delete", ["interfaces", "ethernet", "eth0", "address", "192.0.2.1/24"])
        self.assertEqual(cmds, [expected])


class TestVifAddrCmdsNeverWholeSubtree(unittest.TestCase):
    """Primary confirmed severe bug: the original generated a whole-
    VIF delete (`delete ... vif <id>`) for an omitted VIF under
    replaced/overridden/deleted. Since VIFs are shared with
    vyos_interfaces (which owns description/mtu/disable on them),
    this would destroy that module's own fields, not just this
    module's addresses. Confirmed 4 separate occurrences in the
    original build_commands. Fixed: every VIF operation here is
    scoped to exactly the address leaf, never the VIF subtree."""

    def test_omitted_vif_only_deletes_its_addresses(self):
        have_vifs = {100: {"ipv4": ["192.0.2.100/24"], "ipv6": []}}
        cmds = _vif_addr_cmds(["interfaces", "ethernet", "eth0"], {}, have_vifs, "replaced")
        whole_vif_delete = ("delete", ["interfaces", "ethernet", "eth0", "vif", "100"])
        self.assertNotIn(whole_vif_delete, cmds)
        vif_addr_delete = (
            "delete",
            ["interfaces", "ethernet", "eth0", "vif", "100", "address", "192.0.2.100/24"],
        )
        self.assertIn(vif_addr_delete, cmds)

    def test_deleted_state_also_never_whole_subtree(self):
        have_vifs = {100: {"ipv4": ["192.0.2.100/24"], "ipv6": []}}
        cmds = _vif_addr_cmds(["interfaces", "ethernet", "eth0"], {}, have_vifs, "deleted")
        whole_vif_delete = ("delete", ["interfaces", "ethernet", "eth0", "vif", "100"])
        self.assertNotIn(whole_vif_delete, cmds)

    def test_overridden_also_never_whole_subtree(self):
        have_vifs = {100: {"ipv4": ["192.0.2.100/24"], "ipv6": []}}
        cmds = _vif_addr_cmds(["interfaces", "ethernet", "eth0"], {}, have_vifs, "overridden")
        whole_vif_delete = ("delete", ["interfaces", "ethernet", "eth0", "vif", "100"])
        self.assertNotIn(whole_vif_delete, cmds)


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_all_interfaces_with_addresses_present(self):
        have = self.gather()
        names = {e["name"] for e in have}
        # eth1 has no addresses at all -- must not appear
        self.assertEqual(names, {"eth0", "lo"})

    def test_eth0_addresses_and_vif_parsed(self):
        have = self.gather()
        eth0 = next(e for e in have if e["name"] == "eth0")
        self.assertEqual(eth0["ipv4"][0]["address"], "192.0.2.1/24")
        self.assertEqual(eth0["ipv6"][0]["address"], "2001:db8::1/64")
        self.assertEqual(eth0["vifs"][0]["vlan_id"], 100)
        self.assertEqual(eth0["vifs"][0]["ipv4"][0]["address"], "192.0.2.100/24")

    def test_collapsed_single_address_string(self):
        entry = _device_to_argspec({"ethernet": {"eth0": {"address": "192.0.2.1/24"}}})
        self.assertEqual(entry[0]["ipv4"][0]["address"], "192.0.2.1/24")


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_deleted_all_never_whole_interface_subtree(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.0.2.1/24"]}}}
        cmds = build_commands([], raw_have, "deleted")
        self.assertNotIn(("delete", _BASE + ["ethernet", "eth0"]), cmds)
        self.assertIn(("delete", _BASE + ["ethernet", "eth0", "address", "192.0.2.1/24"]), cmds)

    def test_deleted_named_never_whole_interface_subtree(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.0.2.1/24"]}}}
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertNotIn(("delete", _BASE + ["ethernet", "eth0"]), cmds)

    def test_overridden_omitted_interface_never_whole_subtree(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.0.2.1/24"]}}}
        cmds = build_commands([], raw_have, "overridden")
        self.assertNotIn(("delete", _BASE + ["ethernet", "eth0"]), cmds)

    def test_merged_adds_without_removing(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.0.2.1/24"]}}}
        config = [{"name": "eth0", "ipv4": [{"address": "192.0.2.2/24"}]}]
        cmds = build_commands(config, raw_have, "merged")
        self.assertIn(("set", _BASE + ["ethernet", "eth0", "address", "192.0.2.2/24"]), cmds)
        self.assertFalse(any(c[0] == "delete" for c in cmds))

    def test_replaced_removes_unlisted_address(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.0.2.1/24", "192.0.2.2/24"]}}}
        config = [{"name": "eth0", "ipv4": [{"address": "192.0.2.1/24"}]}]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["ethernet", "eth0", "address", "192.0.2.2/24"]), cmds)

    def test_merged_new_vif_address(self):
        config = [
            {"name": "eth0", "vifs": [{"vlan_id": 200, "ipv4": [{"address": "192.0.2.200/24"}]}]},
        ]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["ethernet", "eth0", "vif", "200", "address", "192.0.2.200/24"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
