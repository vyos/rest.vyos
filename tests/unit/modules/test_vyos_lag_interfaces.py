# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_lag_interfaces import (
    _bond_base,
    _bond_cmds,
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


class TestVyOSLagInterfacesBondBase(unittest.TestCase):

    def test_bond_base(self):
        self.assertEqual(
            _bond_base("bond0"),
            ["interfaces", "bonding", "bond0"],
        )


class TestVyOSLagInterfacesGetRunningFixture(VyOSModuleTestCase):

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("lag_interfaces_running.json")

    def test_fixture_parses_bond0_mode(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        bond0 = next((e for e in result if e["name"] == "bond0"), None)
        self.assertIsNotNone(bond0)
        self.assertEqual(bond0["mode"], "active-backup")

    def test_fixture_parses_hash_policy(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        bond0 = next(e for e in result if e["name"] == "bond0")
        self.assertEqual(bond0["hash_policy"], "layer2")

    def test_fixture_parses_arp_monitor(self):
        self.set_running_config(self.fixture)
        result = get_running_config(self.mock_vyos)
        bond0 = next(e for e in result if e["name"] == "bond0")
        self.assertIn("arp_monitor", bond0)
        self.assertEqual(bond0["arp_monitor"]["interval"], 100)
        self.assertIn("192.0.2.1", bond0["arp_monitor"]["target"])

    def test_fixture_unwraps_bonding_key(self):
        # wrap in extra "bonding" key as VyOS sometimes returns
        wrapped = {"bonding": self.fixture}
        self.set_running_config(wrapped)
        result = get_running_config(self.mock_vyos)
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["name"], "bond0")


class TestVyOSLagInterfacesGetRunning(VyOSModuleTestCase):

    def test_empty_returns_empty_list(self):
        self.set_running_config({})
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result, [])

    def test_parses_mode(self):
        self.set_running_config(
            {
                "bond0": {"mode": "802.3ad"},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result[0]["mode"], "802.3ad")

    def test_parses_hash_policy(self):
        self.set_running_config(
            {
                "bond0": {"hash-policy": "layer2+3"},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result[0]["hash_policy"], "layer2+3")

    def test_parses_members(self):
        self.set_running_config(
            {
                "bond0": {"member": {"interface": {"eth1": {}, "eth2": {}}}},
            },
        )
        result = get_running_config(self.mock_vyos)
        members = [m["member"] for m in result[0]["members"]]
        self.assertIn("eth1", members)
        self.assertIn("eth2", members)

    def test_parses_arp_monitor_interval(self):
        self.set_running_config(
            {
                "bond0": {"arp-monitor": {"interval": "100"}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertEqual(result[0]["arp_monitor"]["interval"], 100)

    def test_parses_arp_monitor_target_dict(self):
        self.set_running_config(
            {
                "bond0": {"arp-monitor": {"target": {"192.0.2.1": {}}}},
            },
        )
        result = get_running_config(self.mock_vyos)
        self.assertIn("192.0.2.1", result[0]["arp_monitor"]["target"])

    def test_skips_type_keys(self):
        self.set_running_config(
            {
                "bonding": {"bond0": {"mode": "802.3ad"}},
            },
        )
        result = get_running_config(self.mock_vyos)
        # "bonding" key should be skipped
        names = [e["name"] for e in result]
        self.assertNotIn("bonding", names)


class TestVyOSLagInterfacesNormalize(unittest.TestCase):

    def test_normalize_basic(self):
        config = [{"name": "bond0", "mode": "802.3ad", "hash_policy": "layer2"}]
        result = _normalize(config)
        self.assertIn("bond0", result)
        self.assertEqual(result["bond0"]["mode"], "802.3ad")
        self.assertEqual(result["bond0"]["hash_policy"], "layer2")

    def test_normalize_members_sorted(self):
        config = [
            {
                "name": "bond0",
                "members": [{"member": "eth2"}, {"member": "eth1"}],
            },
        ]
        result = _normalize(config)
        self.assertEqual(result["bond0"]["members"], ["eth1", "eth2"])

    def test_normalize_arp_targets_sorted(self):
        config = [
            {
                "name": "bond0",
                "arp_monitor": {"interval": 100, "target": ["192.0.2.2", "192.0.2.1"]},
            },
        ]
        result = _normalize(config)
        self.assertEqual(result["bond0"]["arp_targets"], ["192.0.2.1", "192.0.2.2"])

    def test_normalize_empty(self):
        result = _normalize([])
        self.assertEqual(result, {})


class TestVyOSLagInterfacesBondCmds(unittest.TestCase):

    def test_set_mode(self):
        want = {"mode": "802.3ad"}
        cmds = _bond_cmds("bond0", want, {})
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "mode", "802.3ad"]),
            cmds,
        )

    def test_set_hash_policy(self):
        want = {"hash_policy": "layer2"}
        cmds = _bond_cmds("bond0", want, {})
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "hash-policy", "layer2"]),
            cmds,
        )

    def test_set_member(self):
        want = {"members": ["eth1"]}
        cmds = _bond_cmds("bond0", want, {})
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "member", "interface", "eth1"]),
            cmds,
        )

    def test_set_arp_interval(self):
        want = {"arp_interval": 100}
        cmds = _bond_cmds("bond0", want, {})
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "arp-monitor", "interval", "100"]),
            cmds,
        )

    def test_set_arp_target(self):
        want = {"arp_targets": ["192.0.2.1"]}
        cmds = _bond_cmds("bond0", want, {})
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "arp-monitor", "target", "192.0.2.1"]),
            cmds,
        )

    def test_idempotent_mode(self):
        want = {"mode": "802.3ad"}
        have = {"mode": "802.3ad"}
        cmds = _bond_cmds("bond0", want, have)
        self.assertEqual(cmds, [])

    def test_no_commands_when_empty_want(self):
        cmds = _bond_cmds("bond0", {}, {})
        self.assertEqual(cmds, [])


