# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ha import (
    _device_to_argspec,
    _group_from_device,
    _group_to_device,
    _real_server_from_device,
    _real_server_to_device,
    _virtual_server_from_device,
    _virtual_server_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["high-availability"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("ha_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestRealServer(unittest.TestCase):
    def test_to_device_generic_fields(self):
        result = _real_server_to_device({"address": "10.0.0.2", "port": 8080})
        self.assertEqual(result, {"port": 8080})

    def test_to_device_health_check_script_nested(self):
        """health_check_script is a genuine structural exception -- the
        argspec has it flat, the device nests it under health-check.script."""
        result = _real_server_to_device(
            {"address": "10.0.0.2", "health_check_script": "/check.sh"},
        )
        self.assertEqual(result, {"health-check": {"script": "/check.sh"}})

    def test_from_device_basic(self):
        entry = _real_server_from_device("10.0.0.2", {"port": "8080"})
        self.assertEqual(entry["address"], "10.0.0.2")
        self.assertEqual(entry["port"], 8080)

    def test_from_device_health_check_script_extracted(self):
        entry = _real_server_from_device(
            "10.0.0.2",
            {"health-check": {"script": "/check.sh"}},
        )
        self.assertEqual(entry["health_check_script"], "/check.sh")


class TestVirtualServer(unittest.TestCase):
    def test_to_device_keyed_fields(self):
        result = _virtual_server_to_device({"name": "s1", "address": "10.0.0.1", "port": 80})
        self.assertEqual(result, {"address": "10.0.0.1", "port": 80})

    def test_to_device_real_server_keyed_by_address(self):
        vs = {
            "name": "s1",
            "port": 80,
            "real_server": [{"address": "10.0.0.2", "port": 8080}],
        }
        result = _virtual_server_to_device(vs)
        self.assertEqual(result["real-server"]["10.0.0.2"], {"port": 8080})

    def test_from_device_list_with_real_servers(self):
        entry = _virtual_server_from_device(
            "s1",
            {"port": "80", "real-server": {"10.0.0.2": {"port": "8080"}}},
        )
        self.assertEqual(entry["name"], "s1")
        self.assertEqual(entry["port"], 80)
        self.assertEqual(entry["real_server"][0]["address"], "10.0.0.2")
        self.assertEqual(entry["real_server"][0]["port"], 8080)


class TestGroup(unittest.TestCase):
    """address/excluded_address are genuine tagNodes (confirmed); track
    is NOT special-cased for interface since that's a plain list."""

    def test_to_device_basic_fields_generic(self):
        result = _group_to_device({"name": "g1", "vrid": 20, "interface": "eth0"})
        self.assertEqual(result, {"vrid": 20, "interface": "eth0"})

    def test_to_device_address_tag_node(self):
        result = _group_to_device(
            {"name": "g1", "address": ["192.168.1.1/24", "192.168.1.2/24"]},
        )
        self.assertEqual(
            result["address"],
            {"192.168.1.1/24": {}, "192.168.1.2/24": {}},
        )

    def test_to_device_excluded_address_tag_node(self):
        result = _group_to_device({"name": "g1", "excluded_address": ["10.0.0.1"]})
        self.assertEqual(result["excluded-address"], {"10.0.0.1": {}})

    def test_to_device_track_interface_stays_plain_list(self):
        """Regression test: track.interface is a confirmed <multi/>
        leafNode, not a tag node -- must NOT be reshaped into a
        dict-of-presence like address/excluded_address are."""
        result = _group_to_device({"name": "g1", "track": {"interface": ["eth1", "eth2"]}})
        self.assertEqual(result["track"]["interface"], ["eth1", "eth2"])

    def test_to_device_bool_fields(self):
        result = _group_to_device(
            {"name": "g1", "disable": True, "no_preempt": True, "rfc3768_compatibility": False},
        )
        self.assertEqual(result["disable"], {})
        self.assertEqual(result["no_preempt"], {})
        self.assertNotIn("rfc3768_compatibility", result)

    def test_from_device_vrid_and_priority_cast_to_int(self):
        entry = _group_from_device("g1", {"vrid": "20", "priority": "100"})
        self.assertEqual(entry["vrid"], 20)
        self.assertEqual(entry["priority"], 100)

    def test_from_device_address_tag_node_to_sorted_list(self):
        entry = _group_from_device(
            "g1",
            {"address": {"192.168.1.2/24": {}, "192.168.1.1/24": {}}},
        )
        self.assertEqual(entry["address"], ["192.168.1.1/24", "192.168.1.2/24"])

    def test_from_device_single_address_string_collapse(self):
        entry = _group_from_device("g1", {"address": "192.168.1.1/24"})
        self.assertEqual(entry["address"], ["192.168.1.1/24"])

    def test_from_device_track_interface_stays_plain_list(self):
        entry = _group_from_device("g1", {"track": {"interface": ["eth1", "eth2"]}})
        self.assertEqual(entry["track"]["interface"], ["eth1", "eth2"])

    def test_from_device_bool_presence_nodes(self):
        entry = _group_from_device("g1", {"disable": {}, "no-preempt": {}})
        self.assertTrue(entry["disable"])
        self.assertTrue(entry["no_preempt"])


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_disable(self):
        result = _want_to_device({"disable": True})
        self.assertEqual(result["disable"], {})

    def test_virtual_server_keyed_by_name(self):
        config = {"virtual_servers": [{"name": "s1", "address": "10.0.0.1", "port": 80}]}
        result = _want_to_device(config)
        self.assertIn("s1", result["virtual-server"])

    def test_vrrp_global_parameters_generic(self):
        config = {
            "vrrp": {"global_parameters": {"startup_delay": 30, "garp": {"master_repeat": 6}}},
        }
        result = _want_to_device(config)
        gp = result["vrrp"]["global_parameters"]
        self.assertEqual(gp["startup_delay"], 30)
        self.assertEqual(gp["garp"]["master_repeat"], 6)

    def test_snmp_enabled_becomes_presence_node(self):
        result = _want_to_device({"vrrp": {"snmp": "enabled"}})
        self.assertEqual(result["vrrp"]["snmp"], {})

    def test_snmp_disabled_not_in_want(self):
        result = _want_to_device({"vrrp": {"snmp": "disabled"}})
        self.assertNotIn("snmp", result.get("vrrp", {}))

    def test_group_keyed_by_name(self):
        config = {"vrrp": {"groups": [{"name": "g1", "vrid": 20, "interface": "eth0"}]}}
        result = _want_to_device(config)
        self.assertEqual(result["vrrp"]["group"]["g1"]["vrid"], 20)

    def test_sync_group_member_stays_plain_list(self):
        """Regression test: member is a confirmed <multi/> leafNode, not
        a tag node -- must stay a plain list."""
        config = {"vrrp": {"sync_groups": [{"name": "sg1", "member": ["g1", "g2"]}]}}
        result = _want_to_device(config)
        self.assertEqual(result["vrrp"]["sync-group"]["sg1"]["member"], ["g1", "g2"])


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_disable_parsed(self):
        result = _device_to_argspec(self.fixture)
        self.assertTrue(result["disable"])

    def test_virtual_server_parsed(self):
        result = _device_to_argspec(self.fixture)
        vs = result["virtual_servers"][0]
        self.assertEqual(vs["name"], "s1")
        self.assertEqual(vs["port"], 80)
        self.assertEqual(vs["real_server"][0]["address"], "10.10.50.2")
        self.assertEqual(vs["real_server"][0]["port"], 8443)

    def test_global_parameters_parsed(self):
        result = _device_to_argspec(self.fixture)
        gp = result["vrrp"]["global_parameters"]
        self.assertEqual(gp["startup_delay"], 30)
        self.assertEqual(gp["garp"]["master_repeat"], 6)

    def test_snmp_parsed(self):
        result = _device_to_argspec(self.fixture)
        self.assertEqual(result["vrrp"]["snmp"], "enabled")

    def test_groups_parsed_with_track_interface_as_list(self):
        result = _device_to_argspec(self.fixture)
        groups = {g["name"]: g for g in result["vrrp"]["groups"]}
        self.assertEqual(groups["g1"]["interface"], "eth0")
        self.assertEqual(groups["g1"]["vrid"], 20)
        self.assertIn("192.168.1.100/24", groups["g1"]["address"])
        self.assertTrue(groups["g1"]["no_preempt"])
        self.assertEqual(groups["g1"]["track"]["interface"], ["eth1", "eth2"])
        # g2: single address string collapsed by device -> list
        self.assertEqual(groups["g2"]["address"], ["192.168.2.100/24"])

    def test_sync_group_parsed_member_as_list(self):
        result = _device_to_argspec(self.fixture)
        sg = result["vrrp"]["sync_groups"][0]
        self.assertEqual(sg["name"], "sg1")
        self.assertEqual(sg["member"], ["g1"])
        self.assertEqual(sg["health_check"]["failure_count"], 5)
        self.assertEqual(sg["health_check"]["ping"], "192.168.1.1")

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

    def test_overridden_idempotent_against_own_fixture(self):
        """overridden is a single dict_op purge+set call (simplified from
        the original manual section-scan loop -- confirmed identical
        behavior before removing the loop)."""
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "overridden"), [])

    def test_merged_adds_vrrp_group(self):
        config = {
            "vrrp": {
                "groups": [{"name": "g3", "vrid": 30, "interface": "eth2", "priority": 100}],
            },
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(("set", _BASE + ["vrrp", "group", "g3", "vrid", "30"]), cmds)
        self.assertIn(("set", _BASE + ["vrrp", "group", "g3", "interface", "eth2"]), cmds)

    def test_overridden_deletes_omitted_top_level_section(self):
        raw_have = {"virtual-server": {"s1": {"port": "80"}}, "vrrp": {"group": {"g1": {}}}}
        config = {"vrrp": {"groups": [{"name": "g1"}]}}
        cmds = build_commands(config, raw_have, "overridden")
        self.assertIn(("delete", _BASE + ["virtual-server"]), cmds)

    def test_replaced_removes_stale_track_interface_member(self):
        """Regression test for the dict_op purge list-value fix (this
        session): track.interface being a plain list means removing a
        member under 'replaced' relies on dict_op's list-purge handling."""
        raw_have = {"vrrp": {"group": {"g1": {"track": {"interface": ["eth1", "eth2"]}}}}}
        config = {"vrrp": {"groups": [{"name": "g1", "track": {"interface": ["eth1"]}}]}}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            ("delete", _BASE + ["vrrp", "group", "g1", "track", "interface", "eth2"]),
            cmds,
        )

    def test_replaced_removes_stale_sync_group_member(self):
        raw_have = {"vrrp": {"sync-group": {"sg1": {"member": ["g1", "g2"]}}}}
        config = {"vrrp": {"sync_groups": [{"name": "sg1", "member": ["g1"]}]}}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(
            ("delete", _BASE + ["vrrp", "sync-group", "sg1", "member", "g2"]),
            cmds,
        )

    def test_snmp_disabled_deletes_presence_node(self):
        raw_have = {"vrrp": {"snmp": {}}}
        config = {"vrrp": {"snmp": "disabled"}}
        cmds = build_commands(config, raw_have, "merged")
        self.assertIn(("delete", _BASE + ["vrrp", "snmp"]), cmds)

    def test_deleted_no_have_is_noop(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_deleted_with_have(self):
        self.assertEqual(
            build_commands({}, {"vrrp": {"group": {"g1": {}}}}, "deleted"),
            [("delete", _BASE)],
        )

    def test_collapsed_track_interface_no_char_iteration_bug(self):
        """A group with exactly one tracked interface, collapsed by the
        device to a bare string, must not be iterated character-by-
        character (dict_op's own list handling corrects this natively)."""
        raw_have = {"vrrp": {"group": {"g1": {"track": {"interface": "eth1"}}}}}
        config = {"vrrp": {"groups": [{"name": "g1", "track": {"interface": ["eth1"]}}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_collapsed_sync_group_member_no_char_iteration_bug(self):
        raw_have = {"vrrp": {"sync-group": {"sg1": {"member": "g1"}}}}
        config = {"vrrp": {"sync_groups": [{"name": "sg1", "member": ["g1"]}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_virtual_server_address_never_treated_as_tag_node(self):
        """Regression test: virtual-server.<name>.address is a flat
        scalar (the load-balancer bind address), unlike vrrp.group.
        <name>.address which IS a genuine tag node (VRRP virtual IPs).
        Same key name, different device shape depending on section --
        a blanket key-name-based coercion previously corrupted this
        into a spurious diff every single run."""
        raw_have = {"virtual-server": {"s1": {"address": "10.10.10.5", "port": "80"}}}
        config = {"virtual_servers": [{"name": "s1", "address": "10.10.10.5", "port": 80}]}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])
        self.assertEqual(build_commands(config, raw_have, "replaced"), [])


if __name__ == "__main__":
    unittest.main()
