# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_route_maps import (
    ARGUMENT_SPEC,
    _derive_key_field,
    _device_to_argspec,
    _keyed_list_from_device,
    _keyed_list_to_device,
    _match_from_device,
    _match_to_device,
    _rule_entry_from_device,
    _rule_entry_to_device,
    _seed_route_map_placeholders,
    _set_from_device,
    _set_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["policy", "route-map"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("route_maps_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_unwraps_route_map_wrapper_key(self):
        """Confirmed against the pre-existing fixture (built from real
        device data): the REST API wraps the response in an extra
        "route-map" key even when querying at the policy/route-map
        path itself -- the same defensive-unwrap pattern every other
        module this session needed for its own top-level get_config."""
        result = get_running_config(self.mock_vyos)
        self.assertIn("RM-TEST-EXPORT-POLICY", result)
        self.assertNotIn("route-map", result)

    def test_no_wrapper_key_passes_through(self):
        self.mock_vyos.get_config = MagicMock(return_value={"RM1": {"rule": {}}})
        result = get_running_config(self.mock_vyos)
        self.assertIn("RM1", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestDeriveKeyField(unittest.TestCase):
    def test_derives_route_map_key(self):
        opts = ARGUMENT_SPEC["config"]["options"]
        self.assertEqual(_derive_key_field(opts), "route_map")

    def test_derives_sequence_key(self):
        entry_opts = ARGUMENT_SPEC["config"]["options"]["entries"]["options"]
        self.assertEqual(_derive_key_field(entry_opts), "sequence")

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"type": "str"}})

    def test_raises_if_more_than_one_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"required": True}, "b": {"required": True}})


class TestKeyedListHelper(unittest.TestCase):
    def test_to_device_default_transform_is_autoclean(self):
        result = _keyed_list_to_device([{"route_map": "RM1", "description": "x"}], "route_map")
        self.assertEqual(result, {"RM1": {"description": "x"}})

    def test_from_device_default_transform_is_from_device(self):
        result = _keyed_list_from_device({"RM1": {"description": "x"}}, "route_map")
        self.assertEqual(result, [{"route_map": "RM1", "description": "x"}])

    def test_empty(self):
        self.assertEqual(_keyed_list_to_device([], "route_map"), {})
        self.assertEqual(_keyed_list_from_device({}, "route_map"), [])


class TestMatchToDeviceFromDevice(unittest.TestCase):
    """Most match options are fully generic; only prefix_list/
    prefix_list6 and ip/ipv6 nexthop matching are genuine structural
    exceptions (confirmed against vyos-1x: the device nests these
    deeper than the argspec)."""

    def test_simple_fields_generic(self):
        result = _match_to_device({"peer": "192.0.2.1", "protocol": "bgp", "metric": 100})
        self.assertEqual(result, {"peer": "192.0.2.1", "protocol": "bgp", "metric": 100})

    def test_prefix_list_nested_two_levels(self):
        result = _match_to_device({"prefix_list": "PL1"})
        self.assertEqual(result, {"ip": {"address": {"prefix-list": "PL1"}}})

    def test_prefix_list6_nested_two_levels(self):
        result = _match_to_device({"prefix_list6": "PL6"})
        self.assertEqual(result, {"ipv6": {"address": {"prefix-list": "PL6"}}})

    def test_ip_nexthop_extra_nesting_level(self):
        result = _match_to_device(
            {"ip": {"nexthop_address": "10.0.0.1", "nexthop_prefix_list": "PL2"}},
        )
        self.assertEqual(
            result,
            {"ip": {"nexthop": {"address": "10.0.0.1", "prefix-list": "PL2"}}},
        )

    def test_ipv6_nexthop_extra_nesting_level(self):
        result = _match_to_device({"ipv6": {"nexthop_address": "2001:db8::1"}})
        self.assertEqual(result, {"ipv6": {"nexthop": {"address": "2001:db8::1"}}})

    def test_from_device_prefix_list(self):
        entry = _match_from_device({"ip": {"address": {"prefix-list": "PL1"}}})
        self.assertEqual(entry["prefix_list"], "PL1")

    def test_from_device_nexthop(self):
        entry = _match_from_device({"ip": {"nexthop": {"address": "10.0.0.1"}}})
        self.assertEqual(entry["ip"], {"nexthop_address": "10.0.0.1"})

    def test_from_device_generic_fields(self):
        entry = _match_from_device({"peer": "192.0.2.1", "protocol": "bgp"})
        self.assertEqual(entry, {"peer": "192.0.2.1", "protocol": "bgp"})

    def test_empty(self):
        self.assertEqual(_match_to_device({}), {})
        self.assertEqual(_match_to_device(None), {})
        self.assertEqual(_match_from_device({}), {})
        self.assertEqual(_match_from_device(None), {})


