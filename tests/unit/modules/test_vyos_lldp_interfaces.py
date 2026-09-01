# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_lldp_interfaces import (
    ARGUMENT_SPEC,
    _device_to_argspec,
    _entry_from_device,
    _entry_to_device,
    _iface_base,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE = ["service", "lldp", "interface"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("lldp_interfaces_running.json")
        self.mock_vyos.get_config = MagicMock(return_value={"interface": self.fixture})

    def gather(self):
        have = _device_to_argspec(self.fixture)
        for entry in have:
            cast_by_spec(entry, ARGUMENT_SPEC["config"]["options"])
        return have


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_interface_dict(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("eth0", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_non_dict_response_is_safe(self):
        self.mock_vyos.get_config = MagicMock(return_value="eth0")
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestIfaceBase(unittest.TestCase):
    def test_base_path(self):
        self.assertEqual(_iface_base("eth0"), _BASE + ["eth0"])


class TestEntryToDeviceFromDevice(unittest.TestCase):
    def test_mode(self):
        result = _entry_to_device({"mode": "disable"})
        self.assertEqual(result, {"mode": "disable"})

    def test_elin(self):
        result = _entry_to_device({"location": {"elin": "1234567890"}})
        self.assertEqual(result, {"location": {"elin": "1234567890"}})

    def test_coordinate_based(self):
        cb = {"latitude": "1N", "longitude": "1E", "altitude": 10}
        result = _entry_to_device({"location": {"coordinate_based": cb}})
        self.assertEqual(result, {"location": {"coordinate-based": cb}})

    def test_from_device_defers_int_casting_to_cast_by_spec(self):
        """_entry_from_device no longer manually casts altitude --
        that's cast_by_spec's job, applied later by callers (matching
        the established pattern elsewhere, e.g. vyos_ospfv2's
        distance/redistribute fields). Confirmed end-to-end via
        TestDeviceToArgspecFixture, which does go through cast_by_spec."""
        cb = {"latitude": "1N", "longitude": "1E", "altitude": "10"}
        entry = _entry_from_device({"location": {"coordinate-based": cb}})
        self.assertEqual(entry["location"]["coordinate_based"]["altitude"], "10")

    def test_empty(self):
        self.assertEqual(_entry_to_device({}), {})
        self.assertEqual(_entry_from_device({}), {})


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_both_interfaces_present(self):
        have = self.gather()
        names = {e["name"] for e in have}
        self.assertEqual(names, {"eth0", "eth1"})

    def test_eth0_mode_and_elin_parsed(self):
        have = self.gather()
        eth0 = next(e for e in have if e["name"] == "eth0")
        self.assertEqual(eth0["mode"], "disable")
        self.assertEqual(eth0["location"]["elin"], "1234567890")

    def test_eth1_coordinate_based_parsed(self):
        have = self.gather()
        eth1 = next(e for e in have if e["name"] == "eth1")
        coord = eth1["location"]["coordinate_based"]
        self.assertEqual(coord["latitude"], "33.524449N")
        self.assertEqual(coord["altitude"], 2200)


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_clear_omitted_location_entirely_via_replaced(self):
        """Confirmed bug in the original: elin/latitude/longitude/
        altitude/datum had no clear-on-omit logic at all, unlike mode
        (a genuine inconsistency). dict_op's purge handles this
        uniformly -- when location is entirely absent from want, the
        whole node is deleted (not descended into)."""
        raw_have = {"eth0": {"mode": "disable", "location": {"elin": "1234567890"}}}
        config = [{"name": "eth0", "mode": "disable"}]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["eth0", "location"]), cmds)

    def test_clear_specific_field_when_location_partially_present(self):
        raw_have = {
            "eth0": {
                "location": {
                    "elin": "123",
                    "coordinate-based": {"latitude": "1N", "longitude": "1E"},
                },
            },
        }
        coord = {"latitude": "1N", "longitude": "1E"}
        config = [{"name": "eth0", "location": {"coordinate_based": coord}}]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["eth0", "location", "elin"]), cmds)
        self.assertNotIn(("delete", _BASE + ["eth0", "location"]), cmds)

    def test_replaced_does_not_touch_unrelated_interfaces(self):
        raw_have = {"eth0": {"mode": "disable"}, "eth1": {"mode": "rx"}}
        config = [{"name": "eth0", "mode": "disable"}]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertEqual(cmds, [])

    def test_deleted_all(self):
        cmds = build_commands([], {"eth0": {}}, "deleted")
        self.assertEqual(cmds, [("delete", _BASE + ["eth0"])])

    def test_deleted_named(self):
        cmds = build_commands([{"name": "eth0"}], {"eth0": {}}, "deleted")
        self.assertEqual(cmds, [("delete", _BASE + ["eth0"])])

    def test_deleted_named_nonexistent_is_noop(self):
        cmds = build_commands([{"name": "eth99"}], {"eth0": {}}, "deleted")
        self.assertEqual(cmds, [])

    def test_overridden_removes_omitted_interface(self):
        raw_have = {"eth0": {}, "eth1": {"mode": "rx"}}
        cmds = build_commands([{"name": "eth0"}], raw_have, "overridden")
        self.assertIn(("delete", _BASE + ["eth1"]), cmds)

    def test_merged_new_interface(self):
        config = [{"name": "eth2", "mode": "tx"}]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["eth2", "mode", "tx"]), cmds)


if __name__ == "__main__":
    unittest.main()
