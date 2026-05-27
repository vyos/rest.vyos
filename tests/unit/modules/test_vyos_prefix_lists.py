# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from ansible_collections.vyos.rest.plugins.modules.vyos_prefix_lists import (
    _normalize,
    build_commands,
    get_running_config,
)

from tests.unit.modules.base import VyOSModuleTestCase, load_fixture


class TestVyOSPrefixListsGetRunning(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("prefix_lists_running.json")

    def test_parses_ipv4_prefix_list(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next((e for e in result if e["afi"] == "ipv4"), None)
        self.assertIsNotNone(ipv4)
        pl = next((p for p in ipv4["prefix_lists"] if p["name"] == "AnsibleIPv4PrefixList"), None)
        self.assertIsNotNone(pl)
        self.assertEqual(pl["description"], "PL configured by ansible")

    def test_parses_ipv4_rules(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        pl = ipv4["prefix_lists"][0]
        seqs = [r["sequence"] for r in pl["entries"]]
        self.assertIn(2, seqs)
        self.assertIn(3, seqs)

    def test_parses_ipv4_rule_fields(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        rule2 = next(r for r in ipv4["prefix_lists"][0]["entries"] if r["sequence"] == 2)
        self.assertEqual(rule2["action"], "permit")
        self.assertEqual(rule2["prefix"], "92.168.10.0/26")
        self.assertEqual(rule2["le"], 32)

    def test_parses_ipv6_prefix_lists(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv6 = next((e for e in result if e["afi"] == "ipv6"), None)
        self.assertIsNotNone(ipv6)
        names = [p["name"] for p in ipv6["prefix_lists"]]
        self.assertIn("AllowIPv6Prefix", names)
        self.assertIn("DenyIPv6Prefix", names)

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSPrefixListsNormalize(unittest.TestCase):

    def test_normalize_ipv4(self):
        config = [
            {
                "afi": "ipv4",
                "prefix_lists": [
                    {
                        "name": "PL1",
                        "entries": [{"sequence": 10, "action": "permit", "prefix": "10.0.0.0/8"}],
                    },
                ],
            },
        ]
        result = _normalize(config)
        self.assertIn("PL1", result["ipv4"])
        self.assertIn(10, result["ipv4"]["PL1"]["rules"])
        self.assertEqual(result["ipv4"]["PL1"]["rules"][10]["action"], "permit")

    def test_normalize_filters_none_values(self):
        config = [
            {
                "afi": "ipv4",
                "prefix_lists": [
                    {
                        "name": "PL1",
                        "entries": [
                            {
                                "sequence": 10,
                                "action": "permit",
                                "prefix": "10.0.0.0/8",
                                "ge": None,
                                "le": None,
                            },
                        ],
                    },
                ],
            },
        ]
        result = _normalize(config)
        rule = result["ipv4"]["PL1"]["rules"][10]
        self.assertNotIn("ge", rule)
        self.assertNotIn("le", rule)


class TestVyOSPrefixListsBuildCommands(unittest.TestCase):

    def _have_empty(self):
        return []

    def _have_with_ipv4_pl(self):
        return [
            {
                "afi": "ipv4",
                "prefix_lists": [
                    {
                        "name": "PL1",
                        "entries": [
                            {
                                "sequence": 10,
                                "action": "permit",
                                "prefix": "10.0.0.0/8",
                            },
                        ],
                    },
                ],
            },
        ]

    def test_merged_adds_new_prefix_list(self):
        config = [
            {
                "afi": "ipv4",
                "prefix_lists": [
                    {
                        "name": "PL-NEW",
                        "entries": [
                            {
                                "sequence": 5,
                                "action": "permit",
                                "prefix": "192.168.0.0/24",
                            },
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, self._have_empty(), "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(["policy", "prefix-list", "PL-NEW", "rule", "5", "action", "permit"], paths)
        self.assertIn(
            ["policy", "prefix-list", "PL-NEW", "rule", "5", "prefix", "192.168.0.0/24"],
            paths,
        )

    def test_merged_idempotent_existing_rule(self):
        config = self._have_with_ipv4_pl()
        cmds = build_commands(config, self._have_with_ipv4_pl(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_deletes_all(self):
        cmds = build_commands([], self._have_with_ipv4_pl(), "deleted")
        self.assertIn(("delete", ["policy", "prefix-list"]), cmds)

    def test_deleted_with_config_deletes_named(self):
        config = [{"afi": "ipv4", "prefix_lists": [{"name": "PL1"}]}]
        cmds = build_commands(config, self._have_with_ipv4_pl(), "deleted")
        self.assertIn(("delete", ["policy", "prefix-list", "PL1"]), cmds)

    def test_replaced_deletes_then_resets(self):
        config = [
            {
                "afi": "ipv4",
                "prefix_lists": [
                    {
                        "name": "PL1",
                        "entries": [
                            {
                                "sequence": 10,
                                "action": "deny",
                                "prefix": "10.0.0.0/8",
                            },
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, self._have_with_ipv4_pl(), "replaced")
        # Should delete PL1 first then re-add
        ops = [(c[0], c[1]) for c in cmds]
        delete_idx = next(
            i for i, c in enumerate(ops) if c == ("delete", ["policy", "prefix-list", "PL1"])
        )
        set_idx = next(i for i, c in enumerate(ops) if c[0] == "set" and "deny" in c[1])
        self.assertLess(delete_idx, set_idx)


if __name__ == "__main__":
    unittest.main()
