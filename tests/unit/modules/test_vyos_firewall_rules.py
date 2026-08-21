# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_rules import (
    _device_to_argspec,
    _endpoint_from_device,
    _endpoint_to_device,
    _rule_set_from_device,
    _rule_set_to_device,
    _rules_from_device,
    _rules_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["firewall"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("firewall_rules_running.json")

        def _get_config(path):
            # path == _BASE + [afi, "name"]; fixture is wrapped one level
            # deeper ({"ipv4": {"name": {...}}}), matching a real device
            # response that still needs the defensive unwrap.
            afi = path[1]
            return self.fixture.get(afi)

        self.mock_vyos.get_config = MagicMock(side_effect=_get_config)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_targeted_per_afi_fetch(self):
        """Confirm the targeted firewall.<afi>.name fetch is preserved
        (not widened to a broader firewall.<afi> or firewall fetch)."""
        get_running_config(self.mock_vyos)
        calls = [c.args[0] for c in self.mock_vyos.get_config.call_args_list]
        self.assertEqual(calls, [_BASE + ["ipv4", "name"], _BASE + ["ipv6", "name"]])

    def test_unwraps_name_wrapper(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("RULE-SET1", result["ipv4"])

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestEndpointToDeviceFromDevice(unittest.TestCase):
    """The one genuine device-shape exception in this module: group."""

    def test_group_wraps_under_address_group(self):
        result = _endpoint_to_device({"address": "10.0.0.0/8", "group": "GROUP1"})
        self.assertEqual(result, {"address": "10.0.0.0/8", "group": {"address-group": "GROUP1"}})

    def test_no_group_no_exception_applied(self):
        result = _endpoint_to_device({"address": "10.0.0.0/8", "port": "80"})
        self.assertEqual(result, {"address": "10.0.0.0/8", "port": "80"})

    def test_from_device_extracts_group_regardless_of_kind(self):
        """Read side stays generic: it can surface any group kind already
        configured (address-group, network-group, ...), even though
        write side (above) can only ever create address-group."""
        result = _endpoint_from_device({"group": {"network-group": "NETGRP1"}})
        self.assertEqual(result, {"group": "NETGRP1"})

    def test_from_device_bare_string_group(self):
        result = _endpoint_from_device({"group": "GROUP1"})
        self.assertEqual(result, {"group": "GROUP1"})


class TestRulesToDeviceFromDevice(unittest.TestCase):
    def test_bare_rule_is_presence(self):
        self.assertEqual(_rules_to_device([{"number": 10}]), {"10": {}})

    def test_full_rule_with_source_destination(self):
        result = _rules_to_device(
            [
                {
                    "number": 10,
                    "action": "accept",
                    "protocol": "tcp",
                    "source": {"address": "192.168.1.0/24"},
                    "destination": {"port": "80"},
                },
            ],
        )
        self.assertEqual(
            result,
            {
                "10": {
                    "action": "accept",
                    "protocol": "tcp",
                    "source": {"address": "192.168.1.0/24"},
                    "destination": {"port": "80"},
                },
            },
        )

    def test_icmp_generic_no_exception_needed(self):
        result = _rules_to_device([{"number": 10, "icmp": {"type": 8, "code": 0}}])
        self.assertEqual(result, {"10": {"icmp": {"type": 8, "code": 0}}})

    def test_from_device_number_cast_and_sorted_numerically(self):
        result = _rules_from_device({"20": {}, "9": {}})
        self.assertEqual([r["number"] for r in result], [9, 20])

    def test_from_device_icmp_cast_to_int(self):
        result = _rules_from_device({"10": {"icmp": {"type": "8", "code": "0"}}})
        self.assertEqual(result[0]["icmp"], {"type": "8", "code": "0"})
        # Note: icmp int-casting happens via cast_by_spec in
        # _device_to_argspec, not in the raw _rules_from_device step --
        # verified separately in TestDeviceToArgspecFixture.


class TestRuleSetToDeviceFromDevice(unittest.TestCase):
    def test_bare_rule_set_is_presence(self):
        self.assertEqual(_rule_set_to_device({"name": "RS1"}), {})

    def test_with_rules(self):
        result = _rule_set_to_device(
            {
                "name": "RS1",
                "default_action": "drop",
                "rules": [{"number": 10, "action": "accept"}],
            },
        )
        self.assertEqual(
            result,
            {"default_action": "drop", "rule": {"10": {"action": "accept"}}},
        )

    def test_from_device(self):
        entry = _rule_set_from_device(
            "RS1",
            {"default-action": "drop", "rule": {"10": {"action": "accept"}}},
        )
        self.assertEqual(entry["name"], "RS1")
        self.assertEqual(entry["default_action"], "drop")
        self.assertEqual(entry["rules"], [{"number": 10, "action": "accept"}])


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device([]), {})
        self.assertEqual(_want_to_device(None), {})

    def test_afi_with_no_rule_sets_omitted(self):
        self.assertEqual(_want_to_device([{"afi": "ipv4", "rule_sets": []}]), {})

    def test_full_config(self):
        config = [
            {
                "afi": "ipv4",
                "rule_sets": [{"name": "RS1", "default_action": "drop"}],
            },
        ]
        self.assertEqual(
            _want_to_device(config),
            {"ipv4": {"RS1": {"default_action": "drop"}}},
        )


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_ipv4_rule_set_with_rules(self):
        raw = get_running_config(self.mock_vyos)
        have = _device_to_argspec(raw)
        ipv4 = next(e for e in have if e["afi"] == "ipv4")
        rs1 = next(r for r in ipv4["rule_sets"] if r["name"] == "RULE-SET1")
        self.assertEqual(rs1["default_action"], "drop")
        rule10 = next(r for r in rs1["rules"] if r["number"] == 10)
        self.assertEqual(rule10["source"], {"address": "192.168.1.0/24"})
        self.assertEqual(rule10["destination"], {"port": "80"})

    def test_ipv6_present(self):
        raw = get_running_config(self.mock_vyos)
        have = _device_to_argspec(raw)
        afis = {e["afi"] for e in have}
        self.assertIn("ipv6", afis)

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), [])
        self.assertEqual(_device_to_argspec(None), [])


