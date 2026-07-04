# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_interfaces import (
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
        self.fixture = load_fixture("firewall_interfaces_running.json")

    def _set_afi(self, afi):
        data = self.fixture.get(afi, {})
        self.mock_vyos.get_config = MagicMock(return_value=data)


class TestVyOSFirewallInterfacesGetRunning(VyOSModuleTestCase):

    def test_parses_ipv4_hooks(self):
        self._set_afi("ipv4")
        result = get_running_config(self.mock_vyos)
        ipv4 = next((e for e in result if e["afi"] == "ipv4"), None)
        self.assertIsNotNone(ipv4)
        hook_names = [h["hook"] for h in ipv4["hooks"]]
        self.assertIn("input", hook_names)
        self.assertIn("forward", hook_names)
        self.assertIn("output", hook_names)

    def test_parses_input_rules(self):
        self._set_afi("ipv4")
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        input_hook = next(h for h in ipv4["hooks"] if h["hook"] == "input")
        self.assertEqual(input_hook["default_action"], "accept")
        self.assertEqual(len(input_hook["rules"]), 2)
        r10 = next(r for r in input_hook["rules"] if r["number"] == 10)
        self.assertEqual(r10["action"], "accept")
        self.assertEqual(r10["state"], "established")

    def test_parses_ipv6_hooks(self):
        self._set_afi("ipv6")
        result = get_running_config(self.mock_vyos)
        ipv6 = next((e for e in result if e["afi"] == "ipv6"), None)
        self.assertIsNotNone(ipv6)
        self.assertEqual(ipv6["hooks"][0]["hook"], "input")

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSFirewallInterfacesBuildCommands(unittest.TestCase):

    def _have(self):
        return [
            {
                "afi": "ipv4",
                "hooks": [
                    {
                        "hook": "input",
                        "default_action": "accept",
                        "rules": [
                            {"number": 10, "action": "accept", "state": "established"},
                            {"number": 20, "action": "drop", "state": "invalid"},
                        ],
                    },
                    {"hook": "forward", "default_action": "accept"},
                ],
            },
        ]

    def test_deleted_all(self):
        cmds = build_commands([], self._have(), "deleted")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["ipv4", "input", "filter"], paths)
        self.assertIn(_BASE + ["ipv4", "forward", "filter"], paths)

    def test_deleted_specific(self):
        config = [{"afi": "ipv4", "hooks": [{"hook": "input"}]}]
        cmds = build_commands(config, self._have(), "deleted")
        self.assertIn(("delete", _BASE + ["ipv4", "input", "filter"]), cmds)
        paths = [c[1] for c in cmds]
        self.assertNotIn(_BASE + ["ipv4", "forward", "filter"], paths)

    def test_merged_hook(self):
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {
                        "hook": "input",
                        "default_action": "accept",
                        "rules": [{"number": 10, "action": "accept", "state": "established"}],
                    },
                ],
            },
        ]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", _BASE + ["ipv4", "input", "filter", "default-action", "accept"]),
            cmds,
        )
        self.assertIn(
            ("set", _BASE + ["ipv4", "input", "filter", "rule", "10", "action", "accept"]),
            cmds,
        )

    def test_merged_idempotent(self):
        have = self._have()
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {
                        "hook": "input",
                        "default_action": "accept",
                        "rules": [
                            {"number": 10, "action": "accept", "state": "established"},
                            {"number": 20, "action": "drop", "state": "invalid"},
                        ],
                    },
                    {"hook": "forward", "default_action": "accept"},
                ],
            },
        ]
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_overridden_removes_extra_hook(self):
        have = self._have()
        config = [
            {
                "afi": "ipv4",
                "hooks": [
                    {"hook": "output", "default_action": "accept"},
                ],
            },
        ]
        cmds = build_commands(config, have, "overridden")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["ipv4", "input", "filter"], paths)
        self.assertIn(_BASE + ["ipv4", "forward", "filter"], paths)


if __name__ == "__main__":
    unittest.main()
