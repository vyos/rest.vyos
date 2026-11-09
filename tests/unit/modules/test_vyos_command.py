# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock, patch

from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSRestError
from ansible_collections.vyos.rest.plugins.modules import vyos_command as command_module
from ansible_collections.vyos.rest.plugins.modules.vyos_command import (
    CommandFailed,
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


class TestVyOSCommandFailures(unittest.TestCase):
    """CORE-7: a command the device rejects must fail the task, not hide in stdout."""

    def setUp(self):
        self.vyos = MagicMock()

    def test_a_rejected_command_raises_with_the_earlier_output(self):
        self.vyos.show.side_effect = ["out1", VyOSRestError("Invalid command (HTTP 400)")]
        with self.assertRaises(CommandFailed) as ctx:
            run_commands(self.vyos, ["show version", "show bogus"])
        self.assertEqual(ctx.exception.command, "show bogus")
        self.assertIn("Invalid command", ctx.exception.error)
        self.assertEqual(ctx.exception.stdout, ["out1"])

    def test_the_first_command_failing_leaves_no_output(self):
        self.vyos.show.side_effect = VyOSRestError("boom")
        with self.assertRaises(CommandFailed) as ctx:
            run_commands(self.vyos, ["show version"])
        self.assertEqual(ctx.exception.stdout, [])

    def test_other_exceptions_are_bugs_and_propagate(self):
        self.vyos.show.side_effect = RuntimeError("connection reset")
        with self.assertRaises(RuntimeError):
            run_commands(self.vyos, ["show version"])

    def run_main(self, show_side_effect, **params):
        module = MagicMock()
        module.params = dict(
            {
                "commands": ["show version", "show bogus"],
                "wait_for": None,
                "match": "all",
                "retries": 3,
                "interval": 0,
            },
            **params,
        )
        module.fail_json.side_effect = SystemExit
        self.vyos.show.side_effect = show_side_effect
        with patch.object(command_module, "AnsibleModule", return_value=module):
            with patch.object(command_module, "VyOSModule", return_value=self.vyos):
                try:
                    command_module.main()
                except SystemExit:
                    pass
        return module

    def test_main_fails_the_task_and_keeps_the_output_so_far(self):
        module = self.run_main(["out1", VyOSRestError("Invalid command (HTTP 400)")])
        kwargs = module.fail_json.call_args[1]
        self.assertIn("command failed: show bogus", kwargs["msg"])
        self.assertEqual(kwargs["failed_command"], "show bogus")
        self.assertEqual(kwargs["stdout"], ["out1"])
        module.exit_json.assert_not_called()

    def test_a_rejected_command_is_not_retried(self):
        module = self.run_main(VyOSRestError("boom"), wait_for=["result[0] contains x"])
        self.assertEqual(self.vyos.show.call_count, 1)
        module.fail_json.assert_called_once()

    def test_main_still_succeeds_when_every_command_works(self):
        module = self.run_main(["out1", "out2"])
        module.fail_json.assert_not_called()
        kwargs = module.exit_json.call_args[1]
        self.assertEqual((kwargs["changed"], kwargs["stdout"]), (False, ["out1", "out2"]))


if __name__ == "__main__":
    unittest.main()
