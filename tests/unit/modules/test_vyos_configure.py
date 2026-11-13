# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock, patch

from ansible_collections.vyos.rest.plugins.modules import vyos_configure as configure_module
from ansible_collections.vyos.rest.plugins.modules.vyos_configure import (
    _parse_command,
)


class TestVyOSConfigureParseCommand(unittest.TestCase):

    def test_set_simple(self):
        result = _parse_command("set system host-name vyos")
        self.assertEqual(result, ("set", ["system", "host-name", "vyos"]))

    def test_set_with_address(self):
        result = _parse_command("set interfaces loopback lo address 20.1.1.1/32")
        self.assertEqual(
            result,
            ("set", ["interfaces", "loopback", "lo", "address", "20.1.1.1/32"]),
        )

    def test_delete_simple(self):
        result = _parse_command("delete service snmp")
        self.assertEqual(result, ("delete", ["service", "snmp"]))

    def test_delete_with_path(self):
        result = _parse_command("delete interfaces loopback lo address 20.1.1.1/32")
        self.assertEqual(
            result,
            ("delete", ["interfaces", "loopback", "lo", "address", "20.1.1.1/32"]),
        )

    def test_strips_leading_whitespace(self):
        result = _parse_command("  set system host-name vyos")
        self.assertEqual(result, ("set", ["system", "host-name", "vyos"]))

    def test_invalid_command_returns_none(self):
        result = _parse_command("commit")
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        result = _parse_command("")
        self.assertIsNone(result)

    def test_unknown_op_returns_none(self):
        result = _parse_command("show interfaces")
        self.assertIsNone(result)

    def test_set_single_token_path(self):
        result = _parse_command("set service")
        self.assertEqual(result, ("set", ["service"]))

    def test_delete_single_token_path(self):
        result = _parse_command("delete service")
        self.assertEqual(result, ("delete", ["service"]))


class TestVyOSConfigureQuoting(unittest.TestCase):
    """CORE-6: quoted values are one path element and the quotes are not part of the value."""

    def test_double_quoted_value_with_spaces_is_one_element(self):
        result = _parse_command('set interfaces ethernet eth0 description "WAN link"')
        self.assertEqual(
            result,
            ("set", ["interfaces", "ethernet", "eth0", "description", "WAN link"]),
        )

    def test_single_quoted_value_with_spaces_is_one_element(self):
        result = _parse_command("set system login banner pre-login 'Authorized use only'")
        self.assertEqual(
            result,
            ("set", ["system", "login", "banner", "pre-login", "Authorized use only"]),
        )

    def test_quotes_are_not_part_of_a_single_word_value(self):
        result = _parse_command("set service snmp contact 'noc@example.com'")
        self.assertEqual(result, ("set", ["service", "snmp", "contact", "noc@example.com"]))

    def test_delete_with_a_quoted_value(self):
        result = _parse_command('delete interfaces ethernet eth0 description "WAN link"')
        self.assertEqual(
            result,
            ("delete", ["interfaces", "ethernet", "eth0", "description", "WAN link"]),
        )

    def test_repeated_spaces_and_tabs_between_words_are_tolerated(self):
        result = _parse_command("set   system \t host-name    vyos")
        self.assertEqual(result, ("set", ["system", "host-name", "vyos"]))

    def test_an_unclosed_quote_raises(self):
        with self.assertRaises(ValueError):
            _parse_command('set system description "oops')

    def test_an_op_without_a_path_is_invalid(self):
        self.assertIsNone(_parse_command("set"))
        self.assertIsNone(_parse_command("delete   "))


class TestVyOSConfigureMain(unittest.TestCase):
    def run_main(self, commands, save=False, save_result=True, check_mode=False):
        module = MagicMock()
        module.params = {"commands": commands, "save": save}
        module.check_mode = check_mode
        module.fail_json.side_effect = SystemExit
        module.exit_json.side_effect = SystemExit
        vyos = MagicMock()
        vyos.save_config.return_value = save_result
        with patch.object(configure_module, "AnsibleModule", return_value=module):
            with patch.object(configure_module, "VyOSModule", return_value=vyos):
                try:
                    configure_module.main()
                except SystemExit:
                    pass
        return module, vyos

    def test_a_quoted_value_reaches_the_device_as_one_element(self):
        _module, vyos = self.run_main(['set interfaces ethernet eth0 description "WAN link"'])
        vyos.apply_commands.assert_called_once_with(
            [("set", ["interfaces", "ethernet", "eth0", "description", "WAN link"])],
        )

    def test_an_unclosed_quote_fails_and_applies_nothing(self):
        module, vyos = self.run_main(['set system description "oops'])
        self.assertIn(
            "Invalid command 'set system description \"oops'",
            module.fail_json.call_args[1]["msg"],
        )
        vyos.apply_commands.assert_not_called()

    def test_a_failed_save_fails_the_task_after_the_commands_were_applied(self):
        module, vyos = self.run_main(["set system host-name vyos"], save=True, save_result=False)
        vyos.apply_commands.assert_called_once()
        kwargs = module.fail_json.call_args[1]
        self.assertIs(kwargs["changed"], True)
        self.assertIn("saving the configuration failed", kwargs["msg"])
        self.assertEqual(kwargs["commands"], [("set", ["system", "host-name", "vyos"])])
        module.exit_json.assert_not_called()

    def test_a_successful_save_succeeds(self):
        module, vyos = self.run_main(["set system host-name vyos"], save=True)
        vyos.save_config.assert_called_once()
        module.fail_json.assert_not_called()
        self.assertIs(module.exit_json.call_args[1]["changed"], True)

    def test_save_is_not_called_unless_requested(self):
        _module, vyos = self.run_main(["set system host-name vyos"], save=False)
        vyos.save_config.assert_not_called()

    def test_check_mode_applies_and_saves_nothing(self):
        module, vyos = self.run_main(["set system host-name vyos"], save=True, check_mode=True)
        vyos.apply_commands.assert_not_called()
        vyos.save_config.assert_not_called()
        self.assertIs(module.exit_json.call_args[1]["changed"], True)


if __name__ == "__main__":
    unittest.main()
