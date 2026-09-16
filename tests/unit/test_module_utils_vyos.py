# -*- coding: utf-8 -*-
"""Unit tests for the shared functions in plugins/module_utils/vyos.py.

Kept separate from any single module's test file since these tests
shared, cross-module infrastructure (cast_by_spec, dict_op, autoclean,
from_device) rather than any one module's own behavior -- a fix here
should be verifiable, and shippable, independently of any module that
happens to use it.
"""
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import unittest

from unittest.mock import MagicMock

from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    cast_by_spec,
)


class TestCastBySpecIntCollapse(unittest.TestCase):
    """Regression test for a confirmed defensive gap: cast_by_spec's
    own docstring claims to handle VyOS's single-value collapse, and
    the list branch already does, but the int branch previously called
    int() directly with no such guard -- a genuinely collapsed list
    for an int-typed leaf would have raised TypeError rather than
    being handled. No module's own fields are known to hit this case
    in live device output today (confirmed for vyos_static_routes:
    distance/admin_distance are always plain scalars) -- this hardens
    shared infrastructure against a case that could arise for a future
    module's fields, matching what the docstring already promises.
    """

    def test_collapsed_single_value_list_for_int_field(self):
        entry = {"distance": ["200"]}
        cast_by_spec(entry, {"distance": {"type": "int"}})
        self.assertEqual(entry["distance"], 200)

    def test_plain_scalar_still_works(self):
        entry = {"distance": "200"}
        cast_by_spec(entry, {"distance": {"type": "int"}})
        self.assertEqual(entry["distance"], 200)

    def test_empty_list_becomes_none(self):
        entry = {"distance": []}
        cast_by_spec(entry, {"distance": {"type": "int"}})
        self.assertIsNone(entry["distance"])

    def test_none_value_untouched(self):
        entry = {"distance": None}
        cast_by_spec(entry, {"distance": {"type": "int"}})
        self.assertIsNone(entry["distance"])


class TestGetValue(unittest.TestCase):
    """Regression tests for a confirmed bug (Copilot): get_value()
    previously did `result.get("data") or ""`, which incorrectly
    converts any falsy-but-valid scalar (0, False, an already-empty
    string) into an empty string -- indistinguishable from the value
    being genuinely unset. Fixed to only treat a missing "data" key
    (None) as unset, leaving every other value -- including falsy
    ones -- exactly as returned."""

    def _vyos_with_data(self, data):
        vyos = VyOSModule.__new__(VyOSModule)
        vyos._client = MagicMock()
        vyos._client.retrieve_return_value.return_value = {"data": data}
        return vyos

    def test_zero_preserved_not_emptied(self):
        vyos = self._vyos_with_data(0)
        self.assertEqual(vyos.get_value(["some", "path"]), 0)

    def test_false_preserved_not_emptied(self):
        vyos = self._vyos_with_data(False)
        self.assertEqual(vyos.get_value(["some", "path"]), False)

    def test_genuine_string_value_passes_through(self):
        vyos = self._vyos_with_data("vyos-core-01")
        self.assertEqual(vyos.get_value(["some", "path"]), "vyos-core-01")

    def test_already_empty_string_stays_empty(self):
        vyos = self._vyos_with_data("")
        self.assertEqual(vyos.get_value(["some", "path"]), "")

    def test_missing_data_key_becomes_empty_string(self):
        vyos = VyOSModule.__new__(VyOSModule)
        vyos._client = MagicMock()
        vyos._client.retrieve_return_value.return_value = {}
        self.assertEqual(vyos.get_value(["some", "path"]), "")


class TestShow(unittest.TestCase):
    """Regression tests for the same confirmed bug class as
    TestGetValue, found independently in show(): `result.get("data")
    or ""` incorrectly converts any falsy-but-valid scalar (0, False,
    an already-empty string) from an operational show command into an
    empty string -- indistinguishable from the command genuinely
    returning nothing. Fixed to only treat a missing "data" key
    (None) as empty, leaving every other value -- including falsy
    ones -- exactly as returned."""

    def _vyos_with_data(self, data):
        vyos = VyOSModule.__new__(VyOSModule)
        vyos._client = MagicMock()
        vyos._client.show.return_value = {"data": data}
        return vyos

    def test_zero_preserved_not_emptied(self):
        vyos = self._vyos_with_data(0)
        self.assertEqual(vyos.show(["some", "op", "path"]), 0)

    def test_false_preserved_not_emptied(self):
        vyos = self._vyos_with_data(False)
        self.assertEqual(vyos.show(["some", "op", "path"]), False)

    def test_genuine_output_passes_through(self):
        vyos = self._vyos_with_data("interface eth0 up")
        self.assertEqual(vyos.show(["some", "op", "path"]), "interface eth0 up")

    def test_already_empty_string_stays_empty(self):
        vyos = self._vyos_with_data("")
        self.assertEqual(vyos.show(["some", "op", "path"]), "")

    def test_missing_data_key_becomes_empty_string(self):
        vyos = VyOSModule.__new__(VyOSModule)
        vyos._client = MagicMock()
        vyos._client.show.return_value = {}
        self.assertEqual(vyos.show(["some", "op", "path"]), "")


if __name__ == "__main__":
    unittest.main()
