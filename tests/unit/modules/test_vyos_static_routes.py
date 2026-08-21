# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_static_routes import (
    _ROUTE_OPTIONS,
    ARGUMENT_SPEC,
    _derive_key_field,
    _device_to_argspec,
    _keyed_list_from_device,
    _keyed_list_to_device,
    _next_hop_entry_from_device,
    _next_hop_entry_to_device,
    _route_entry_from_device,
    _route_entry_to_device,
    _want_to_device,
    build_commands,
    cast_by_spec,
    get_running_config,
)

from .base import load_fixture


_BASE = ["protocols", "static"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("static_routes_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_config_directly(self):
        result = get_running_config(self.mock_vyos)
        self.assertIn("route", result)
        self.assertIn("route6", result)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestDeriveKeyField(unittest.TestCase):
    def test_derives_dest_key(self):
        route_opts = ARGUMENT_SPEC["config"]["options"]["routes"]["options"]
        self.assertEqual(_derive_key_field(route_opts), "dest")

    def test_derives_forward_router_address_key(self):
        nh_opts = ARGUMENT_SPEC["config"]["options"]["routes"]["options"]["next_hops"]["options"]
        self.assertEqual(_derive_key_field(nh_opts), "forward_router_address")

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"type": "str"}})

    def test_raises_if_more_than_one_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"required": True}, "b": {"required": True}})


class TestKeyedListHelper(unittest.TestCase):
    def test_to_device_basic(self):
        result = _keyed_list_to_device(
            [{"dest": "192.0.2.0/24", "blackhole_config": {"distance": 200}}],
            "dest",
        )
        self.assertEqual(result, {"192.0.2.0/24": {"blackhole_config": {"distance": 200}}})

    def test_from_device_basic(self):
        result = _keyed_list_from_device({"192.0.2.0/24": {"a": 1}}, "dest")
        self.assertEqual(result, [{"dest": "192.0.2.0/24", "a": 1}])

    def test_empty(self):
        self.assertEqual(_keyed_list_to_device([], "dest"), {})
        self.assertEqual(_keyed_list_from_device({}, "dest"), [])


class TestBlackholeNoTypeField(unittest.TestCase):
    """Regression test for the confirmed hallucinated field: the
    original module's blackhole_config.type does not correspond to
    anything on the device -- confirmed against vyos-1x, the
    "blackhole" node has only "distance" (and "tag", out of scope).
    The field has been removed entirely."""

    def test_type_not_in_argspec(self):
        bh_opts = ARGUMENT_SPEC["config"]["options"]["routes"]["options"]["blackhole_config"]
        self.assertNotIn("type", bh_opts["options"])
        self.assertEqual(set(bh_opts["options"].keys()), {"distance"})


