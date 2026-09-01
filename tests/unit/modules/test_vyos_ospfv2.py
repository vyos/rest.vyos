# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospfv2 import (
    _CONFIG_OPTIONS,
    ARGUMENT_SPEC,
    _area_type_from_device,
    _area_type_to_device,
    _derive_key_field,
    _device_to_argspec,
    _distance_from_device,
    _distance_to_device,
    _kebab_fields,
    _passive_from_device,
    _passive_to_device,
    _timers_from_device,
    _timers_to_device_refresh,
    _timers_to_device_throttle,
    _vlink_auth_from_device,
    _vlink_auth_to_device,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE = ["protocols", "ospf"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("ospfv2_running.json")
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


class TestDeriveKeyField(unittest.TestCase):
    def test_derives_area_id(self):
        area_opts = ARGUMENT_SPEC["config"]["options"]["areas"]["options"]
        self.assertEqual(_derive_key_field(area_opts), "area_id")

    def test_derives_neighbor_id(self):
        nb_opts = ARGUMENT_SPEC["config"]["options"]["neighbor"]["options"]
        self.assertEqual(_derive_key_field(nb_opts), "neighbor_id")

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"type": "str"}})


class TestKebabFields(unittest.TestCase):
    """Regression tests for the primary confirmed bug found during
    development: dict_op requires have's keys to already be genuine
    device kebab-case (it only normalizes underscores for its own
    lookup index, not for the output path). autoclean deliberately
    leaves keys as given, so any multi-word field reconstructed via
    this module's own entry-transforms (rather than coming straight
    from the device) needs explicit conversion, or a generated delete
    command uses the wrong (snake_case) path segment."""

    def test_converts_multiword_keys(self):
        result = _kebab_fields({"default_cost": 20, "no_summary": True})
        self.assertEqual(result, {"default-cost": 20, "no-summary": {}})

    def test_drops_none_and_false(self):
        result = _kebab_fields({"default_cost": None, "no_summary": False})
        self.assertEqual(result, {})

    def test_single_word_keys_unaffected(self):
        result = _kebab_fields({"cost": 10})
        self.assertEqual(result, {"cost": 10})


class TestAreaType(unittest.TestCase):
    def test_nssa_set_flag_is_node_presence_not_a_device_leaf(self):
        """Confirmed genuine structural exception: the argspec's
        nssa.set/stub.set boolean doesn't exist as a device leaf --
        the node's own presence IS the set flag."""
        result = _area_type_to_device({"nssa": {"set": True, "default_cost": 5}})
        self.assertEqual(result, {"nssa": {"default-cost": 5}})
        self.assertNotIn("set", result["nssa"])

    def test_stub_no_summary(self):
        """Regression test for the confirmed original bug: stub's
        no_summary was declared in ARGUMENT_SPEC but never checked
        anywhere in the original hand-rolled command-building logic."""
        result = _area_type_to_device({"stub": {"no_summary": True}})
        self.assertEqual(result, {"stub": {"no-summary": {}}})

    def test_from_device_restores_set_flag(self):
        entry = _area_type_from_device({"nssa": {"default-cost": "5"}})
        self.assertTrue(entry["nssa"]["set"])

    def test_normal_presence(self):
        result = _area_type_to_device({"normal": True})
        self.assertEqual(result, {"normal": {}})

    def test_empty(self):
        self.assertEqual(_area_type_to_device({}), {})
        self.assertIsNone(_area_type_from_device({}))


class TestDistance(unittest.TestCase):
    def test_global_and_ospf(self):
        result = _distance_to_device({"global": 110, "ospf": {"inter_area": 120}})
        self.assertEqual(result, {"global": 110, "ospf": {"inter-area": 120}})

    def test_from_device(self):
        entry = _distance_from_device({"global": "110", "ospf": {"external": "150"}})
        self.assertEqual(entry["global"], 110)
        self.assertEqual(entry["ospf"]["external"], "150")  # cast_by_spec's job downstream


class TestTimers(unittest.TestCase):
    """Confirmed genuine structural exception: the argspec groups
    "refresh" and "throttle" both under one "timers" parent, but the
    device has them as two separate top-level nodes."""

    def test_refresh_maps_to_separate_top_level_node(self):
        result = _timers_to_device_refresh({"refresh": {"timers": 300}})
        self.assertEqual(result, {"timers": 300})

    def test_throttle_maps_to_device_timers_node(self):
        result = _timers_to_device_throttle({"throttle": {"spf": {"delay": 200}}})
        self.assertEqual(result, {"throttle": {"spf": {"delay": 200}}})

    def test_from_device_recombines_both(self):
        entry = _timers_from_device({"timers": "300"}, {"throttle": {"spf": {"delay": "200"}}})
        self.assertEqual(entry["refresh"]["timers"], 300)
        self.assertEqual(entry["throttle"]["spf"]["delay"], "200")


class TestPassiveInterface(unittest.TestCase):
    """Confirmed genuine structural exception: passive_interface and
    passive_interface_exclude both map onto the same per-interface
    "interface <name> passive" device subtree -- presence alone means
    enabled, "passive.disable" means explicitly excluded."""

    def test_to_device_both(self):
        result = _passive_to_device(["eth1"], ["eth2"])
        self.assertEqual(result, {"eth1": {"passive": {}}, "eth2": {"passive": {"disable": {}}}})

    def test_from_device_both(self):
        passive, excluded = _passive_from_device(
            {"eth1": {"passive": {}}, "eth2": {"passive": {"disable": {}}}},
        )
        self.assertEqual(passive, ["eth1"])
        self.assertEqual(excluded, ["eth2"])

    def test_from_device_ignores_non_passive_interfaces(self):
        passive, excluded = _passive_from_device({"eth3": {"some-other-key": {}}})
        self.assertEqual(passive, [])
        self.assertEqual(excluded, [])


