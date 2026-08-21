# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_ntp_global import (
    _device_to_argspec,
    _servers_from_device,
    _servers_to_device,
    _want_to_device,
    build_commands,
    get_running_config,
)

from .base import load_fixture


_BASE = ["service", "ntp"]


class VyOSModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_vyos = MagicMock()
        self.fixture = load_fixture("ntp_global_running.json")
        self.mock_vyos.get_config = MagicMock(return_value=self.fixture)


class TestGetRunningConfig(VyOSModuleTestCase):
    def test_returns_raw_device_dict(self):
        self.assertEqual(get_running_config(self.mock_vyos), self.fixture)

    def test_empty_config(self):
        self.mock_vyos.get_config = MagicMock(return_value=None)
        self.assertEqual(get_running_config(self.mock_vyos), {})


class TestServersToDeviceFromDevice(unittest.TestCase):
    """options is the one genuine structural exception: the argspec
    wraps them in a named field, but the device puts each option as a
    direct presence-leaf sibling under the server tag node itself."""

    def test_to_device_bare_server_is_presence(self):
        self.assertEqual(_servers_to_device([{"server": "time1.vyos.net"}]), {"time1.vyos.net": {}})

    def test_to_device_options_become_sibling_presence_leaves(self):
        result = _servers_to_device([{"server": "203.0.113.0", "options": ["prefer", "nts"]}])
        self.assertEqual(result, {"203.0.113.0": {"prefer": {}, "nts": {}}})

    def test_from_device_bare_server(self):
        result = _servers_from_device({"time1.vyos.net": {}})
        self.assertEqual(result, [{"server": "time1.vyos.net"}])

    def test_from_device_options_extracted_as_sorted_list(self):
        result = _servers_from_device({"203.0.113.0": {"prefer": {}, "nts": {}}})
        self.assertEqual(result, [{"server": "203.0.113.0", "options": ["nts", "prefer"]}])


class TestWantToDevice(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})

    def test_allow_clients_nested_under_address(self):
        """allow_clients is a flat argspec list, but the device nests
        the multi-value leaf one level deeper under a literal "address"
        child -- confirmed against vyos-1x (allow-client.xml.i)."""
        result = _want_to_device({"allow_clients": ["10.6.6.0/24"]})
        self.assertEqual(result, {"allow-client": {"address": ["10.6.6.0/24"]}})

    def test_listen_addresses_direct_no_nesting(self):
        result = _want_to_device({"listen_addresses": ["10.1.3.1"]})
        self.assertEqual(result, {"listen-address": ["10.1.3.1"]})

    def test_servers_keyed_by_address(self):
        result = _want_to_device({"servers": [{"server": "203.0.113.0", "options": ["prefer"]}]})
        self.assertEqual(result, {"server": {"203.0.113.0": {"prefer": {}}}})


class TestDeviceToArgspecFixture(VyOSModuleTestCase):
    def test_allow_clients_parsed(self):
        result = _device_to_argspec(self.fixture)
        self.assertIn("10.6.6.0/24", result["allow_clients"])

    def test_listen_addresses_parsed(self):
        result = _device_to_argspec(self.fixture)
        self.assertIn("10.1.3.1", result["listen_addresses"])

    def test_servers_parsed_with_options(self):
        result = _device_to_argspec(self.fixture)
        servers = {s["server"]: s.get("options", []) for s in result["servers"]}
        self.assertIn("time1.vyos.net", servers)
        self.assertIn("prefer", servers["203.0.113.0"])

    def test_empty_config(self):
        result = _device_to_argspec({})
        self.assertEqual(result, {"allow_clients": [], "listen_addresses": [], "servers": []})

    def test_1_5_plus_shape_no_address_wrapper(self):
        """Confirmed against vyos-1x, but kept defensive: some REST
        responses omit the "address" subnode under allow-client."""
        raw = {"allow-client": {"10.6.6.0/24": {}}}
        result = _device_to_argspec(raw)
        self.assertEqual(result["allow_clients"], ["10.6.6.0/24"])


class TestBuildCommands(VyOSModuleTestCase):
    def test_merged_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "merged"), [])

    def test_replaced_idempotent_against_own_fixture(self):
        have = _device_to_argspec(self.fixture)
        self.assertEqual(build_commands(have, self.fixture, "replaced"), [])

    def test_1_5_plus_shape_idempotent(self):
        """Regression test for the real bug caught this session: want
        always emits the "address"-wrapped shape, but dict_op compares
        directly against the raw device tree -- without normalizing
        have's shape first, a device reporting the unwrapped 1.5+
        variant would never be idempotent."""
        raw_have = {"allow-client": {"10.6.6.0/24": {}}}
        have = _device_to_argspec(raw_have)
        self.assertEqual(build_commands(have, raw_have, "merged"), [])

    def test_merged_adds_new_server(self):
        cmds = build_commands({"servers": [{"server": "new.server.com"}]}, {}, "merged")
        self.assertIn(("set", _BASE + ["server", "new.server.com"]), cmds)

    def test_merged_adds_server_option(self):
        raw_have = {"server": {"time1.vyos.net": {}}}
        config = {"servers": [{"server": "time1.vyos.net", "options": ["prefer"]}]}
        cmds = build_commands(config, raw_have, "merged")
        self.assertIn(("set", _BASE + ["server", "time1.vyos.net", "prefer"]), cmds)

    def test_replaced_removes_extra_server(self):
        raw_have = {"server": {"time1.vyos.net": {}, "time2.vyos.net": {}}}
        config = {"servers": [{"server": "time1.vyos.net"}]}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["server", "time2.vyos.net"]), cmds)

    def test_replaced_removes_extra_allow_client(self):
        """This exercises the real dict_op purge gap fixed this session:
        have's allow-client returned as dict-of-presence (not a plain
        list) while want is a plain list -- purge must still correctly
        remove the stale entry."""
        raw_have = {"allow-client": {"address": {"10.1.0.0/24": {}, "10.2.0.0/24": {}}}}
        config = {"allow_clients": ["10.1.0.0/24"]}
        cmds = build_commands(config, raw_have, "replaced")
        self.assertIn(("delete", _BASE + ["allow-client", "address", "10.2.0.0/24"]), cmds)

    def test_deleted_removes_all(self):
        raw_have = {"server": {"time1.vyos.net": {}}}
        cmds = build_commands({}, raw_have, "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_idempotent_when_empty(self):
        self.assertEqual(build_commands({}, {}, "deleted"), [])

    def test_overridden_deletes_then_merges(self):
        raw_have = {"server": {"old.server.com": {}}}
        config = {"servers": [{"server": "new.server.com"}]}
        cmds = build_commands(config, raw_have, "overridden")
        self.assertIn(("delete", _BASE + ["server", "old.server.com"]), cmds)
        self.assertIn(("set", _BASE + ["server", "new.server.com"]), cmds)

    def test_no_commands_when_already_correct(self):
        raw_have = {"allow-client": {"address": {"10.0.0.0/24": {}}}}
        config = {"allow_clients": ["10.0.0.0/24"]}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])

    def test_collapsed_single_server_no_char_iteration_bug(self):
        raw_have = {"server": "203.0.113.0"}
        config = {"servers": [{"server": "203.0.113.0"}]}
        self.assertEqual(build_commands(config, raw_have, "merged"), [])


if __name__ == "__main__":
    unittest.main()
