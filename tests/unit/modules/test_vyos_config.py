# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_config import (
    filter_commands,
    parse_commands,
    parse_line,
)


class TestVyOSConfigParseLine(unittest.TestCase):

    def test_set_single_value(self):
        op, path = parse_line("set system host-name router1")
        self.assertEqual(op, "set")
        self.assertEqual(path, ["system", "host-name", "router1"])

    def test_delete(self):
        op, path = parse_line("delete protocols bgp")
        self.assertEqual(op, "delete")
        self.assertEqual(path, ["protocols", "bgp"])

    def test_quoted_value(self):
        op, path = parse_line('set interfaces ethernet eth0 description "My WAN"')
        self.assertEqual(op, "set")
        self.assertEqual(path, ["interfaces", "ethernet", "eth0", "description", "My WAN"])

    def test_blank_line(self):
        self.assertIsNone(parse_line(""))

    def test_comment_line(self):
        self.assertIsNone(parse_line("# this is a comment"))

    def test_whitespace_only(self):
        self.assertIsNone(parse_line("   "))

    def test_invalid_op(self):
        self.assertIsNone(parse_line("get system host-name"))


class TestVyOSConfigParseCommands(unittest.TestCase):

    def test_mixed_lines(self):
        lines = [
            "# comment",
            "",
            "set system host-name router1",
            "delete protocols bgp",
        ]
        result = parse_commands(lines)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("set", ["system", "host-name", "router1"]))
        self.assertEqual(result[1], ("delete", ["protocols", "bgp"]))


class TestVyOSConfigFilterCommands(unittest.TestCase):

    def setUp(self):
        self.mock_vyos = MagicMock()

    def test_set_already_exists(self):
        # API returns {"host-name": "router1"} for path ["system", "host-name"]
        self.mock_vyos.get_config = MagicMock(
            return_value={"host-name": "router1"},
        )
        cmds = [("set", ["system", "host-name", "router1"])]
        result = filter_commands(cmds, self.mock_vyos)
        self.assertEqual(result, [])

    def test_set_different_value(self):
        self.mock_vyos.get_config = MagicMock(
            return_value={"host-name": "old-name"},
        )
        cmds = [("set", ["system", "host-name", "new-name"])]
        result = filter_commands(cmds, self.mock_vyos)
        self.assertEqual(len(result), 1)

    def test_set_not_present(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        cmds = [("set", ["system", "host-name", "router1"])]
        result = filter_commands(cmds, self.mock_vyos)
        self.assertEqual(len(result), 1)

    def test_delete_exists(self):
        self.mock_vyos.get_config = MagicMock(
            return_value={"description": "some desc"},
        )
        cmds = [("delete", ["interfaces", "ethernet", "eth0", "description"])]
        result = filter_commands(cmds, self.mock_vyos)
        self.assertEqual(len(result), 1)

    def test_delete_not_exists(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        cmds = [("delete", ["interfaces", "ethernet", "eth0", "description"])]
        result = filter_commands(cmds, self.mock_vyos)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
