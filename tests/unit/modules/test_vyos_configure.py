# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

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


if __name__ == "__main__":
    unittest.main()
