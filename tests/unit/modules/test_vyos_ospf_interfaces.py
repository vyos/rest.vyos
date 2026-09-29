# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospf_interfaces import (
    _AF_OPTIONS,
    ARGUMENT_SPEC,
    _af4_entry_from_device,
    _af4_entry_to_device,
    _af6_entry_from_device,
    _af6_entry_to_device,
    _auth_from_device,
    _auth_to_device,
    _derive_key_field,
    _device_to_argspec,
    _kebab_fields,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE4 = ["protocols", "ospf", "interface"]
_BASE6 = ["protocols", "ospfv3", "interface"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.ipv4_fixture = load_fixture("ospf_interfaces_ipv4.json")
        self.ipv6_fixture = load_fixture("ospf_interfaces_ipv6.json")
        self.mock_vyos.get_config = MagicMock(
            side_effect=lambda path: (self.ipv4_fixture if path == _BASE4 else self.ipv6_fixture),
        )

    def gather(self):
        raw4, raw6 = get_running_config(self.mock_vyos)
        have = _device_to_argspec(raw4, raw6)
        for iface in have:
            for af in iface.get("address_family") or []:
                cast_by_spec(af, _AF_OPTIONS)
        return have


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_both_afi_trees_separately(self):
        raw4, raw6 = get_running_config(self.mock_vyos)
        self.assertIn("eth1", raw4)
        self.assertIn("eth1", raw6)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        raw4, raw6 = get_running_config(self.mock_vyos)
        self.assertEqual(raw4, {})
        self.assertEqual(raw6, {})


class TestDeriveKeyField(unittest.TestCase):
    def test_derives_name(self):
        opts = ARGUMENT_SPEC["config"]["options"]
        self.assertEqual(_derive_key_field(opts), "name")

    def test_derives_afi(self):
        af_opts = ARGUMENT_SPEC["config"]["options"]["address_family"]["options"]
        self.assertEqual(_derive_key_field(af_opts), "afi")


class TestKebabFields(unittest.TestCase):
    """Regression coverage for the confirmed bug from vyos_ospfv2's
    build, applied here from the start: dict_op requires have's keys
    to already be genuine device kebab-case, but autoclean deliberately
    leaves keys as given."""

    def test_converts_multiword_keys(self):
        result = _kebab_fields({"dead_interval": 40, "mtu_ignore": True})
        self.assertEqual(result, {"dead-interval": 40, "mtu-ignore": {}})


class TestAuthentication(unittest.TestCase):
    """IPv4-only. Confirmed against vyos-1x: md5 is a fixed "key-id"
    node containing a single tagNode entry, not a list."""

    def test_plaintext_to_device(self):
        result = _auth_to_device({"plaintext_password": "pw"})
        self.assertEqual(result, {"plaintext-password": "pw"})

    def test_md5_to_device(self):
        result = _auth_to_device({"md5_key": {"key_id": 10, "key": "secret"}})
        self.assertEqual(result, {"md5": {"key-id": {"10": {"md5-key": "secret"}}}})

    def test_md5_from_device(self):
        entry = _auth_from_device({"md5": {"key-id": {"10": {"md5-key": "secret"}}}})
        self.assertEqual(entry["md5_key"], {"key_id": 10, "key": "secret"})

    def test_empty(self):
        self.assertEqual(_auth_to_device({}), {})
        self.assertIsNone(_auth_from_device({}))


class TestAf6InstanceRename(unittest.TestCase):
    """Confirmed genuine rename: the argspec's "instance" (matching
    the CLI collection's naming) maps to the device's actual leaf
    name "instance-id"."""

    def test_to_device(self):
        result = _af6_entry_to_device({"instance": "5"})
        self.assertEqual(result, {"instance-id": "5"})

    def test_from_device(self):
        entry = _af6_entry_from_device({"instance-id": "5"})
        self.assertEqual(entry["instance"], "5")


class TestAf4EntryToDeviceFromDevice(unittest.TestCase):
    def test_generic_fields(self):
        result = _af4_entry_to_device({"cost": 100, "priority": 26})
        self.assertEqual(result, {"cost": 100, "priority": 26})

    def test_mtu_ignore_presence(self):
        result = _af4_entry_to_device({"mtu_ignore": True})
        self.assertEqual(result, {"mtu-ignore": {}})

    def test_from_device_with_authentication(self):
        entry = _af4_entry_from_device(
            {"cost": "100", "authentication": {"plaintext-password": "pw"}},
        )
        self.assertEqual(entry["authentication"]["plaintext_password"], "pw")


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_both_interfaces_present(self):
        have = self.gather()
        names = [i["name"] for i in have]
        self.assertIn("eth1", names)
        self.assertIn("eth2", names)

    def test_eth1_has_both_afis(self):
        have = self.gather()
        eth1 = next(i for i in have if i["name"] == "eth1")
        afis = {af["afi"] for af in eth1["address_family"]}
        self.assertEqual(afis, {"ipv4", "ipv6"})

    def test_eth2_ipv4_only_minimal(self):
        """eth2's ipv6 fixture entry is empty ({}) -- confirms an
        interface with config on only one AFI doesn't spuriously
        appear on the other."""
        have = self.gather()
        eth2 = next(i for i in have if i["name"] == "eth2")
        afis = {af["afi"] for af in eth2["address_family"]}
        self.assertEqual(afis, {"ipv4"})

    def test_ipv4_fields_parsed(self):
        have = self.gather()
        eth1 = next(i for i in have if i["name"] == "eth1")
        af4 = next(af for af in eth1["address_family"] if af["afi"] == "ipv4")
        self.assertEqual(af4["cost"], 100)
        self.assertTrue(af4["mtu_ignore"])
        self.assertEqual(af4["authentication"]["md5_key"]["key_id"], 10)

    def test_ipv6_fields_parsed(self):
        have = self.gather()
        eth1 = next(i for i in have if i["name"] == "eth1")
        af6 = next(af for af in eth1["address_family"] if af["afi"] == "ipv6")
        self.assertTrue(af6["passive"])
        self.assertEqual(af6["instance"], "5")
        self.assertEqual(af6["ifmtu"], 1500)

    def test_empty(self):
        self.assertEqual(_device_to_argspec({}, {}), [])


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        raw4, raw6 = get_running_config(self.mock_vyos)
        self.assertEqual(build_commands(have, (raw4, raw6), "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        raw4, raw6 = get_running_config(self.mock_vyos)
        self.assertEqual(build_commands(have, (raw4, raw6), "replaced"), [])

    def test_clear_omitted_attribute_on_replaced(self):
        """Primary confirmed bug: the original's clear-on-omit logic
        only fired for op="replace", which was never actually passed
        anywhere in build_commands -- genuinely dead code, since
        "replaced" already deleted and recreated the whole AFI block
        before calling it with an empty have."""
        raw4 = {"eth1": {"cost": "100", "priority": "26"}}
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, (raw4, {}), "replaced")
        self.assertIn(("delete", _BASE4 + ["eth1", "priority"]), cmds)

    def test_replaced_does_not_touch_unrelated_interfaces(self):
        """Confirmed fix for the original's disruptive "delete
        everything and recreate" replaced heuristic."""
        raw4 = {"eth1": {"cost": "100"}, "eth2": {"cost": "200"}}
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, (raw4, {}), "replaced")
        self.assertEqual(cmds, [])

    def test_ipv4_and_ipv6_target_separate_device_trees(self):
        config = [
            {
                "name": "eth1",
                "address_family": [
                    {"afi": "ipv4", "cost": 100},
                    {"afi": "ipv6", "passive": True},
                ],
            },
        ]
        cmds = build_commands(config, ({}, {}), "merged")
        self.assertIn(("set", _BASE4 + ["eth1", "cost", "100"]), cmds)
        self.assertIn(("set", _BASE6 + ["eth1", "passive"]), cmds)

    def test_overridden_removes_omitted_interface(self):
        raw4 = {"eth1": {"cost": "100"}, "eth3": {"cost": "50"}}
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, (raw4, {}), "overridden")
        self.assertIn(("delete", _BASE4 + ["eth3"]), cmds)

    def test_deleted_all_covers_both_trees(self):
        cmds = build_commands([], ({"eth1": {}}, {"eth1": {}}), "deleted")
        self.assertIn(("delete", _BASE4 + ["eth1"]), cmds)
        self.assertIn(("delete", _BASE6 + ["eth1"]), cmds)
        self.assertEqual(len(cmds), 2)

    def test_deleted_named_no_afi_removes_both(self):
        cmds = build_commands([{"name": "eth1"}], ({"eth1": {}}, {"eth1": {}}), "deleted")
        self.assertIn(("delete", _BASE4 + ["eth1"]), cmds)
        self.assertIn(("delete", _BASE6 + ["eth1"]), cmds)
        self.assertEqual(len(cmds), 2)

    def test_deleted_named_specific_afi_only(self):
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4"}]}]
        cmds = build_commands(config, ({"eth1": {}}, {"eth1": {}}), "deleted")
        self.assertEqual(cmds, [("delete", _BASE4 + ["eth1"])])

    def test_deleted_named_nonexistent_is_noop(self):
        cmds = build_commands([{"name": "eth99"}], ({"eth1": {}}, {}), "deleted")
        self.assertEqual(cmds, [])

    def test_merged_adds_cost(self):
        config = [{"name": "eth1", "address_family": [{"afi": "ipv4", "cost": 100}]}]
        cmds = build_commands(config, ({}, {}), "merged")
        self.assertIn(("set", _BASE4 + ["eth1", "cost", "100"]), cmds)


if __name__ == "__main__":
    unittest.main()
