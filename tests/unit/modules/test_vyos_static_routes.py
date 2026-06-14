# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_static_routes import (
    _normalize,
    _route_cmds,
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


class TestVyOSStaticRoutesGetRunningFixture(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("static_routes_running.json")

    def test_fixture_parses_ipv4(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        dests = [r["dest"] for r in ipv4["routes"]]
        self.assertIn("192.0.2.0/24", dests)
        self.assertIn("203.0.113.0/24", dests)

    def test_fixture_parses_ipv4_next_hop(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        route = next(r for r in ipv4["routes"] if r["dest"] == "192.0.2.0/24")
        self.assertEqual(route["next_hops"][0]["forward_router_address"], "10.0.0.1")

    def test_fixture_parses_blackhole_distance(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        route = next(r for r in ipv4["routes"] if r["dest"] == "203.0.113.0/24")
        self.assertEqual(route["blackhole_config"]["distance"], 200)

    def test_fixture_parses_ipv6(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        ipv6 = next(e for e in result if e["afi"] == "ipv6")
        self.assertEqual(ipv6["routes"][0]["dest"], "2001:db8::/32")


class TestVyOSStaticRoutesGetRunning(VyOSModuleTestCase):

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_parses_ipv4_next_hop(self):
        self.set_running_config(
            {
                "route": {
                    "192.0.2.0/24": {
                        "next-hop": {"10.0.0.1": {}},
                    },
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        route = ipv4["routes"][0]
        self.assertEqual(route["dest"], "192.0.2.0/24")
        self.assertEqual(route["next_hops"][0]["forward_router_address"], "10.0.0.1")

    def test_parses_ipv4_blackhole(self):
        self.set_running_config(
            {
                "route": {
                    "203.0.113.0/24": {"blackhole": {}},
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        route = ipv4["routes"][0]
        self.assertIn("blackhole_config", route)

    def test_parses_ipv4_blackhole_distance(self):
        self.set_running_config(
            {
                "route": {
                    "203.0.113.0/24": {"blackhole": {"distance": "200"}},
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        route = ipv4["routes"][0]
        self.assertEqual(route["blackhole_config"]["distance"], 200)

    def test_parses_ipv6_next_hop(self):
        self.set_running_config(
            {
                "route6": {
                    "2001:db8::/32": {
                        "next-hop": {"2001:db8::1": {}},
                    },
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv6 = next(e for e in result if e["afi"] == "ipv6")
        route = ipv6["routes"][0]
        self.assertEqual(route["dest"], "2001:db8::/32")
        self.assertEqual(route["next_hops"][0]["forward_router_address"], "2001:db8::1")

    def test_parses_next_hop_admin_distance(self):
        self.set_running_config(
            {
                "route": {
                    "192.0.2.0/24": {
                        "next-hop": {"10.0.0.1": {"distance": "10"}},
                    },
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        nh = ipv4["routes"][0]["next_hops"][0]
        self.assertEqual(nh["admin_distance"], 10)

    def test_parses_disabled_next_hop(self):
        self.set_running_config(
            {
                "route": {
                    "192.0.2.0/24": {
                        "next-hop": {"10.0.0.1": {"disable": {}}},
                    },
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        ipv4 = next(e for e in result if e["afi"] == "ipv4")
        nh = ipv4["routes"][0]["next_hops"][0]
        self.assertFalse(nh["enabled"])

    def test_no_ipv4_entry_when_only_ipv6(self):
        self.set_running_config(
            {
                "route6": {
                    "2001:db8::/32": {"next-hop": {"2001:db8::1": {}}},
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        afis = [e["afi"] for e in result]
        self.assertNotIn("ipv4", afis)
        self.assertIn("ipv6", afis)


class TestVyOSStaticRoutesNormalize(unittest.TestCase):

    def test_normalize_ipv4_next_hop(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "192.0.2.0/24",
                        "next_hops": [{"forward_router_address": "10.0.0.1"}],
                    },
                ],
            },
        ]
        result = _normalize(config)
        self.assertIn("192.0.2.0/24", result["ipv4"])
        self.assertIn("10.0.0.1", result["ipv4"]["192.0.2.0/24"]["next_hops"])

    def test_normalize_blackhole(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "203.0.113.0/24",
                        "blackhole_config": {"distance": 200},
                    },
                ],
            },
        ]
        result = _normalize(config)
        route = result["ipv4"]["203.0.113.0/24"]
        self.assertEqual(route["blackhole_config"]["distance"], 200)

    def test_normalize_empty_config(self):
        result = _normalize([])
        self.assertEqual(result["ipv4"], {})
        self.assertEqual(result["ipv6"], {})

    def test_normalize_unknown_afi_ignored(self):
        config = [{"afi": "ipv99", "routes": []}]
        result = _normalize(config)
        self.assertNotIn("ipv99", result)


class TestVyOSStaticRoutesRouteCmds(unittest.TestCase):

    def test_new_next_hop(self):
        want = {"next_hops": {"10.0.0.1": {"forward_router_address": "10.0.0.1"}}}
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, {})
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["protocols", "static", "route", "192.0.2.0/24", "next-hop", "10.0.0.1"],
            paths,
        )

    def test_new_blackhole(self):
        want = {"blackhole_config": {}}
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, {})
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["protocols", "static", "route", "192.0.2.0/24", "blackhole"],
            paths,
        )

    def test_blackhole_distance(self):
        want = {"blackhole_config": {"distance": 200}}
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, {})
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["protocols", "static", "route", "192.0.2.0/24", "blackhole", "distance", "200"],
            paths,
        )

    def test_idempotent_next_hop(self):
        want = {"next_hops": {"10.0.0.1": {"forward_router_address": "10.0.0.1"}}}
        have = {"next_hops": {"10.0.0.1": {"forward_router_address": "10.0.0.1"}}}
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, have)
        self.assertEqual(cmds, [])

    def test_admin_distance_added(self):
        want = {
            "next_hops": {
                "10.0.0.1": {
                    "forward_router_address": "10.0.0.1",
                    "admin_distance": 10,
                },
            },
        }
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, {})
        paths = [c[1] for c in cmds]
        self.assertIn(
            [
                "protocols",
                "static",
                "route",
                "192.0.2.0/24",
                "next-hop",
                "10.0.0.1",
                "distance",
                "10",
            ],
            paths,
        )

    def test_disable_next_hop(self):
        want = {
            "next_hops": {
                "10.0.0.1": {
                    "forward_router_address": "10.0.0.1",
                    "enabled": False,
                },
            },
        }
        have = {
            "next_hops": {
                "10.0.0.1": {
                    "forward_router_address": "10.0.0.1",
                    "enabled": True,
                },
            },
        }
        cmds = _route_cmds("ipv4", "192.0.2.0/24", want, have)
        ops = [(c[0], c[1][-1]) for c in cmds]
        self.assertIn(("set", "disable"), ops)


class TestVyOSStaticRoutesBuildCommands(unittest.TestCase):

    def _have_ipv4(self):
        return [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "192.0.2.0/24",
                        "next_hops": [{"forward_router_address": "10.0.0.1"}],
                    },
                ],
            },
        ]

    def test_merged_adds_new_route(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {"dest": "10.0.0.0/8", "next_hops": [{"forward_router_address": "1.2.3.4"}]},
                ],
            },
        ]
        cmds = build_commands(config, [], "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["protocols", "static", "route", "10.0.0.0/8", "next-hop", "1.2.3.4"],
            paths,
        )

    def test_merged_idempotent(self):
        cmds = build_commands(self._have_ipv4(), self._have_ipv4(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self._have_ipv4(), "deleted")
        self.assertIn(("delete", ["protocols", "static", "route"]), cmds)

    def test_deleted_with_config_removes_specific(self):
        config = [{"afi": "ipv4", "routes": [{"dest": "192.0.2.0/24"}]}]
        cmds = build_commands(config, self._have_ipv4(), "deleted")
        self.assertIn(
            ("delete", ["protocols", "static", "route", "192.0.2.0/24"]),
            cmds,
        )

    def test_deleted_idempotent_when_empty(self):
        cmds = build_commands([], [], "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        cmds = build_commands(self._have_ipv4(), self._have_ipv4(), "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_deletes_then_rebuilds(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {"dest": "192.0.2.0/24", "next_hops": [{"forward_router_address": "9.9.9.9"}]},
                ],
            },
        ]
        cmds = build_commands(config, self._have_ipv4(), "replaced")
        delete_idx = next(
            i
            for i, c in enumerate(cmds)
            if c == ("delete", ["protocols", "static", "route", "192.0.2.0/24"])
        )
        set_idx = next(i for i, c in enumerate(cmds) if c[0] == "set" and "9.9.9.9" in c[1])
        self.assertLess(delete_idx, set_idx)

    def test_overridden_removes_extra_routes(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {"dest": "10.0.0.0/8", "next_hops": [{"forward_router_address": "1.2.3.4"}]},
                ],
            },
        ]
        cmds = build_commands(config, self._have_ipv4(), "overridden")
        self.assertIn(
            ("delete", ["protocols", "static", "route", "192.0.2.0/24"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
