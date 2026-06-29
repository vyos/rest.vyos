# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ospfv2 import (
    _parse_areas,
    _parse_default_information,
    _parse_neighbor,
    _parse_parameters,
    _parse_redistribute,
    build_commands,
    get_running_config,
)


_BASE = ["protocols", "ospf"]


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    with open(os.path.join(fixtures_dir, filename)) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("ospfv2_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestVyOSOspfv2Parse(VyOSModuleTestCase):

    def test_parse_parameters(self):
        result = _parse_parameters(self.fixture["parameters"])
        self.assertEqual(result["router_id"], "192.0.1.1")
        self.assertEqual(result["abr_type"], "cisco")
        self.assertTrue(result["opaque_lsa"])
        self.assertTrue(result["rfc1583_compatibility"])

    def test_parse_redistribute(self):
        result = _parse_redistribute(self.fixture["redistribute"])
        route_types = [r["route_type"] for r in result]
        self.assertIn("bgp", route_types)
        self.assertIn("connected", route_types)
        bgp = next(r for r in result if r["route_type"] == "bgp")
        self.assertEqual(bgp["metric"], 10)
        self.assertEqual(bgp["metric_type"], 2)

    def test_parse_neighbor(self):
        result = _parse_neighbor(self.fixture["neighbor"])
        self.assertEqual(len(result), 1)
        nb = result[0]
        self.assertEqual(nb["neighbor_id"], "192.0.11.12")
        self.assertEqual(nb["priority"], 2)
        self.assertEqual(nb["poll_interval"], 10)

    def test_parse_default_information(self):
        result = _parse_default_information(self.fixture["default-information"])
        orig = result["originate"]
        self.assertTrue(orig["always"])
        self.assertEqual(orig["metric"], 10)
        self.assertEqual(orig["metric_type"], 2)
        self.assertEqual(orig["route_map"], "ingress")

    def test_parse_areas(self):
        result = _parse_areas(self.fixture["area"])
        self.assertEqual(len(result), 3)
        area2 = next(a for a in result if a["area_id"] == "2")
        self.assertTrue(area2["area_type"]["normal"])
        self.assertEqual(area2["network"][0]["address"], "192.0.2.0/24")

        area3 = next(a for a in result if a["area_id"] == "3")
        self.assertTrue(area3["area_type"]["nssa"]["set"])

        area4 = next(a for a in result if a["area_id"] == "4")
        self.assertEqual(area4["area_type"]["stub"]["default_cost"], 20)
        self.assertEqual(len(area4["range"]), 2)
        r = next(r for r in area4["range"] if r["address"] == "192.0.3.0/24")
        self.assertEqual(r["cost"], 10)

    def test_get_running_config(self):
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result["parameters"]["router_id"], "192.0.1.1")
        self.assertIn("eth1", result["passive_interface"])
        self.assertIn("eth2", result["passive_interface"])
        self.assertEqual(result["auto_cost"]["reference_bandwidth"], 2)
        self.assertEqual(result["log_adjacency_changes"], "detail")

    def test_get_running_config_empty(self):
        self.mock_vyos.get_config = MagicMock(return_value={})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, {})


class TestVyOSOspfv2BuildCommands(unittest.TestCase):

    def test_deleted_with_have(self):
        have = {"parameters": {"router_id": "192.0.1.1"}}
        cmds = build_commands({}, have, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_without_have(self):
        cmds = build_commands({}, {}, "deleted")
        self.assertEqual(cmds, [])

    def test_merged_parameters(self):
        config = {"parameters": {"router_id": "192.0.1.1"}}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["parameters", "router-id", "192.0.1.1"]), cmds)

    def test_merged_redistribute(self):
        config = {"redistribute": [{"route_type": "bgp", "metric": 10}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["redistribute", "bgp"]), cmds)
        self.assertIn(("set", _BASE + ["redistribute", "bgp", "metric", "10"]), cmds)

    def test_merged_passive_interface(self):
        config = {"passive_interface": ["eth1"]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["interface", "eth1", "passive"]), cmds)

    def test_merged_area_normal(self):
        config = {"areas": [{"area_id": "2", "area_type": {"normal": True}}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["area", "2", "area-type", "normal"]), cmds)

    def test_merged_area_stub_with_cost(self):
        config = {"areas": [{"area_id": "4", "area_type": {"stub": {"default_cost": 20}}}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["area", "4", "area-type", "stub", "default-cost", "20"]),
            cmds,
        )

    def test_merged_idempotent(self):
        have = {"parameters": {"router_id": "192.0.1.1"}}
        config = {"parameters": {"router_id": "192.0.1.1"}}
        cmds = build_commands(config, have, "merged")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        have = {"parameters": {"router_id": "192.0.1.1"}}
        config = {"parameters": {"router_id": "192.0.1.1"}}
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_rebuilds_on_change(self):
        have = {"parameters": {"router_id": "192.0.1.1"}}
        config = {"parameters": {"router_id": "192.0.1.2"}}
        cmds = build_commands(config, have, "replaced")
        self.assertEqual(cmds[0], ("delete", _BASE))
        self.assertIn(
            ("set", _BASE + ["parameters", "router-id", "192.0.1.2"]),
            cmds,
        )

    def test_merged_neighbor(self):
        config = {"neighbor": [{"neighbor_id": "192.0.11.12", "priority": 2}]}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["neighbor", "192.0.11.12"]), cmds)
        self.assertIn(("set", _BASE + ["neighbor", "192.0.11.12", "priority", "2"]), cmds)

    def test_merged_default_information(self):
        config = {"default_information": {"originate": {"always": True, "metric": 10}}}
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["default-information", "originate", "always"]), cmds)
        self.assertIn(("set", _BASE + ["default-information", "originate", "metric", "10"]), cmds)


if __name__ == "__main__":
    unittest.main()
