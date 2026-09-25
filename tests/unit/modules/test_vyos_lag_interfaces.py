# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_lag_interfaces import (
    ARGUMENT_SPEC,
    _bond_entry_from_device,
    _bond_entry_to_device,
    _device_to_argspec,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE = ["interfaces", "bonding"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("lag_interfaces_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)

    def gather(self):
        have = _device_to_argspec(self.fixture)
        for entry in have:
            cast_by_spec(entry, ARGUMENT_SPEC["config"]["options"])
        return have


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("bond0", result)

    def test_unwraps_bonding_wrapper_key(self):
        self.mock_vyos.get_config = MagicMock(
            return_value={"bonding": {"bond0": {"mode": "802.3ad"}}},
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {"bond0": {"mode": "802.3ad"}})

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_collapsed_response_normalized(self):
        self.mock_vyos.get_config = MagicMock(return_value="bond0")
        self.assertEqual(get_running_config(self.mock_vyos), {"bond0": {}})


class TestScopeIsolation(unittest.TestCase):
    """Primary confirmed severe bug, same class as vyos_interfaces/
    vyos_l3_interfaces: bond0's device path is shared with
    vyos_interfaces (description/mtu/vrf) and vyos_l3_interfaces
    (address). A blanket pass-through when parsing device data would
    leak these into have, and a whole-subtree delete would destroy
    them alongside this module's own fields."""

    def test_from_device_does_not_leak_unmanaged_fields(self):
        entry = _bond_entry_from_device(
            {"description": "lag", "mtu": "1500", "address": ["10.0.0.1/24"], "mode": "802.3ad"},
        )
        self.assertNotIn("description", entry)
        self.assertNotIn("mtu", entry)
        self.assertNotIn("address", entry)
        self.assertEqual(entry, {"mode": "802.3ad"})

    def test_deleted_all_never_whole_bond_subtree(self):
        raw_have = {
            "bond0": {
                "mode": "802.3ad",
                "description": "lag interface",
                "mtu": "1500",
                "address": ["10.0.0.1/24"],
            },
        }
        cmds = build_commands([], raw_have, "deleted")
        self.assertNotIn(("delete", _BASE + ["bond0"]), cmds)
        self.assertIn(("delete", _BASE + ["bond0", "mode"]), cmds)

    def test_deleted_named_never_whole_bond_subtree(self):
        raw_have = {"bond0": {"mode": "802.3ad", "description": "important"}}
        cmds = build_commands([{"name": "bond0"}], raw_have, "deleted")
        self.assertNotIn(("delete", _BASE + ["bond0"]), cmds)

    def test_overridden_omitted_bond_never_whole_subtree(self):
        raw_have = {
            "bond0": {},
            "bond1": {"mode": "802.3ad", "description": "important", "address": ["10.0.0.1/24"]},
        }
        cmds = build_commands([{"name": "bond0"}], raw_have, "overridden")
        self.assertNotIn(("delete", _BASE + ["bond1"]), cmds)
        self.assertIn(("delete", _BASE + ["bond1", "mode"]), cmds)

    def test_replaced_never_whole_bond_subtree(self):
        raw_have = {"bond0": {"mode": "802.3ad", "description": "important"}}
        cmds = build_commands([{"name": "bond0"}], raw_have, "replaced")
        self.assertNotIn(("delete", _BASE + ["bond0"]), cmds)

    def test_allowlist_derived_from_argspec_not_a_separate_constant(self):
        """Confirmed via scope_to_spec (module_utils/vyos.py), not a
        second, manually-maintained field list that could drift out
        of sync with the argspec -- already used by vyos_bgp_global
        for exactly this cross-module scope problem."""
        from ansible_collections.vyos.rest.plugins.modules.vyos_lag_interfaces import (
            _ENTRY_OPTIONS,
        )

        entry = _bond_entry_from_device({k: "x" for k in _ENTRY_OPTIONS if k != "name"})
        # every simple scalar field in the argspec should survive
        for field in ("mode", "primary"):
            self.assertIn(field, entry)


class TestMemberAndArpMonitorPreservation(unittest.TestCase):
    """Regression coverage for a bug caught during this module's own
    build: autoclean recursively drops nested empty-dict values,
    treating a presence-only leaf like {"eth1": {}} as "nothing to
    see here" -- but that's a meaningful member-interface reference,
    not nothing. Caught by testing the full round-trip, not assumed."""

    def test_members_preserved_in_device_shape(self):
        result = _bond_entry_to_device(
            {"members": [{"member": "eth1"}, {"member": "eth2"}]},
        )
        self.assertEqual(result, {"member": {"interface": {"eth1": {}, "eth2": {}}}})

    def test_arp_monitor_target_preserved_in_device_shape(self):
        result = _bond_entry_to_device(
            {"arp_monitor": {"interval": 100, "target": ["192.0.2.1"]}},
        )
        self.assertEqual(result, {"arp-monitor": {"interval": 100, "target": {"192.0.2.1": {}}}})

    def test_partial_member_change_generates_per_interface_commands(self):
        """Confirmed correct: dict_op generates per-interface set/
        delete for a partial member list change, not a whole-node
        delete -- that only happens when members is entirely absent
        from want."""
        raw_have = {"bond0": {"member": {"interface": {"eth1": {}, "eth2": {}}}}}
        config = [{"name": "bond0", "members": [{"member": "eth1"}, {"member": "eth3"}]}]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["bond0", "member", "interface", "eth2"]), cmds)
        self.assertIn(("set", _BASE + ["bond0", "member", "interface", "eth3"]), cmds)
        self.assertNotIn(("delete", _BASE + ["bond0", "member"]), cmds)


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_both_bonds_present(self):
        have = self.gather()
        names = {e["name"] for e in have}
        self.assertEqual(names, {"bond0", "bond1"})

    def test_bond0_full_fields_parsed(self):
        have = self.gather()
        bond0 = next(e for e in have if e["name"] == "bond0")
        self.assertEqual(bond0["mode"], "802.3ad")
        self.assertEqual(bond0["hash_policy"], "layer2")
        self.assertEqual({m["member"] for m in bond0["members"]}, {"eth1", "eth2"})
        self.assertEqual(bond0["arp_monitor"]["interval"], 100)
        self.assertEqual(set(bond0["arp_monitor"]["target"]), {"192.0.2.1", "192.0.2.2"})


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_clear_all_omitted_fields_on_replaced(self):
        cmds = build_commands([{"name": "bond0", "mode": "802.3ad"}], self.fixture, "replaced")
        self.assertIn(("delete", _BASE + ["bond0", "primary"]), cmds)
        self.assertIn(("delete", _BASE + ["bond0", "hash-policy"]), cmds)
        self.assertIn(("delete", _BASE + ["bond0", "member"]), cmds)
        self.assertIn(("delete", _BASE + ["bond0", "arp-monitor"]), cmds)

    def test_merged_new_bond(self):
        config = [{"name": "bond2", "mode": "802.3ad", "members": [{"member": "eth5"}]}]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["bond2", "mode", "802.3ad"]), cmds)
        self.assertIn(("set", _BASE + ["bond2", "member", "interface", "eth5"]), cmds)


if __name__ == "__main__":
    unittest.main()
