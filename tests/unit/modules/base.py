# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os
import unittest

from unittest.mock import MagicMock, patch  # noqa: F401


def load_fixture(filename):
    """Load a JSON fixture file from tests/unit/fixtures/."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    path = os.path.join(fixtures_dir, filename)
    with open(path) as f:
        return json.load(f)


class VyOSModuleTestCase(unittest.TestCase):
    """
    Base class for vyos.rest module unit tests.

    Provides a mock VyOSModule that returns fixture data from
    get_config() without any device connection.

    Usage:
        class TestVyOSNtpGlobal(VyOSModuleTestCase):
            def setUp(self):
                super().setUp()
                self.fixture = load_fixture("ntp_global_running.json")

            def test_merged_adds_new_server(self):
                have = self.module.get_running_config_from_fixture(self.fixture)
                commands = build_commands(want, have, "merged")
                self.assertIn(("set", ["service", "ntp", "server", "1.2.3.4"]), commands)
    """

    def setUp(self):
        self.mock_module = MagicMock()
        self.mock_module.params = {}
        self.mock_module.check_mode = False

        self.mock_vyos = MagicMock()
        self.mock_vyos.get_config = MagicMock(return_value={})

    def set_running_config(self, data):
        """Configure mock get_config to return given data."""
        self.mock_vyos.get_config.return_value = data
