# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_facts import (
    gather_bgp,
    gather_hostname,
    gather_interfaces,
    gather_logging,
    gather_users,
)


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class TestVyOSFactsGather(unittest.TestCase):

    def setUp(self):
        self.mock_vyos = MagicMock()
        self.system_fixture = load_fixture("facts_system.json")
        self.interfaces_fixture = load_fixture("facts_interfaces.json")

    def test_gather_hostname(self):
        self.mock_vyos.get_config = MagicMock(return_value=self.system_fixture)
        result = gather_hostname(self.mock_vyos)
        self.assertEqual(result, "vyos-test")

    def test_gather_hostname_empty(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = gather_hostname(self.mock_vyos)
        self.assertEqual(result, "")

    def test_gather_interfaces(self):
        self.mock_vyos.get_config = MagicMock(return_value=self.interfaces_fixture)
        result = gather_interfaces(self.mock_vyos)
        self.assertIn("ethernet", result)
        self.assertIn("eth0", result["ethernet"])
        self.assertIn("eth1", result["ethernet"])
        self.assertEqual(result["ethernet"]["eth1"]["description"], "uplink")

    def test_gather_users(self):
        self.mock_vyos.get_config = MagicMock(
            return_value=self.system_fixture["login"],
        )
        result = gather_users(self.mock_vyos)
        names = [u["name"] for u in result]
        self.assertIn("vyos", names)
        self.assertIn("alice", names)
        alice = next(u for u in result if u["name"] == "alice")
        self.assertEqual(alice["full_name"], "Alice Smith")
        self.assertIn("alice-key", alice["public_keys"])

    def test_gather_users_empty(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = gather_users(self.mock_vyos)
        self.assertEqual(result, [])

    def test_gather_users_none(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        result = gather_users(self.mock_vyos)
        self.assertEqual(result, [])

    def test_gather_bgp(self):
        data = {"system-as": "65000", "parameters": {"router-id": "192.0.1.1"}}
        self.mock_vyos.get_config = MagicMock(return_value=data)
        result = gather_bgp(self.mock_vyos)
        self.assertEqual(result["system-as"], "65000")
        self.assertEqual(result["parameters"]["router-id"], "192.0.1.1")

    def test_gather_bgp_empty(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = gather_bgp(self.mock_vyos)
        self.assertEqual(result, {})

    def test_gather_logging(self):
        self.mock_vyos.get_config = MagicMock(
            return_value=self.system_fixture["syslog"],
        )
        result = gather_logging(self.mock_vyos)
        self.assertIn("local", result)
        self.assertIn("console", result)


if __name__ == "__main__":
    unittest.main()
