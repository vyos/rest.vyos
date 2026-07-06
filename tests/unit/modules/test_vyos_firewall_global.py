# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.module_utils.vyos import dict_op
from ansible_collections.vyos.rest.plugins.modules.vyos_firewall_global import (
    _device_to_argspec,
    _groups_from_device,
    _groups_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["firewall", "group"]


class TestGroupHelpers(unittest.TestCase):
    """Test group list <-> device dict conversion helpers."""

    def test_groups_to_device_with_members(self):
        groups = [{"name": "SERVERS", "address": ["192.168.1.10", "192.168.1.11"]}]
        result = _groups_to_device(groups, "address")
        self.assertIn("SERVERS", result)
        self.assertIn("192.168.1.10", result["SERVERS"]["address"])
        self.assertIn("192.168.1.11", result["SERVERS"]["address"])

    def test_groups_to_device_with_description(self):
        groups = [{"name": "LAN", "description": "Local network", "network": ["192.168.0.0/16"]}]
        result = _groups_to_device(groups, "network")
        self.assertEqual(result["LAN"]["description"], "Local network")

    def test_groups_to_device_empty(self):
        self.assertEqual(_groups_to_device([], "address"), {})
        self.assertEqual(_groups_to_device(None, "address"), {})

    def test_groups_from_device_with_members(self):
        raw = {"SERVERS": {"address": {"192.168.1.10": {}, "192.168.1.11": {}}}}
        result = _groups_from_device(raw, "address")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "SERVERS")
        self.assertIn("192.168.1.10", result[0]["address"])

    def test_groups_from_device_single_member_string(self):
        # VyOS returns single member as string
        raw = {"WEB": {"port": "80"}}
        result = _groups_from_device(raw, "port")
        self.assertIn("80", result[0]["port"])

    def test_groups_from_device_with_description(self):
        raw = {"LAN": {"description": "Local", "network": {"192.168.0.0/16": {}}}}
        result = _groups_from_device(raw, "network")
        self.assertEqual(result[0]["description"], "Local")

    def test_groups_from_device_sorted(self):
        raw = {"Z-GROUP": {}, "A-GROUP": {}}
        result = _groups_from_device(raw, "address")
        self.assertEqual(result[0]["name"], "A-GROUP")
        self.assertEqual(result[1]["name"], "Z-GROUP")

    def test_groups_from_device_empty(self):
        self.assertEqual(_groups_from_device({}, "address"), [])
        self.assertEqual(_groups_from_device(None, "address"), [])


class TestWantToDevice(unittest.TestCase):
    """Test argspec -> device shape conversion."""

    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_address_group(self):
        config = {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "address": ["192.168.1.10"]},
                ],
            },
        }
        result = _want_to_device(config)
        self.assertIn("address-group", result)
        self.assertIn("SERVERS", result["address-group"])
        self.assertIn("192.168.1.10", result["address-group"]["SERVERS"]["address"])

    def test_network_group(self):
        config = {
            "group": {
                "network_group": [{"name": "LAN", "network": ["192.168.0.0/16"]}],
            },
        }
        result = _want_to_device(config)
        self.assertIn("network-group", result)
        self.assertIn("LAN", result["network-group"])

    def test_port_group(self):
        config = {
            "group": {
                "port_group": [{"name": "WEB", "port": ["80", "443"]}],
            },
        }
        result = _want_to_device(config)
        self.assertIn("port-group", result)
        self.assertIn("80", result["port-group"]["WEB"]["port"])

    def test_interface_group(self):
        config = {
            "group": {
                "interface_group": [{"name": "LAN-IFACES", "interface": ["eth1"]}],
            },
        }
        result = _want_to_device(config)
        self.assertIn("interface-group", result)

    def test_ipv6_network_group(self):
        config = {
            "group": {
                "ipv6_network_group": [{"name": "IPV6-LAN", "network": ["2001:db8::/32"]}],
            },
        }
        result = _want_to_device(config)
        self.assertIn("ipv6-network-group", result)


