# -*- coding: utf-8 -*-
"""Unit tests for the shared functions in plugins/module_utils/vyos.py.

Kept separate from any single module's test file since these test
shared, cross-module infrastructure (cast_by_spec, dict_op, autoclean,
from_device) rather than any one module's own behavior -- a fix here
should be verifiable, and shippable, independently of any module that
happens to use it.
"""
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock, patch

from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


class TestGetValue(unittest.TestCase):
    """Tests for VyOSModule.get_value -- the wrapper for VyOS's
    "returnValue" retrieve operation, added specifically because
    get_config wraps a genuinely different operation ("showConfig",
    for config subtrees) that doesn't fit a plain scalar leaf like
    "system host-name". Confirmed against the actual REST client:
    retrieve_show_config posts op="showConfig", retrieve_return_value
    posts op="returnValue" -- these are different VyOS API operations,
    not interchangeable.
    """

    def _make_vyos(self):
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos.VyOSRestClient",
        ) as mock_client_cls:
            vyos = VyOSModule(MagicMock())
            return vyos, mock_client_cls.return_value

    def test_returns_the_scalar_value(self):
        vyos, mock_client = self._make_vyos()
        mock_client.retrieve_return_value.return_value = {"data": "vyos-core-01"}
        self.assertEqual(vyos.get_value(["system", "host-name"]), "vyos-core-01")

    def test_calls_retrieve_return_value_not_retrieve_show_config(self):
        vyos, mock_client = self._make_vyos()
        mock_client.retrieve_return_value.return_value = {"data": "vyos"}
        vyos.get_value(["system", "host-name"])
        mock_client.retrieve_return_value.assert_called_once_with(["system", "host-name"])
        mock_client.retrieve_show_config.assert_not_called()

    def test_empty_value_returns_empty_string(self):
        vyos, mock_client = self._make_vyos()
        mock_client.retrieve_return_value.return_value = {"data": ""}
        self.assertEqual(vyos.get_value(["system", "host-name"]), "")

    def test_missing_data_key_returns_empty_string(self):
        vyos, mock_client = self._make_vyos()
        mock_client.retrieve_return_value.return_value = {}
        self.assertEqual(vyos.get_value(["system", "host-name"]), "")

    def test_error_propagates_rather_than_being_swallowed(self):
        """Confirmed real bug fixed in vyos_hostname: a genuine backend
        error (auth failure, timeout, malformed response) must not be
        silently treated as "value is unset" -- that could cause a
        caller to overwrite a value that was actually already correct,
        or a delete-state caller to wrongly report no-op success on a
        real failure. get_value lets VyOSRestError propagate; the
        caller is responsible for a clean module.fail_json.
        """
        from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
            VyOSRestError,
        )

        vyos, mock_client = self._make_vyos()
        mock_client.retrieve_return_value.side_effect = VyOSRestError("simulated failure")
        with self.assertRaises(VyOSRestError):
            vyos.get_value(["system", "host-name"])


if __name__ == "__main__":
    unittest.main()
