# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from ansible_collections.vyos.rest.plugins.modules.vyos_logging_global import (
    build_commands,
    normalize_config,
    normalize_running,
)

from tests.unit.modules.base import VyOSModuleTestCase, load_fixture


class TestVyOSLoggingGlobalNormalize(unittest.TestCase):

    def test_normalize_config_console(self):
        cfg = {
            "console": {
                "facilities": [{"facility": "local7", "severity": "err"}],
            },
        }
        result = normalize_config(cfg)
        self.assertIn("local7", result["console"]["facilities"])
        self.assertEqual(
            result["console"]["facilities"]["local7"],
            {"severity": "err", "protocol": None},
        )

    def test_normalize_config_hosts(self):
        cfg = {
            "hosts": [
                {
                    "hostname": "172.16.0.1",
                    "port": 514,
                    "facilities": [
                        {"facility": "local7", "severity": "all"},
                        {"facility": "all", "protocol": "udp"},
                    ],
                },
            ],
        }
        result = normalize_config(cfg)
        self.assertIn("172.16.0.1", result["hosts"])
        host = result["hosts"]["172.16.0.1"]
        self.assertEqual(host["port"], 514)
        self.assertIn("local7", host["facilities"])
        self.assertEqual(host["facilities"]["local7"]["severity"], "all")
        self.assertEqual(host["facilities"]["all"]["protocol"], "udp")

    def test_normalize_running_console(self):
        raw = {
            "console": {
                "facility": {
                    "local7": {"level": "err"},
                    "all": {},
                },
            },
        }
        result = normalize_running(raw)
        self.assertIn("local7", result["console"]["facilities"])
        self.assertEqual(result["console"]["facilities"]["local7"]["severity"], "err")
        self.assertIsNone(result["console"]["facilities"]["all"]["severity"])

    def test_normalize_running_global_archive(self):
        raw = {
            "global": {
                "archive": {"file": "2", "size": "111"},
                "marker": {"interval": "111"},
                "preserve-fqdn": {},
            },
        }
        result = normalize_running(raw)
        self.assertEqual(result["global"]["archive"]["file_num"], 2)
        self.assertEqual(result["global"]["archive"]["size"], 111)
        self.assertEqual(result["global"]["marker_interval"], 111)
        self.assertTrue(result["global"]["preserve_fqdn"])

    def test_normalize_running_host_port_cast(self):
        raw = {
            "host": {
                "172.16.0.1": {
                    "port": "514",
                    "facility": {},
                },
            },
        }
        result = normalize_running(raw)
        self.assertEqual(result["hosts"]["172.16.0.1"]["port"], 514)

    def test_normalize_running_empty(self):
        result = normalize_running({})
        self.assertEqual(result["console"]["facilities"], {})
        self.assertEqual(result["hosts"], {})


class TestVyOSLoggingGlobalBuildCommands(unittest.TestCase):

    def _empty_have(self):
        return {
            "console": {"facilities": {}},
            "global": {"facilities": {}},
            "hosts": {},
            "files": {},
            "users": {},
        }

    def test_merged_adds_console_facility(self):
        want = self._empty_have()
        want["console"]["facilities"]["local7"] = {"severity": "err", "protocol": None}
        cmds = build_commands(want, self._empty_have(), "merged")
        self.assertIn(
            ("set", ["system", "syslog", "console", "facility", "local7", "level", "err"]),
            cmds,
        )

    def test_merged_idempotent_console(self):
        facs = {"local7": {"severity": "err", "protocol": None}}
        want = self._empty_have()
        have = self._empty_have()
        want["console"]["facilities"] = facs
        have["console"]["facilities"] = facs.copy()
        cmds = build_commands(want, have, "merged")
        self.assertEqual(cmds, [])

    def test_merged_adds_host_with_port(self):
        want = self._empty_have()
        want["hosts"]["172.16.0.1"] = {
            "port": 514,
            "facilities": {"local7": {"severity": "all", "protocol": None}},
        }
        cmds = build_commands(want, self._empty_have(), "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(["system", "syslog", "host", "172.16.0.1", "port", "514"], paths)
        self.assertIn(
            ["system", "syslog", "host", "172.16.0.1", "facility", "local7", "level", "all"],
            paths,
        )

    def test_merged_adds_host_facility_protocol(self):
        want = self._empty_have()
        want["hosts"]["172.16.0.1"] = {
            "port": None,
            "facilities": {"all": {"severity": None, "protocol": "udp"}},
        }
        cmds = build_commands(want, self._empty_have(), "merged")
        self.assertIn(
            (
                "set",
                ["system", "syslog", "host", "172.16.0.1", "facility", "all", "protocol", "udp"],
            ),
            cmds,
        )

    def test_replaced_removes_extra_host(self):
        want = self._empty_have()
        have = self._empty_have()
        have["hosts"]["172.16.0.1"] = {"port": None, "facilities": {}}
        cmds = build_commands(want, have, "replaced")
        self.assertIn(("delete", ["system", "syslog", "host", "172.16.0.1"]), cmds)

    def test_deleted_issues_single_delete(self):
        have = self._empty_have()
        have["console"]["facilities"]["all"] = {"severity": None, "protocol": None}
        cmds = build_commands(self._empty_have(), have, "deleted")
        self.assertIn(("delete", ["system", "syslog"]), cmds)

    def test_overridden_deletes_then_merges(self):
        want = self._empty_have()
        have = self._empty_have()
        have["console"]["facilities"]["all"] = {"severity": None, "protocol": None}
        cmds = build_commands(want, have, "overridden")
        self.assertIn(("delete", ["system", "syslog"]), cmds)

    def test_global_preserve_fqdn_added(self):
        want = self._empty_have()
        want["global"]["preserve_fqdn"] = True
        cmds = build_commands(want, self._empty_have(), "merged")
        self.assertIn(("set", ["system", "syslog", "global", "preserve-fqdn"]), cmds)

    def test_global_archive(self):
        want = self._empty_have()
        want["global"]["archive"] = {"file_num": 2, "size": 111}
        cmds = build_commands(want, self._empty_have(), "merged")
        paths = [c[1] for c in cmds]
        self.assertIn(["system", "syslog", "global", "archive", "file", "2"], paths)
        self.assertIn(["system", "syslog", "global", "archive", "size", "111"], paths)


class TestVyOSLoggingGlobalFixture(VyOSModuleTestCase):
    """Test parsing against the confirmed device fixture."""

    def setUp(self):
        super().setUp()
        self.fixture = load_fixture("logging_global_running.json")

    def test_fixture_parses_console(self):
        result = normalize_running(self.fixture)
        self.assertIn("local7", result["console"]["facilities"])
        self.assertEqual(result["console"]["facilities"]["local7"]["severity"], "err")

    def test_fixture_parses_host_port(self):
        result = normalize_running(self.fixture)
        self.assertEqual(result["hosts"]["172.16.0.1"]["port"], 223)

    def test_fixture_parses_global_archive(self):
        result = normalize_running(self.fixture)
        self.assertEqual(result["global"]["archive"]["file_num"], 2)
        self.assertEqual(result["global"]["archive"]["size"], 111)

    def test_fixture_parses_preserve_fqdn(self):
        result = normalize_running(self.fixture)
        self.assertTrue(result["global"]["preserve_fqdn"])

    def test_fixture_parses_marker_interval(self):
        result = normalize_running(self.fixture)
        self.assertEqual(result["global"]["marker_interval"], 111)


if __name__ == "__main__":
    unittest.main()
