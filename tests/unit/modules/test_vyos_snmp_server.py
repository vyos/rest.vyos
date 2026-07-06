# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_snmp_server import (
    _DEVICE_RENAMES,
    ARGUMENT_SPEC,
    _derive_key_field,
    _device_to_argspec,
    _device_to_spec,
    _keyed_list_from_device,
    _keyed_list_to_device,
    _single_from_device,
    _single_to_device,
    _spec_to_device,
    _view_entry_from_device,
    _view_entry_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["service", "snmp"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("snmp_server_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config_path_error_returns_empty(self):
        self.mock_vyos.get_config = MagicMock(
            side_effect=Exception("Configuration under specified path is empty"),
        )
        self.assertEqual(get_running_config(self.mock_vyos), {})

    def test_other_error_reraises(self):
        self.mock_vyos.get_config = MagicMock(side_effect=Exception("some other error"))
        with self.assertRaises(Exception):
            get_running_config(self.mock_vyos)


class TestDeviceRenames(unittest.TestCase):
    """The one thing a purely structural walk can never infer: field
    names that mean something different on the device, and aren't a
    mechanical kebab<->snake conversion. Declared once here as a flat
    value map, not embedded in ARGUMENT_SPEC and not scattered across
    per-section functions."""

    def test_confirmed_renames_present(self):
        for arg_key, device_key in [
            ("communities", "community"),
            ("listen_addresses", "listen-address"),
            ("snmp_v3", "v3"),
            ("authorization_type", "authorization"),
            ("clients", "client"),
            ("networks", "network"),
            ("authentication", "auth"),
            ("encrypted_key", "encrypted-password"),
            ("plaintext_key", "plaintext-password"),
            ("engine_id", "engineid"),
            ("groups", "group"),
            ("users", "user"),
            ("views", "view"),
            ("trap_targets", "trap-target"),
        ]:
            self.assertEqual(_DEVICE_RENAMES.get(arg_key), device_key)


class TestSpecToDevice(unittest.TestCase):
    """The generic recursive walker that replaced a hand-written to-
    device/from-device function pair for every section in this module.
    Driven by ARGUMENT_SPEC's own structure (dict -> recurse, list with
    options -> a named list keyed by _derive_key_field, list with no
    options -> a plain multi-value leaf) plus _DEVICE_RENAMES for the
    handful of non-mechanical name differences."""

    def test_plain_scalar_passes_through_unrenamed(self):
        spec = {"contact": {"type": "str"}}
        self.assertEqual(_spec_to_device({"contact": "x"}, spec), {"contact": "x"})

    def test_rename_applied_via_device_renames(self):
        spec = {"authorization_type": {"type": "str"}}
        result = _spec_to_device({"authorization_type": "rw"}, spec)
        self.assertEqual(result, {"authorization": "rw"})

    def test_nested_dict_recurses(self):
        spec = {
            "authentication": {
                "type": "dict",
                "options": {"type": {"type": "str"}, "encrypted_key": {"type": "str"}},
            },
        }
        result = _spec_to_device(
            {"authentication": {"type": "sha", "encrypted_key": "abc123"}},
            spec,
        )
        self.assertEqual(result, {"auth": {"type": "sha", "encrypted-password": "abc123"}})

    def test_named_list_keyed_by_required_field(self):
        spec = {
            "communities": {
                "type": "list",
                "options": {"name": {"type": "str", "required": True}, "port": {"type": "int"}},
            },
        }
        result = _spec_to_device(
            {"communities": [{"name": "switches", "port": 5}]},
            spec,
        )
        self.assertEqual(result, {"community": {"switches": {"port": 5}}})

    def test_plain_scalar_list_passes_through(self):
        spec = {"clients": {"type": "list", "elements": "str"}}
        result = _spec_to_device({"clients": ["1.1.1.1"]}, spec)
        self.assertEqual(result, {"client": ["1.1.1.1"]})

    def test_bool_true_is_presence(self):
        spec = {"disable": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"disable": True}, spec), {"disable": {}})

    def test_bool_false_omitted(self):
        spec = {"disable": {"type": "bool"}}
        self.assertEqual(_spec_to_device({"disable": False}, spec), {})

    def test_non_dict_value_passes_through(self):
        self.assertEqual(_spec_to_device("not-a-dict", {}), "not-a-dict")