class TestRouteEntryToDeviceFromDevice(unittest.TestCase):
    def test_blackhole_presence_only(self):
        """An empty blackhole_config (no distance) still creates a
        bare presence node -- achieving the same "just blackhole, no
        distance" result the original's bogus "type" field was used
        for, without needing any sentinel field at all."""
        result = _route_entry_to_device({"blackhole_config": {}})
        self.assertEqual(result, {"blackhole": {}})

    def test_blackhole_with_distance(self):
        result = _route_entry_to_device({"blackhole_config": {"distance": 200}})
        self.assertEqual(result, {"blackhole": {"distance": 200}})

    def test_next_hops_keyed_by_address(self):
        result = _route_entry_to_device(
            {"next_hops": [{"forward_router_address": "10.0.0.1", "admin_distance": 50}]},
        )
        self.assertEqual(result, {"next-hop": {"10.0.0.1": {"distance": 50}}})

    def test_disabled_next_hop(self):
        result = _route_entry_to_device(
            {"next_hops": [{"forward_router_address": "10.0.0.1", "enabled": False}]},
        )
        self.assertEqual(result["next-hop"]["10.0.0.1"], {"disable": {}})

    def test_enabled_true_produces_no_disable_leaf(self):
        result = _route_entry_to_device(
            {"next_hops": [{"forward_router_address": "10.0.0.1", "enabled": True}]},
        )
        self.assertNotIn("disable", result["next-hop"]["10.0.0.1"])

    def test_from_device_blackhole(self):
        """from_device stays purely structural (kebab->snake only);
        int-casting is cast_by_spec's responsibility, applied
        downstream in main() -- confirmed separately below."""
        entry = _route_entry_from_device({"blackhole": {"distance": "200"}})
        self.assertEqual(entry["blackhole_config"]["distance"], "200")

    def test_from_device_next_hop_disabled(self):
        entry = _route_entry_from_device({"next-hop": {"10.0.0.1": {"disable": {}}}})
        self.assertEqual(entry["next_hops"][0]["enabled"], False)

    def test_from_device_next_hop_enabled_omitted(self):
        """Confirmed device behavior: an enabled next-hop has no
        "disable" leaf at all -- "enabled" should not appear in the
        parsed entry either, matching the argspec default."""
        entry = _route_entry_from_device({"next-hop": {"10.0.0.1": {}}})
        self.assertNotIn("enabled", entry["next_hops"][0])

    def test_empty(self):
        self.assertEqual(_route_entry_to_device({}), {})
        self.assertEqual(_route_entry_from_device({}), {})


class TestNextHopEntryToDeviceFromDevice(unittest.TestCase):
    def test_interface(self):
        result = _next_hop_entry_to_device({"interface": "eth0"})
        self.assertEqual(result, {"interface": "eth0"})

    def test_from_device_interface(self):
        entry = _next_hop_entry_from_device({"interface": "eth0"})
        self.assertEqual(entry, {"interface": "eth0"})

    def test_from_device_distance_cast_to_int(self):
        entry = _next_hop_entry_from_device({"distance": "50"})
        self.assertEqual(entry["admin_distance"], 50)
        self.assertIsInstance(entry["admin_distance"], int)


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device([]), {})
        self.assertEqual(_want_to_device(None), {})

    def test_afi_without_routes_omitted(self):
        self.assertEqual(_want_to_device([{"afi": "ipv4"}]), {})

    def test_keyed_by_route_key(self):
        config = [{"afi": "ipv4", "routes": [{"dest": "192.0.2.0/24"}]}]
        result = _want_to_device(config)
        self.assertIn("192.0.2.0/24", result["route"])

    def test_ipv6_uses_route6_key(self):
        config = [{"afi": "ipv6", "routes": [{"dest": "2001:db8::/32"}]}]
        result = _want_to_device(config)
        self.assertIn("route6", result)


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_both_afis_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        afis = [e["afi"] for e in result]
        self.assertIn("ipv4", afis)
        self.assertIn("ipv6", afis)

    def test_blackhole_route_parsed_with_casting(self):
        """from_device alone leaves distance as the raw device string;
        cast_by_spec (applied downstream in main(), confirmed here
        directly) is what casts it to int, since cast_by_spec recurses
        into type="dict" suboptions like blackhole_config."""
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        ipv4_routes = next(e for e in result if e["afi"] == "ipv4")["routes"]
        bh_route = next(r for r in ipv4_routes if r["dest"] == "203.0.113.0/24")
        self.assertEqual(bh_route["blackhole_config"]["distance"], "200")
        cast_by_spec(bh_route, _ROUTE_OPTIONS)
        self.assertEqual(bh_route["blackhole_config"]["distance"], 200)

    def test_next_hop_route_parsed(self):
        raw = get_running_config(self.mock_vyos)
        result = _device_to_argspec(raw)
        ipv4_routes = next(e for e in result if e["afi"] == "ipv4")["routes"]
        nh_route = next(r for r in ipv4_routes if r["dest"] == "192.0.2.0/24")
        self.assertEqual(nh_route["next_hops"][0]["forward_router_address"], "10.0.0.1")

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), [])
        self.assertEqual(_device_to_argspec(None), [])


