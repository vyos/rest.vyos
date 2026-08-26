# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_interfaces import (
    ARGUMENT_SPEC,
    _device_to_argspec,
    _guess_iface_type,
    _iface_base,
    _iface_entry_from_device,
    _iface_entry_to_device,
    _resolve_iface_type,
    _vif_entry_from_device,
    _vif_entry_to_device,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("interfaces_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)

    def gather(self):
        have = _device_to_argspec(self.fixture)
        for entry in have:
            cast_by_spec(entry, ARGUMENT_SPEC["config"]["options"])
        return have


class TestAddressNeverLeaksIntoManagedFields(unittest.TestCase):
    """Regression tests for a confirmed severe bug, caught against
    real hardware: this module's deleted/replaced/overridden states
    all operate against a reconstructed "have" -- if that have ever
    included an unmanaged field like "address" (owned by
    vyos_l3_interfaces, not this module), it would be treated as
    "present in have, absent from want" and get deleted right
    alongside the L2 fields this module actually manages. Confirmed
    on real hardware: this destroyed an interface's IP address,
    including the one the REST API itself was reachable through
    ("No route to host" after a deleted-state task)."""

    def test_iface_entry_from_device_does_not_leak_address(self):
        entry = _iface_entry_from_device(
            {"address": ["192.168.122.6/24"], "description": "mgmt", "hw-id": "08:00:27"},
        )
        self.assertNotIn("address", entry)
        self.assertNotIn("hw_id", entry)
        self.assertEqual(entry, {"description": "mgmt"})

    def test_vif_entry_from_device_does_not_leak_address(self):
        entry = _vif_entry_from_device({"address": ["192.0.2.1/24"], "description": "v1"})
        self.assertNotIn("address", entry)

    def test_deleted_named_never_touches_address(self):
        raw_have = {
            "ethernet": {
                "eth0": {"address": ["192.168.122.6/24"], "description": "mgmt", "mtu": "1500"},
            },
        }
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertFalse(any("address" in str(c) for c in cmds))
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)

    def test_deleted_all_never_touches_address(self):
        raw_have = {"ethernet": {"eth0": {"address": ["192.168.122.6/24"]}}}
        cmds = build_commands([], raw_have, "deleted")
        self.assertFalse(any("address" in str(c) for c in cmds))

    def test_overridden_omitted_interface_never_touches_address(self):
        raw_have = {
            "ethernet": {
                "eth0": {},
                "eth1": {"address": ["10.0.0.1/24"], "description": "old"},
            },
        }
        cmds = build_commands([{"name": "eth0"}], raw_have, "overridden")
        self.assertFalse(any("address" in str(c) for c in cmds))
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_replaced_never_touches_address(self):
        raw_have = {
            "ethernet": {"eth0": {"address": ["10.0.0.1/24"], "description": "old"}},
        }
        cmds = build_commands([{"name": "eth0"}], raw_have, "replaced")
        self.assertFalse(any("address" in str(c) for c in cmds))


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("ethernet", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_collapsed_response_normalized(self):
        self.mock_vyos.get_config = MagicMock(return_value="eth0")
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {"eth0": {}})


class TestTypeResolution(unittest.TestCase):
    """Primary confirmed bug fix: the original applied the name-prefix
    guess unconditionally, even for interfaces already known to the
    device (where the real type is directly, reliably available)."""

    def test_resolves_from_have_when_present(self):
        raw_have = {"bridge": {"ethbr0": {}}}
        self.assertEqual(_resolve_iface_type("ethbr0", raw_have), "bridge")

    def test_falls_back_to_guess_for_new_interface(self):
        self.assertEqual(_resolve_iface_type("eth5", {}), "ethernet")

    def test_multiple_existing_interfaces_resolved_correctly(self):
        raw_have = {"ethernet": {"eth0": {}}, "bonding": {"bond0": {}}}
        self.assertEqual(_resolve_iface_type("eth0", raw_have), "ethernet")
        self.assertEqual(_resolve_iface_type("bond0", raw_have), "bonding")

    def test_guess_covers_all_11_types(self):
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