class TestDeviceToSpec(unittest.TestCase):
    """The reverse of _spec_to_device -- same structural rules, same
    single source of truth for renames."""

    def test_mechanical_field_matched_via_hyphen_normalization(self):
        spec = {"local_stratum": {"type": "str"}}
        result = _device_to_spec({"local-stratum": "5"}, spec)
        self.assertEqual(result, {"local_stratum": "5"})

    def test_renamed_field_matched_via_device_renames(self):
        spec = {"authorization_type": {"type": "str"}}
        result = _device_to_spec({"authorization": "rw"}, spec)
        self.assertEqual(result, {"authorization_type": "rw"})

    def test_nested_dict_recurses(self):
        spec = {
            "authentication": {
                "type": "dict",
                "options": {"encrypted_key": {"type": "str"}},
            },
        }
        result = _device_to_spec({"auth": {"encrypted-password": "abc123"}}, spec)
        self.assertEqual(result, {"authentication": {"encrypted_key": "abc123"}})

    def test_named_list_keyed_by_required_field(self):
        spec = {
            "communities": {
                "type": "list",
                "options": {"name": {"type": "str", "required": True}, "port": {"type": "int"}},
            },
        }
        result = _device_to_spec({"community": {"switches": {"port": "5"}}}, spec)
        self.assertEqual(result, {"communities": [{"name": "switches", "port": "5"}]})

    def test_plain_scalar_list_sorted_and_collapse_safe(self):
        spec = {"clients": {"type": "list", "elements": "str"}}
        result = _device_to_spec({"client": "1.1.1.1"}, spec)
        self.assertEqual(result, {"clients": ["1.1.1.1"]})

    def test_presence_dict_becomes_bool(self):
        spec = {"disable": {"type": "bool"}}
        self.assertEqual(_device_to_spec({"disable": {}}, spec), {"disable": True})

    def test_empty_or_non_dict_raw(self):
        self.assertEqual(_device_to_spec({}, {}), {})
        self.assertEqual(_device_to_spec(None, {}), {})
        self.assertEqual(_device_to_spec("not-a-dict", {}), {})


class TestKeyedListHelper(unittest.TestCase):
    """The generic mechanic every named-list section shares: a list of
    dicts identified by one field becomes a device dict keyed by that
    field's value. This used to be reimplemented six separate times."""

    def test_to_device_default_transform_is_autoclean(self):
        result = _keyed_list_to_device([{"group": "admins", "mode": "rw"}], "group")
        self.assertEqual(result, {"admins": {"mode": "rw"}})

    def test_to_device_skips_entries_missing_key_field(self):
        result = _keyed_list_to_device([{"mode": "rw"}], "group")
        self.assertEqual(result, {})

    def test_to_device_custom_entry_transform_receives_rest_only(self):
        seen = {}

        def transform(rest):
            seen.update(rest)
            return rest

        _keyed_list_to_device([{"name": "switches", "authorization_type": "rw"}], "name", transform)
        self.assertNotIn("name", seen)
        self.assertEqual(seen, {"authorization_type": "rw"})

    def test_from_device_default_transform_is_from_device(self):
        result = _keyed_list_from_device({"admins": {"mode": "rw"}}, "group")
        self.assertEqual(result, [{"group": "admins", "mode": "rw"}])

    def test_from_device_bare_string_collapse(self):
        result = _keyed_list_from_device("admins", "group")
        self.assertEqual(result, [{"group": "admins"}])

    def test_empty(self):
        self.assertEqual(_keyed_list_to_device([], "group"), {})
        self.assertEqual(_keyed_list_to_device(None, "group"), {})
        self.assertEqual(_keyed_list_from_device({}, "group"), [])
        self.assertEqual(_keyed_list_from_device(None, "group"), [])


