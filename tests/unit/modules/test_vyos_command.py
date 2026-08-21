# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_command import (
    evaluate_conditions,
    parse_command,
    run_commands,
)


class TestVyOSCommandParseCommand(unittest.TestCase):

    def test_string_single_word(self):
        self.assertEqual(parse_command("version"), ["version"])

    def test_string_multi_word(self):
        self.assertEqual(parse_command("ip route"), ["ip", "route"])

    def test_list_passthrough(self):
        self.assertEqual(parse_command(["ip", "route"]), ["ip", "route"])


class TestVyOSCommandEvaluateConditions(unittest.TestCase):

    def _stdout(self):
        return ["VyOS 1.5.0 output", "eth0  192.168.1.1"]

    def test_contains_match(self):
        failed, conds = evaluate_conditions(
            self._stdout(),
            ["result[0] contains VyOS"],
            "all",
        )
        self.assertFalse(failed)
        self.assertEqual(conds, [])

    def test_contains_no_match(self):
        failed, conds = evaluate_conditions(
            self._stdout(),
            ["result[0] contains NonExistent"],
            "all",
        )
        self.assertTrue(failed)
        self.assertIn("result[0] contains NonExistent", conds)

    def test_match_all_both_pass(self):
        failed, conditions = evaluate_conditions(
            self._stdout(),
            ["result[0] contains VyOS", "result[1] contains eth0"],
            "all",
        )
        self.assertFalse(failed)

    def test_match_all_one_fails(self):
        failed, conditions = evaluate_conditions(
            self._stdout(),
            ["result[0] contains VyOS", "result[1] contains NonExistent"],
            "all",
        )
        self.assertTrue(failed)

    def test_match_any_one_passes(self):
        failed, conditions = evaluate_conditions(
            self._stdout(),
            ["result[0] contains VyOS", "result[1] contains NonExistent"],
            "any",
        )
        self.assertFalse(failed)

    def test_empty_conditions(self):
        failed, conds = evaluate_conditions(self._stdout(), [], "all")
        self.assertFalse(failed)
        self.assertEqual(conds, [])


class TestVyOSCommandRunCommands(unittest.TestCase):

    def setUp(self):
        self.mock_vyos = MagicMock()

    def test_run_list_command(self):
        self.mock_vyos.show = MagicMock(return_value="VyOS 1.5.0")
        result = run_commands(self.mock_vyos, [["version"]])
        self.mock_vyos.show.assert_called_once_with(["version"])
        self.assertEqual(result, ["VyOS 1.5.0"])

    def test_run_string_command(self):
        self.mock_vyos.show = MagicMock(return_value="uptime")
        run_commands(self.mock_vyos, ["system uptime"])
        self.mock_vyos.show.assert_called_once_with(["system", "uptime"])

    def test_run_multiple_commands(self):
        self.mock_vyos.show = MagicMock(side_effect=["out1", "out2"])
        result = run_commands(self.mock_vyos, [["version"], ["interfaces"]])
        self.assertEqual(result, ["out1", "out2"])

    def test_run_none_returns_empty_string(self):
        self.mock_vyos.show = MagicMock(return_value=None)
        result = run_commands(self.mock_vyos, [["version"]])
        self.assertEqual(result, [""])


if __name__ == "__main__":
    unittest.main()
