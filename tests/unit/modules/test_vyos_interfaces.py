# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_interfaces import (
    _delete_iface_config,
    _iface_base,
    _iface_cmds,
    _iface_type,
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


class TestVyOSInterfacesIfaceType(unittest.TestCase):

    def test_eth_is_ethernet(self):
        self.assertEqual(_iface_type("eth0"), "ethernet")

    def test_bond_is_bonding(self):
        self.assertEqual(_iface_type("bond0"), "bonding")

    def test_lo_is_loopback(self):
        self.assertEqual(_iface_type("lo"), "loopback")

    def test_wg_is_wireguard(self):
        self.assertEqual(_iface_type("wg0"), "wireguard")

    def test_br_is_bridge(self):
        self.assertEqual(_iface_type("br0"), "bridge")

    def test_unknown_defaults_to_ethernet(self):
        self.assertEqual(_iface_type("xyz0"), "ethernet")

    def test_iface_base_ethernet(self):
        self.assertEqual(
            _iface_base("eth0"),
            ["interfaces", "ethernet", "eth0"],
        )

    def test_iface_base_loopback(self):
        self.assertEqual(
            _iface_base("lo"),
            ["interfaces", "loopback", "lo"],
        )


class TestVyOSInterfacesGetRunningFixture(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("interfaces_running.json")

    def test_fixture_parses_eth0(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertEqual(eth0["description"], "Management")
        self.assertEqual(eth0["mtu"], 1500)
        self.assertEqual(eth0["duplex"], "auto")
        self.assertEqual(eth0["speed"], "auto")
        self.assertTrue(eth0["enabled"])

    def test_fixture_parses_loopback(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        lo = next(e for e in result if e["name"] == "lo")
        self.assertTrue(lo["enabled"])
        self.assertNotIn("description", lo)

    def test_fixture_disabled_interface(self):
        fixture = dict(self.fixture)
        fixture["ethernet"]["eth1"] = {"disable": {}, "description": "Unused"}
        self.set_running_config(fixture)
        result = get_running_config(self.mock_vyos)
        eth1 = next(e for e in result if e["name"] == "eth1")
        self.assertFalse(eth1["enabled"])


class TestVyOSInterfacesGetRunning(VyOSModuleTestCase):

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_mtu_cast_to_int(self):
        self.set_running_config(
            {
                "ethernet": {
                    "eth0": {"mtu": "1500"},
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertIsInstance(eth0["mtu"], int)
        self.assertEqual(eth0["mtu"], 1500)

    def test_hw_id_not_included(self):
        self.set_running_config(
            {
                "ethernet": {
                    "eth0": {"hw-id": "52:54:00:65:5a:24"},
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertNotIn("hw_id", eth0)
        self.assertNotIn("hw-id", eth0)

    def test_enabled_true_when_no_disable(self):
        self.set_running_config(
            {
                "ethernet": {"eth0": {}},
            },
        )
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertTrue(eth0["enabled"])

    def test_enabled_false_when_disable_present(self):
        self.set_running_config(
            {
                "ethernet": {"eth0": {"disable": {}}},
            },
        )
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertFalse(eth0["enabled"])


class TestVyOSInterfacesIfaceCmds(unittest.TestCase):

    def test_set_description(self):
        want = {"description": "WAN", "enabled": True}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "description", "WAN"]),
            cmds,
        )

    def test_set_mtu(self):
        want = {"mtu": 9000, "enabled": True}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "mtu", "9000"]),
            cmds,
        )

    def test_set_duplex(self):
        want = {"duplex": "full", "enabled": True}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "duplex", "full"]),
            cmds,
        )

    def test_set_speed(self):
        want = {"speed": "1000", "enabled": True}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "speed", "1000"]),
            cmds,
        )

    def test_disable_interface(self):
        want = {"enabled": False}
        have = {"enabled": True}
        cmds = _iface_cmds("eth0", want, have)
        self.assertIn(
            ("set", ["interfaces", "ethernet", "eth0", "disable"]),
            cmds,
        )

    def test_enable_interface(self):
        want = {"enabled": True}
        have = {"enabled": False}
        cmds = _iface_cmds("eth0", want, have)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "disable"]),
            cmds,
        )

    def test_idempotent_description(self):
        want = {"description": "WAN", "enabled": True}
        have = {"description": "WAN", "enabled": True}
        cmds = _iface_cmds("eth0", want, have)
        self.assertEqual(cmds, [])

    def test_delete_description_when_none(self):
        want = {"enabled": True}
        have = {"description": "Old", "enabled": True}
        cmds = _iface_cmds("eth0", want, have)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "description"]),
            cmds,
        )