class TestCommunity(unittest.TestCase):
    """authorization_type->authorization and clients/networks->
    client/network are genuine renames (in _DEVICE_RENAMES, not
    embedded in ARGUMENT_SPEC); both member fields are confirmed plain
    multi-value leaves, passed straight through. Tested via the
    generic walker directly against communities' own entry options,
    since there's no bespoke per-entry function anymore."""

    def setUp(self):
        self.entry_options = ARGUMENT_SPEC["config"]["options"]["communities"]["options"]

    def test_to_device_authorization_rename(self):
        result = _spec_to_device({"authorization_type": "rw"}, self.entry_options)
        self.assertEqual(result, {"authorization": "rw"})

    def test_to_device_clients_networks_rename(self):
        result = _spec_to_device(
            {"clients": ["1.1.1.1"], "networks": ["10.0.0.0/8"]},
            self.entry_options,
        )
        self.assertEqual(result, {"client": ["1.1.1.1"], "network": ["10.0.0.0/8"]})

    def test_from_device(self):
        entry = _device_to_spec(
            {"client": ["1.1.1.1", "12.1.1.10"], "authorization": "ro"},
            self.entry_options,
        )
        self.assertEqual(entry["clients"], ["1.1.1.1", "12.1.1.10"])
        self.assertEqual(entry["authorization_type"], "ro")

    def test_from_device_single_client_collapse(self):
        entry = _device_to_spec({"client": "1.1.1.1"}, self.entry_options)
        self.assertEqual(entry["clients"], ["1.1.1.1"])

    def test_full_pipeline_via_keyed_list_helper(self):
        """Confirms the entry-transform and the generic keying mechanic
        compose correctly end to end, matching how _spec_to_device
        itself calls them for any named-list section."""
        result = _keyed_list_to_device(
            [{"name": "switches", "authorization_type": "rw"}],
            "name",
            lambda rest: _spec_to_device(rest, self.entry_options),
        )
        self.assertEqual(result, {"switches": {"authorization": "rw"}})


class TestDeriveKeyField(unittest.TestCase):
    """key_field is derived from each section's argspec, not
    hand-declared -- every named-list section marks exactly one
    suboption required=True (you can't create a community without a
    name, and so on), so that's the field identifying each entry."""

    def test_derives_the_single_required_field(self):
        self.assertEqual(
            _derive_key_field({"name": {"required": True}, "clients": {"type": "list"}}),
            "name",
        )

    def test_raises_if_none_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"clients": {"type": "list"}})

    def test_raises_if_more_than_one_required(self):
        with self.assertRaises(ValueError):
            _derive_key_field({"a": {"required": True}, "b": {"required": True}})


class TestTrapTarget(unittest.TestCase):
    """Confirmed a genuine tagNode keyed by address on the device, but
    the argspec models only a single object -- a documented limitation
    (the device supports multiple), preserved as-is. Reuses the same
    generic keyed-list mechanic as "a list capped to one entry" rather
    than a bespoke pair of functions."""

    def test_to_device_keyed_by_address(self):
        result = _single_to_device({"address": "203.0.113.5", "community": "public"}, "address")
        self.assertEqual(result, {"203.0.113.5": {"community": "public"}})

    def test_to_device_no_address_is_noop(self):
        self.assertEqual(_single_to_device({}, "address"), {})
        self.assertEqual(_single_to_device(None, "address"), {})

    def test_from_device(self):
        entry = _single_from_device(
            {"203.0.113.5": {"community": "public", "port": "162"}},
            "address",
        )
        self.assertEqual(entry["address"], "203.0.113.5")
        self.assertEqual(entry["community"], "public")

    def test_from_device_bare_string_collapse(self):
        entry = _single_from_device("203.0.113.5", "address")
        self.assertEqual(entry, {"address": "203.0.113.5"})

    def test_from_device_empty_is_none(self):
        self.assertIsNone(_single_from_device(None, "address"))
        self.assertIsNone(_single_from_device({}, "address"))