class TestBuildCommands(VyOSModuleTestCase):
    def _have_and_raw(self):
        raw = get_running_config(self.mock_vyos)
        have = _device_to_argspec(raw)
        return have, raw

    def test_merged_idempotent_against_own_fixture(self):
        have, raw = self._have_and_raw()
        self.assertEqual(build_commands(have, raw, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have, raw = self._have_and_raw()
        self.assertEqual(build_commands(have, raw, "replaced"), [])

    def test_overridden_idempotent_against_own_fixture(self):
        have, raw = self._have_and_raw()
        self.assertEqual(build_commands(have, raw, "overridden"), [])

    def test_replaced_scoped_to_named_rule_sets_only(self):
        raw = {
            "ipv4": {
                "RS1": {"default-action": "drop", "rule": {"10": {"action": "accept"}}},
                "RS2": {"default-action": "accept"},
            },
        }
        cfg = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "RS1",
                        "default_action": "drop",
                        "rules": [{"number": 10, "action": "accept"}],
                    },
                ],
            },
        ]
        self.assertEqual(build_commands(cfg, raw, "replaced"), [])

    def test_overridden_deletes_omitted_rule_set(self):
        raw = {"ipv4": {"RS1": {"default-action": "drop"}, "RS2": {"default-action": "accept"}}}
        cfg = [{"afi": "ipv4", "rule_sets": [{"name": "RS1", "default_action": "drop"}]}]
        cmds = build_commands(cfg, raw, "overridden")
        self.assertIn(("delete", _BASE + ["ipv4", "name", "RS2"]), cmds)

    def test_overridden_never_touches_sibling_hook_filters(self):
        """Regression test: firewall.ipv4.{input,output,forward} (owned
        by vyos_firewall_interfaces) and firewall.group (owned by
        vyos_firewall_global) must never be touched by this module."""
        raw = {"ipv4": {"RS1": {"default-action": "drop"}}}
        cmds = build_commands([], raw, "overridden")
        self.assertTrue(all("input" not in c[1] and "group" not in c[1] for c in cmds))

    def test_deleted_no_config_deletes_all_present(self):
        raw = {"ipv4": {"RS1": {}}, "ipv6": {"RS6": {}}}
        cmds = build_commands([], raw, "deleted")
        self.assertIn(("delete", _BASE + ["ipv4", "name", "RS1"]), cmds)
        self.assertIn(("delete", _BASE + ["ipv6", "name", "RS6"]), cmds)

    def test_deleted_scoped_to_named_config(self):
        raw = {"ipv4": {"RS1": {}, "RS2": {}}}
        cmds = build_commands([{"afi": "ipv4", "rule_sets": [{"name": "RS1"}]}], raw, "deleted")
        self.assertEqual(cmds, [("delete", _BASE + ["ipv4", "name", "RS1"])])

    def test_collapsed_rule_no_char_iteration_bug(self):
        raw = {"ipv4": {"RS1": {"rule": "10"}}}
        cfg = [{"afi": "ipv4", "rule_sets": [{"name": "RS1", "rules": [{"number": 10}]}]}]
        self.assertEqual(build_commands(cfg, raw, "merged"), [])

    def test_merged_new_rule_with_group(self):
        cfg = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "RS1",
                        "rules": [{"number": 30, "action": "accept", "source": {"group": "G1"}}],
                    },
                ],
            },
        ]
        cmds = build_commands(cfg, {}, "merged")
        self.assertIn(
            (
                "set",
                _BASE
                + ["ipv4", "name", "RS1", "rule", "30", "source", "group", "address-group", "G1"],
            ),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
