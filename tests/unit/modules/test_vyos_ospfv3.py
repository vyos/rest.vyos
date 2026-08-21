# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospfv3 import (
    build_commands,
    get_running_config,
)


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.mock_vyos.get_config = MagicMock(return_value={})

    def set_running_config(self, data):
        self.mock_vyos.get_config.return_value = data


class TestVyOSOspfv3Parse(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("ospfv3_running.json")

    def test_parses_parameters(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["parameters"]["router_id"], "192.0.2.10")

    def test_parses_redistribute(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        route_types = [r["route_type"] for r in result["redistribute"]]
        self.assertIn("bgp", route_types)
        self.assertIn("connected", route_types)
        connected = next(r for r in result["redistribute"] if r["route_type"] == "connected")
        self.assertEqual(connected["route_map"], "RM1")

    def test_parses_areas(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        self.assertEqual(len(result["areas"]), 2)
        area2 = next(a for a in result["areas"] if a["area_id"] == "2")
        self.assertEqual(area2["export_list"], "export1")
        self.assertEqual(area2["import_list"], "import1")
        self.assertEqual(len(area2["range"]), 2)
        not_adv = next(r for r in area2["range"] if r["address"] == "2001:db20::/32")
        self.assertTrue(not_adv["not_advertise"])

    def test_empty_config_returns_empty(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {})


class TestVyOSOspfv3BuildCommands(unittest.TestCase):

    def test_deleted_with_have(self):
        have = {"parameters": {"router_id": "192.0.2.10"}}
        cmds = build_commands({}, have, "deleted")
        self.assertEqual(cmds, [("delete", ["protocols", "ospfv3"])])

    def test_deleted_without_have(self):
        cmds = build_commands({}, {}, "deleted")
        self.assertEqual(cmds, [])

    def test_merged_parameters(self):
        config = {"parameters": {"router_id": "192.0.2.10"}}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", ["protocols", "ospfv3", "parameters", "router-id", "192.0.2.10"]),
            cmds,
        )

    def test_merged_redistribute(self):
        config = {"redistribute": [{"route_type": "bgp"}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", ["protocols", "ospfv3", "redistribute", "bgp"]),
            cmds,
        )

    def test_merged_idempotent(self):
        config = {"parameters": {"router_id": "192.0.2.10"}}
        have = {"parameters": {"router_id": "192.0.2.10"}}
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_merged_area_range(self):
        config = {
            "areas": [{"area_id": "2", "range": [{"address": "2001:db10::/32"}]}],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", ["protocols", "ospfv3", "area", "2", "range", "2001:db10::/32"]),
            cmds,
        )

    def test_replaced_idempotent(self):
        config = {"parameters": {"router_id": "192.0.2.10"}}
        have = {"parameters": {"router_id": "192.0.2.10"}}
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_rebuilds_on_change(self):
        config = {"parameters": {"router_id": "192.0.2.11"}}
        have = {"parameters": {"router_id": "192.0.2.10"}}
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds[0], ("delete", ["protocols", "ospfv3"]))
        self.assertIn(
            ("set", ["protocols", "ospfv3", "parameters", "router-id", "192.0.2.11"]),
            cmds,
        )

    def test_merged_area_export_list(self):
        config = {"areas": [{"area_id": "2", "export_list": "export1"}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", ["protocols", "ospfv3", "area", "2", "export-list", "export1"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