class TestDeviceToArgspec(unittest.TestCase):
    """Test device response -> argspec shape conversion."""

    def test_empty(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})

    def test_address_group(self):
        raw = {
            "address-group": {
                "SERVERS": {
                    "description": "Web servers",
                    "address": {"192.168.1.10": {}, "192.168.1.11": {}},
                },
            },
        }
        result = _device_to_argspec(raw)
        groups = result["group"]["address_group"]
        servers = next(g for g in groups if g["name"] == "SERVERS")
        self.assertEqual(servers["description"], "Web servers")
        self.assertIn("192.168.1.10", servers["address"])

    def test_no_group_returns_empty(self):
        self.assertEqual(_device_to_argspec({}), {})


class TestDeviceToArgspecFixture(unittest.TestCase):
    """Test _device_to_argspec against fixture."""

    def setUp(self):
        self.fixture = load_fixture("firewall_global_running.json")

    def test_parses_address_groups(self):
        result = _device_to_argspec(self.fixture)
        groups = result["group"]["address_group"]
        names = [g["name"] for g in groups]
        self.assertIn("SERVERS", names)
        self.assertIn("DNS", names)
        servers = next(g for g in groups if g["name"] == "SERVERS")
        self.assertEqual(servers["description"], "Web servers")
        self.assertIn("192.168.1.10", servers["address"])

    def test_parses_network_groups(self):
        result = _device_to_argspec(self.fixture)
        groups = result["group"]["network_group"]
        dmz = next(g for g in groups if g["name"] == "DMZ")
        self.assertIn("10.0.0.0/8", dmz["network"])

    def test_parses_port_groups(self):
        result = _device_to_argspec(self.fixture)
        groups = result["group"]["port_group"]
        web = next(g for g in groups if g["name"] == "WEB-PORTS")
        self.assertIn("80", web["port"])

    def test_parses_interface_groups(self):
        result = _device_to_argspec(self.fixture)
        groups = result["group"]["interface_group"]
        lan = next(g for g in groups if g["name"] == "LAN-IFACES")
        self.assertIn("eth1", lan["interface"])

    def test_parses_ipv6_network_groups(self):
        result = _device_to_argspec(self.fixture)
        groups = result["group"]["ipv6_network_group"]
        ipv6 = next(g for g in groups if g["name"] == "IPV6-LAN")
        self.assertIn("2001:db8::/32", ipv6["network"])

    def test_empty_config(self):
        result = _device_to_argspec({})
        self.assertEqual(result, {})


