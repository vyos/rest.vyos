# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_bgp_global import (
    _device_to_argspec,
    _neighbors_from_device,
    _neighbors_to_device,
    _peer_groups_from_device,
    _peer_groups_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["protocols", "bgp"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("bgp_global_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestNeighborsToDeviceFromDevice(unittest.TestCase):
    def test_bare_neighbor_is_presence(self):
        self.assertEqual(
            _neighbors_to_device([{"neighbor_address": "192.0.2.1"}]),
            {"192.0.2.1": {}},
        )

    def test_full_neighbor(self):
        result = _neighbors_to_device(
            [
                {
                    "neighbor_address": "192.0.2.1",
                    "remote_as": 65001,
                    "description": "peer1",
                    "shutdown": True,
                    "timers": {"holdtime": 30, "keepalive": 10},
                },
            ],
        )
        self.assertEqual(
            result,
            {
                "192.0.2.1": {
                    "remote_as": 65001,
                    "description": "peer1",
                    "shutdown": {},
                    "timers": {"holdtime": 30, "keepalive": 10},
                },
            },
        )

    def test_from_device_ints_cast_via_argspec(self):
        result = _neighbors_from_device(
            {
                "192.0.2.1": {
                    "remote-as": "65001",
                    "ebgp-multihop": "2",
                    "timers": {"holdtime": "30", "keepalive": "10"},
                },
            },
        )
        entry = result[0]
        self.assertEqual(entry["remote_as"], 65001)
        self.assertEqual(entry["ebgp_multihop"], 2)
        self.assertEqual(entry["timers"], {"holdtime": 30, "keepalive": 10})

    def test_from_device_foreign_address_family_never_surfaces(self):
        """Regression test: a neighbor's address-family subtree (owned by
        vyos_bgp_address_family) must never appear in this module's have/
        gathered output."""
        result = _neighbors_from_device(
            {
                "192.0.2.1": {
                    "remote-as": "65001",
                    "address-family": {"ipv4-unicast": {"nexthop-self": {}}},
                },
            },
        )
        entry = result[0]
        self.assertEqual(entry["remote_as"], 65001)
        self.assertNotIn("address_family", entry)


class TestPeerGroupsToDeviceFromDevice(unittest.TestCase):
    def test_bare_peer_group_is_presence(self):
        self.assertEqual(_peer_groups_to_device([{"peer_group": "PG1"}]), {"PG1": {}})

    def test_full_peer_group(self):
        result = _peer_groups_to_device(
            [{"peer_group": "PG1", "remote_as": 65002, "timers": {"holdtime": 30}}],
        )
        self.assertEqual(
            result,
            {"PG1": {"remote_as": 65002, "timers": {"holdtime": 30}}},
        )

    def test_from_device_cast(self):
        result = _peer_groups_from_device({"PG1": {"remote-as": "65002"}})
        self.assertEqual(result, [{"peer_group": "PG1", "remote_as": 65002}])


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_confederation_peers_list_passes_through(self):
        result = _want_to_device(
            {
                "as_number": 65000,
                "parameters": {"confederation": {"identifier": 100, "peers": [65001, 65002]}},
            },
        )
        self.assertEqual(
            result,
            {
                "system_as": 65000,
                "parameters": {"confederation": {"identifier": 100, "peers": [65001, 65002]}},
            },
        )

    def test_full_config(self):
        config = {
            "as_number": 65000,
            "parameters": {"router_id": "192.0.1.1", "graceful_restart": True},
            "neighbors": [{"neighbor_address": "192.0.2.1", "remote_as": 65001}],
            "peer_groups": [{"peer_group": "PG1", "remote_as": 65002}],
        }
        result = _want_to_device(config)
        self.assertEqual(
            result,
            {
                "system_as": 65000,
                "parameters": {"router_id": "192.0.1.1", "graceful_restart": {}},
                "neighbor": {"192.0.2.1": {"remote_as": 65001}},
                "peer_group": {"PG1": {"remote_as": 65002}},
            },
        )


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_as_number_and_parameters(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(have["as_number"], 65000)
        self.assertEqual(have["parameters"]["router_id"], "192.0.1.1")
        self.assertEqual(
            have["parameters"]["confederation"],
            {"identifier": 100, "peers": [65001, 65002]},
        )

    def test_neighbor_and_peer_group(self):
        have = _device_to_argspec(self.fixture)
        nb = next(n for n in have["neighbors"] if n["neighbor_address"] == "192.0.2.1")
        self.assertEqual(nb["remote_as"], 65001)
        self.assertEqual(nb["timers"], {"holdtime": 30, "keepalive": 10})
        self.assertNotIn("address_family", nb)
        pg = have["peer_groups"][0]
        self.assertEqual(pg["peer_group"], "PG1")
        self.assertEqual(pg["remote_as"], 65003)

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_replaced_purges_extra_confederation_peer(self):
        """Regression test: dict_op's purge mode originally had no
        handling for list-valued leaves at all (only dicts), so removing
        a peer from confederation.peers under 'replaced' silently did
        nothing. Fixed centrally in dict_op itself."""
        have = _device_to_argspec(self.fixture)
        have["parameters"]["confederation"]["peers"] = [65001]
        cmds = build_commands(have, self.fixture, "replaced")
        self.assertIn(
            ("delete", _BASE + ["parameters", "confederation", "peers", "65002"]),
            cmds,
        )

    def test_merged_new_neighbor_field(self):
        have = _device_to_argspec(self.fixture)
        have["neighbors"][0]["local_as"] = 65099
        cmds = build_commands(have, self.fixture, "merged")
        self.assertIn(
            ("set", _BASE + ["neighbor", "192.0.2.1", "local-as", "65099"]),
            cmds,
        )

    def test_replaced_never_touches_address_family(self):
        """Regression test: this module shares protocols.bgp with
        vyos_bgp_address_family; replaced/deleted must never purge or
        delete that sibling module's address-family subtree."""
        cmds = build_commands({"as_number": 65000}, self.fixture, "replaced")
        self.assertTrue(all("address-family" not in c[1] for c in cmds))

    def test_deleted_removes_atomically_not_scoped(self):
        """Regression test for the real device-model bug: VyOS rejects any
        commit that removes system-as while other protocols.bgp content
        (including a neighbor's address-family, owned by
        vyos_bgp_address_family) still exists. A scoped/incremental
        deletion here would leave an invalid intermediate state and hard-
        fail at commit time -- deleted must delete the whole tree in one
        atomic command whenever system-as is present."""
        cmds = build_commands({}, self.fixture, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_with_no_system_as_is_a_noop(self):
        cmds = build_commands({}, {}, "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_without_as_number_also_nukes_atomically(self):
        """The same VyOS constraint applies to 'replaced' whenever the new
        desired state omits as_number -- not just 'deleted'."""
        cmds = build_commands({"neighbors": []}, self.fixture, "replaced")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_merged_with_empty_config_is_a_safe_noop(self):
        """Regression test: merged must NEVER trigger the nuke short-
        circuit just because as_number was omitted -- an omitted config
        for merged means "nothing to change", not "delete everything"."""
        cmds = build_commands({}, self.fixture, "merged")
        self.assertEqual(cmds, [])

    def test_replaced_keeping_as_number_still_scopes_normally(self):
        """When as_number is retained, replaced must still use the normal
        scoped purge/set flow, not the atomic nuke."""
        have = _device_to_argspec(self.fixture)
        cmds = build_commands(have, self.fixture, "replaced")
        self.assertEqual(cmds, [])
        self.assertNotEqual(cmds, [("delete", _BASE)])

    def test_collapsed_single_neighbor_no_char_iteration_bug(self):
        """A neighbor tag node collapsed to a bare address string by the
        device (single neighbor, otherwise unconfigured) must not be
        iterated character-by-character."""
        raw_have = {"system-as": "65000", "neighbor": "192.0.2.1"}
        config = {"as_number": 65000, "neighbors": [{"neighbor_address": "192.0.2.1"}]}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_fresh_merged_add(self):
        config = {
            "as_number": 65000,
            "neighbors": [{"neighbor_address": "10.0.0.1", "remote_as": 65010}],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["neighbor", "10.0.0.1", "remote-as", "65010"]),
            cmds,
        )
        self.assertIn(("set", _BASE + ["system-as", "65000"]), cmds)


if __name__ == "__main__":
    unittest.main()