class TestSetToDeviceFromDevice(unittest.TestCase):
    """as_path_* collapse onto one nested device node. community/
    large_community/ipv6_next_hop are fully generic once modeled as
    real nested dicts. "as_" is a genuine Python-keyword-collision
    rename, nested inside aggregator specifically."""

    def test_atomic_aggregate_fully_generic(self):
        result = _set_to_device({"atomic_aggregate": True})
        self.assertEqual(result, {"atomic_aggregate": {}})

    def test_as_path_options_collapse_onto_one_node(self):
        result = _set_to_device(
            {"as_path_exclude": "111", "as_path_prepend": "65001", "as_path_prepend_last_as": 2},
        )
        self.assertEqual(
            result["as-path"],
            {"exclude": "111", "prepend": "65001", "prepend-last-as": 2},
        )

    def test_aggregator_as_rename(self):
        """Regression test for the real bug caught this session: "as_"
        is nested inside "aggregator", not a top-level set field -- a
        flat rename map applied only at the top level misses it
        entirely."""
        result = _set_to_device({"aggregator": {"as_": 100, "ip": "10.0.0.5"}})
        self.assertEqual(result, {"aggregator": {"as": 100, "ip": "10.0.0.5"}})

    def test_aggregator_as_only(self):
        result = _set_to_device({"aggregator": {"as_": 100}})
        self.assertEqual(result, {"aggregator": {"as": 100}})

    def test_community_add_stays_a_plain_list(self):
        result = _set_to_device({"community": {"add": ["no-export", "no-advertise"]}})
        self.assertEqual(result["community"], {"add": ["no-export", "no-advertise"]})

    def test_large_community_none_presence(self):
        result = _set_to_device({"large_community": {"none": True}})
        self.assertEqual(result["large_community"], {"none": {}})

    def test_ipv6_next_hop_generic(self):
        result = _set_to_device({"ipv6_next_hop": {"global": "2001:db8::1"}})
        self.assertEqual(result["ipv6_next_hop"], {"global": "2001:db8::1"})

    def test_ipv6_next_hop_valueless_options(self):
        result = _set_to_device({"ipv6_next_hop": {"peer_address": True, "prefer_global": True}})
        self.assertEqual(
            result["ipv6_next_hop"],
            {"peer_address": {}, "prefer_global": {}},
        )

    def test_from_device_community_add(self):
        entry = _set_from_device({"community": {"add": ["no-export"]}})
        self.assertEqual(entry["community"], {"add": ["no-export"]})

    def test_from_device_large_community_none(self):
        entry = _set_from_device({"large-community": {"none": {}}})
        self.assertEqual(entry["large_community"], {"none": True})

    def test_from_device_as_path(self):
        entry = _set_from_device({"as-path": {"exclude": "111", "prepend-last-as": "2"}})
        self.assertEqual(entry["as_path_exclude"], "111")
        self.assertEqual(entry["as_path_prepend_last_as"], 2)

    def test_from_device_aggregator_as_rename_with_int_cast(self):
        entry = _set_from_device({"aggregator": {"as": "100", "ip": "10.0.0.5"}})
        self.assertEqual(entry["aggregator"]["as_"], 100)
        self.assertEqual(entry["aggregator"]["ip"], "10.0.0.5")

    def test_empty(self):
        self.assertEqual(_set_to_device({}), {})
        self.assertEqual(_set_to_device(None), {})
        self.assertEqual(_set_from_device({}), {})
        self.assertEqual(_set_from_device(None), {})


