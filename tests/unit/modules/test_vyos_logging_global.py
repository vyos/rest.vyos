# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from ansible_collections.vyos.rest.plugins.module_utils.vyos import dict_op
from ansible_collections.vyos.rest.plugins.modules.vyos_logging_global import (
    _device_to_argspec,
    _fac_device_to_list,
    _fac_list_to_device,
    _want_to_device,
)


_BASE = ["system", "syslog"]


class TestFacHelpers(unittest.TestCase):
    """Test facility list <-> device dict conversion helpers."""

    def test_fac_list_to_device_with_severity(self):
        facs = [{"facility": "local7", "severity": "err"}]
        result = _fac_list_to_device(facs)
        self.assertEqual(result, {"local7": {"level": "err"}})

    def test_fac_list_to_device_no_severity(self):
        facs = [{"facility": "all"}]
        result = _fac_list_to_device(facs)
        self.assertEqual(result, {"all": {}})

    def test_fac_list_to_device_with_protocol(self):
        facs = [{"facility": "all", "protocol": "udp"}]
        result = _fac_list_to_device(facs)
        self.assertEqual(result["all"]["protocol"], "udp")
        self.assertNotIn("level", result["all"])

    def test_fac_list_to_device_empty(self):
        self.assertEqual(_fac_list_to_device([]), {})
        self.assertEqual(_fac_list_to_device(None), {})

    def test_fac_device_to_list_with_level(self):
        raw = {"local7": {"level": "err"}, "all": {}}
        result = _fac_device_to_list(raw)
        names = [f["facility"] for f in result]
        self.assertIn("local7", names)
        self.assertIn("all", names)
        local7 = next(f for f in result if f["facility"] == "local7")
        self.assertEqual(local7["severity"], "err")

    def test_fac_device_to_list_empty(self):
        self.assertEqual(_fac_device_to_list({}), [])
        self.assertEqual(_fac_device_to_list(None), [])

    def test_fac_device_to_list_sorted(self):
        raw = {"z-fac": {}, "a-fac": {}}
        result = _fac_device_to_list(raw)
        self.assertEqual(result[0]["facility"], "a-fac")
        self.assertEqual(result[1]["facility"], "z-fac")


class TestWantToDevice(unittest.TestCase):
    """Test argspec -> device shape conversion."""

    def test_empty(self):
        self.assertEqual(_want_to_device({}), {})
        self.assertEqual(_want_to_device(None), {})

    def test_console_facilities(self):
        config = {"console": {"facilities": [{"facility": "local7", "severity": "err"}]}}
        result = _want_to_device(config)
        self.assertIn("console", result)
        self.assertEqual(result["console"]["facility"]["local7"], {"level": "err"})

    def test_global_params_facilities(self):
        config = {"global_params": {"facilities": [{"facility": "cron", "severity": "debug"}]}}
        result = _want_to_device(config)
        self.assertIn("local", result)
        self.assertEqual(result["local"]["facility"]["cron"], {"level": "debug"})

    def test_global_params_marker_interval(self):
        config = {"global_params": {"marker_interval": 111}}
        result = _want_to_device(config)
        self.assertEqual(result["marker"], {"interval": 111})

    def test_global_params_preserve_fqdn(self):
        config = {"global_params": {"preserve_fqdn": True}}
        result = _want_to_device(config)
        self.assertEqual(result["preserve-fqdn"], {})

    def test_hosts_mapped_to_remote(self):
        config = {
            "hosts": [
                {
                    "hostname": "172.16.0.1",
                    "port": 514,
                    "facilities": [{"facility": "local7", "severity": "all"}],
                },
            ],
        }
        result = _want_to_device(config)
        self.assertIn("remote", result)
        self.assertIn("172.16.0.1", result["remote"])
        self.assertEqual(result["remote"]["172.16.0.1"]["port"], 514)
        self.assertIn("local7", result["remote"]["172.16.0.1"]["facility"])

    def test_users_mapped_to_user(self):
        config = {
            "users": [
                {
                    "username": "vyos",
                    "facilities": [{"facility": "local7", "severity": "debug"}],
                },
            ],
        }
        result = _want_to_device(config)
        self.assertIn("user", result)
        self.assertIn("vyos", result["user"])


