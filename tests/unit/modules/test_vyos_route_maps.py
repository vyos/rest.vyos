# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_route_maps import (
    _want_to_api_match,
    _want_to_api_set,
    build_commands,
    get_running_config,
)


def load_fixture(filename):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    path = os.path.join(fixtures_dir, filename)
    with open(path) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.mock_vyos.get_config = MagicMock(return_value={})

    def set_running_config(self, data):
        self.mock_vyos.get_config.return_value = data


class TestVyOSRouteMapsGetRunning(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("route_maps_running.json")

    def test_unwraps_route_map_nesting(self):
        """API returns {"route-map": {"NAME": {...}}} — must unwrap."""
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        names = [e["route_map"] for e in result]
        self.assertIn("RM-TEST-EXPORT-POLICY", names)
        self.assertIn("rm1", names)
        # "route-map" itself must NOT appear as a route map name
        self.assertNotIn("route-map", names)

    def test_parses_rule_action(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        rm = next(e for e in result if e["route_map"] == "RM-TEST-EXPORT-POLICY")
        rule = rm["entries"][0]
        self.assertEqual(rule["action"], "permit")
        self.assertEqual(rule["sequence"], 10)

    def test_parses_match_peer(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        rm = next(e for e in result if e["route_map"] == "RM-TEST-EXPORT-POLICY")
        rule = rm["entries"][0]
        self.assertEqual(rule["match"]["peer"], "192.0.2.32")

    def test_parses_set_fields(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        rm = next(e for e in result if e["route_map"] == "RM-TEST-EXPORT-POLICY")
        rule = rm["entries"][0]
        self.assertEqual(rule["set"]["metric"], "5")
        self.assertEqual(rule["set"]["aggregator"]["as"], "100")
        self.assertEqual(rule["set"]["as-path"]["exclude"], "111")

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])


class TestVyOSRouteMapsWantToApi(unittest.TestCase):

    def test_as_path_exclude_nested(self):
        """as_path_exclude maps to nested as-path.exclude."""
        result = _want_to_api_set({"as_path_exclude": "111"})
        self.assertEqual(result["as-path"]["exclude"], "111")

    def test_metric_flat(self):
        result = _want_to_api_set({"metric": "5"})
        self.assertEqual(result["metric"], "5")

    def test_aggregator_as(self):
        result = _want_to_api_set({"aggregator": {"as": 100}})
        self.assertEqual(result["aggregator"]["as"], "100")

    def test_aggregator_as_underscore(self):
        """aggregator.as_ is an alias for aggregator.as."""
        result = _want_to_api_set({"aggregator": {"as_": 100}})
        self.assertEqual(result["aggregator"]["as"], "100")

    def test_large_community_presence_node(self):
        result = _want_to_api_set({"large_community": "none"})
        self.assertEqual(result["large-community"], {"none": {}})

    def test_match_peer(self):
        result = _want_to_api_match({"peer": "192.0.2.32"})
        self.assertEqual(result["peer"], "192.0.2.32")


class TestVyOSRouteMapsBuildCommands(unittest.TestCase):

    def _have_empty(self):
        return []

    def _have_with_rm(self):
        return [
            {
                "route_map": "RM1",
                "entries": [
                    {
                        "sequence": 10,
                        "action": "permit",
                        "match": {"peer": "192.0.2.32"},
                        "set": {"metric": "5", "as-path": {"exclude": "111"}},
                    },
                ],
            },
        ]

    def test_merged_adds_new_rm(self):
        config = [
            {
                "route_map": "RM-NEW",
                "entries": [{"sequence": 10, "action": "permit"}],
            },
        ]
        cmds = build_commands(config, self._have_empty(), "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(["policy", "route-map", "RM-NEW", "rule", "10", "action", "permit"], paths)

    def test_merged_idempotent(self):
        config = [
            {
                "route_map": "RM1",
                "entries": [
                    {
                        "sequence": 10,
                        "action": "permit",
                        "match": {"peer": "192.0.2.32"},
                        "set": {"metric": "5", "as_path_exclude": "111"},
                    },
                ],
            },
        ]
        cmds = build_commands(config, self._have_with_rm(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_deletes_all(self):
        cmds = build_commands([], self._have_with_rm(), "deleted")
        self.assertIn(("delete", ["policy", "route-map"]), cmds)

    def test_deleted_with_config_deletes_named(self):
        config = [{"route_map": "RM1"}]
        cmds = build_commands(config, self._have_with_rm(), "deleted")
        self.assertIn(("delete", ["policy", "route-map", "RM1"]), cmds)

    def test_replaced_deletes_then_resets(self):
        config = [
            {
                "route_map": "RM1",
                "entries": [{"sequence": 10, "action": "deny"}],
            },
        ]
        cmds = build_commands(config, self._have_with_rm(), "replaced")
        ops = [c[0] for c in cmds]
        # delete must come before set
        self.assertIn("delete", ops)
        self.assertIn("set", ops)
        delete_idx = ops.index("delete")
        set_idx = ops.index("set")
        self.assertLess(delete_idx, set_idx)

    def test_overridden_removes_extra_rm(self):
        config = [{"route_map": "RM-NEW", "entries": []}]
        have = self._have_with_rm()  # has RM1
        cmds = build_commands(config, have, "overridden")
        self.assertIn(("delete", ["policy", "route-map", "RM1"]), cmds)


if __name__ == "__main__":
    unittest.main()