class TestRuleEntryToDeviceFromDevice(unittest.TestCase):
    def test_continue_sequence_renamed(self):
        """ "continue" is a Python keyword and can't be used as a
        dict() kwarg -- "continue_sequence" is the unavoidable argspec
        name, handled directly at the rule level (not a set field)."""
        result = _rule_entry_to_device({"continue_sequence": 20})
        self.assertEqual(result["continue"], 20)

    def test_generic_fields(self):
        result = _rule_entry_to_device({"action": "permit", "call": "RM2"})
        self.assertEqual(result, {"action": "permit", "call": "RM2"})

    def test_from_device_continue(self):
        entry = _rule_entry_from_device({"continue": "20"})
        self.assertEqual(entry["continue_sequence"], 20)

    def test_from_device_bare_collapse(self):
        entry = _rule_entry_from_device(None)
        self.assertEqual(entry, {})


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device([]), {})
        self.assertEqual(_want_to_device(None), {})

    def test_route_map_without_entries_omitted(self):
        self.assertEqual(_want_to_device([{"route_map": "RM1"}]), {})

    def test_keyed_by_route_map_name(self):
        config = [{"route_map": "RM1", "entries": [{"sequence": 10, "action": "permit"}]}]
        result = _want_to_device(config)
        self.assertIn("10", result["RM1"]["rule"])

    def test_underscore_route_map_name_stays_verbatim(self):
        """Confirmed against vyos-1x: route-map names may legitimately
        contain underscores. _want_to_device itself must not alter the
        key -- the dict_op-level protection is tested separately in
        TestBuildCommands."""
        config = [{"route_map": "my_route_map", "entries": [{"sequence": 10}]}]
        result = _want_to_device(config)
        self.assertIn("my_route_map", result)


class TestSeedRouteMapPlaceholders(unittest.TestCase):
    """Regression tests for the confirmed bug: dict_op's fallback
    guesses a kebab-cased device key whenever a want key is missing
    from have -- correct for schema field names, wrong for a route-map
    name (an opaque value that may contain an underscore). Reproduced
    directly before this fix: "my_route_map" became "my-route-map" in
    the generated command on first creation."""

    def test_seeds_new_route_map_verbatim(self):
        want = {"my_route_map": {"rule": {"10": {}}}}
        have = {}
        _seed_route_map_placeholders(want, have)
        self.assertIn("my_route_map", have)

    def test_seeds_new_rule_with_none_not_empty_dict(self):
        """Seeding with {} instead of None would make dict_op think a
        presence-only rule already matches and skip emitting its set
        command -- the same mistake caught once already this session."""
        want = {"RM1": {"rule": {"10": {}}}}
        have = {"RM1": {"rule": {}}}
        _seed_route_map_placeholders(want, have)
        self.assertIsNone(have["RM1"]["rule"]["10"])

    def test_does_not_overwrite_existing_entries(self):
        want = {"RM1": {"rule": {"10": {}}}}
        have = {"RM1": {"rule": {"10": {"action": "permit"}}}}
        _seed_route_map_placeholders(want, have)
        self.assertEqual(have["RM1"]["rule"]["10"], {"action": "permit"})


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_all_route_maps_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        names = [rm["route_map"] for rm in result]
        self.assertIn("RM-TEST-EXPORT-POLICY", names)
        self.assertIn("rm1", names)

    def test_prefix_list_and_nexthop_match_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        rm = next(rm for rm in result if rm["route_map"] == "RM-TEST-EXPORT-POLICY")
        rule = rm["entries"][0]
        self.assertEqual(rule["match"]["prefix_list"], "PL-MATCH")
        self.assertEqual(rule["match"]["ip"]["nexthop_address"], "10.0.0.1")

    def test_community_add_parsed_as_list(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        rm = next(rm for rm in result if rm["route_map"] == "RM-TEST-EXPORT-POLICY")
        rule = rm["entries"][0]
        self.assertEqual(rule["set"]["community"]["add"], ["no-export", "no-advertise"])

    def test_large_community_none_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        rm1 = next(rm for rm in result if rm["route_map"] == "rm1")
        self.assertTrue(rm1["entries"][0]["set"]["large_community"]["none"])

    def test_aggregator_as_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        rm = next(rm for rm in result if rm["route_map"] == "RM-TEST-EXPORT-POLICY")
        self.assertEqual(rm["entries"][0]["set"]["aggregator"]["as_"], 100)

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), [])
        self.assertEqual(_device_to_argspec(None), [])


