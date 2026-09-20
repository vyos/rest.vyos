# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.modules.vyos_vrf import (
    _device_to_argspec,
    _proto_from_device,
    _proto_to_device,
    _protocols_from_device,
    build_commands,
)

from .base import load_fixture


_RAW_HAVE = load_fixture("vrf_running.json")


class TestDeviceToArgspec(unittest.TestCase):
    def setUp(self):
        self.result = _device_to_argspec(_RAW_HAVE)

    def test_bind_to_all(self):
        self.assertTrue(self.result["bind_to_all"])

    def test_instances_count(self):
        self.assertEqual(len(self.result["instances"]), 2)

    def test_vrf1_properties(self):
        vrf1 = next(i for i in self.result["instances"] if i["name"] == "vrf1")
        self.assertEqual(vrf1["description"], "red")
        self.assertTrue(vrf1["disable"])
        self.assertEqual(vrf1["table_id"], 101)
        self.assertEqual(vrf1["vni"], 501)

    def test_vrf2_address_family(self):
        vrf2 = next(i for i in self.result["instances"] if i["name"] == "vrf2")
        afis = {af["afi"]: af for af in vrf2["address_family"]}
        self.assertIn("ipv4", afis)
        self.assertTrue(afis["ipv4"]["disable_forwarding"])
        self.assertTrue(afis["ipv4"]["nht_no_resolve_via_default"])
        self.assertIn("ipv6", afis)
        self.assertTrue(afis["ipv6"]["disable_forwarding"])
        self.assertTrue(afis["ipv6"]["nht_no_resolve_via_default"])

    def test_empty_input(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})


class TestBgpFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["bgp"]
        self.result = _proto_from_device(self.raw, "bgp")

    def test_system_as(self):
        self.assertEqual(self.result["system_as"], 65001)

    def test_neighbor_list(self):
        self.assertEqual(len(self.result["neighbor"]), 1)
        n = self.result["neighbor"][0]
        self.assertEqual(n["address"], "10.0.0.1")
        self.assertEqual(n["remote_as"], 65002)
        self.assertEqual(n["description"], "peer1")

    def test_empty_input(self):
        self.assertEqual(_proto_from_device({}, "bgp"), {})
        self.assertEqual(_proto_from_device(None, "bgp"), {})


class TestBgpToDevice(unittest.TestCase):
    def test_system_as_to_device(self):
        result = _proto_to_device({"system_as": 65001}, "bgp")
        self.assertIn("system-as", result)
        self.assertEqual(result["system-as"], 65001)

    def test_neighbor_to_device(self):
        result = _proto_to_device(
            {
                "system_as": 65001,
                "neighbor": [{"address": "10.0.0.1", "remote_as": 65002}],
            },
            "bgp",
        )
        self.assertIn("neighbor", result)
        self.assertIn("10.0.0.1", result["neighbor"])
        self.assertEqual(result["neighbor"]["10.0.0.1"]["remote-as"], 65002)

    def test_idempotent(self):
        want = _proto_from_device(_RAW_HAVE["name"]["vrf1"]["protocols"]["bgp"], "bgp")
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"bgp": want}}]},
            _RAW_HAVE,
            "merged",
        )
        bgp_cmds = [c for c in cmds if "bgp" in str(c)]
        self.assertEqual(bgp_cmds, [])

    def test_add_neighbor(self):
        want_bgp = {
            "system_as": 65001,
            "neighbor": [
                {"address": "10.0.0.1", "remote_as": 65002, "description": "peer1"},
                {"address": "10.0.0.2", "remote_as": 65003},
            ],
        }
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"bgp": want_bgp}}]},
            _RAW_HAVE,
            "merged",
        )
        paths = [c[1] for c in cmds]
        self.assertIn(
            [
                "vrf",
                "name",
                "vrf1",
                "protocols",
                "bgp",
                "neighbor",
                "10.0.0.2",
                "remote-as",
                "65003",
            ],
            paths,
        )
        self.assertNotIn(
            [
                "vrf",
                "name",
                "vrf1",
                "protocols",
                "bgp",
                "neighbor",
                "10.0.0.1",
                "remote-as",
                "65002",
            ],
            paths,
        )


class TestOspfFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["ospf"]
        self.result = _proto_from_device(self.raw, "ospf")

    def test_areas(self):
        self.assertEqual(len(self.result["areas"]), 1)
        area = self.result["areas"][0]
        self.assertEqual(area["area_id"], "0")
        self.assertIn("10.0.0.0/24", area["networks"])
        self.assertIn("172.16.0.0/24", area["networks"])

    def test_parameters(self):
        self.assertEqual(self.result["parameters"]["router_id"], "10.0.0.1")

    def test_empty_input(self):
        self.assertEqual(_proto_from_device({}, "ospf"), {})


