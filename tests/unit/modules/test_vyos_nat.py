# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.module_utils.vyos import dict_op
from ansible_collections.vyos.rest.plugins.modules.vyos_nat import (
    _cgnat_from_device,
    _cgnat_to_device,
    _device_to_argspec,
    _normalize_nat_have,
    _rules_from_device,
    _rules_to_device,
    _want_to_device,
)

from .base import load_fixture


def _load_nat_fixture():
    return load_fixture("nat_running.json")


class TestRulesToDevice(unittest.TestCase):
    """Keys stay snake_case here -- dict_op does kebab translation itself
    at comparison time, so _rules_to_device must not do it manually."""

    def test_simple_source_rule(self):
        rules = [
            {
                "id": 100,
                "outbound_interface": {"name": "eth0"},
                "translation": {"address": "masquerade"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertIn("100", result)
        self.assertEqual(result["100"]["outbound_interface"]["name"], "eth0")
        self.assertEqual(result["100"]["translation"]["address"], "masquerade")

    def test_bool_fields_become_presence_nodes(self):
        rules = [
            {
                "id": 100,
                "log": True,
                "exclude": True,
                "translation": {"address": "masquerade"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["100"]["log"], {})
        self.assertEqual(result["100"]["exclude"], {})

    def test_false_bool_not_emitted(self):
        rules = [{"id": 100, "log": False, "translation": {"address": "masquerade"}}]
        result = _rules_to_device(rules)
        self.assertNotIn("log", result["100"])

    def test_destination_rule_with_port(self):
        rules = [
            {
                "id": 200,
                "protocol": "tcp",
                "inbound_interface": {"name": "eth0"},
                "destination": {"address": "198.51.100.10", "port": "80"},
                "translation": {"address": "192.168.1.10", "port": "8080"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["200"]["protocol"], "tcp")
        self.assertEqual(result["200"]["destination"]["address"], "198.51.100.10")
        self.assertEqual(result["200"]["destination"]["port"], "80")

    def test_static_rule_inbound_interface_string(self):
        """inbound_interface is a genuine union type: a plain string for
        static NAT (confirmed vyos-1x: bare leafNode), a dict for source/
        destination NAT (confirmed: node with name/group children). No
        special-casing needed either way -- autoclean passes a string
        through unchanged and recurses into a dict identically."""
        rules = [
            {
                "id": 300,
                "inbound_interface": "eth0",
                "destination": {"address": "198.51.100.20"},
                "translation": {"address": "192.168.1.20"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["300"]["inbound_interface"], "eth0")

    def test_multiple_rules_keyed_by_id(self):
        rules = [
            {"id": 100, "translation": {"address": "masquerade"}},
            {"id": 200, "translation": {"address": "masquerade"}},
        ]
        result = _rules_to_device(rules)
        self.assertIn("100", result)
        self.assertIn("200", result)

    def test_none_values_not_emitted(self):
        rules = [{"id": 100, "description": None, "translation": {"address": "masquerade"}}]
        result = _rules_to_device(rules)
        self.assertNotIn("description", result["100"])

    def test_load_balance_hash_stays_a_plain_list(self):
        """hash is a multi-value leafNode (confirmed <multi/>), not a tag
        node -- it must pass through as a plain list untouched, letting
        dict_op's own native list handling manage it."""
        rules = [
            {
                "id": 100,
                "load_balance": {"hash": ["source-address", "random"]},
                "translation": {"address": "masquerade"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["100"]["load_balance"]["hash"], ["source-address", "random"])

    def test_load_balance_backend_reshaped_to_tag_node(self):
        """backend IS a genuine tag node (confirmed: nested "weight"
        leaf), unlike hash -- this one needs the structural reshape."""
        rules = [
            {
                "id": 100,
                "load_balance": {"backend": [{"ip": "192.168.1.10", "weight": 50}]},
                "translation": {"address": "masquerade"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["100"]["load_balance"]["backend"], {"192.168.1.10": {"weight": 50}})

    def test_load_balance_backend_without_weight_is_bare_presence(self):
        """Regression check for the autoclean-based simplification: a
        backend entry with no weight must still produce a bare presence
        node, matching the previous manual if/else exactly."""
        rules = [
            {
                "id": 100,
                "load_balance": {"backend": [{"ip": "192.168.1.10"}]},
                "translation": {"address": "masquerade"},
            },
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["100"]["load_balance"]["backend"], {"192.168.1.10": {}})

    def test_nat64_translation_pool_reshaped_to_tag_node(self):
        rules = [
            {"id": 10, "translation": {"pool": [{"id": 1, "address": "192.168.100.10"}]}},
        ]
        result = _rules_to_device(rules)
        self.assertEqual(result["10"]["translation"]["pool"], {"1": {"address": "192.168.100.10"}})


class TestRulesFromDevice(unittest.TestCase):
    def test_simple_rule(self):
        raw = {
            "100": {
                "outbound-interface": {"name": "eth0"},
                "translation": {"address": "masquerade"},
            },
        }
        result = _rules_from_device(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 100)
        self.assertEqual(result[0]["outbound_interface"]["name"], "eth0")

    def test_rules_sorted_by_id(self):
        raw = {
            "200": {"translation": {"address": "masquerade"}},
            "100": {"translation": {"address": "masquerade"}},
        }
        result = _rules_from_device(raw)
        self.assertEqual(result[0]["id"], 100)
        self.assertEqual(result[1]["id"], 200)

    def test_presence_node_becomes_bool(self):
        raw = {"100": {"log": {}, "translation": {"address": "masquerade"}}}
        result = _rules_from_device(raw)
        self.assertTrue(result[0]["log"])

    def test_static_inbound_interface_string(self):
        raw = {
            "300": {
                "inbound-interface": "eth0",
                "destination": {"address": "198.51.100.20"},
                "translation": {"address": "192.168.1.20"},
            },
        }
        result = _rules_from_device(raw)
        self.assertEqual(result[0]["inbound_interface"], "eth0")

    def test_load_balance_hash_single_value_collapse(self):
        """The device can collapse a single-value multi-leaf to a bare
        string; this must come back as a 1-element list, not a string,
        to match the field's real (list) type."""
        raw = {"100": {"load_balance": {}, "load-balance": {"hash": "random"}}}
        # (duplicate key above is just illustrating intent; real call:)
        raw = {"100": {"load-balance": {"hash": "random"}}}
        result = _rules_from_device(raw)
        self.assertEqual(result[0]["load_balance"]["hash"], ["random"])

    def test_load_balance_backend_from_tag_node(self):
        raw = {"100": {"load-balance": {"backend": {"192.168.1.10": {"weight": "50"}}}}}
        result = _rules_from_device(raw)
        self.assertEqual(
            result[0]["load_balance"]["backend"],
            [{"ip": "192.168.1.10", "weight": 50}],
        )

    def test_nat64_pool_from_tag_node(self):
        raw = {"10": {"translation": {"pool": {"1": {"address": "192.168.100.10"}}}}}
        result = _rules_from_device(raw)
        self.assertEqual(result[0]["translation"]["pool"], [{"id": 1, "address": "192.168.100.10"}])

    def test_empty_returns_empty(self):
        self.assertEqual(_rules_from_device({}), [])
        self.assertEqual(_rules_from_device(None), [])


class TestCgnat(unittest.TestCase):
    """The core bug-fix area: external pool range is a genuine tag node
    (nested "seq" leaf), internal pool range is a plain multi-value leaf
    -- confirmed against vyos-1x schema, and previously conflated."""

    def test_external_pool_range_is_tag_node_with_seq(self):
        cgnat = {
            "pool": {
                "external": [
                    {"name": "EXT1", "range": [{"value": "203.0.113.1-203.0.113.10", "seq": 1}]},
                ],
            },
        }
        result = _cgnat_to_device(cgnat)
        self.assertEqual(
            result["pool"]["external"]["EXT1"]["range"],
            {"203.0.113.1-203.0.113.10": {"seq": 1}},
        )

    def test_external_pool_range_without_seq(self):
        cgnat = {"pool": {"external": [{"name": "EXT1", "range": [{"value": "203.0.113.1-.10"}]}]}}
        result = _cgnat_to_device(cgnat)
        self.assertEqual(result["pool"]["external"]["EXT1"]["range"], {"203.0.113.1-.10": {}})

    def test_internal_pool_range_stays_a_plain_list(self):
        cgnat = {"pool": {"internal": [{"name": "INT1", "range": ["10.0.0.0/24", "10.0.1.0/24"]}]}}
        result = _cgnat_to_device(cgnat)
        self.assertEqual(
            result["pool"]["internal"]["INT1"]["range"],
            ["10.0.0.0/24", "10.0.1.0/24"],
        )

    def test_internal_pool_multi_value_range_from_device_not_dropped(self):
        """Regression test for the confirmed data-loss bug: the previous
        implementation only checked isinstance(str)/isinstance(dict) for
        internal pool range and silently dropped it whenever the device
        returned the real shape for >1 value -- a plain list."""
        raw = {"pool": {"internal": {"INT1": {"range": ["10.0.0.0/24", "10.0.1.0/24"]}}}}
        result = _cgnat_from_device(raw)
        pool = result["pool"]["internal"][0]
        self.assertEqual(pool["range"], ["10.0.0.0/24", "10.0.1.0/24"])

    def test_internal_pool_single_value_range_collapse(self):
        raw = {"pool": {"internal": {"INT1": {"range": "10.0.2.0/24"}}}}
        result = _cgnat_from_device(raw)
        self.assertEqual(result["pool"]["internal"][0]["range"], ["10.0.2.0/24"])

    def test_external_pool_range_from_device_with_seq(self):
        raw = {"pool": {"external": {"EXT1": {"range": {"203.0.113.1-.10": {"seq": "1"}}}}}}
        result = _cgnat_from_device(raw)
        rng = result["pool"]["external"][0]["range"]
        self.assertEqual(rng, [{"value": "203.0.113.1-.10", "seq": 1}])

    def test_log_allocation_generic_presence(self):
        result = _cgnat_to_device({"log_allocation": True})
        self.assertEqual(result["log_allocation"], {})

    def test_cgnat_rule_generic(self):
        cgnat = {"rule": [{"id": 1, "destination": {"group": {"address_group": "CGNAT-DST"}}}]}
        result = _cgnat_to_device(cgnat)
        self.assertEqual(
            result["rule"]["1"]["destination"]["group"]["address_group"],
            "CGNAT-DST",
        )

    def test_empty(self):
        self.assertEqual(_cgnat_to_device({}), {})
        self.assertEqual(_cgnat_from_device({}), {})


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_source_nat(self):
        config = {
            "nat": {
                "source": {
                    "rule": [
                        {
                            "id": 100,
                            "outbound_interface": {"name": "eth0"},
                            "translation": {"address": "masquerade"},
                        },
                    ],
                },
            },
        }
        result = _want_to_device(config)
        self.assertIn("100", result["nat"]["source"]["rule"])

    def test_nat64_pools(self):
        config = {
            "nat64": {
                "source": {
                    "rule": [
                        {
                            "id": 10,
                            "translation": {"pool": [{"id": 1, "address": "192.168.100.10"}]},
                        },
                    ],
                },
            },
        }
        result = _want_to_device(config)
        rule = result["nat64"]["source"]["rule"]["10"]
        self.assertIn("1", rule["translation"]["pool"])

    def test_nat66(self):
        config = {
            "nat66": {
                "source": {
                    "rule": [{"id": 10, "outbound_interface": {"name": "eth0"}}],
                },
            },
        }
        result = _want_to_device(config)
        self.assertIn("10", result["nat66"]["source"]["rule"])

    def test_nat66_destination_and_source_via_dispatch_table(self):
        """nat66 has no cgnat, and only destination/source (no static) --
        exercised via _NAT_TYPE_SECTIONS, not hand-written per-type
        blocks."""
        config = {
            "nat66": {
                "destination": {"rule": [{"id": 10, "protocol": "tcp"}]},
                "source": {"rule": [{"id": 20}]},
            },
        }
        result = _want_to_device(config)
        self.assertIn("10", result["nat66"]["destination"]["rule"])
        self.assertIn("20", result["nat66"]["source"]["rule"])
        self.assertNotIn("cgnat", result["nat66"])

    def test_cgnat_in_want(self):
        config = {"nat": {"cgnat": {"log_allocation": True}}}
        result = _want_to_device(config)
        self.assertEqual(result["nat"]["cgnat"]["log_allocation"], {})


class TestDeviceToArgspec(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})

    def test_source_rule(self):
        raw = {"nat": {"source": {"rule": {"100": {"translation": {"address": "masquerade"}}}}}}
        result = _device_to_argspec(raw)
        self.assertEqual(result["nat"]["source"]["rule"][0]["id"], 100)

    def test_nat64_pools_parsed(self):
        raw = {
            "nat64": {
                "source": {
                    "rule": {"10": {"translation": {"pool": {"1": {"address": "192.168.100.10"}}}}},
                },
            },
        }
        result = _device_to_argspec(raw)
        pools = result["nat64"]["source"]["rule"][0]["translation"]["pool"]
        self.assertEqual(pools[0]["id"], 1)

    def test_static_inbound_interface_string(self):
        raw = {"nat": {"static": {"rule": {"300": {"inbound-interface": "eth0"}}}}}
        result = _device_to_argspec(raw)
        self.assertEqual(result["nat"]["static"]["rule"][0]["inbound_interface"], "eth0")


class TestDeviceToArgspecFixture(unittest.TestCase):
    def setUp(self):
        self.fixture = _load_nat_fixture()

    def test_source_rules_parsed(self):
        result = _device_to_argspec(self.fixture)
        ids = [r["id"] for r in result["nat"]["source"]["rule"]]
        self.assertIn(100, ids)
        self.assertIn(101, ids)

    def test_destination_rule_parsed(self):
        result = _device_to_argspec(self.fixture)
        rule = result["nat"]["destination"]["rule"][0]
        self.assertEqual(rule["id"], 200)
        self.assertEqual(rule["destination"]["port"], "80")

    def test_static_rule_parsed(self):
        result = _device_to_argspec(self.fixture)
        rule = result["nat"]["static"]["rule"][0]
        self.assertEqual(rule["inbound_interface"], "eth0")

    def test_nat64_pools_parsed(self):
        result = _device_to_argspec(self.fixture)
        pools = result["nat64"]["source"]["rule"][0]["translation"]["pool"]
        self.assertEqual(pools[0]["port"], "1-65535")

    def test_description_parsed(self):
        result = _device_to_argspec(self.fixture)
        rule100 = next(r for r in result["nat"]["source"]["rule"] if r["id"] == 100)
        self.assertEqual(rule100["description"], "Source rule 100")

    def test_hash_single_value_collapse_from_fixture(self):
        result = _device_to_argspec(self.fixture)
        rule100 = next(r for r in result["nat"]["source"]["rule"] if r["id"] == 100)
        self.assertEqual(rule100["load_balance"]["hash"], ["random"])

    def test_backend_from_fixture(self):
        result = _device_to_argspec(self.fixture)
        rule100 = next(r for r in result["nat"]["source"]["rule"] if r["id"] == 100)
        backends = {b["ip"]: b.get("weight") for b in rule100["load_balance"]["backend"]}
        self.assertEqual(backends["192.168.1.10"], 50)
        self.assertEqual(backends["192.168.1.11"], None)

    def test_cgnat_internal_pool_range_not_dropped(self):
        """The actual regression this whole refactor was triggered by."""
        result = _device_to_argspec(self.fixture)
        pool = result["nat"]["cgnat"]["pool"]["internal"][0]
        self.assertEqual(pool["range"], ["10.0.0.0/24", "10.0.1.0/24"])

    def test_cgnat_external_pool_range_with_seq(self):
        result = _device_to_argspec(self.fixture)
        pool = result["nat"]["cgnat"]["pool"]["external"][0]
        self.assertEqual(pool["range"], [{"value": "203.0.113.1-203.0.113.10", "seq": 1}])

    def test_cgnat_rule_parsed(self):
        result = _device_to_argspec(self.fixture)
        rule = result["nat"]["cgnat"]["rule"][0]
        self.assertEqual(rule["destination"]["group"]["address_group"], "CGNAT-DST")


class TestDictOpNat(unittest.TestCase):
    """End-to-end command generation, exactly as main() calls it."""

    def test_merged_adds_source_rule(self):
        want = _want_to_device(
            {
                "nat": {
                    "source": {
                        "rule": [
                            {
                                "id": 100,
                                "outbound_interface": {"name": "eth0"},
                                "translation": {"address": "masquerade"},
                            },
                        ],
                    },
                },
            },
        )
        cmds = dict_op(want.get("nat", {}), {}, ["nat"], op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(["nat", "source", "rule", "100", "outbound-interface", "name", "eth0"], paths)
        self.assertIn(
            ["nat", "source", "rule", "100", "translation", "address", "masquerade"],
            paths,
        )

    def test_merged_idempotent_against_fixture(self):
        fixture = _load_nat_fixture()
        have = _device_to_argspec(fixture)
        want = _want_to_device({"nat": have.get("nat", {})}).get("nat", {})
        norm_have = _normalize_nat_have(fixture, "nat")
        cmds = dict_op(want, norm_have, ["nat"], op="set")
        self.assertEqual(cmds, [])

    def test_nat64_idempotent_against_fixture(self):
        fixture = _load_nat_fixture()
        have = _device_to_argspec(fixture)
        want = _want_to_device({"nat64": have.get("nat64", {})}).get("nat64", {})
        norm_have = _normalize_nat_have(fixture, "nat64")
        cmds = dict_op(want, norm_have, ["nat64"], op="set")
        self.assertEqual(cmds, [])

    def test_cgnat_idempotent_against_fixture_including_ranges(self):
        """The real proof the bug is fixed: idempotency now holds even
        though it involves both the tag-node (external) and plain-list
        (internal) range shapes at once."""
        fixture = _load_nat_fixture()
        have = _device_to_argspec(fixture)
        want = _want_to_device({"nat": have.get("nat", {})}).get("nat", {})
        norm_have = _normalize_nat_have(fixture, "nat")
        cmds = dict_op(want, norm_have, ["nat"], op="set")
        self.assertEqual(cmds, [])

    def test_replaced_purges_stale_internal_range_member(self):
        """The internal-pool range being a plain list means removing a
        member under 'replaced' relies on dict_op's list-purge handling
        (fixed earlier this session) -- confirmed it applies here too."""
        raw_have = {
            "cgnat": {"pool": {"internal": {"INT1": {"range": ["10.0.0.0/24", "10.0.1.0/24"]}}}},
        }
        want = _want_to_device(
            {
                "nat": {
                    "cgnat": {"pool": {"internal": [{"name": "INT1", "range": ["10.0.0.0/24"]}]}},
                },
            },
        )["nat"]
        norm_have = _normalize_nat_have({"nat": raw_have}, "nat")
        cmds = dict_op(want, norm_have, ["nat"], op="purge")
        self.assertIn(
            ("delete", ["nat", "cgnat", "pool", "internal", "INT1", "range", "10.0.1.0/24"]),
            cmds,
        )

    def test_overridden_deletes_entire_omitted_section(self):
        """overridden is full-model: a section entirely omitted from
        want (not just a rule within it) must be deleted, via the same
        single dict_op purge call main() uses -- no manual section-scan
        loop needed."""
        raw_have = {
            "destination": {"rule": {"200": {"protocol": "tcp"}}},
            "source": {"rule": {"100": {}}},
        }
        nat_want = _want_to_device(
            {"nat": {"source": {"rule": [{"id": 100}]}}},
        )["nat"]
        norm_have = _normalize_nat_have({"nat": raw_have}, "nat")
        cmds = dict_op(nat_want, norm_have, ["nat"], op="purge")
        self.assertIn(("delete", ["nat", "destination"]), cmds)
        self.assertTrue(all(c[1] != ["nat", "source"] for c in cmds))

    def test_overridden_full_wipe_deletes_each_section_individually(self):
        """Empty want under overridden purges every present section --
        granular per-section deletes, not one blanket delete of the
        whole nat_type (that distinction only matters for vyos_bgp_global,
        where system-as's device-model constraint forces atomicity; NAT
        has no equivalent cross-field constraint)."""
        raw_have = {"destination": {"rule": {"200": {}}}, "source": {"rule": {"100": {}}}}
        norm_have = _normalize_nat_have({"nat": raw_have}, "nat")
        cmds = dict_op({}, norm_have, ["nat"], op="purge")
        self.assertIn(("delete", ["nat", "destination"]), cmds)
        self.assertIn(("delete", ["nat", "source"]), cmds)


if __name__ == "__main__":
    unittest.main()