class TestV3View(unittest.TestCase):
    """The confirmed structural bug: "oid" is a genuine tag node (keyed
    by the OID value) with its own exclude/mask children -- the
    previous implementation read exclude/mask from the wrong nesting
    level (directly under the view) and only handled a single oid key
    via list(oid_data.keys())[0], silently dropping any others. Like
    community, the entry-transform receives only the dict's "rest"
    (the key field "view" is stripped by the generic helper first)."""

    def test_to_device_oid_is_nested_tag_node(self):
        result = _view_entry_to_device({"oid": "1.3.6.1", "mask": "ff"})
        self.assertEqual(result, {"oid": {"1.3.6.1": {"mask": "ff"}}})

    def test_to_device_exclude_nested_under_oid_not_view(self):
        result = _view_entry_to_device({"oid": "1.3.6.1", "exclude": "1.3.6.1.9"})
        self.assertEqual(result, {"oid": {"1.3.6.1": {"exclude": ["1.3.6.1.9"]}}})

    def test_to_device_no_oid_is_empty(self):
        self.assertEqual(_view_entry_to_device({}), {})

    def test_from_device_reads_exclude_mask_from_oid_level(self):
        """Regression test for the confirmed bug: exclude/mask must be
        read from data["oid"][<value>], not data directly."""
        entry = _view_entry_from_device(
            {"oid": {"1.3.6.1": {"exclude": ["1.3.6.1.9"], "mask": "ff.ff"}}},
        )
        self.assertEqual(entry["oid"], "1.3.6.1")
        self.assertEqual(entry["exclude"], "1.3.6.1.9")
        self.assertEqual(entry["mask"], "ff.ff")

    def test_from_device_bare_oid_string_collapse(self):
        entry = _view_entry_from_device({"oid": "1.3.6.1"})
        self.assertEqual(entry["oid"], "1.3.6.1")
        self.assertNotIn("exclude", entry)

    def test_from_device_no_oid(self):
        entry = _view_entry_from_device({})
        self.assertEqual(entry, {})


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_engine_id_rename(self):
        """Confirmed bug: "engineid" (device, one word) vs "engine_id"
        (argspec) is not a mechanical kebab<->snake conversion since
        there's no hyphen to split -- a genuine rename exception."""
        result = _want_to_device({"snmp_v3": {"engine_id": "0002"}})
        self.assertEqual(result["v3"]["engineid"], "0002")
        self.assertNotIn("engine_id", result["v3"])

    def test_communities_keyed_by_name(self):
        config = {"communities": [{"name": "switches", "authorization_type": "rw"}]}
        result = _want_to_device(config)
        self.assertEqual(result["community"]["switches"], {"authorization": "rw"})

    def test_generic_scalar_fields(self):
        result = _want_to_device({"contact": "admin@example.com", "location": "DC1"})
        self.assertEqual(result, {"contact": "admin@example.com", "location": "DC1"})


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_communities_parsed(self):
        have = _device_to_argspec(self.fixture)
        names = {c["name"] for c in have["communities"]}
        self.assertEqual(names, {"switches", "bridges"})

    def test_engine_id_parsed(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(have["snmp_v3"]["engine_id"], "000000000000000000000002")

    def test_v3_user_authentication_parsed(self):
        have = _device_to_argspec(self.fixture)
        user = have["snmp_v3"]["users"][0]
        self.assertEqual(user["authentication"]["type"], "sha")
        self.assertEqual(user["authentication"]["encrypted_key"], "abc123")

    def test_v3_view_oid_parsed(self):
        have = _device_to_argspec(self.fixture)
        view = have["snmp_v3"]["views"][0]
        self.assertEqual(view["oid"], "1")

    def test_trap_target_parsed(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(have["trap_target"]["address"], "203.0.113.5")
        self.assertEqual(have["trap_target"]["community"], "public")
        self.assertEqual(have["trap_target"]["port"], 162)

    def test_v3_trap_targets_parsed(self):
        have = _device_to_argspec(self.fixture)
        target = have["snmp_v3"]["trap_targets"][0]
        self.assertEqual(target["address"], "198.51.100.5")
        self.assertEqual(target["protocol"], "udp")
        self.assertEqual(target["authentication"]["type"], "sha")

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
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "overridden"), [])

    def test_underscore_username_not_kebab_cased_on_creation(self):
        """Confirmed real bug: dict_op's fallback for a key missing from
        have assumed every key is a translatable schema field name --
        but a brand-new tag-node entry (username, community name, any
        user-supplied identifier) is opaque data, and "admin_user" was
        silently becoming "admin-user" in the generated command on
        first creation, before verbatim_keys was wired in."""
        cmds = build_commands(
            {"snmp_v3": {"users": [{"user": "admin_user", "group": "admins"}]}},
            {},
            "merged",
        )
        self.assertTrue(any("admin_user" in c[1] for c in cmds))
        self.assertFalse(any("admin-user" in c[1] for c in cmds))

    def test_underscore_names_verbatim_across_every_tag_node_section(self):
        """Same regression, covering every section with an opaque
        tag-node key in this module, not just v3 users."""
        config = {
            "communities": [{"name": "my_community"}],
            "snmp_v3": {
                "groups": [{"group": "my_group"}],
                "views": [{"view": "my_view", "oid": "1.3.6.1"}],
                "trap_targets": [{"address": "198.51.100.5"}],
            },
        }
        cmds = build_commands(config, {}, "merged")
        joined = [str(c[1]) for c in cmds]
        self.assertTrue(any("my_community" in p for p in joined))
        self.assertTrue(any("my_group" in p for p in joined))
        self.assertTrue(any("my_view" in p for p in joined))
        self.assertFalse(any("my-community" in p for p in joined))
        self.assertFalse(any("my-group" in p for p in joined))
        self.assertFalse(any("my-view" in p for p in joined))

    def test_underscore_username_removed_verbatim_on_replaced(self):
        """The purge path (replaced/overridden) must also match and
        delete the opaque key verbatim, not a kebab-cased guess."""
        raw_have = {"v3": {"user": {"admin_user": {"group": "admins"}}}}
        cmds = build_commands({"snmp_v3": {"users": []}}, raw_have, "replaced")
        self.assertIn(("delete", ["service", "snmp", "v3", "user", "admin_user"]), cmds)

    def test_replaced_does_not_purge_credential_without_new_password(self):
        """Confirmed real device-rejected commit: VyOS requires an
        auth/privacy node to carry an encrypted-password or plaintext-
        password whenever it exists at all. A "replaced" config update
        that changes an unrelated field (or nothing) without
        re-supplying a password -- which the user can never read back
        to re-supply -- must not purge the existing credential out from
        under it, or the commit is rejected entirely."""
        raw_have = {
            "v3": {
                "user": {
                    "admin_user": {
                        "auth": {"type": "sha", "encrypted-password": "hash1"},
                        "privacy": {"type": "aes", "encrypted-password": "hash2"},
                        "group": "admins",
                    },
                },
            },
        }
        config = {
            "snmp_v3": {
                "users": [
                    {
                        "user": "admin_user",
                        "group": "admins",
                        "authentication": {"type": "sha"},
                        "privacy": {"type": "aes"},
                    },
                ],
            },
        }
        cmds = build_commands(config, raw_have, "replaced")
        self.assertFalse(any("encrypted-password" in str(c) for c in cmds))

    def test_replaced_still_sets_a_genuinely_new_password(self):
        """The credential-protection fix must not mask an intentional
        password change -- only fill in what's missing."""
        raw_have = {
            "v3": {
                "user": {
                    "admin_user": {
                        "auth": {"type": "sha", "encrypted-password": "hash1"},
                        "group": "admins",
                    },
                },
            },
        }
        config = {
            "snmp_v3": {
                "users": [
                    {
                        "user": "admin_user",
                        "group": "admins",
                        "authentication": {"type": "sha", "plaintext_key": "newpass"},
                    },
                ],
            },
        }
        cmds = build_commands(config, raw_have, "replaced")
        expected = (
            "set",
            [
                "service",
                "snmp",
                "v3",
                "user",
                "admin_user",
                "auth",
                "plaintext-password",
                "newpass",
            ],
        )
        self.assertIn(expected, cmds)

    def test_plaintext_password_write_path(self):
        """The primary confirmed bug fix, exercised end to end: the
        device path must use plaintext-password, not plaintext-key."""
        config = {
            "snmp_v3": {
                "users": [
                    {
                        "user": "newuser",
                        "authentication": {"type": "sha", "plaintext_key": "abc1234567"},
                    },
                ],
            },
        }
        cmds = build_commands(config, {}, "merged")
        self.assertIn(
            ("set", _BASE + ["v3", "user", "newuser", "auth", "plaintext-password", "abc1234567"]),
            cmds,
        )
        self.assertTrue(all("plaintext-key" not in c[1] for c in cmds))

    def test_replaced_scoped_to_named_sections_only(self):
        """Regression test for the three-way key-name-collision bug this
        session's investigation found (community/view/group each mean a
        tag node at one level and an unrelated scalar leaf at another) --
        replaced must not touch an unrelated section, and must not
        crash comparing a scalar have value as if it were a dict."""
        raw_have = {
            "community": {"switches": {"authorization": "rw"}, "bridges": {"client": ["1.1.1.1"]}},
            "contact": "old@example.com",
        }
        config = {"communities": [{"name": "switches", "authorization_type": "rw"}]}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["community", "bridges"]), cmds)
        self.assertTrue(all(c[1][: len(_BASE) + 1] != _BASE + ["contact"] for c in cmds))

    def test_overridden_removes_omitted_scalar_field(self):
        raw_have = {"contact": "old@example.com", "community": {"switches": {}}}
        config = {"communities": [{"name": "switches"}]}
        cmds = build_commands(config, raw_have, "overridden")
        self.assertIn(("delete", _BASE + ["contact"]), cmds)

    def test_deleted_no_have_is_noop(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_deleted_with_have(self):
        self.assertEqual(build_commands({}, {"contact": "x"}, "deleted"), [("delete", _BASE)])

    def test_collapsed_v3_group_no_char_iteration_bug(self):
        """A single v3 group with no other config, collapsed by the
        device to a bare group-name string, must not be iterated
        character-by-character."""
        raw_have = {"v3": {"group": "admins"}}
        config = {"snmp_v3": {"groups": [{"group": "admins"}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_collapsed_trap_target_no_char_iteration_bug(self):
        raw_have = {"trap-target": "203.0.113.5"}
        config = {"trap_target": {"address": "203.0.113.5"}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_v3_group_view_scalar_not_confused_with_v3_view_tag_node(self):
        """Regression test: v3.group.<name>.view (a scalar leaf naming
        which view the group uses) must never be coerced into a
        presence-dict just because "view" is also a genuine tag node
        one level up, under v3 itself."""
        raw_have = {"v3": {"group": {"admins": {"view": "all"}}}}
        config = {"snmp_v3": {"groups": [{"group": "admins", "view": "all"}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_v3_user_group_scalar_not_confused_with_v3_group_tag_node(self):
        raw_have = {"v3": {"user": {"admin_user": {"group": "admins"}}}}
        config = {"snmp_v3": {"users": [{"user": "admin_user", "group": "admins"}]}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_trap_target_community_scalar_not_confused_with_community_tag_node(self):
        raw_have = {"trap-target": {"203.0.113.5": {"community": "public"}}}
        config = {"trap_target": {"address": "203.0.113.5", "community": "public"}}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])


if __name__ == "__main__":
    unittest.main()
