# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_interfaces import (
    _DEVICE_RENAMES,
    ARGUMENT_SPEC,
    _derive_key_field,
    _device_to_argspec,
    _device_to_spec,
    _entry_to_device,
    _guess_iface_type,
    _iface_base,
    _keyed_list_from_device,
    _keyed_list_to_device,
    _resolve_iface_type,
    _spec_to_device,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_FIXTURES = load_fixture("interfaces_running.json")


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = _FIXTURES["default"]
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("ethernet", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_collapsed_response_normalized(self):
        """VyOS's REST API collapses a single-child tag node to a bare
        string -- get_running_config must always return a genuine
        dict regardless."""
        self.mock_vyos.get_config = MagicMock(return_value="eth0")
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {"eth0": {}})


class TestDeviceRenames(unittest.TestCase):
    """The one thing a purely structural walk can never infer: "vifs"
    (argspec, plural) vs "vif" (device, singular) is a genuine word-
    form rename, not a hyphen/underscore difference dict_op's own
    normalization could fold on its own. Declared once here as a flat
    value map, not embedded in ARGUMENT_SPEC."""

    def test_confirmed_rename_present(self):
        self.assertEqual(_DEVICE_RENAMES.get("vifs"), "vif")


class TestSpecToDevice(unittest.TestCase):
    """The generic recursive walker that replaced a hand-written to-
    device/from-device function pair for every nesting level in this
    module. Driven by the options spec's own structure (dict ->
    recurse, list with options -> a named list keyed by
    _derive_key_field) plus _DEVICE_RENAMES and the enabled/disable
    exception for the handful of non-mechanical differences."""

    def test_plain_scalar_passes_through_unrenamed(self):
        spec = {"description": {"type": "str"}}
        self.assertEqual(_spec_to_device({"description": "x"}, spec), {"description": "x"})

    def test_rename_applied_via_device_renames(self):
        spec = {"vifs": {"type": "list", "options": {"vlan_id": {"required": True}}}}
        result = _spec_to_device({"vifs": [{"vlan_id": 200}]}, spec)
        self.assertEqual(result, {"vif": {"200": {}}})

    def test_enabled_true_omitted(self):
        spec = {"enabled": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"enabled": True}, spec), {})

    def test_enabled_false_becomes_disable_presence(self):
        spec = {"enabled": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"enabled": False}, spec), {"disable": {}})

    def test_named_list_keyed_by_required_field(self):
        spec = {
            "vifs": {
                "type": "list",
                "options": {
                    "vlan_id": {"type": "int", "required": True},
                    "description": {"type": "str"},
                },
            },
        }
        result = _spec_to_device(
            {"vifs": [{"vlan_id": 200, "description": "v200"}]},
            spec,
        )
        self.assertEqual(result, {"vif": {"200": {"description": "v200"}}})

    def test_plain_scalar_list_passes_through(self):
        spec = {"tags": {"type": "list"}}
        result = _spec_to_device({"tags": ["a", "b"]}, spec)
        self.assertEqual(result, {"tags": ["a", "b"]})

    def test_bool_true_is_presence_for_non_enabled_fields(self):
        spec = {"disable": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"disable": True}, spec), {"disable": {}})

    def test_bool_false_omitted_for_non_enabled_fields(self):
        spec = {"disable": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"disable": False}, spec), {})

    def test_non_dict_value_passes_through(self):
        self.assertEqual(_spec_to_device("not-a-dict", {}), "not-a-dict")


class TestDeviceToSpec(unittest.TestCase):
    """The reverse of _spec_to_device -- same structural rules, same
    single source of truth for renames and the enabled/disable
    exception."""

    def test_mechanical_field_matched_via_hyphen_normalization(self):
        spec = {"mtu_size": {"type": "str"}}
        result = _device_to_spec({"mtu-size": "1500"}, spec)
        self.assertEqual(result, {"mtu_size": "1500"})

    def test_renamed_field_matched_via_device_renames(self):
        spec = {
            "vifs": {
                "type": "list",
                "options": {"vlan_id": {"type": "int", "required": True}},
            },
        }
        result = _device_to_spec({"vif": {"200": {}}}, spec)
        self.assertEqual(result, {"vifs": [{"vlan_id": 200}]})

    def test_disable_presence_becomes_enabled_false(self):
        spec = {"enabled": {"type": "bool"}}
        self.assertEqual(_device_to_spec({"disable": {}}, spec), {"enabled": False})

    def test_enabled_omitted_when_no_disable_leaf(self):
        spec = {"enabled": {"type": "bool"}, "description": {"type": "str"}}
        result = _device_to_spec({"description": "v1"}, spec)
        self.assertNotIn("enabled", result)

    def test_plain_scalar_list_sorted_and_collapse_safe(self):
        spec = {"tags": {"type": "list"}}
        result = _device_to_spec({"tags": "a"}, spec)
        self.assertEqual(result, {"tags": ["a"]})

    def test_empty_or_non_dict_raw(self):
        self.assertEqual(_device_to_spec({}, {}), {})
        self.assertEqual(_device_to_spec(None, {}), {})
        self.assertEqual(_device_to_spec("not-a-dict", {}), {})


