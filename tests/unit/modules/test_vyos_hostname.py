# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.modules.vyos_hostname import (
    _BASE,
    ARGUMENT_SPEC,
    build_commands,
    get_running_config,
)


class TestGetRunningConfig(unittest.TestCase):
    def test_returns_current_hostname(self):
        mock_vyos = MagicMock()
        mock_vyos.get_value = MagicMock(return_value="vyos-core-01")
        self.assertEqual(get_running_config(mock_vyos), "vyos-core-01")

    def test_uses_get_value_not_get_config(self):
        """Regression test for the confirmed architectural bug: this
        module was previously calling a "showConfig"-equivalent
        operation directly via a bare VyOSRestClient, appropriate for
        config subtrees, not the "returnValue" operation VyOS provides
        specifically for a single scalar leaf like this one. Confirms
        get_running_config goes through VyOSModule.get_value, not
        get_config."""
        mock_vyos = MagicMock()
        mock_vyos.get_value = MagicMock(return_value="vyos")
        mock_vyos.get_config = MagicMock(return_value={})
        get_running_config(mock_vyos)
        mock_vyos.get_value.assert_called_once_with(_BASE)
        mock_vyos.get_config.assert_not_called()


class TestBuildCommands(unittest.TestCase):
    def test_merged_sets_new_hostname(self):
        cmds = build_commands({"hostname": "newhost"}, "vyos", "merged")
        self.assertEqual(cmds, [("set", _BASE + ["newhost"])])

    def test_merged_idempotent_when_already_correct(self):
        cmds = build_commands({"hostname": "vyos"}, "vyos", "merged")
        self.assertEqual(cmds, [])

    def test_merged_noop_when_hostname_not_specified(self):
        cmds = build_commands({}, "vyos", "merged")
        self.assertEqual(cmds, [])

    def test_deleted_with_existing_value(self):
        cmds = build_commands({}, "somehost", "deleted")
        self.assertEqual(cmds, [("delete", _BASE)])

    def test_deleted_idempotent_when_already_empty(self):
        cmds = build_commands({}, "", "deleted")
        self.assertEqual(cmds, [])

    def test_config_none_does_not_crash(self):
        cmds = build_commands(None, "vyos", "merged")
        self.assertEqual(cmds, [])


class TestHostnameKeyAlwaysPresent(unittest.TestCase):
    """Regression test for a real bug caught via integration testing:
    "hostname" was conditionally omitted from the gathered/before/after
    dict entirely when its value was empty (e.g. after deletion),
    rather than being present with an empty value. This broke any
    downstream access like gathered.gathered.hostname with an
    AttributeError-equivalent ("object of type 'dict' has no attribute
    'hostname'"), rather than a clean value comparison."""

    def test_gathered_includes_hostname_key_when_empty(self):
        import json
        import sys

        from unittest.mock import patch

        sys.argv = ["x", json.dumps({"ANSIBLE_MODULE_ARGS": {"state": "gathered"}})]
        captured = {}

        def fake_exit_json(self_mod, **kwargs):
            captured.update(kwargs)
            raise SystemExit(0)

        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos.VyOSRestClient",
        ) as mock_client, patch(
            "ansible.module_utils.basic.AnsibleModule.exit_json",
            fake_exit_json,
        ):
            mock_client.return_value.retrieve_return_value.return_value = {"data": ""}
            from ansible_collections.vyos.rest.plugins.modules import vyos_hostname

            with self.assertRaises(SystemExit):
                vyos_hostname.main()

        self.assertIn("hostname", captured["gathered"])
        self.assertEqual(captured["gathered"]["hostname"], "")


class TestGatheredReturnsCommands(unittest.TestCase):
    """Regression test for a bug caught during rework: the gathered
    branch initially dropped commands=[] entirely, contradicting the
    RETURN doc's own "returned: always" claim and regressing from the
    original module's behavior."""

    def test_gathered_includes_empty_commands(self):
        import json
        import sys

        from unittest.mock import patch

        sys.argv = [
            "x",
            json.dumps({"ANSIBLE_MODULE_ARGS": {"state": "gathered"}}),
        ]
        captured = {}

        def fake_exit_json(self_mod, **kwargs):
            captured.update(kwargs)
            raise SystemExit(0)

        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos.VyOSRestClient",
        ) as mock_client, patch(
            "ansible.module_utils.basic.AnsibleModule.exit_json",
            fake_exit_json,
        ):
            mock_client.return_value.retrieve_return_value.return_value = {"data": "vyos"}
            from ansible_collections.vyos.rest.plugins.modules import vyos_hostname

            with self.assertRaises(SystemExit):
                vyos_hostname.main()

        self.assertIn("commands", captured)
        self.assertEqual(captured["commands"], [])
        self.assertEqual(captured["gathered"], {"hostname": "vyos"})


class TestCollapsedStates(unittest.TestCase):
    """replaced/overridden collapse onto merged for this single-value
    resource -- there is nothing else to distinctly replace/override
    when there is only one field. Confirmed via the argspec: no
    separate branch exists for them in build_commands, matching the
    module's own documented design decision."""

    def test_argspec_declares_all_four_states(self):
        self.assertEqual(
            set(ARGUMENT_SPEC["state"]["choices"]),
            {"merged", "replaced", "overridden", "deleted", "gathered"},
        )

    def test_no_rendered_or_parsed_states(self):
        """Confirmed architectural fix: rendered/parsed are CLI-
        collection concepts (offline command/config-text rendering)
        that don't correspond to anything meaningful for a REST
        transport, where the actual payload is a structured API call,
        not a CLI line."""
        self.assertNotIn("rendered", ARGUMENT_SPEC["state"]["choices"])
        self.assertNotIn("parsed", ARGUMENT_SPEC["state"]["choices"])


class TestArgumentSpecNoConnectionParams(unittest.TestCase):
    """Confirmed architectural fix: module-level hostname/port/api_key/
    timeout/verify_ssl params were a genuine outlier in this collection
    -- every other module relies exclusively on the httpapi connection
    plugin for transport/auth, never on module params."""

    def test_no_connection_params_in_argspec(self):
        for key in ("hostname", "port", "api_key", "timeout", "verify_ssl"):
            self.assertNotIn(key, ARGUMENT_SPEC)


if __name__ == "__main__":
    unittest.main()
