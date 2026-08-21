# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_rules import (
    build_commands,
    get_running_config,
)


_BASE = ["firewall"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("firewall_rules_running.json")

    def _set_afi(self, afi):
        data = self.fixture.get(afi, {})
        self.mock_vyos.get_config = MagicMock(return_value=data)


class TestVyOSFirewallRulesGetRunning(VyOSModuleTestCase):

    def test_parses_ipv4_rule_sets(self):
        self._set_afi("ipv4")
        result = get_running_config(self.mock_vyos)
        ipv4 = next((e for e in result if e["afi"] == "ipv4"), None)
        self.assertIsNotNone(ipv4)
        rs = next(rs for rs in ipv4["rule_sets"] if rs["name"] == "RULE-SET1")
        self.assertEqual(rs["default_action"], "drop")
        self.assertEqual(len(rs["rules"]), 2)
        r10 = next(r for r in rs["rules"] if r["number"] == 10)
        self.assertEqual(r10["action"], "accept")
        self.assertEqual(r10["protocol"], "tcp")
        self.assertEqual(r10["source"]["address"], "192.168.1.0/24")
        self.assertEqual(r10["destination"]["port"], "80")

    def test_parses_rule_state(self):
        self._set_afi("ipv4")
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        rs = ipv4["rule_sets"][0]
        r20 = next(r for r in rs["rules"] if r["number"] == 20)
        self.assertEqual(r20["state"], "invalid")

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSFirewallRulesBuildCommands(unittest.TestCase):

    def _have(self):
        return [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "RULE-SET1",
                        "default_action": "drop",
                        "rules": [
                            {"number": 10, "action": "accept", "protocol": "tcp"},
                            {"number": 20, "action": "drop", "state": "invalid"},
                        ],
                    },
                ],
            },
        ]

    def test_deleted_all(self):
        cmds = build_commands([], self._have(), "deleted")
        self.assertIn(("delete", _BASE), cmds)

    def test_deleted_specific(self):
        config = [{"afi": "ipv4", "rule_sets": [{"name": "RULE-SET1"}]}]
        cmds = build_commands(config, self._have(), "deleted")
        self.assertIn(("delete", _BASE + ["ipv4", "name", "RULE-SET1"]), cmds)

    def test_merged_rule_set(self):
        config = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "NEW-SET",
                        "default_action": "accept",
                        "rules": [{"number": 10, "action": "accept"}],
                    },
                ],
            },
        ]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", _BASE + ["ipv4", "name", "NEW-SET", "default-action", "accept"]),
            cmds,
        )
        self.assertIn(
            ("set", _BASE + ["ipv4", "name", "NEW-SET", "rule", "10", "action", "accept"]),
            cmds,
        )

    def test_merged_rule_with_protocol_and_source(self):
        config = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "RULE-SET1",
                        "rules": [
                            {
                                "number": 10,
                                "action": "accept",
                                "protocol": "tcp",
                                "source": {"address": "10.0.0.0/8"},
                            },
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", _BASE + ["ipv4", "name", "RULE-SET1", "rule", "10", "protocol", "tcp"]),
            cmds,
        )
        self.assertIn(
            (
                "set",
                _BASE
                + [
                    "ipv4",
                    "name",
                    "RULE-SET1",
                    "rule",
                    "10",
                    "source",
                    "address",
                    "10.0.0.0/8",
                ],
            ),
            cmds,
        )

    def test_merged_idempotent(self):
        have = self._have()
        config = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "RULE-SET1",
                        "default_action": "drop",
                        "rules": [
                            {"number": 10, "action": "accept", "protocol": "tcp"},
                            {"number": 20, "action": "drop", "state": "invalid"},
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_overridden_removes_extra_rule_set(self):
        have = self._have()
        config = [
            {
                "afi": "ipv4",
                "rule_sets": [
                    {
                        "name": "NEW-SET",
                        "default_action": "accept",
                        "rules": [{"number": 10, "action": "accept"}],
                    },
                ],
            },
        ]
        cmds = build_commands(config, have, "overridden")
        self.assertIn(
            ("delete", _BASE + ["ipv4", "name", "RULE-SET1"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