class TestKeyedListHelper(unittest.TestCase):
    """The generic mechanic the VIF section shares with any other
    named-list section: a list of dicts identified by one field
    becomes a device dict keyed by that field's value."""

    def test_to_device_skips_entries_missing_key_field(self):
        result = _keyed_list_to_device([{"description": "x"}], "vlan_id", lambda r: r)
        self.assertEqual(result, {})

    def test_to_device_key_field_stripped_from_rest(self):
        seen = {}

        def transform(rest):
            seen.update(rest)
            return rest

        _keyed_list_to_device([{"vlan_id": 200, "description": "v200"}], "vlan_id", transform)
        self.assertNotIn("vlan_id", seen)
        self.assertEqual(seen, {"description": "v200"})

    def test_from_device_key_cast_applied(self):
        result = _keyed_list_from_device({"200": {}}, "vlan_id", lambda d: d, key_cast=int)
        self.assertEqual(result, [{"vlan_id": 200}])

    def test_from_device_bare_string_collapse(self):
        result = _keyed_list_from_device("200", "vlan_id", lambda d: d, key_cast=int)
        self.assertEqual(result, [{"vlan_id": 200}])

    def test_empty(self):
        self.assertEqual(_keyed_list_to_device([], "vlan_id", lambda r: r), {})
        self.assertEqual(_keyed_list_to_device(None, "vlan_id", lambda r: r), {})
        self.assertEqual(_keyed_list_from_device({}, "vlan_id", lambda d: d), [])
        self.assertEqual(_keyed_list_from_device(None, "vlan_id", lambda d: d), [])


class TestDeriveKeyField(unittest.TestCase):
    """key_field is derived from each section's own options spec, not
    hand-declared -- every named-list section marks exactly one
    suboption required=True (you can't create a VIF without a
    vlan_id), so that's the field identifying each entry."""

    def test_derives_the_single_required_field(self):
        self.assertEqual(
            _derive_key_field({"vlan_id": {"required": True}, "mtu": {"type": "int"}}),
            "vlan_id",
        )

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"mtu": {"type": "int"}})

    def test_raises_if_more_than_one_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"required": True}, "b": {"required": True}})


class TestEntryToDevice(unittest.TestCase):
    """_entry_to_device strips an entry's own identifying key field
    (the same role _keyed_list_to_device already strips "vlan_id" for
    -- here, "name" for a top-level interface entry) before the
    generic walk, since it identifies the entry itself (already
    expressed in the API path via _iface_base) rather than a child
    leaf to set/purge under it."""

    def setUp(self):
        self.entry_options = ARGUMENT_SPEC["config"]["options"]
        self.vif_options = self.entry_options["vifs"]["options"]

    def test_name_never_leaks_as_a_device_field(self):
        result = _entry_to_device({"name": "eth0", "description": "x"}, self.entry_options)
        self.assertNotIn("name", result)
        self.assertEqual(result, {"description": "x"})

    def test_vifs_keyed_by_vlan_id(self):
        result = _entry_to_device(
            {"name": "eth0", "vifs": [{"vlan_id": 200, "description": "v200"}]},
            self.entry_options,
        )
        self.assertEqual(result, {"vif": {"200": {"description": "v200"}}})

    def test_disabled_interface(self):
        result = _entry_to_device({"name": "eth0", "enabled": False}, self.entry_options)
        self.assertEqual(result, {"disable": {}})

    def test_vrf_only_no_stray_vif_key(self):
        result = _entry_to_device({"name": "eth0", "vrf": "mgmt"}, self.entry_options)
        self.assertEqual(result, {"vrf": "mgmt"})

    def test_vif_entry_to_device(self):
        result = _entry_to_device(
            {"vlan_id": 200, "description": "v1", "mtu": 1400},
            self.vif_options,
        )
        self.assertEqual(result, {"description": "v1", "mtu": 1400})

    def test_vif_disabled(self):
        result = _entry_to_device({"vlan_id": 200, "enabled": False}, self.vif_options)
        self.assertEqual(result, {"disable": {}})


