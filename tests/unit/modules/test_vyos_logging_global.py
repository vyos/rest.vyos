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


class TestVyOSLoggingGlobalNormalize(unittest.TestCase):

    def test_normalize_config_console_severity_is_string(self):
        cfg = {
            "console": {
                "facilities": [{"facility": "local7", "severity": "err"}],
            },
        }
        result = normalize_config(cfg)
        self.assertIn("local7", result["console"]["facilities"])
        # severity is stored as plain string, not dict
        self.assertEqual(result["console"]["facilities"]["local7"], "err")

    def test_normalize_config_console_no_severity(self):
        cfg = {
            "console": {
                "facilities": [{"facility": "all"}],
            },
        }
        result = normalize_config(cfg)
        self.assertIsNone(result["console"]["facilities"]["all"])

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
        # host facilities are dicts with severity/protocol
        self.assertEqual(host["facilities"]["local7"]["severity"], "all")
        self.assertEqual(host["facilities"]["all"]["protocol"], "udp")

    def test_normalize_config_global_preserve_fqdn(self):
        cfg = {"global_params": {"preserve_fqdn": True}}
        result = normalize_config(cfg)
        self.assertTrue(result["global"]["preserve_fqdn"])

    def test_normalize_config_global_archive(self):
        cfg = {"global_params": {"archive": {"file_num": 2, "size": 111}}}
        result = normalize_config(cfg)
        self.assertEqual(result["global"]["archive"]["file_num"], 2)
        self.assertEqual(result["global"]["archive"]["size"], 111)

    def test_normalize_config_empty(self):
        result = normalize_config({})
        self.assertEqual(result["console"]["facilities"], {})
        self.assertEqual(result["hosts"], {})
        self.assertEqual(result["files"], {})
        self.assertEqual(result["users"], {})

    def test_normalize_running_console_severity_is_string(self):
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
        # severity is plain string from "level" key
        self.assertEqual(result["console"]["facilities"]["local7"], "err")
        self.assertIsNone(result["console"]["facilities"]["all"])

    def test_normalize_running_host_port_not_cast(self):
        """Port is NOT cast to int — stored as-is from API response."""
        raw = {
            "remote": {
                "172.16.0.1": {
                    "port": "514",
                    "facility": {},
                },
            },
        }
        result = normalize_running(raw)
        # port stays as string — module does not cast
        self.assertEqual(result["hosts"]["172.16.0.1"]["port"], "514")

    def test_normalize_running_global_archive_key(self):
        """Archive stored under 'archive' key — no file_num remapping."""
        raw = {
            "local": {
                "archive": {"file": "2", "size": "111"},
                "marker": {"interval": "111"},
                "preserve-fqdn": {},
            },
        }
        result = normalize_running(raw)
        # archive stored as-is from API
        self.assertEqual(result["global"]["archive"]["file"], "2")
        self.assertEqual(result["global"]["archive"]["size"], "111")
        # marker_interval stored as string — no cast
        self.assertEqual(result["global"]["marker_interval"], "111")
        self.assertTrue(result["global"]["preserve_fqdn"])

    def test_normalize_running_empty(self):
        result = normalize_running({})
        self.assertEqual(result["console"]["facilities"], {})
        self.assertEqual(result["hosts"], {})

    def test_normalize_running_host_facilities(self):
        raw = {
            "remote": {
                "172.16.0.1": {
                    "facility": {
                        "local7": {"level": "all"},
                        "all": {"protocol": "udp"},
                    },
                    "port": "223",
                },
            },
        }
        result = normalize_running(raw)
        h = result["hosts"]["172.16.0.1"]
        self.assertEqual(h["facilities"]["local7"]["severity"], "all")
        self.assertEqual(h["facilities"]["all"]["protocol"], "udp")


class TestVyOSLoggingGlobalBuildCommands(unittest.TestCase):

    def _empty_have(self):
        return {
            "console": {"facilities": {}},
            "global": {"facilities": {}},
            "hosts": {},
            "files": {},
            "users": {},
        }

    def test_merged_adds_console_facility_with_severity(self):
        want = self._empty_have()
        want["console"]["facilities"]["local7"] = "err"
        cmds = build_commands(want, self._empty_have(), "merged")
        self.assertIn(
            ("set", ["system", "syslog", "console", "facility", "local7", "level", "err"]),
            cmds,
        )

    def test_merged_adds_console_facility_no_severity(self):
        want = self._empty_have()
        want["console"]["facilities"]["all"] = None
        cmds = build_commands(want, self._empty_have(), "merged")
        self.assertIn(
            ("set", ["system", "syslog", "console", "facility", "all"]),
            cmds,
        )

    def test_merged_idempotent_console(self):
        facs = {"local7": "err"}
        want = self._empty_have()
        have = self._empty_have()
        want["console"]["facilities"] = facs
        have["console"]["facilities"] = dict(facs)
        cmds = build_commands(want, have, "merged")
        self.assertEqual(cmds, [])

    def test_merged_adds_host(self):
        want = self._empty_have()
        want["hosts"]["172.16.0.1"] = {
            "port": 514,
            "facilities": {"local7": {"severity": "all", "protocol": None}},
        }
        cmds = build_commands(want, self._empty_have(), "merged")
        paths = [c[1] for c in cmds]
        # diff_map only adds the host key, not per-facility details
        self.assertIn(["system", "syslog", "remote", "172.16.0.1"], paths)

    def test_replaced_removes_extra_host(self):
        want = self._empty_have()
        have = self._empty_have()
        have["hosts"]["172.16.0.1"] = {"port": None, "facilities": {}}
        cmds = build_commands(want, have, "replaced")
        self.assertIn(("delete", ["system", "syslog", "remote", "172.16.0.1"]), cmds)

    def test_deleted_removes_per_field(self):
        """deleted state removes per-facility entries, not single subtree."""
        have = self._empty_have()
        have["console"]["facilities"]["all"] = None
        cmds = build_commands(self._empty_have(), have, "deleted")
        self.assertIn(
            ("delete", ["system", "syslog", "console", "facility", "all"]),
            cmds,
        )

    def test_overridden_deletes_all_then_merges(self):
        want = self._empty_have()
        want["console"]["facilities"]["local7"] = "err"
        have = self._empty_have()
        have["console"]["facilities"]["all"] = None
        cmds = build_commands(want, have, "overridden")
        # first command is full syslog delete
        self.assertEqual(cmds[0], ("delete", ["system", "syslog"]))
        # then adds wanted facility
        self.assertIn(
            ("set", ["system", "syslog", "console", "facility", "local7", "level", "err"]),
            cmds,
        )

    def test_no_commands_when_already_correct(self):
        state = self._empty_have()
        state["console"]["facilities"]["local7"] = "err"
        cmds = build_commands(state, state, "merged")
        self.assertEqual(cmds, [])


if __name__ == "__main__":
    unittest.main()