class TestBuildCommands(VyOSModuleTestCase):
    def setUp(self):
        super().setUp()
        self.raw = get_running_config(self.mock_vyos)

    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "replaced"), [])

    def test_overridden_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.raw)
        self.assertEqual(build_commands(have, self.raw, "overridden"), [])

    def test_clear_omitted_next_hop_attribute_on_replaced(self):
        """The primary confirmed bug fix from the PR review: the
        original _route_cmds only emitted commands for setting values,
        never for clearing an omitted attribute back to default, and
        "replaced" state's own change-detection missed this entirely
        since it only inspected generated set-commands."""
        raw_have = {"route": {"192.0.2.0/24": {"next-hop": {"10.0.0.1": {"distance": "50"}}}}}
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "192.0.2.0/24",
                        "next_hops": [
                            {"forward_router_address": "10.0.0.1"},
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        expected = ("delete", _BASE + ["route", "192.0.2.0/24", "next-hop", "10.0.0.1", "distance"])
        self.assertIn(expected, cmds)

    def test_replaced_scoped_to_named_route_only(self):
        raw_have = {
            "route": {
                "192.0.2.0/24": {"next-hop": {"10.0.0.1": {}}},
                "203.0.113.0/24": {"blackhole": {"distance": "200"}},
            },
        }
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "192.0.2.0/24",
                        "next_hops": [
                            {"forward_router_address": "10.0.0.1"},
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, raw_have, "replaced")
        self.assertEqual(cmds, [])
        self.assertFalse(any("203.0.113.0/24" in str(c) for c in cmds))

    def test_overridden_deletes_omitted_route(self):
        raw_have = {
            "route": {
                "192.0.2.0/24": {"next-hop": {"10.0.0.1": {}}},
                "203.0.113.0/24": {"blackhole": {"distance": "200"}},
            },
        }
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "192.0.2.0/24",
                        "next_hops": [
                            {"forward_router_address": "10.0.0.1"},
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, raw_have, "overridden")
        self.assertIn(("delete", _BASE + ["route", "203.0.113.0/24"]), cmds)

    def test_deleted_named_route(self):
        cmds = build_commands(
            [{"afi": "ipv4", "routes": [{"dest": "192.0.2.0/24"}]}],
            self.raw,
            "deleted",
        )
        self.assertEqual(cmds, [("delete", _BASE + ["route", "192.0.2.0/24"])])

    def test_deleted_named_afi_no_routes(self):
        cmds = build_commands([{"afi": "ipv4"}], self.raw, "deleted")
        self.assertEqual(cmds, [("delete", _BASE + ["route"])])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self.raw, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_named_nonexistent_is_noop(self):
        cmds = build_commands(
            [{"afi": "ipv4", "routes": [{"dest": "198.51.100.0/24"}]}],
            self.raw,
            "deleted",
        )
        self.assertEqual(cmds, [])

    def test_collapsed_bare_route_no_blackhole_or_next_hop(self):
        raw_have = {"route": {"192.0.2.0/24": {}}}
        config = [{"afi": "ipv4", "routes": [{"dest": "192.0.2.0/24"}]}]
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_merged_new_blackhole_route(self):
        config = [{"afi": "ipv4", "routes": [{"dest": "198.51.100.0/24", "blackhole_config": {}}]}]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["route", "198.51.100.0/24", "blackhole"]), cmds)

    def test_merged_new_disabled_next_hop(self):
        config = [
            {
                "afi": "ipv4",
                "routes": [
                    {
                        "dest": "198.51.100.0/24",
                        "next_hops": [
                            {"forward_router_address": "10.0.0.9", "enabled": False},
                        ],
                    },
                ],
            },
        ]
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["route", "198.51.100.0/24", "next-hop", "10.0.0.9", "disable"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
