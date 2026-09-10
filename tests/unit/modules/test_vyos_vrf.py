# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.modules.vyos_vrf import (
    _bgp_build_commands,
    _bgp_from_device,
    _device_to_argspec,
    _ospf_build_commands,
    _ospf_from_device,
    _protocols_from_device,
    _static_build_commands,
    _static_from_device,
    build_commands,
)

from .base import load_fixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RAW_HAVE = load_fixture("vrf_running.json")


# ---------------------------------------------------------------------------
# _device_to_argspec
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _bgp_from_device
# ---------------------------------------------------------------------------


class TestBgpFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["bgp"]
        self.result = _bgp_from_device(self.raw)

    def test_system_as(self):
        self.assertEqual(self.result["system_as"], 65001)

    def test_neighbor_list(self):
        self.assertEqual(len(self.result["neighbor"]), 1)
        n = self.result["neighbor"][0]
        self.assertEqual(n["address"], "10.0.0.1")
        self.assertEqual(n["remote_as"], 65002)
        self.assertEqual(n["description"], "peer1")

    def test_empty_input(self):
        self.assertEqual(_bgp_from_device({}), {})
        self.assertEqual(_bgp_from_device(None), {})


# ---------------------------------------------------------------------------
# _bgp_build_commands
# ---------------------------------------------------------------------------


class TestBgpBuildCommands(unittest.TestCase):
    def _have(self):
        return _RAW_HAVE["name"]["vrf1"]["protocols"]["bgp"]

    def test_idempotent(self):
        want = {
            "system_as": 65001,
            "neighbor": [
                {"address": "10.0.0.1", "remote_as": 65002, "description": "peer1"},
            ],
        }
        cmds = _bgp_build_commands("vrf1", want, self._have(), "merged")
        self.assertEqual(cmds, [])

    def test_add_neighbor(self):
        want = {
            "system_as": 65001,
            "neighbor": [
                {"address": "10.0.0.1", "remote_as": 65002, "description": "peer1"},
                {"address": "10.0.0.2", "remote_as": 65003},
            ],
        }
        cmds = _bgp_build_commands("vrf1", want, self._have(), "merged")
        paths = [p for _, p in cmds]
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

    def test_no_commands_on_empty_want(self):
        cmds = _bgp_build_commands("vrf1", {}, {}, "merged")
        self.assertEqual(cmds, [])


# ---------------------------------------------------------------------------
# _ospf_from_device
# ---------------------------------------------------------------------------


class TestOspfFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["ospf"]
        self.result = _ospf_from_device(self.raw)

    def test_areas(self):
        self.assertEqual(len(self.result["areas"]), 1)
        area = self.result["areas"][0]
        self.assertEqual(area["area_id"], "0")
        self.assertIn("10.0.0.0/24", area["networks"])
        self.assertIn("172.16.0.0/24", area["networks"])

    def test_parameters(self):
        self.assertEqual(self.result["parameters"]["router_id"], "10.0.0.1")

    def test_empty_input(self):
        self.assertEqual(_ospf_from_device({}), {})


# ---------------------------------------------------------------------------
# _ospf_build_commands
# ---------------------------------------------------------------------------


class TestOspfBuildCommands(unittest.TestCase):
    def _have(self):
        return _RAW_HAVE["name"]["vrf1"]["protocols"]["ospf"]

    def test_idempotent(self):
        want = {
            "areas": [{"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24"]}],
            "parameters": {"router_id": "10.0.0.1"},
        }
        cmds = _ospf_build_commands("vrf1", want, self._have(), "merged")
        self.assertEqual(cmds, [])

    def test_add_network(self):
        want = {
            "areas": [
                {"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24", "192.168.0.0/24"]},
            ],
        }
        cmds = _ospf_build_commands("vrf1", want, self._have(), "merged")
        paths = [p for _, p in cmds]
        self.assertIn(
            ["vrf", "name", "vrf1", "protocols", "ospf", "area", "0", "network", "192.168.0.0/24"],
            paths,
        )

    def test_add_area(self):
        want = {
            "areas": [
                {"area_id": "0", "networks": ["10.0.0.0/24", "172.16.0.0/24"]},
                {"area_id": "1", "networks": ["10.1.0.0/24"]},
            ],
        }
        cmds = _ospf_build_commands("vrf1", want, self._have(), "merged")
        paths = [p for _, p in cmds]
        self.assertIn(
            ["vrf", "name", "vrf1", "protocols", "ospf", "area", "1", "network", "10.1.0.0/24"],
            paths,
        )


