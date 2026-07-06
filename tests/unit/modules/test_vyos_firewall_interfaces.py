# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_interfaces import (
    _device_to_argspec,
    _hook_filter_from_device,
    _hook_filter_to_device,
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
        self.fixture = load_fixture("firewall_interfaces_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_single_combined_fetch(self):
        """Confirm get_running_config fetches once at _BASE, not per-AFI."""
        get_running_config(self.mock_vyos)
        self.mock_vyos.get_config.assert_called_once_with(_BASE)

    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestRulesToDeviceFromDevice(unittest.TestCase):
    def test_bare_rule_is_presence(self):
        self.assertEqual(_rules_to_device([{"number": 10}]), {"10": {}})

    def test_full_rule(self):
        result = _rules_to_device(
            [
                {
                    "number": 20,
                    "action": "drop",
                    "state": "invalid",
                    "source": {"address": "10.0.0.0/8"},
                    "disable": True,
                },
            ],
        )
        self.assertEqual(
            result,
            {
                "20": {
                    "action": "drop",
                    "state": "invalid",
                    "source": {"address": "10.0.0.0/8"},
                    "disable": {},
                },
            },
        )

    def test_from_device_number_cast_to_int(self):
        result = _rules_from_device({"10": {"action": "accept"}})
        self.assertEqual(result, [{"number": 10, "action": "accept"}])

    def test_from_device_sorted_numerically_not_lexically(self):
        result = _rules_from_device({"20": {}, "9": {}, "100": {}})
        self.assertEqual([r["number"] for r in result], [9, 20, 100])

    def test_source_destination_round_trip(self):
        raw = {"20": {"source": {"address": "10.0.0.0/8"}, "destination": {"port": "22"}}}
        result = _rules_from_device(raw)
        self.assertEqual(result[0]["source"], {"address": "10.0.0.0/8"})
        self.assertEqual(result[0]["destination"], {"port": "22"})


class TestHookFilterToDeviceFromDevice(unittest.TestCase):
    def test_bare_hook_is_presence(self):
        self.assertEqual(_hook_filter_to_device({"hook": "input"}), {})

    def test_default_action_and_description(self):
        result = _hook_filter_to_device(
            {"hook": "input", "default_action": "accept", "description": "desc"},
        )
        self.assertEqual(result, {"default_action": "accept", "description": "desc"})

    def test_with_rules(self):
        result = _hook_filter_to_device(
            {"hook": "input", "rules": [{"number": 10, "action": "accept"}]},
        )
        self.assertEqual(result, {"rule": {"10": {"action": "accept"}}})

    def test_from_device_basic(self):
        entry = _hook_filter_from_device("input", {"default-action": "accept"})
        self.assertEqual(entry, {"hook": "input", "default_action": "accept"})

    def test_from_device_with_rules(self):
        entry = _hook_filter_from_device(
            "input",
            {"default-action": "accept", "rule": {"10": {"action": "accept"}}},
        )
        self.assertEqual(entry["default_action"], "accept")
        self.assertEqual(entry["rules"], [{"number": 10, "action": "accept"}])


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device([]), {})
        self.assertEqual(_want_to_device(None), {})

    def test_afi_with_no_hooks_omitted(self):
        self.assertEqual(_want_to_device([{"afi": "ipv4", "hooks": []}]), {})

    def test_full_config(self):
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {"hook": "input", "default_action": "accept"},
                ],
            },
        ]
        result = _want_to_device(config)
        self.assertEqual(
            result,
            {"ipv4": {"input": {"filter": {"default_action": "accept"}}}},
        )


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_ipv4_input_with_rules(self):
        have = _device_to_argspec(self.fixture)
        ipv4 = next(e for e in have if e["afi"] == "ipv4")
        input_hook = next(h for h in ipv4["hooks"] if h["hook"] == "input")
        self.assertEqual(input_hook["default_action"], "accept")
        rule20 = next(r for r in input_hook["rules"] if r["number"] == 20)
        self.assertEqual(rule20["source"], {"address": "10.0.0.0/8"})
        self.assertEqual(rule20["destination"], {"port": "22"})

    def test_sibling_module_data_never_surfaces(self):
        """Regression test: firewall.ipv4.name (owned by
        vyos_firewall_rules) must never appear in this module's output."""
        have = _device_to_argspec(self.fixture)
        ipv4 = next(e for e in have if e["afi"] == "ipv4")
        hook_names = {h["hook"] for h in ipv4["hooks"]}
        self.assertEqual(hook_names, {"input", "forward", "output"})

    def test_ipv6_present(self):
        have = _device_to_argspec(self.fixture)
        afis = {e["afi"] for e in have}
        self.assertIn("ipv6", afis)

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

    def test_replaced_scoped_to_named_hooks_only(self):
        """replaced only touches hooks explicitly named in config -- an
        omitted hook (output here) must be left alone."""
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {
                        "hook": "input",
                        "default_action": "accept",
                        "rules": [
                            {"number": 10, "action": "accept", "state": "established"},
                            {
                                "number": 20,
                                "action": "drop",
                                "state": "invalid",
                                "source": {"address": "10.0.0.0/8"},
                                "destination": {"port": "22"},
                            },
                        ],
                    },
                ],
            },
        ]
        self.assertEqual(build_commands(config, self.fixture, "replaced"), [])

    def test_overridden_deletes_omitted_hook(self):
        """overridden is full-model: an omitted hook must be deleted."""
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {
                        "hook": "input",
                        "default_action": "accept",
                        "rules": [
                            {"number": 10, "action": "accept", "state": "established"},
                            {
                                "number": 20,
                                "action": "drop",
                                "state": "invalid",
                                "source": {"address": "10.0.0.0/8"},
                                "destination": {"port": "22"},
                            },
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, self.fixture, "overridden")
        self.assertIn(("delete", _BASE + ["ipv4", "output", "filter"]), cmds)
        self.assertIn(("delete", _BASE + ["ipv4", "forward", "filter"]), cmds)
        self.assertIn(("delete", _BASE + ["ipv6", "input", "filter"]), cmds)

    def test_overridden_never_touches_sibling_ruleset(self):
        cmds = build_commands([], self.fixture, "overridden")
        self.assertTrue(all("name" not in c[1] for c in cmds))

    def test_deleted_never_touches_sibling_ruleset(self):
        cmds = build_commands([], self.fixture, "deleted")
        self.assertTrue(all("name" not in c[1] for c in cmds))
        self.assertIn(("delete", _BASE + ["ipv4", "input", "filter"]), cmds)

    def test_deleted_scoped_to_named_config(self):
        cmds = build_commands(
            [{"afi": "ipv4", "hooks": [{"hook": "input"}]}],
            self.fixture,
            "deleted",
        )
        self.assertEqual(cmds, [("delete", _BASE + ["ipv4", "input", "filter"])])

    def test_collapsed_rule_no_char_iteration_bug(self):
        """A single rule with no other config collapsed to a bare string
        by the device must not be iterated character-by-character."""
        raw_have = {"ipv4": {"input": {"filter": {"rule": "10"}}}}
        config = [{"afi": "ipv4", "hooks": [{"hook": "input", "rules": [{"number": 10}]}]}]
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_merged_new_rule(self):
        cmds = build_commands(
            [
                {
                    "afi": "ipv4",
                    "hooks": [{"hook": "input", "rules": [{"number": 30, "action": "accept"}]}],
                },
            ],
            self.fixture,
            "merged",
        )
        self.assertIn(
            ("set", _BASE + ["ipv4", "input", "filter", "rule", "30", "action", "accept"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
