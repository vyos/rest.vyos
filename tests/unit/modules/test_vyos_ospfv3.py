# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospfv3 import (
    _CONFIG_OPTIONS,
    ARGUMENT_SPEC,
    _area_entry_from_device,
    _area_entry_to_device,
    _derive_key_field,
    _device_to_argspec,
    _kebab_fields,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE = ["protocols", "ospfv3"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("ospfv3_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)

    def gather(self):
        have = _device_to_argspec(self.fixture)
        cast_by_spec(have, _CONFIG_OPTIONS)
        return have


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("area", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_collapsed_response_normalized(self):
        """Regression coverage for the confirmed failure mode from
        vyos_ospf_interfaces's build: an unguarded collapsed response
        (VyOS's single-value tag-node quirk) would otherwise be
        iterated character-by-character downstream."""
        self.mock_vyos.get_config = MagicMock(return_value="eth1")
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {"eth1": {}})


class TestDeriveKeyField(unittest.TestCase):
    def test_derives_area_id(self):
        area_opts = ARGUMENT_SPEC["config"]["options"]["areas"]["options"]
        self.assertEqual(_derive_key_field(area_opts), "area_id")

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"type": "str"}})


class TestKebabFields(unittest.TestCase):
    def test_converts_multiword_keys(self):
        result = _kebab_fields({"router_id": "1.1.1.1"})
        self.assertEqual(result, {"router-id": "1.1.1.1"})


class TestAreaEntry(unittest.TestCase):
    def test_export_import_list_to_device(self):
        result = _area_entry_to_device({"export_list": "el1", "import_list": "il1"})
        self.assertEqual(result, {"export-list": "el1", "import-list": "il1"})

    def test_range_to_device(self):
        result = _area_entry_to_device(
            {"range": [{"address": "2001:db1::/32", "not_advertise": True}]},
        )
        self.assertEqual(result, {"range": {"2001:db1::/32": {"not-advertise": {}}}})

    def test_from_device(self):
        entry = _area_entry_from_device(
            {"export-list": "el1", "range": {"2001:db1::/32": {"advertise": {}}}},
        )
        self.assertEqual(entry["export_list"], "el1")
        self.assertEqual(entry["range"][0]["address"], "2001:db1::/32")
        self.assertTrue(entry["range"][0]["advertise"])

    def test_empty(self):
        self.assertEqual(_area_entry_to_device({}), {})
        self.assertEqual(_area_entry_from_device({}), {})


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_areas_parsed(self):
        have = self.gather()
        area_ids = {a["area_id"] for a in have["areas"]}
        self.assertEqual(area_ids, {"2", "3"})

    def test_area_export_import_list_parsed(self):
        have = self.gather()
        area2 = next(a for a in have["areas"] if a["area_id"] == "2")
        self.assertEqual(area2["export_list"], "export1")
        self.assertEqual(area2["import_list"], "import1")

    def test_range_advertise_not_advertise_parsed(self):
        have = self.gather()
        area2 = next(a for a in have["areas"] if a["area_id"] == "2")
        r1 = next(r for r in area2["range"] if r["address"] == "2001:db10::/32")
        r2 = next(r for r in area2["range"] if r["address"] == "2001:db20::/32")
        self.assertNotIn("advertise", r1)
        self.assertNotIn("not_advertise", r1)
        self.assertTrue(r2["not_advertise"])

        area3 = next(a for a in have["areas"] if a["area_id"] == "3")
        self.assertTrue(area3["range"][0]["advertise"])

    def test_parameters_parsed(self):
        have = self.gather()
        self.assertEqual(have["parameters"]["router_id"], "192.0.2.10")

    def test_redistribute_parsed(self):
        have = self.gather()
        route_types = {r["route_type"] for r in have["redistribute"]}
        self.assertEqual(route_types, {"bgp", "static"})
        bgp = next(r for r in have["redistribute"] if r["route_type"] == "bgp")
        self.assertEqual(bgp["route_map"], "redist-map")

    def test_empty(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_changing_existing_range_flag_via_replaced(self):
        """Primary confirmed bug from the original hand-rolled
        implementation: range advertise/not_advertise were only ever
        set on initial range creation (an "if addr not in have_ranges"
        guard) -- changing an existing range's flag generated no
        command under either state. dict_op's purge (via "replaced")
        correctly handles this generically."""
        raw_have = {"area": {"2": {"range": {"2001:db20::/32": {"not-advertise": {}}}}}}
        config = {
            "areas": [
                {
                    "area_id": "2",
                    "range": [
                        {"address": "2001:db20::/32", "advertise": True},
                    ],
                },
            ],
        }
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            ("delete", _BASE + ["area", "2", "range", "2001:db20::/32", "not-advertise"]),
            cmds,
        )
        self.assertIn(
            ("set", _BASE + ["area", "2", "range", "2001:db20::/32", "advertise"]),
            cmds,
        )

    def test_merged_does_not_clear_conflicting_flag(self):
        """merged never runs a purge pass, by design (established,
        consistent semantic throughout this collection) -- confirms
        it correctly does NOT clear not-advertise even when advertise
        is set instead, unlike replaced above."""
        raw_have = {"area": {"2": {"range": {"2001:db20::/32": {"not-advertise": {}}}}}}
        config = {
            "areas": [
                {
                    "area_id": "2",
                    "range": [
                        {"address": "2001:db20::/32", "advertise": True},
                    ],
                },
            ],
        }
        cmds = build_commands(config, raw_have, "merged")
        self.assertFalse(any(c[0] == "delete" and "not-advertise" in str(c) for c in cmds))

    def test_replaced_is_whole_resource_not_scoped(self):
        """Confirmed matching this module's own documented contract
        ("replaced replaces the entire OSPFv3 configuration") and
        vyos_ospfv2's own established precedent -- unlike
        vyos_static_routes/vyos_route_maps, which scope replaced per
        named item."""
        raw_have = {"parameters": {"router-id": "1.1.1.1"}, "redistribute": {"bgp": {}}}
        config = {"parameters": {"router_id": "1.1.1.1"}}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["redistribute"]), cmds)

    def test_deleted_with_have(self):
        cmds = build_commands({}, {"parameters": {"router-id": "1.1.1.1"}}, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_no_have_is_noop(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_merged_new_area(self):
        config = {"areas": [{"area_id": "5", "export_list": "el5"}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["area", "5", "export-list", "el5"]), cmds)


if __name__ == "__main__":
    unittest.main()