class TestTypeResolution(unittest.TestCase):
    """Primary confirmed bug fix: the original applied the name-prefix
    guess unconditionally, even for interfaces already known to the
    device (where the real type is directly, reliably available)."""

    def test_resolves_from_have_when_present(self):
        raw_have = _FIXTURES["bridge_ethbr0"]
        self.assertEqual(_resolve_iface_type("ethbr0", raw_have), "bridge")

    def test_falls_back_to_guess_for_new_interface(self):
        self.assertEqual(_resolve_iface_type("eth5", {}), "ethernet")

    def test_multiple_existing_interfaces_resolved_correctly(self):
        raw_have = _FIXTURES["ethernet_and_bonding"]
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
        raw_have = _FIXTURES["bonding_bond0_only"]
        self.assertEqual(_iface_base("bond0", raw_have), ["interfaces", "bonding", "bond0"])


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
    ("No route to host" after a deleted-state task).

    The tests from test_deleted_vif_address_never_deletes_whole_vif
    onward are the command-level companion CodeRabbit asked for: a VIF
    carrying an address, confirming the purge never wholesale-deletes
    that VIF's container -- the actual channel through which address
    could be lost on a real device, which the earlier tests alone did
    not cover.
    """

    def test_device_to_spec_does_not_leak_address(self):
        entry = _device_to_spec(
            {"address": ["192.168.122.6/24"], "description": "mgmt", "hw-id": "08:00:27"},
            ARGUMENT_SPEC["config"]["options"],
        )
        self.assertNotIn("address", entry)
        self.assertNotIn("hw_id", entry)
        self.assertEqual(entry, {"description": "mgmt"})

    def test_vif_device_to_spec_does_not_leak_address(self):
        entry = _device_to_spec(
            {"address": ["192.0.2.1/24"], "description": "v1"},
            ARGUMENT_SPEC["config"]["options"]["vifs"]["options"],
        )
        self.assertNotIn("address", entry)

    def test_deleted_named_never_touches_address(self):
        raw_have = _FIXTURES["iface_with_address_mtu_description"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertFalse(any("address" in str(c) for c in cmds))
        self.assertFalse(any("name" in c[1] for c in cmds))
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)

    def test_deleted_all_never_touches_address(self):
        raw_have = _FIXTURES["iface_address_only"]
        cmds = build_commands([], raw_have, "deleted")
        self.assertFalse(any("address" in str(c) for c in cmds))

    def test_overridden_omitted_interface_never_touches_address(self):
        raw_have = _FIXTURES["two_ifaces_one_with_address"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "overridden")
        self.assertFalse(any("address" in str(c) for c in cmds))
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_replaced_never_touches_address(self):
        raw_have = _FIXTURES["iface_address_and_description"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "replaced")
        self.assertFalse(any("address" in str(c) for c in cmds))

    # -----------------------------------------------------------------
    # Command-level VIF-address-preservation tests (CodeRabbit, PR #33)
    # -----------------------------------------------------------------

    def test_deleted_vif_address_never_deletes_whole_vif(self):
        raw_have = _FIXTURES["vif_address_base"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif"], paths)
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "description"]),
            cmds,
        )

    def test_replaced_omitting_vifs_never_deletes_whole_vif(self):
        raw_have = _FIXTURES["vif_address_base"]
        config = [{"name": "eth0", "description": "mgmt-updated"}]
        cmds = build_commands(config, raw_have, "replaced")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif"], paths)
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "description"]),
            cmds,
        )

    def test_overridden_unlisted_interface_never_deletes_whole_vif(self):
        raw_have = _FIXTURES["vif_address_base"]
        cmds = build_commands([], raw_have, "overridden")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif"], paths)
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "description"]),
            cmds,
        )

    def test_overridden_listed_interface_never_deletes_whole_vif(self):
        """Companion to the unlisted case above: the VIF-bearing
        interface here is explicitly listed in want (not omitted
        entirely), which routes through the inline purge path rather
        than _scoped_purge_commands -- both must be equally safe."""
        raw_have = _FIXTURES["vif_address_base"]
        cmds = build_commands([{"name": "eth0", "description": "mgmt"}], raw_have, "overridden")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif"], paths)
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)

    def test_vif_kept_in_want_still_updates_normally(self):
        """Confirms the fix didn't also break the unrelated, working
        path: a VIF present in both want and have must still go
        through the normal op="set" field-by-field reconciliation."""
        raw_have = _FIXTURES["vif_address_base"]
        config = [
            {
                "name": "eth0",
                "description": "mgmt",
                "vifs": [{"vlan_id": 200, "description": "updated-vlan"}],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            (
                "set",
                ["interfaces", "ethernet", "eth0", "vif", "200", "description", "updated-vlan"],
            ),
            cmds,
        )

    def test_replaced_still_removes_stale_disable_on_kept_vif(self):
        """Regression test for a bug introduced by the fix itself and
        caught by a real ansible-test network-integration run: a VIF
        kept in both want and have, with enabled: true, must still
        have its stale "disable" leaf removed under
        replaced/overridden -- the fix must not also disable field-
        level purging within a kept VIF."""
        raw_have = _FIXTURES["vif_stale_disable_kept"]
        config = [
            {
                "name": "eth0",
                "description": "x",
                "vifs": [{"vlan_id": 200, "description": "management vlan", "enabled": True}],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "disable"]),
            cmds,
        )

    def test_multi_vif_mixed_kept_removed_and_address_only(self):
        """Three VIFs in one interface, each in a different state: one
        kept and updated, one removed (with an address that must
        survive), one address-only (never touched at all)."""
        raw_have = _FIXTURES["vif_multi_mixed"]
        config = [
            {
                "name": "eth0",
                "description": "mgmt",
                "vifs": [{"vlan_id": 100, "description": "kept-vlan-updated"}],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        paths = [c[1] for c in cmds]

        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "description"]),
            cmds,
        )
        self.assertIn(
            (
                "set",
                [
                    "interfaces",
                    "ethernet",
                    "eth0",
                    "vif",
                    "100",
                    "description",
                    "kept-vlan-updated",
                ],
            ),
            cmds,
        )
        self.assertFalse(any("300" in p for p in paths))

    def test_mtu_purged_individually_not_whole_vif(self):
        """The managed-leaf purge must work for mtu specifically, not
        just description/disable -- otherwise mtu's path stays
        unconfirmed."""
        raw_have = _FIXTURES["vif_mtu_with_address"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["interfaces", "ethernet", "eth0", "vif", "200"], paths)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "mtu"]), cmds)

    def test_brand_new_vif_still_added_via_set_path(self):
        """A VIF present in want but entirely absent from have (a
        genuinely new VIF, not a purge scenario at all) must still be
        added correctly -- confirms the fix didn't collaterally affect
        the unrelated add path."""
        raw_have = _FIXTURES["vif_new_vif_base"]
        config = [
            {
                "name": "eth0",
                "description": "mgmt",
                "vifs": [{"vlan_id": 400, "description": "new-vlan"}],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "vif", "400", "description", "new-vlan"]),
            cmds,
        )


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_all_interfaces_present(self):
        have = _device_to_argspec(self.fixture)
        names = {e["name"] for e in have}
        self.assertEqual(names, {"eth0", "eth1", "bond0", "lo"})

    def test_eth0_full_fields_parsed(self):
        """main() applies cast_by_spec to _device_to_argspec's output
        before returning it to the caller -- applied the same way
        here to confirm mtu is reported as an int, not the raw device
        string."""
        have = _device_to_argspec(self.fixture)
        eth0 = next(e for e in have if e["name"] == "eth0")
        cast_by_spec(eth0, ARGUMENT_SPEC["config"]["options"])
        self.assertEqual(eth0["mtu"], 1500)
        self.assertEqual(eth0["vrf"], "mgmt")
        self.assertEqual(eth0["vifs"][0]["vlan_id"], 200)
        self.assertEqual(eth0["vifs"][0]["mtu"], 1400)

    def test_eth1_disabled(self):
        have = _device_to_argspec(self.fixture)
        eth1 = next(e for e in have if e["name"] == "eth1")
        self.assertFalse(eth1["enabled"])

    def test_lo_minimal(self):
        have = _device_to_argspec(self.fixture)
        lo = next(e for e in have if e["name"] == "lo")
        self.assertNotIn("mtu", lo)

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), [])
        self.assertEqual(_device_to_argspec(None), [])


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_overridden_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "overridden"), [])

    def test_merged_basic_set(self):
        cmds = build_commands([{"name": "eth0", "description": "x", "mtu": 1500}], {}, "merged")
        self.assertIn(("set", ["interfaces", "ethernet", "eth0", "description", "x"]), cmds)
        self.assertIn(("set", ["interfaces", "ethernet", "eth0", "mtu", "1500"]), cmds)

    def test_merged_never_purges_unlisted_fields(self):
        """merged only ever adds/updates fields present in want -- a
        field present on the device but omitted from want must never
        be purged, unlike replaced/overridden."""
        raw_have = _FIXTURES["description_mtu_only"]
        cmds = build_commands([{"name": "eth0", "description": "y"}], raw_have, "merged")
        self.assertFalse(any("mtu" in c[1] for c in cmds))

    def test_merged_enabled_true_removes_disable(self):
        """Interface-level re-enable under merged: mtu/description
        must stay untouched, only the stale disable leaf is removed."""
        raw_have = _FIXTURES["iface_disabled_with_fields"]
        cmds = build_commands([{"name": "eth0", "enabled": True}], raw_have, "merged")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "disable"]), cmds)
        self.assertFalse(any("mtu" in c[1] for c in cmds))
        self.assertFalse(any("description" in c[1] for c in cmds))

    def test_merged_vif_enabled_true_removes_disable(self):
        raw_have = _FIXTURES["vif_disabled_on_device"]
        config = [{"name": "eth0", "vifs": [{"vlan_id": 200, "enabled": True}]}]
        cmds = build_commands(config, raw_have, "merged")
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "vif", "200", "disable"]),
            cmds,
        )

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

    def test_replaced_basic_purge_and_set(self):
        raw_have = _FIXTURES["description_mtu_old_1400"]
        cmds = build_commands([{"name": "eth0", "description": "new"}], raw_have, "replaced")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)
        self.assertIn(("set", ["interfaces", "ethernet", "eth0", "description", "new"]), cmds)

    def test_clear_omitted_fields_on_replaced(self):
        """Primary confirmed bug: description had explicit clear-on-
        omit logic, but mtu/duplex/speed did not -- a genuine
        inconsistency. dict_op's purge handles all fields uniformly."""
        raw_have = _FIXTURES["description_mtu_duplex"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "replaced")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "duplex"]), cmds)

    def test_overridden_basic_unlisted_purged_listed_reconciled(self):
        raw_have = _FIXTURES["eth0_old_eth1_keepme"]
        cmds = build_commands([{"name": "eth0", "description": "new"}], raw_have, "overridden")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)
        self.assertIn(("set", ["interfaces", "ethernet", "eth0", "description", "new"]), cmds)

    def test_overridden_removes_omitted_interface(self):
        raw_have = _FIXTURES["eth0_empty_eth1_described"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "overridden")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_deleted_all(self):
        raw_have = _FIXTURES["two_described_ifaces"]
        cmds = build_commands([], raw_have, "deleted")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth1", "description"]), cmds)

    def test_deleted_named(self):
        raw_have = _FIXTURES["one_described_iface"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "description"]), cmds)
        self.assertIn(("delete", ["interfaces", "ethernet", "eth0", "mtu"]), cmds)

    def test_deleted_named_empty_interface_is_noop(self):
        """A named interface with no L2 fields set has nothing for
        this module to delete -- confirmed correct, not a bug: an
        empty {} in have means an empty purge."""
        raw_have = _FIXTURES["eth0_truly_empty"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertEqual(cmds, [])

    def test_deleted_idempotent_absent_interface(self):
        """Deleting an interface not present on the device at all
        must be a no-op -- nothing to purge against."""
        raw_have = _FIXTURES["eth1_truly_empty"]
        cmds = build_commands([{"name": "eth0"}], raw_have, "deleted")
        self.assertEqual(cmds, [])


if __name__ == "__main__":
    unittest.main()