# ---------------------------------------------------------------------------
# _static_from_device
# ---------------------------------------------------------------------------


class TestStaticFromDevice(unittest.TestCase):
    def setUp(self):
        self.raw = _RAW_HAVE["name"]["vrf1"]["protocols"]["static"]
        self.result = _static_from_device(self.raw)

    def test_routes(self):
        self.assertEqual(len(self.result["routes"]), 1)
        route = self.result["routes"][0]
        self.assertEqual(route["dest"], "192.168.10.0/24")
        self.assertIn("10.0.0.254", route["next_hops"])

    def test_empty_input(self):
        self.assertEqual(_static_from_device({}), {})


# ---------------------------------------------------------------------------
# _static_build_commands
# ---------------------------------------------------------------------------


class TestStaticBuildCommands(unittest.TestCase):
    def _have(self):
        return _RAW_HAVE["name"]["vrf1"]["protocols"]["static"]

    def test_idempotent(self):
        want = {
            "routes": [{"dest": "192.168.10.0/24", "next_hops": ["10.0.0.254"]}],
        }
        cmds = _static_build_commands("vrf1", want, self._have(), "merged")
        self.assertEqual(cmds, [])

    def test_add_route(self):
        want = {
            "routes": [
                {"dest": "192.168.10.0/24", "next_hops": ["10.0.0.254"]},
                {"dest": "192.168.20.0/24", "next_hops": ["10.0.0.254"]},
            ],
        }
        cmds = _static_build_commands("vrf1", want, self._have(), "merged")
        paths = [p for _, p in cmds]
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


# ---------------------------------------------------------------------------
# _protocols_from_device
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# build_commands
# ---------------------------------------------------------------------------


class TestBuildCommands(unittest.TestCase):
    def test_merged_new_vrf(self):
        config = {"instances": [{"name": "vrf3", "table_id": 200, "vni": 2000}]}
        cmds = build_commands(config, _RAW_HAVE, "merged")
        paths = [p for _, p in cmds]
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
        # vrf2 should not be deleted
        self.assertNotIn(("delete", ["vrf", "name", "vrf2"]), cmds)

    def test_deleted_all(self):
        cmds = build_commands({}, _RAW_HAVE, "deleted")
        self.assertIn(("delete", ["vrf"]), cmds)

    def test_overridden_removes_extra_vrf(self):
        config = {"instances": [{"name": "vrf1", "table_id": 101}]}
        cmds = build_commands(config, _RAW_HAVE, "overridden")
        paths = [p for _, p in cmds]
        self.assertIn(["vrf", "name", "vrf2"], paths)

    def test_merged_bgp_in_vrf(self):
        config = {
            "instances": [
                {
                    "name": "vrf1",
                    "table_id": 101,
                    "protocols": {
                        "bgp": {
                            "system_as": 65001,
                            "neighbor": [
                                {"address": "10.0.0.1", "remote_as": 65002, "description": "peer1"},
                                {"address": "10.0.0.2", "remote_as": 65003},
                            ],
                        },
                    },
                },
            ],
        }
        cmds = build_commands(config, _RAW_HAVE, "merged")
        paths = [p for _, p in cmds]
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
        # existing neighbor should not be re-set
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


if __name__ == "__main__":
    unittest.main()