class TestDictOpFirewall(unittest.TestCase):
    """Test dict_op behaviour with firewall group shapes."""

    def test_merged_adds_address_group(self):
        want = _want_to_device(
            {
                "group": {
                    "address_group": [{"name": "SERVERS", "address": ["192.168.1.10"]}],
                },
            },
        )
        cmds = dict_op(want, {}, _BASE, op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["address-group", "SERVERS", "address", "192.168.1.10"], paths)

    def test_merged_idempotent(self):
        config = {
            "group": {
                "address_group": [{"name": "SERVERS", "address": ["192.168.1.10"]}],
            },
        }
        want = _want_to_device(config)
        have = {"address-group": {"SERVERS": {"address": {"192.168.1.10": {}}}}}
        cmds = dict_op(want, have, _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_merged_adds_network_group(self):
        want = _want_to_device(
            {
                "group": {
                    "network_group": [{"name": "LAN", "network": ["192.168.0.0/16"]}],
                },
            },
        )
        cmds = dict_op(want, {}, _BASE, op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["network-group", "LAN", "network", "192.168.0.0/16"], paths)

    def test_purge_removes_extra_group(self):
        want = _want_to_device(
            {
                "group": {
                    "network_group": [{"name": "DMZ", "network": ["10.0.0.0/8"]}],
                },
            },
        )
        have = {
            "address-group": {"SERVERS": {"address": {"192.168.1.10": {}}}},
            "network-group": {"LAN": {"network": {"192.168.0.0/16": {}}}},
        }
        cmds = dict_op(want, have, _BASE, op="purge")
        paths = [c[1] for c in cmds]
        # address-group entirely absent from want -> whole type deleted
        self.assertIn(_BASE + ["address-group"], paths)
        self.assertIn(_BASE + ["network-group", "LAN"], paths)

    def test_merged_idempotent_with_description(self):
        """Regression test: the original implementation's have-side
        normalization corrupted plain scalar fields (description) into
        bogus presence-dicts via the same blanket conversion used for
        member lists, breaking idempotency for any group with a
        description set. Fixed by using dict_op's native list handling
        for members and never touching scalar fields at all."""
        config = {
            "group": {
                "address_group": [
                    {"name": "SERVERS", "description": "Web servers", "address": ["10.0.0.1"]},
                ],
            },
        }
        want = _want_to_device(config)
        have = {
            "address-group": {
                "SERVERS": {"description": "Web servers", "address": ["10.0.0.1"]},
            },
        }
        cmds = dict_op(want, have, _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_replaced_removes_stale_member(self):
        """Regression test: dict_op's purge mode originally had no
        handling for list-valued leaves (only dicts), so a member
        present on the device but absent from the desired list was
        silently never removed under 'replaced'. Fixed centrally in
        dict_op itself."""
        want = _want_to_device(
            {"group": {"address_group": [{"name": "SERVERS", "address": ["10.0.0.1"]}]}},
        )
        have = {"address-group": {"SERVERS": {"address": ["10.0.0.1", "10.0.0.2"]}}}
        cmds = dict_op(want, have, _BASE, op="purge")
        self.assertIn(
            ("delete", _BASE + ["address-group", "SERVERS", "address", "10.0.0.2"]),
            cmds,
        )

    def test_deleted_removes_base(self):
        # deleted state is handled in main() not dict_op
        # just verify want_to_device produces correct shape
        want = _want_to_device({})
        self.assertEqual(want, {})


class TestBuildCommands(unittest.TestCase):
    """build_commands/get_running_config were extracted from main() during
    the dict_op refactor so they're independently testable."""

    def test_get_running_config_fetches_at_base(self):
        from unittest.mock import MagicMock

        mock_vyos = MagicMock()
        mock_vyos.get_config = MagicMock(return_value={"address-group": {}})
        get_running_config(mock_vyos)
        mock_vyos.get_config.assert_called_once_with(_BASE)

    def test_merged_idempotent_against_fixture(self):
        fixture = load_fixture("firewall_global_running.json")
        have = _device_to_argspec(fixture)
        self.assertEqual(build_commands(have, fixture, "merged"), [])

    def test_replaced_idempotent_against_fixture(self):
        fixture = load_fixture("firewall_global_running.json")
        have = _device_to_argspec(fixture)
        self.assertEqual(build_commands(have, fixture, "replaced"), [])

    def test_deleted_no_have_is_noop(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_deleted_with_have(self):
        self.assertEqual(
            build_commands({}, {"address-group": {"SERVERS": {}}}, "deleted"),
            [("delete", _BASE)],
        )

    def test_single_value_member_collapse_no_char_iteration_bug(self):
        """A group with exactly one member, collapsed by the device to a
        bare string instead of a list, must not be iterated
        character-by-character."""
        raw_have = {"port-group": {"WEB": {"port": "80"}}}
        config = {"group": {"port_group": [{"name": "WEB", "port": ["80"]}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_group_tag_node_collapse_no_char_iteration_bug(self):
        """A single group with zero other fields, collapsed by the
        device to a bare group-name string, must not be iterated
        character-by-character."""
        raw_have = {"address-group": "SERVERS"}
        config = {"group": {"address_group": [{"name": "SERVERS"}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])


if __name__ == "__main__":
    unittest.main()