class TestVyOSLagInterfacesBuildCommands(unittest.TestCase):

    def _have_bond0(self):
        return [
            {
                "name": "bond0",
                "mode": "active-backup",
                "hash_policy": "layer2",
                "arp_monitor": {"interval": 100, "target": ["192.0.2.1"]},
            },
        ]

    def test_merged_adds_bond(self):
        config = [{"name": "bond0", "mode": "802.3ad"}]
        cmds = build_commands(config, [], "merged")
        self.assertIn(
            ("set", ["interfaces", "bonding", "bond0", "mode", "802.3ad"]),
            cmds,
        )

    def test_merged_idempotent(self):
        cmds = build_commands(self._have_bond0(), self._have_bond0(), "merged")
        self.assertEqual(cmds, [])

    def test_deleted_no_config_removes_all(self):
        cmds = build_commands([], self._have_bond0(), "deleted")
        self.assertIn(
            ("delete", ["interfaces", "bonding", "bond0"]),
            cmds,
        )

    def test_deleted_with_name_removes_bond(self):
        config = [{"name": "bond0"}]
        cmds = build_commands(config, self._have_bond0(), "deleted")
        self.assertIn(
            ("delete", ["interfaces", "bonding", "bond0"]),
            cmds,
        )

    def test_deleted_idempotent_when_empty(self):
        cmds = build_commands([], [], "deleted")
        self.assertEqual(cmds, [])

    def test_replaced_idempotent(self):
        cmds = build_commands(self._have_bond0(), self._have_bond0(), "replaced")
        self.assertEqual(cmds, [])

    def test_overridden_removes_unlisted_bond(self):
        config = [{"name": "bond1", "mode": "802.3ad"}]
        cmds = build_commands(config, self._have_bond0(), "overridden")
        self.assertIn(
            ("delete", ["interfaces", "bonding", "bond0"]),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
