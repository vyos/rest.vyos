# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_bgp_global import (
    build_commands,
    get_running_config,
)


_BASE = ["protocols", "bgp"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("bgp_global_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestVyOSBgpGlobalGetRunning(VyOSModuleTestCase):

    def test_parses_as_number(self):
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["as_number"], 65000)

    def test_parses_parameters(self):
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["parameters"]["router_id"], "192.0.1.1")
        self.assertTrue(result["parameters"]["log_neighbor_changes"])

    def test_parses_neighbors(self):
        result = get_running_config(self.mock_vyos)
        nb_addrs = [n["neighbor_address"] for n in result["neighbors"]]
        self.assertIn("192.0.2.1", nb_addrs)
        self.assertIn("192.0.2.2", nb_addrs)
        nb1 = next(n for n in result["neighbors"] if n["neighbor_address"] == "192.0.2.1")
        self.assertEqual(nb1["remote_as"], 65001)
        self.assertEqual(nb1["description"], "peer1")
        self.assertEqual(nb1["timers"]["holdtime"], 30)
        self.assertEqual(nb1["timers"]["keepalive"], 10)
        nb2 = next(n for n in result["neighbors"] if n["neighbor_address"] == "192.0.2.2")
        self.assertEqual(nb2["ebgp_multihop"], 2)
        self.assertEqual(nb2["update_source"], "eth0")

    def test_parses_peer_groups(self):
        result = get_running_config(self.mock_vyos)
        self.assertEqual(len(result["peer_groups"]), 1)
        self.assertEqual(result["peer_groups"][0]["peer_group"], "PG1")
        self.assertEqual(result["peer_groups"][0]["remote_as"], 65003)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {})


class TestVyOSBgpGlobalBuildCommands(unittest.TestCase):

    def _have(self):
        return {
            "as_number": 65000,
            "parameters": {"router_id": "192.0.1.1"},
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "remote_as": 65001,
                    "description": "peer1",
                },
            ],
            "peer_groups": [{"peer_group": "PG1", "remote_as": 65003}],
        }

    def test_deleted_with_have(self):
        cmds = build_commands({}, self._have(), "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_without_have(self):
        cmds = build_commands({}, {}, "deleted")
        self.assertEqual(cmds, [])

    def test_merged_as_number(self):
        config = {"as_number": 65000}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["system-as", "65000"]), cmds)

    def test_merged_router_id(self):
        config = {"as_number": 65000, "parameters": {"router_id": "192.0.1.1"}}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["parameters", "router-id", "192.0.1.1"]), cmds)

    def test_merged_neighbor(self):
        config = {
            "as_number": 65000,
            "neighbors": [
                {"neighbor_address": "192.0.2.1", "remote_as": 65001},
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["neighbor", "192.0.2.1", "remote-as", "65001"]), cmds)

    def test_merged_neighbor_timers(self):
        config = {
            "as_number": 65000,
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "remote_as": 65001,
                    "timers": {"holdtime": 30, "keepalive": 10},
                },
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["neighbor", "192.0.2.1", "timers", "holdtime", "30"]),
            cmds,
        )
        self.assertIn(
            ("set", _BASE + ["neighbor", "192.0.2.1", "timers", "keepalive", "10"]),
            cmds,
        )

    def test_merged_idempotent(self):
        have = self._have()
        config = {
            "as_number": 65000,
            "parameters": {"router_id": "192.0.1.1"},
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "remote_as": 65001,
                    "description": "peer1",
                },
            ],
            "peer_groups": [{"peer_group": "PG1", "remote_as": 65003}],
        }
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        have = self._have()
        config = {
            "as_number": 65000,
            "parameters": {"router_id": "192.0.1.1"},
            "neighbors": [
                {
                    "neighbor_address": "192.0.2.1",
                    "remote_as": 65001,
                    "description": "peer1",
                },
            ],
            "peer_groups": [{"peer_group": "PG1", "remote_as": 65003}],
        }
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_rebuilds_on_change(self):
        have = self._have()
        config = {"as_number": 65000, "parameters": {"router_id": "192.0.1.2"}}
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds[0], ("delete", _BASE))
        self.assertIn(("set", _BASE + ["parameters", "router-id", "192.0.1.2"]), cmds)

    def test_merged_peer_group(self):
        config = {
            "as_number": 65000,
            "peer_groups": [{"peer_group": "PG1", "remote_as": 65003}],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["peer-group", "PG1", "remote-as", "65003"]), cmds)


if __name__ == "__main__":
    unittest.main()