class TestVirtualLinkAuth(unittest.TestCase):
    def test_md5_to_device(self):
        result = _vlink_auth_to_device({"md5": [{"key_id": 10, "md5_key": "secret"}]})
        self.assertEqual(result, {"md5": {"10": {"md5-key": "secret"}}})

    def test_plaintext_to_device(self):
        result = _vlink_auth_to_device({"plaintext_password": "pw"})
        self.assertEqual(result, {"plaintext-password": "pw"})

    def test_md5_from_device(self):
        entry = _vlink_auth_from_device({"md5": {"10": {"md5-key": "secret"}}})
        self.assertEqual(entry["md5"], [{"key_id": 10, "md5_key": "secret"}])


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_areas_parsed(self):
        have = self.gather()
        area_ids = [a["area_id"] for a in have["areas"]]
        self.assertEqual(set(area_ids), {"2", "4", "5"})

    def test_stub_area_no_summary_parsed(self):
        have = self.gather()
        area4 = next(a for a in have["areas"] if a["area_id"] == "4")
        self.assertTrue(area4["area_type"]["stub"]["no_summary"])

    def test_virtual_link_parsed(self):
        have = self.gather()
        area4 = next(a for a in have["areas"] if a["area_id"] == "4")
        vlink = area4["virtual_link"][0]
        self.assertEqual(vlink["address"], "10.0.0.1")
        self.assertEqual(vlink["authentication"]["plaintext_password"], "secret")
        self.assertEqual(vlink["dead_interval"], 40)

    def test_passive_interface_and_exclude_parsed(self):
        have = self.gather()
        self.assertEqual(have["passive_interface"], ["eth1"])
        self.assertEqual(have["passive_interface_exclude"], ["eth2"])

    def test_timers_parsed(self):
        have = self.gather()
        self.assertEqual(have["timers"]["refresh"]["timers"], 300)
        self.assertEqual(have["timers"]["throttle"]["spf"]["delay"], 200)

    def test_max_metric_parsed(self):
        have = self.gather()
        self.assertTrue(have["max_metric"]["router_lsa"]["administrative"])
        self.assertEqual(have["max_metric"]["router_lsa"]["on_shutdown"], 10)

    def test_mpls_te_parsed(self):
        have = self.gather()
        self.assertTrue(have["mpls_te"]["enabled"])
        self.assertEqual(have["mpls_te"]["router_address"], "192.0.11.11")

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = self.gather()
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_clear_omitted_attribute_on_replaced(self):
        """Primary confirmed bug from the original hand-rolled
        implementation: clearing an omitted attribute never generated
        a delete command. Also the exact scenario that caught the
        kebab-key regression during development."""
        raw_have = {"area": {"4": {"area-type": {"stub": {"default-cost": "20"}}}}}
        config = {"areas": [{"area_id": "4", "area_type": {"stub": {"set": True}}}]}
        cmds = build_commands(config, raw_have, "replaced")
        expected = ("delete", _BASE + ["area", "4", "area-type", "stub", "default-cost"])
        self.assertIn(expected, cmds)

    def test_stub_no_summary_now_works(self):
        config = {"areas": [{"area_id": "4", "area_type": {"stub": {"no_summary": True}}}]}
        cmds = build_commands(config, {}, "merged")
        expected = ("set", _BASE + ["area", "4", "area-type", "stub", "no-summary"])
        self.assertIn(expected, cmds)

    def test_replaced_only_touches_what_changed(self):
        """Confirmed fix for the original's disruptive "delete
        everything and recreate" replaced heuristic -- a targeted
        dict_op purge only touches the sections that actually
        differ."""
        raw_have = {
            "area": {"2": {"area-type": {"normal": {}}}},
            "parameters": {"router-id": "1.1.1.1"},
        }
        config = {
            "areas": [{"area_id": "2", "area_type": {"normal": True}}],
            "parameters": {"router_id": "2.2.2.2"},
        }
        cmds = build_commands(config, raw_have, "replaced")
        self.assertFalse(any("area" in str(c) for c in cmds))
        expected = ("set", _BASE + ["parameters", "router-id", "2.2.2.2"])
        self.assertIn(expected, cmds)

    def test_passive_interface_and_exclude_together(self):
        config = {"passive_interface": ["eth1"], "passive_interface_exclude": ["eth2"]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["interface", "eth1", "passive"]), cmds)
        self.assertIn(("set", _BASE + ["interface", "eth2", "passive", "disable"]), cmds)

    def test_deleted_with_have(self):
        cmds = build_commands({}, {"parameters": {"router-id": "1.1.1.1"}}, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_no_have_is_noop(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_merged_new_virtual_link(self):
        config = {
            "areas": [
                {
                    "area_id": "4",
                    "virtual_link": [
                        {"address": "10.0.0.1", "authentication": {"plaintext_password": "pw"}},
                    ],
                },
            ],
        }
        cmds = build_commands(config, {}, "merged")
        vlink_path = _BASE + [
            "area",
            "4",
            "virtual-link",
            "10.0.0.1",
            "authentication",
            "plaintext-password",
            "pw",
        ]
        self.assertIn(("set", vlink_path), cmds)


if __name__ == "__main__":
    unittest.main()
