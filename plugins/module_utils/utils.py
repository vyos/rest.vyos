"""
Shared utility functions for the vyos.rest collection.
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type


def normalize_to_list(value):
    """Coerce any VyOS config value into a flat Python list.

    VyOS returns config data in inconsistent shapes depending on how many
    values are present:
      - ``None``        -> no config exists          -> ``[]``
      - ``{}``          -> empty dict (node exists)  -> ``[]``
      - ``"10.0.0.1"``  -> single string value       -> ``["10.0.0.1"]``
      - ``["a", "b"]``  -> already a list            -> ``["a", "b"]``
      - ``{"a": {}, "b": {}}`` -> dict of leaf nodes -> ``["a", "b"]``

    Args:
        value: Raw value from a VyOS ``showConfig`` response.

    Returns:
        list: Flat list of string values.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        # Keys are the values; dict values are sub-config (ignored here)
        return [str(k) for k in value.keys()]
    # Fallback: try to convert
    return [str(value)]


def normalize_to_dict(value):
    """Coerce a VyOS multi-value node into a dict keyed by value.

    Args:
        value: Raw value from showConfig (None, str, list, or dict).

    Returns:
        dict: ``{value: sub_config}`` pairs.
    """
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {str(v): {} for v in value}
    if isinstance(value, str):
        return {value: {}}
    return {}