class TestVyOSInterfacesDeleteIfaceConfig(unittest.TestCase):

    def test_deletes_all_l2_fields(self):
        have = {
            "description": "WAN",
            "mtu": 1500,
            "duplex": "auto",
            "speed": "auto",
            "enabled": True,
        }
        cmds = _delete_iface_config("eth0", have)
        paths = [c[1] for c in cmds]
        self.assertIn(["interfaces", "ethernet", "eth0", "description"], paths)
        self.assertIn(["interfaces", "ethernet", "eth0", "mtu"], paths)
        self.assertIn(["interfaces", "ethernet", "eth0", "duplex"], paths)
        self.assertIn(["interfaces", "ethernet", "eth0", "speed"], paths)

    def test_deletes_disable_when_disabled(self):
        have = {"enabled": False}
        cmds = _delete_iface_config("eth0", have)
        self.assertIn(
            ("delete", ["interfaces", "ethernet", "eth0", "disable"]),
            cmds,
        )

    def test_empty_have_produces_no_commands(self):
        cmds = _delete_iface_config("eth0", {})
        self.assertEqual(cmds, [])


class TestVyOSInterfacesBuildCommands(unittest.TestCase):

    def _have_eth0(self):
        return [
            {
                "name": "eth0",
                "description": "Management",
                "mtu": 1500,
                "enabled": True,
            },
        ]

    def test_merged_adds_description(self):
        config = [{"name": "eth0", "description": "WAN", "enabled": True}]
        cmds = build_commands(config, [], "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(
            ["interfaces", "ethernet", "eth0", "description", "WAN"],
            paths,
        )

    def test_merged_idempotent(self):
        cmds = build_commands(self._have_eth0(), self._have_eth0(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_removes_l2_fields(self):
        config = [{"name": "eth0", "enabled": True}]
        cmds = build_commands(config, self._have_eth0(), "deleted")
        paths = [c[1] for c in cmds]
        self.assertIn(["interfaces", "ethernet", "eth0", "description"], paths)
        self.assertIn(["interfaces", "ethernet", "eth0", "mtu"], paths)

    def test_deleted_idempotent_when_no_l2(self):
        have = [{"name": "eth0", "enabled": True}]
        config = [{"name": "eth0", "enabled": True}]
        cmds = build_commands(config, have, "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        cmds = build_commands(self._have_eth0(), self._have_eth0(), "replaced")
        self.assertEqual(cmds, [])

    def test_replaced_updates_description(self):
        config = [{"name": "eth0", "description": "NEW", "mtu": 1500, "enabled": True}]
        cmds = build_commands(config, self._have_eth0(), "replaced")
        self.assertTrue(len(cmds) > 0)

    def test_overridden_clears_interfaces_not_in_want(self):
        have = [
            {"name": "eth0", "description": "Management", "enabled": True},
            {"name": "eth1", "description": "LAN", "enabled": True},
        ]
        config = [{"name": "eth0", "description": "Management", "enabled": True}]
        cmds = build_commands(config, have, "overridden")
        paths = [c[1] for c in cmds]
        self.assertIn(["interfaces", "ethernet", "eth1", "description"], paths)


if __name__ == "__main__":
    unittest.main()
