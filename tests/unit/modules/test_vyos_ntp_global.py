# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import os
import sys
import unittest


# Allow importing collection modules without full ansible-test runner
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from ansible_collections.vyos.rest.plugins.modules.vyos_ntp_global import (
    build_commands,
    get_running_config,
    normalize_config,
    normalize_servers,
)

from tests.unit.modules.base import VyOSModuleTestCase, load_fixture


class TestVyOSNtpGlobalNormalize(unittest.TestCase):
    """Test normalize_config and normalize_servers — no device needed."""

    def test_normalize_config_empty(self):
        result = normalize_config({})
        self.assertEqual(result["allow_clients"], [])
        self.assertEqual(result["listen_addresses"], [])
        self.assertEqual(result["servers"], {})

    def test_normalize_config_servers_sorted(self):
        config = {
            "servers": [
                {"server": "b.example.com", "options": ["prefer", "noselect"]},
                {"server": "a.example.com"},
            ],
        }
        result = normalize_config(config)
        self.assertIn("a.example.com", result["servers"])
        self.assertIn("b.example.com", result["servers"])
        self.assertEqual(result["servers"]["b.example.com"], ["noselect", "prefer"])

    def test_normalize_servers_dict_with_options(self):
        raw = {
            "time1.vyos.net": {},
            "203.0.113.0": {"prefer": {}},
        }
        result = normalize_servers(raw)
        self.assertEqual(result["time1.vyos.net"], [])
        self.assertEqual(result["203.0.113.0"], ["prefer"])

    def test_normalize_servers_list(self):
        raw = ["time1.vyos.net", "time2.vyos.net"]
        result = normalize_servers(raw)
        self.assertEqual(result["time1.vyos.net"], [])

    def test_normalize_servers_string(self):
        result = normalize_servers("time1.vyos.net")
        self.assertEqual(result["time1.vyos.net"], [])


class TestVyOSNtpGlobalGetRunning(VyOSModuleTestCase):
    """Test get_running_config parsing against fixture API responses."""

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("ntp_global_running.json")

    def test_parses_allow_clients(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        self.assertIn("10.6.6.0/24", result["allow_clients"])

    def test_parses_listen_addresses(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        self.assertIn("10.1.3.1", result["listen_addresses"])

    def test_parses_servers(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        self.assertIn("time1.vyos.net", result["servers"])
        self.assertIn("203.0.113.0", result["servers"])
        self.assertIn("prefer", result["servers"]["203.0.113.0"])

    def test_empty_config_returns_empty(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["allow_clients"], [])
        self.assertEqual(result["servers"], {})


class TestVyOSNtpGlobalBuildCommands(unittest.TestCase):
    """Test build_commands diff logic — no device needed."""

    def _have(self, **kwargs):
        base = {"allow_clients": [], "listen_addresses": [], "servers": {}}
        base.update(kwargs)
        return base

    def _want(self, **kwargs):
        return self._have(**kwargs)

    def test_merged_adds_new_server(self):
        want = self._want(servers={"new.server.com": []})
        have = self._have(servers={})
        cmds = build_commands(want, have, "merged")
        self.assertIn(("set", ["service", "ntp", "server", "new.server.com"]), cmds)

    def test_merged_idempotent_existing_server(self):
        want = self._want(servers={"time1.vyos.net": []})
        have = self._have(servers={"time1.vyos.net": []})
        cmds = build_commands(want, have, "merged")
        self.assertEqual(cmds, [])

    def test_merged_adds_server_option(self):
        want = self._want(servers={"time1.vyos.net": ["prefer"]})
        have = self._have(servers={"time1.vyos.net": []})
        cmds = build_commands(want, have, "merged")
        self.assertIn(("set", ["service", "ntp", "server", "time1.vyos.net", "prefer"]), cmds)

    def test_replaced_removes_extra_server(self):
        want = self._want(servers={"time1.vyos.net": []})
        have = self._have(servers={"time1.vyos.net": [], "time2.vyos.net": []})
        cmds = build_commands(want, have, "replaced")
        self.assertIn(("delete", ["service", "ntp", "server", "time2.vyos.net"]), cmds)

    def test_replaced_removes_extra_allow_client(self):
        want = self._want(allow_clients=["10.1.0.0/24"])
        have = self._have(allow_clients=["10.1.0.0/24", "10.2.0.0/24"])
        cmds = build_commands(want, have, "replaced")
        self.assertIn(
            ("delete", ["service", "ntp", "allow-client", "address", "10.2.0.0/24"]),
            cmds,
        )

    def test_deleted_removes_all(self):
        want = self._want(servers={}, allow_clients=[], listen_addresses=[])
        have = self._have(
            servers={"time1.vyos.net": []},
            allow_clients=["10.0.0.0/24"],
            listen_addresses=["192.168.1.1"],
        )
        cmds = build_commands(want, have, "deleted")
        paths = [c[1] for c in cmds]
        self.assertIn(["service", "ntp", "server", "time1.vyos.net"], paths)
        self.assertIn(["service", "ntp", "allow-client", "address", "10.0.0.0/24"], paths)

    def test_overridden_deletes_then_merges(self):
        want = self._want(servers={"new.server.com": []})
        have = self._have(servers={"old.server.com": []})
        cmds = build_commands(want, have, "overridden")
        paths = [c[1] for c in cmds]
        # overridden deletes existing server subtree first
        self.assertIn(["service", "ntp", "server"], paths)
        # then adds new server
        self.assertIn(["service", "ntp", "server", "new.server.com"], paths)

    def test_no_commands_when_already_correct(self):
        state = {"allow_clients": ["10.0.0.0/24"], "listen_addresses": [], "servers": {}}
        cmds = build_commands(state, state, "merged")
        self.assertEqual(cmds, [])


if __name__ == "__main__":
    unittest.main()
