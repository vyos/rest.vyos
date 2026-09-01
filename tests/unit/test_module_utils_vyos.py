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

from ansible_collections.vyos.rest.plugins.module_utils.vyos import cast_by_spec


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


if __name__ == "__main__":
    unittest.main()