class TestDeviceToArgspec(unittest.TestCase):
    """Test device response -> argspec shape conversion."""

    def test_empty(self):
        self.assertEqual(_device_to_argspec({}), {})
        self.assertEqual(_device_to_argspec(None), {})

    def test_console(self):
        raw = {"console": {"facility": {"local7": {"level": "err"}}}}
        result = _device_to_argspec(raw)
        self.assertIn("console", result)
        facs = result["console"]["facilities"]
        self.assertEqual(facs[0]["facility"], "local7")
        self.assertEqual(facs[0]["severity"], "err")

    def test_local_to_global_params(self):
        raw = {"local": {"facility": {"cron": {"level": "debug"}}}}
        result = _device_to_argspec(raw)
        self.assertIn("global_params", result)
        facs = result["global_params"]["facilities"]
        self.assertEqual(facs[0]["facility"], "cron")

    def test_marker_interval(self):
        raw = {"marker": {"interval": "111"}}
        result = _device_to_argspec(raw)
        self.assertEqual(result["global_params"]["marker_interval"], "111")

    def test_preserve_fqdn(self):
        raw = {"preserve-fqdn": {}}
        result = _device_to_argspec(raw)
        self.assertTrue(result["global_params"]["preserve_fqdn"])

    def test_remote_to_hosts(self):
        raw = {
            "remote": {
                "172.16.0.1": {
                    "port": 514,
                    "facility": {"local7": {"level": "all"}},
                },
            },
        }
        result = _device_to_argspec(raw)
        self.assertIn("hosts", result)
        host = result["hosts"][0]
        self.assertEqual(host["hostname"], "172.16.0.1")
        self.assertEqual(host["port"], 514)
        self.assertEqual(host["facilities"][0]["facility"], "local7")

    def test_user_to_users(self):
        raw = {"user": {"vyos": {"facility": {"local7": {"level": "debug"}}}}}
        result = _device_to_argspec(raw)
        self.assertIn("users", result)
        self.assertEqual(result["users"][0]["username"], "vyos")

    def test_hosts_sorted(self):
        raw = {"remote": {"z.host": {}, "a.host": {}}}
        result = _device_to_argspec(raw)
        self.assertEqual(result["hosts"][0]["hostname"], "a.host")


class TestDictOpLogging(unittest.TestCase):
    """Test dict_op behaviour with logging device shapes."""

    def test_merged_adds_console_facility(self):
        want = _want_to_device(
            {
                "console": {"facilities": [{"facility": "local7", "severity": "err"}]},
            },
        )
        cmds = dict_op(want, {}, _BASE, op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["console", "facility", "local7", "level", "err"], paths)

    def test_merged_idempotent_console(self):
        want = _want_to_device(
            {
                "console": {"facilities": [{"facility": "local7", "severity": "err"}]},
            },
        )
        have = {"console": {"facility": {"local7": {"level": "err"}}}}
        cmds = dict_op(want, have, _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_merged_adds_preserve_fqdn(self):
        want = _want_to_device({"global_params": {"preserve_fqdn": True}})
        cmds = dict_op(want, {}, _BASE, op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["preserve-fqdn"], paths)

    def test_preserve_fqdn_idempotent(self):
        want = _want_to_device({"global_params": {"preserve_fqdn": True}})
        have = {"preserve-fqdn": {}}
        cmds = dict_op(want, have, _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_purge_removes_extra_remote_host(self):
        want = _want_to_device(
            {
                "hosts": [{"hostname": "10.0.0.1", "facilities": []}],
            },
        )
        have = {
            "remote": {
                "10.0.0.1": {},
                "10.0.0.2": {},
            },
        }
        cmds = dict_op(want, have, _BASE, op="purge")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["remote", "10.0.0.2"], paths)
        self.assertNotIn(_BASE + ["remote", "10.0.0.1"], paths)

    def test_merged_adds_marker_interval(self):
        want = _want_to_device({"global_params": {"marker_interval": 111}})
        cmds = dict_op(want, {}, _BASE, op="set")
        paths = [c[1] for c in cmds]
        self.assertIn(_BASE + ["marker", "interval", "111"], paths)

    def test_no_commands_when_already_correct(self):
        config = {
            "console": {"facilities": [{"facility": "local7", "severity": "err"}]},
            "global_params": {"marker_interval": 111},
        }
        want = _want_to_device(config)
        have = {
            "console": {"facility": {"local7": {"level": "err"}}},
            "marker": {"interval": 111},
        }
        cmds = dict_op(want, have, _BASE, op="set")
        self.assertEqual(cmds, [])

    def test_overridden_idempotent(self):
        config = {
            "console": {"facilities": [{"facility": "local7", "severity": "err"}]},
            "global_params": {"marker_interval": 111},
        }
        want = _want_to_device(config)
        have = {
            "console": {"facility": {"local7": {"level": "err"}}},
            "marker": {"interval": 111},
        }
        # First pass — purge+set
        purge_cmds = []
        for section, section_want in want.items():
            section_have = have.get(section, {})
            purge_cmds += dict_op(section_want, section_have, _BASE + [section], op="purge")
        set_cmds = dict_op(want, have, _BASE, op="set")
        cmds = purge_cmds + set_cmds
        # Second pass — should be empty (idempotent)
        self.assertEqual(cmds, [])


if __name__ == "__main__":
    unittest.main()