class TestVifEntry(unittest.TestCase):
    def test_to_device(self):
        result = _vif_entry_to_device({"description": "v1", "mtu": 1400})
        self.assertEqual(result, {"description": "v1", "mtu": 1400})

    def test_disabled_vif(self):
        result = _vif_entry_to_device({"enabled": False})
        self.assertEqual(result, {"disable": {}})

    def test_from_device_disabled(self):
        entry = _vif_entry_from_device({"disable": {}})
        self.assertFalse(entry["enabled"])

    def test_from_device_enabled_omitted(self):
        entry = _vif_entry_from_device({"description": "v1"})
        self.assertNotIn("enabled", entry)


class TestIfaceEntry(unittest.TestCase):
    def test_vifs_keyed_by_vlan_id(self):
        result = _iface_entry_to_device(
            {"vifs": [{"vlan_id": 200, "description": "v200"}]},
        )
        self.assertEqual(result, {"vif": {"200": {"description": "v200"}}})

    def test_disabled_interface(self):
        result = _iface_entry_to_device({"enabled": False})
        self.assertEqual(result, {"disable": {}})

    def test_vrf(self):
        result = _iface_entry_to_device({"vrf": "mgmt"})
        self.assertEqual(result, {"vrf": "mgmt"})

    def test_from_device_vifs_key_cast_to_int(self):
        entry = _iface_entry_from_device({"vif": {"200": {}}})
        self.assertEqual(entry["vifs"][0]["vlan_id"], 200)
        self.assertIsInstance(entry["vifs"][0]["vlan_id"], int)


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_all_interfaces_present(self):
        have = self.gather()
        names = {e["name"] for e in have}
        self.assertEqual(names, {"eth0", "eth1", "bond0", "lo"})

    def test_eth0_full_fields_parsed(self):
        have = self.gather()
        eth0 = next(e for e in have if e["name"] == "eth0")
        self.assertEqual(eth0["mtu"], 1500)
        self.assertEqual(eth0["vrf"], "mgmt")
        self.assertEqual(eth0["vifs"][0]["vlan_id"], 200)
        self.assertEqual(eth0["vifs"][0]["mtu"], 1400)

    def test_eth1_disabled(self):
        have = self.gather()
        eth1 = next(e for e in have if e["name"] == "eth1")
        self.assertFalse(eth1["enabled"])

    def test_lo_minimal(self):
        have = self.gather()
        lo = next(e for e in have if e["name"] == "lo")
        self.assertNotIn("mtu", lo)


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_clear_omitted_fields_on_replaced(self):
        """Primary confirmed bug: description had explicit clear-on-
        omit logic, but mtu/duplex/speed did not -- a genuine
        inconsistency. dict_op's purge handles all fields uniformly."""
        raw_have = {
            "ethernet": {"eth0": {"description": "old", "mtu": "1500", "duplex": "auto"}},
        }
        cmds = build_commands([{"name": "eth0"}], raw_have, "replaced")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "duplex"]), cmds)

    def test_overridden_removes_omitted_interface(self):
        raw_have = {"ethernet": {"eth0": {}, "eth1": {"description": "old"}}}
        cmds = build_commands([{"name": "eth0"}], raw_have, "overridden")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_deleted_all(self):
        raw_have = {"ethernet": {"eth0": {"description": "a"}, "eth1": {"description": "b"}}}
        cmds = build_commands([], raw_have, "deleted")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_deleted_named(self):
        raw_have = {"ethernet": {"eth0": {"description": "a", "mtu": "1500"}}}
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)

    def test_deleted_named_empty_interface_is_noop(self):
        """A named interface with no L2 fields set has nothing for
        this module to delete -- confirmed correct, not a bug: an
        empty {} in have means an empty purge."""
        raw_have = {"ethernet": {"eth0": {}}}
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertEqual(cmds, [])

    def test_merged_new_interface_with_vrf_and_vif(self):
        config = [
            {
                "name": "eth0",
                "vrf": "mgmt",
                "vifs": [{"vlan_id": 100, "description": "v100"}],
            },
        ]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", ["interfaces", "ethernet", "eth0", "vrf", "mgmt"]), cmds)
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "vif", "100", "description", "v100"]),
            cmds,
        )

    def test_merged_disabled_vif(self):
        config = [{"name": "eth0", "vifs": [{"vlan_id": 100, "enabled": False}]}]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "vif", "100", "disable"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
