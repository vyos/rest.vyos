# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_lldp_interfaces import (
    _iface_base,
    _iface_cmds,
    _normalize,
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


class TestVyOSLldpInterfacesIfaceBase(unittest.TestCase):

    def test_iface_base(self):
        self.assertEqual(
            _iface_base("eth0"),
            ["service", "lldp", "interface", "eth0"],
        )


class TestVyOSLldpInterfacesGetRunningFixture(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("lldp_interfaces_running.json")

    def test_fixture_parses_eth0_mode(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth0 = next((e for e in result if e["name"] == "eth0"), None)
        self.assertIsNotNone(eth0)
        self.assertEqual(eth0["mode"], "disable")

    def test_fixture_parses_elin(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth0 = next(e for e in result if e["name"] == "eth0")
        self.assertEqual(eth0["location"]["elin"], "1234567890")

    def test_fixture_parses_coordinate_based(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        eth1 = next((e for e in result if e["name"] == "eth1"), None)
        self.assertIsNotNone(eth1)
        cb = eth1["location"]["coordinate_based"]
        self.assertEqual(cb["latitude"], "33.524449N")
        self.assertEqual(cb["longitude"], "22.267255E")
        self.assertEqual(cb["altitude"], 2200)
        self.assertEqual(cb["datum"], "WGS84")


class TestVyOSLldpInterfacesGetRunning(VyOSModuleTestCase):

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_no_interface_returns_empty(self):
        self.set_running_config({"snmp": "enable"})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_parses_mode(self):
        self.set_running_config(
            {
                "interface": {"eth0": {"mode": "rx-tx"}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result[0]["mode"], "rx-tx")

    def test_parses_elin(self):
        self.set_running_config(
            {
                "interface": {"eth0": {"location": {"elin": "9876543210"}}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result[0]["location"]["elin"], "9876543210")

    def test_parses_coordinate_based(self):
        self.set_running_config(
            {
                "interface": {
                    "eth0": {
                        "location": {
                            "coordinate-based": {
                                "latitude": "33.524449N",
                                "longitude": "22.267255E",
                                "altitude": "2200",
                                "datum": "WGS84",
                            },
                        },
                    },
                },
            },
        )
        result = get_running_config(self.mock_vyos)
        cb = result[0]["location"]["coordinate_based"]
        self.assertEqual(cb["latitude"], "33.524449N")
        self.assertEqual(cb["altitude"], 2200)

    def test_no_mode_not_in_entry(self):
        self.set_running_config(
            {
                "interface": {"eth0": {"location": {"elin": "1234567890"}}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertNotIn("mode", result[0])


class TestVyOSLldpInterfacesNormalize(unittest.TestCase):

    def test_normalize_mode(self):
        config = [{"name": "eth0", "mode": "disable"}]
        result = _normalize(config)
        self.assertEqual(result["eth0"]["mode"], "disable")

    def test_normalize_elin(self):
        config = [{"name": "eth0", "location": {"elin": "1234567890"}}]
        result = _normalize(config)
        self.assertEqual(result["eth0"]["elin"], "1234567890")

    def test_normalize_coordinate_based(self):
        config = [
            {
                "name": "eth0",
                "location": {
                    "coordinate_based": {
                        "latitude": "33.524449N",
                        "longitude": "22.267255E",
                        "altitude": 2200,
                        "datum": "WGS84",
                    },
                },
            },
        ]
        result = _normalize(config)
        self.assertEqual(result["eth0"]["latitude"], "33.524449N")
        self.assertEqual(result["eth0"]["altitude"], 2200)

    def test_normalize_empty(self):
        result = _normalize([])
        self.assertEqual(result, {})


class TestVyOSLldpInterfacesIfaceCmds(unittest.TestCase):

    def test_set_mode(self):
        want = {"mode": "disable"}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["service", "lldp", "interface", "eth0", "mode", "disable"]),
            cmds,
        )

    def test_set_elin(self):
        want = {"elin": "1234567890"}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            ("set", ["service", "lldp", "interface", "eth0", "location", "elin", "1234567890"]),
            cmds,
        )

    def test_set_latitude(self):
        want = {"latitude": "33.524449N", "longitude": "22.267255E"}
        cmds = _iface_cmds("eth0", want, {})
        self.assertIn(
            (
                "set",
                [
                    "service",
                    "lldp",
                    "interface",
                    "eth0",
                    "location",
                    "coordinate-based",
                    "latitude",
                    "33.524449N",
                ],
            ),
            cmds,
        )

    def test_idempotent_mode(self):
        want = {"mode": "disable"}
        have = {"mode": "disable"}
        cmds = _iface_cmds("eth0", want, have)
        self.assertEqual(cmds, [])

    def test_idempotent_elin(self):
        want = {"elin": "1234567890"}
        have = {"elin": "1234567890"}
        cmds = _iface_cmds("eth0", want, have)
        self.assertEqual(cmds, [])

    def test_delete_mode_when_none(self):
        want = {}
        have = {"mode": "disable"}
        cmds = _iface_cmds("eth0", want, have)
        self.assertIn(
            ("delete", ["service", "lldp", "interface", "eth0", "mode"]),
            cmds,
        )


class TestVyOSLldpInterfacesBuildCommands(unittest.TestCase):

    def _have_eth0(self):
        return [
            {
                "name": "eth0",
                "mode": "disable",
                "location": {"elin": "1234567890"},
            },
        ]

    def test_merged_adds_interface(self):
        config = [{"name": "eth0", "mode": "disable"}]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", ["service", "lldp", "interface", "eth0", "mode", "disable"]),
            cmds,
        )

    def test_merged_idempotent(self):
        cmds = build_commands(self._have_eth0(), self._have_eth0(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self._have_eth0(), "deleted")
        self.assertIn(
            ("delete", ["service", "lldp", "interface", "eth0"]),
            cmds,
        )

    def test_deleted_with_config_removes_named(self):
        config = [{"name": "eth0"}]
        cmds = build_commands(config, self._have_eth0(), "deleted")
        self.assertIn(
            ("delete", ["service", "lldp", "interface", "eth0"]),
            cmds,
        )

    def test_deleted_idempotent_when_empty(self):
        cmds = build_commands([], [], "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        cmds = build_commands(self._have_eth0(), self._have_eth0(), "replaced")
        self.assertEqual(cmds, [])

    def test_overridden_removes_unlisted(self):
        config = [{"name": "eth1", "mode": "rx-tx"}]
        cmds = build_commands(config, self._have_eth0(), "overridden")
        self.assertIn(
            ("delete", ["service", "lldp", "interface", "eth0"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
