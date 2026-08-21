# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_bgp_address_family import (
    _device_to_argspec,
    _global_af_from_device,
    _global_af_to_device,
    _neighbor_af_from_device,
    _neighbor_af_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["protocols", "bgp"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("bgp_af_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestNeighborAfToDevice(unittest.TestCase):
    """The three genuine device-shape exceptions, individually, plus proof
    that everything else is untouched by _autoclean alone."""

    def test_soft_reconfiguration_nests_under_inbound(self):
        result = _neighbor_af_to_device([{"afi": "ipv4", "soft_reconfiguration": True}])
        self.assertEqual(result, {"ipv4-unicast": {"soft_reconfiguration": {"inbound": {}}}})

    def test_allowas_in_wraps_under_number(self):
        result = _neighbor_af_to_device([{"afi": "ipv4", "allowas_in": 3}])
        self.assertEqual(result, {"ipv4-unicast": {"allowas_in": {"number": 3}}})

    def test_capability_orf_value_becomes_dict_key(self):
        result = _neighbor_af_to_device([{"afi": "ipv4", "capability": {"orf": "send"}}])
        self.assertEqual(
            result,
            {"ipv4-unicast": {"capability": {"orf": {"prefix-list": {"send": {}}}}}},
        )

    def test_generic_options_pass_through_autoclean_only(self):
        result = _neighbor_af_to_device(
            [
                {
                    "afi": "ipv4",
                    "nexthop_self": True,
                    "weight": 50,
                    "route_map": {"import": "RM-IN"},
                    "distribute_list": {"import": 10, "export": 20},
                    "attribute_unchanged": {"as_path": True, "next_hop": False},
                },
            ],
        )
        self.assertEqual(
            result,
            {
                "ipv4-unicast": {
                    "nexthop_self": {},
                    "weight": 50,
                    "route_map": {"import": "RM-IN"},
                    "distribute_list": {"import": 10, "export": 20},
                    "attribute_unchanged": {"as_path": {}},
                },
            },
        )

    def test_no_options_is_bare_presence(self):
        self.assertEqual(_neighbor_af_to_device([{"afi": "ipv4"}]), {"ipv4-unicast": {}})


class TestNeighborAfFromDevice(unittest.TestCase):
    def test_soft_reconfiguration_from_nested_inbound(self):
        result = _neighbor_af_from_device(
            {"ipv4-unicast": {"soft-reconfiguration": {"inbound": {}}}},
        )
        self.assertEqual(result, [{"afi": "ipv4", "soft_reconfiguration": True}])

    def test_allowas_in_from_number_wrapper(self):
        result = _neighbor_af_from_device({"ipv4-unicast": {"allowas-in": {"number": "3"}}})
        self.assertEqual(result, [{"afi": "ipv4", "allowas_in": 3}])

    def test_allowas_in_bare_presence_defaults_to_one(self):
        result = _neighbor_af_from_device({"ipv4-unicast": {"allowas-in": {}}})
        self.assertEqual(result, [{"afi": "ipv4", "allowas_in": 1}])

    def test_capability_orf_receive_and_send(self):
        r1 = _neighbor_af_from_device(
            {"ipv4-unicast": {"capability": {"orf": {"prefix-list": {"receive": {}}}}}},
        )
        self.assertEqual(r1[0]["capability"], {"orf": "receive"})
        r2 = _neighbor_af_from_device(
            {"ipv4-unicast": {"capability": {"orf": {"prefix-list": {"send": {}}}}}},
        )
        self.assertEqual(r2[0]["capability"], {"orf": "send"})

    def test_ints_cast_via_argspec_not_hardcoded_list(self):
        result = _neighbor_af_from_device(
            {
                "ipv4-unicast": {
                    "maximum-prefix": "100",
                    "weight": "50",
                    "distribute-list": {"import": "10", "export": "20"},
                },
            },
        )
        entry = result[0]
        self.assertEqual(entry["maximum_prefix"], 100)
        self.assertEqual(entry["weight"], 50)
        self.assertEqual(entry["distribute_list"], {"import": 10, "export": 20})


class TestGlobalAfToDeviceFromDevice(unittest.TestCase):
    def test_networks_keyed_by_prefix(self):
        result = _global_af_to_device(
            [{"afi": "ipv4", "networks": [{"prefix": "192.0.2.0/24", "backdoor": True}]}],
        )
        self.assertEqual(
            result,
            {"ipv4-unicast": {"network": {"192.0.2.0/24": {"backdoor": {}}}}},
        )

    def test_redistribute_keyed_by_protocol(self):
        result = _global_af_to_device(
            [{"afi": "ipv4", "redistribute": [{"protocol": "connected", "metric": 10}]}],
        )
        self.assertEqual(
            result,
            {"ipv4-unicast": {"redistribute": {"connected": {"metric": 10}}}},
        )

    def test_from_device_metric_cast_via_argspec(self):
        result = _global_af_from_device(
            {"ipv4-unicast": {"redistribute": {"connected": {"metric": "10"}}}},
        )
        self.assertEqual(result[0]["redistribute"], [{"protocol": "connected", "metric": 10}])


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_as_number(self):
        self.assertEqual(_device_to_argspec(self.fixture)["as_number"], 65000)

    def test_global_networks_and_redistribute(self):
        af = _device_to_argspec(self.fixture)["address_family"][0]
        prefixes = {n["prefix"]: n for n in af["networks"]}
        self.assertEqual(
            prefixes["192.0.3.0/24"],
            {"prefix": "192.0.3.0/24", "route_map": "RM-OUT", "backdoor": True},
        )
        protocols = {r["protocol"]: r for r in af["redistribute"]}
        self.assertEqual(protocols["connected"]["metric"], 10)

    def test_neighbor_wired_options(self):
        nb = _device_to_argspec(self.fixture)["neighbors"][0]
        ipv4 = next(af for af in nb["address_family"] if af["afi"] == "ipv4")
        self.assertTrue(ipv4["nexthop_self"])
        self.assertTrue(ipv4["soft_reconfiguration"])
        self.assertEqual(ipv4["attribute_unchanged"], {"as_path": True, "med": True})
        self.assertEqual(ipv4["capability"], {"orf": "receive"})
        self.assertEqual(ipv4["distribute_list"], {"import": 10, "export": 20})

    def test_empty_config(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})


class TestBuildCommands(VyOSModuleTestCase):
    """End-to-end, exactly as main() calls it."""

    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_merged_new_option(self):
        have = _device_to_argspec(self.fixture)
        have["neighbors"][0]["address_family"][0]["weight"] = 200
        cmds = build_commands(have, self.fixture, "merged")
        self.assertIn(
            (
                "set",
                _BASE
                + ["neighbor", "192.0.2.1", "address-family", "ipv4-unicast", "weight", "200"],
            ),
            cmds,
        )

    def test_replaced_never_touches_neighbor_siblings(self):
        """Regression test: dict_op is scoped strictly to each neighbor's
        address-family subtree, never the whole neighbor.<addr> entry, so
        fields owned by other modules (remote-as, timers, ...) are safe."""
        cmds = build_commands({"as_number": 65000}, self.fixture, "replaced")
        self.assertTrue(all("remote-as" not in c[1] for c in cmds))
        self.assertIn(
            ("delete", _BASE + ["neighbor", "192.0.2.1", "address-family", "ipv4-unicast"]),
            cmds,
        )
        self.assertIn(
            ("delete", _BASE + ["neighbor", "192.0.2.1", "address-family", "ipv6-unicast"]),
            cmds,
        )

    def test_deleted_scoped_to_address_family_only(self):
        cmds = build_commands({}, self.fixture, "deleted")
        self.assertIn(("delete", _BASE + ["address-family"]), cmds)
        self.assertIn(
            ("delete", _BASE + ["neighbor", "192.0.2.1", "address-family"]),
            cmds,
        )
        self.assertTrue(all(c[1] != _BASE + ["neighbor", "192.0.2.1"] for c in cmds))

    def test_normalize_have_prevents_char_iteration_bug(self):
        """A single-child tag node collapsed to a bare string by the
        device must not be iterated character-by-character."""
        raw_have = {"address-family": {"ipv4-unicast": {"network": "192.0.2.0/24"}}}
        config = {
            "as_number": 65000,
            "address_family": [{"afi": "ipv4", "networks": [{"prefix": "192.0.2.0/24"}]}],
        }
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_fresh_merged_add(self):
        config = {
            "as_number": 65000,
            "neighbors": [
                {
                    "neighbor_address": "10.0.0.1",
                    "address_family": [{"afi": "ipv4", "weight": 200}],
                },
            ],
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            (
                "set",
                _BASE + ["neighbor", "10.0.0.1", "address-family", "ipv4-unicast", "weight", "200"],
            ),
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