class TestBuildCommands(VyOSModuleTestCase):
    def setUp(self):
        super().setUp()
        self.raw = get_running_config(self.mock_vyos)

    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "replaced"), [])

    def test_overridden_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "overridden"), [])

    def test_underscore_route_map_name_not_kebab_cased_on_creation(self):
        """The primary confirmed bug this session, reproduced directly
        end to end before the fix: "my_route_map" became
        "my-route-map" in the generated command on first creation."""
        config = [{"route_map": "my_route_map", "entries": [{"sequence": 10, "action": "permit"}]}]
        cmds = build_commands(config, {}, "merged")
        self.assertFalse(any("my-route-map" in str(c) for c in cmds))
        self.assertTrue(any("my_route_map" in str(c) for c in cmds))

    def test_replaced_scoped_to_named_route_map_only(self):
        have = _device_to_argspec(self.raw)
        config = [
            {
                "route_map": "RM-TEST-EXPORT-POLICY",
                "entries": have[0]["entries"],
            },
        ]
        cmds = build_commands(config, self.raw, "replaced")
        self.assertEqual(cmds, [])
        self.assertFalse(any("rm1" in str(c) for c in cmds))

    def test_replaced_removes_omitted_field_full_replace_semantic(self):
        """Confirms this is the intended "replaced" semantic (matching
        every other module this session), not a bug: omitting a field
        from a route map named in "replaced" removes it."""
        config = [
            {
                "route_map": "RM-TEST-EXPORT-POLICY",
                "entries": [{"sequence": 10, "action": "permit"}],
            },
        ]
        cmds = build_commands(config, self.raw, "replaced")
        self.assertIn(("delete", _BASE + ["RM-TEST-EXPORT-POLICY", "rule", "10", "set"]), cmds)
        self.assertIn(("delete", _BASE + ["RM-TEST-EXPORT-POLICY", "rule", "10", "match"]), cmds)

    def test_overridden_deletes_omitted_route_map(self):
        have = _device_to_argspec(self.raw)
        config = [
            {
                "route_map": "RM-TEST-EXPORT-POLICY",
                "entries": have[0]["entries"],
            },
        ]
        cmds = build_commands(config, self.raw, "overridden")
        self.assertIn(("delete", _BASE + ["rm1"]), cmds)

    def test_deleted_scoped_to_named_route_map(self):
        cmds = build_commands([{"route_map": "rm1"}], self.raw, "deleted")
        self.assertEqual(cmds, [("delete", _BASE + ["rm1"])])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self.raw, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_named_nonexistent_is_noop(self):
        cmds = build_commands([{"route_map": "NONEXISTENT"}], self.raw, "deleted")
        self.assertEqual(cmds, [])

    def test_collapsed_single_rule_no_char_iteration_bug(self):
        raw_have = {"RM1": {"rule": "10"}}
        config = [{"route_map": "RM1", "entries": [{"sequence": 10}]}]
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_merged_new_rule_with_community(self):
        config = [
            {
                "route_map": "RM-NEW",
                "entries": [
                    {
                        "sequence": 10,
                        "action": "permit",
                        "set": {"community": {"add": ["no-export"]}},
                    },
                ],
            },
        ]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["RM-NEW", "rule", "10", "set", "community", "add", "no-export"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