class TestOspfBuildCommands(unittest.TestCase):
    def test_idempotent(self):
        want = _proto_from_device(_RAW_HAVE["name"]["vrf1"]["protocols"]["ospf"], "ospf")
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"ospf": want}}]},
            _RAW_HAVE,
            "merged",
        )
        ospf_cmds = [c for c in cmds if "ospf" in str(c)]
        self.assertEqual(ospf_cmds, [])

    def test_add_network(self):
        want_ospf = {
            "areas": [
                {"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24", "192.168.0.0/24"]},
            ],
        }
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"ospf": want_ospf}}]},
            _RAW_HAVE,
            "merged",
        )
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["vrf", "name", "vrf1", "protocols", "ospf", "area", "0", "network", "192.168.0.0/24"],
            paths,
        )

    def test_add_area(self):
        want_ospf = {
            "areas": [
                {"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24"]},
                {"area_id": "1", "networks": ["10.1.0.0/24"]},
            ],
        }
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"ospf": want_ospf}}]},
            _RAW_HAVE,
            "merged",
        )
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["vrf", "name", "vrf1", "protocols", "ospf", "area", "1", "network", "10.1.0.0/24"],
            paths,
        )

    def test_change_router_id(self):
        """Regression test: confirmed bug where router_id was missing
        from _DEVICE_RENAMES. A brand-new router_id happened to work
        via dict_op's own fallback conversion, and an unchanged value
        happened to stay idempotent since both sides of the comparison
        shared the same (wrong) key -- only *changing* an existing
        router_id actually exposed the corrupted "router_id" (no
        hyphen) device path, which VyOS would reject."""
        want_ospf = {
            "areas": [
                {"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24"]},
            ],
            "parameters": {"router_id": "10.0.0.99"},
        }
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"ospf": want_ospf}}]},
            _RAW_HAVE,
            "merged",
        )
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["vrf", "name", "vrf1", "protocols", "ospf", "parameters", "router-id", "10.0.0.99"],
            paths,
        )
        self.assertFalse(
            any("router_id" in p for p in paths),
            "router_id (underscore) must never appear in a device path",
        )


class TestStaticFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["static"]
        self.result = _proto_from_device(self.raw, "static")

    def test_routes(self):
        self.assertEqual(len(self.result["routes"]), 1)
        route = self.result["routes"][0]
        self.assertEqual(route["dest"], "192.168.10.0/24")
        self.assertIn("10.0.0.254", route["next_hops"])

    def test_empty_input(self):
        self.assertEqual(_proto_from_device({}, "static"), {})


class TestStaticBuildCommands(unittest.TestCase):
    def test_idempotent(self):
        want = _proto_from_device(_RAW_HAVE["name"]["vrf1"]["protocols"]["static"], "static")
        cmds = build_commands(
            {"instances": [{"name": "vrf1", "table_id": 101, "protocols": {"static": want}}]},
            _RAW_HAVE,
            "merged",
        )
        static_cmds = [c for c in cmds if "static" in str(c)]
        self.assertEqual(static_cmds, [])

    def test_add_route(self):
        want_static = {
            "routes": [
                {"dest": "192.168.10.0/24", "next_hops": ["10.0.0.254"]},
                {"dest": "192.168.20.0/24", "next_hops": ["10.0.0.254"]},
            ],
        }
        cmds = build_commands(
            {
                "instances": [
                    {"name": "vrf1", "table_id": 101, "protocols": {"static": want_static}},
                ],
            },
            _RAW_HAVE,
            "merged",
        )
        paths = [c[1] for c in cmds]
        self.assertIn(
            [
                "vrf",
                "name",
                "vrf1",
                "protocols",
                "static",
                "route",
                "192.168.20.0/24",
                "next-hop",
                "10.0.0.254",
            ],
            paths,
        )


class TestProtocolsFromDevice(unittest.TestCase):
    def test_all_protocols(self):
        raw_vrf = _RAW_HAVE["name"]["vrf1"]
        result = _protocols_from_device(raw_vrf)
        self.assertIn("bgp", result)
        self.assertIn("ospf", result)
        self.assertIn("static", result)

    def test_no_protocols(self):
        raw_vrf = _RAW_HAVE["name"]["vrf2"]
        result = _protocols_from_device(raw_vrf)
        self.assertIsNone(result)


class TestBuildCommands(unittest.TestCase):
    def test_merged_new_vrf(self):
        config = {"instances": [{"name": "vrf3", "table_id": 200, "vni": 2000}]}
        cmds = build_commands(config, _RAW_HAVE, "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(["vrf", "name", "vrf3", "table", "200"], paths)
        self.assertIn(["vrf", "name", "vrf3", "vni", "2000"], paths)

    def test_merged_idempotent(self):
        config = {
            "bind_to_all": True,
            "instances": [
                {"name": "vrf1", "description": "red", "table_id": 101, "vni": 501},
            ],
        }
        cmds = build_commands(config, _RAW_HAVE, "merged")
        self.assertEqual(cmds, [])

    def test_deleted_specific_vrf(self):
        config = {"instances": [{"name": "vrf1"}]}
        cmds = build_commands(config, _RAW_HAVE, "deleted")
        self.assertIn(("delete", ["vrf", "name", "vrf1"]), cmds)
        self.assertNotIn(("delete", ["vrf", "name", "vrf2"]), cmds)

    def test_deleted_all(self):
        cmds = build_commands({}, _RAW_HAVE, "deleted")
        self.assertIn(("delete", ["vrf"]), cmds)

    def test_overridden_removes_extra_vrf(self):
        config = {"instances": [{"name": "vrf1", "table_id": 101}]}
        cmds = build_commands(config, _RAW_HAVE, "overridden")
        paths = [c[1] for c in cmds]
        self.assertIn(["vrf", "name", "vrf2"], paths)

    def test_merged_does_not_delete_unreferenced_vrf(self):
        config = {"instances": [{"name": "vrf1", "table_id": 101}]}
        cmds = build_commands(config, _RAW_HAVE, "merged")
        paths = [c[1] for c in cmds]
        self.assertNotIn(["vrf", "name", "vrf2"], paths)


if __name__ == "__main__":
    unittest.main()
