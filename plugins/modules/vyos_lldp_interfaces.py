#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_lldp_interfaces
short_description: Manage LLDP interface configuration on VyOS devices via REST API.
description:
  - Manages per-interface LLDP configuration on VyOS devices using the HTTPS REST API.
  - Targets VyOS 1.5+ where LLDP interface mode replaces the legacy disable flag.
  - For the disable flag used in VyOS 1.3/1.4, see C(vyos.vyos.vyos_lldp_interfaces).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of LLDP interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Name of the interface.
        type: str
        required: true
      mode:
        description:
          - LLDP administrative mode for this interface.
          - C(rx-tx) sends and receives LLDP frames (device default).
          - C(disable) disables LLDP on this interface.
          - C(rx) receives only.
          - C(tx) transmits only.
        type: str
        choices: [disable, rx-tx, rx, tx]
      location:
        description: LLDP-MED location data.
        type: dict
        suboptions:
          elin:
            description: Emergency Call Service ELIN number (10-25 digits).
            type: str
          coordinate_based:
            description: Coordinate-based location.
            type: dict
            suboptions:
              latitude:
                description: Latitude (e.g. 33.524449N).
                type: str
                required: true
              longitude:
                description: Longitude (e.g. 22.267255E).
                type: str
                required: true
              altitude:
                description: Altitude in meters.
                type: int
              datum:
                description: Coordinate datum type.
                type: str
                choices: [WGS84, NAD83, MLLW]
  state:
    description:
      - C(merged) - Merge config with existing LLDP interface settings.
      - C(replaced) - Replace config for listed interfaces.
      - C(overridden) - Replace config for all LLDP interfaces.
      - C(deleted) - Remove listed or all LLDP interface config.
      - C(gathered) - Read LLDP interface config from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
notes:
  - Targets VyOS 1.5+ exclusively. The C(mode) parameter replaces the C(enable)
    boolean used in C(vyos.vyos.vyos_lldp_interfaces) for VyOS 1.3/1.4.
seealso:
  - module: vyos.vyos.vyos_lldp_interfaces
  - module: vyos.rest.vyos_lldp_global
"""

EXAMPLES = r"""
- name: Merge LLDP interface configuration
  vyos.rest.vyos_lldp_interfaces:
    config:
      - name: eth0
        mode: disable
        location:
          elin: "1234567890"
      - name: eth1
        location:
          coordinate_based:
            latitude: "33.524449N"
            longitude: "22.267255E"
            altitude: 2200
            datum: WGS84
    state: merged

- name: Delete all LLDP interface configuration
  vyos.rest.vyos_lldp_interfaces:
    state: deleted

- name: Gather current LLDP interface configuration
  vyos.rest.vyos_lldp_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: LLDP interface configuration before this module ran.
  returned: always
  type: list
after:
  description: LLDP interface configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current LLDP interface configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
response:
  description: Raw API response.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    scope_to_spec,
)


_BASE = ["service", "lldp", "interface"]


def _iface_base(name):
    return _BASE + [name]


def _to_device_recursive(d):
    """autoclean, then recursively kebab-convert every key at every
    level. Needed because dict_op requires have's keys to already be
    genuine device kebab-case; autoclean deliberately doesn't convert
    keys itself (by design, since it's meant to be paired with dict_op
    doing the conversion when comparing against a raw device have --
    but want_device here needs to already match the shape have_device
    is built in). Safe to recurse arbitrarily deep here since every
    level (location, coordinate_based) is plain scalar fields, no
    opaque tag-node values or presence-only nested structures like
    vyos_lag_interfaces' member/arp-monitor.target.
    """
    cleaned = autoclean(d)
    if not isinstance(cleaned, dict):
        return cleaned
    return {k.replace("_", "-"): _to_device_recursive(v) for k, v in cleaned.items()}


def _entry_to_device(rest):
    """Confirmed device path (service lldp interface <name>) is
    exclusively owned by this module -- no sibling module shares it,
    unlike interfaces/l3_interfaces/lag_interfaces' shared
    "interfaces <type> <name>" tree. scope_to_spec is still used here
    for consistency and defense against any field this module's own
    argspec doesn't declare.
    """
    scoped = scope_to_spec(rest, _ENTRY_OPTIONS, exclude=("name",))
    return _to_device_recursive(scoped)


def _entry_from_device(data):
    """from_device already recurses into nested dicts and converts
    keys at every level -- no hand-rolling needed for a structure
    this simple (plain scalar fields throughout, no keyed-list/tag-
    node complexity). scope_to_spec still applied for the same
    defensive reason as the to_device direction.
    """
    scoped = scope_to_spec(data, _ENTRY_OPTIONS, exclude=("name",))
    return from_device(scoped)


def get_running_config(vyos):
    raw = vyos.get_config(["service", "lldp"]) or {}
    if not isinstance(raw, dict):
        return {}
    iface_data = raw.get("interface")
    print("MARKER_REACHED_HERE_998877")
    return iface_data if isinstance(iface_data, dict) else {}


def _device_to_argspec(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        entry = {"name": name}
        entry.update(_entry_from_device(data or {}))
        result.append(entry)
    return result


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    have_list = _device_to_argspec(raw_have)
    have_by_name = {e["name"]: e for e in have_list}
    want_by_name = {e["name"]: e for e in config if e.get("name")}

    if state == "deleted":
        cmds = []
        if not config:
            for name in have_by_name:
                cmds.append(("delete", _iface_base(name)))
            return cmds
        for entry in config:
            name = entry.get("name")
            if name and name in have_by_name:
                cmds.append(("delete", _iface_base(name)))
        return cmds

    commands = []
    if state == "overridden":
        for name in set(have_by_name) - set(want_by_name):
            commands.append(("delete", _iface_base(name)))

    for name, want_entry in want_by_name.items():
        have_entry = have_by_name.get(name, {})
        want_device = _entry_to_device({k: v for k, v in want_entry.items() if k != "name"})
        have_device = _entry_to_device({k: v for k, v in have_entry.items() if k != "name"})
        base = _iface_base(name)

        if state in ("replaced", "overridden"):
            commands += dict_op(want_device, have_device, base, op="purge")
        commands += dict_op(want_device, have_device, base, op="set")

    return commands


_COORD_OPTIONS = dict(
    latitude=dict(type="str", required=True),
    longitude=dict(type="str", required=True),
    altitude=dict(type="int"),
    datum=dict(type="str", choices=["WGS84", "NAD83", "MLLW"]),
)

_LOCATION_OPTIONS = dict(
    elin=dict(type="str"),
    coordinate_based=dict(type="dict", options=_COORD_OPTIONS),
)

_ENTRY_OPTIONS = dict(
    name=dict(type="str", required=True),
    mode=dict(type="str", choices=["disable", "rx-tx", "rx", "tx"]),
    location=dict(type="dict", options=_LOCATION_OPTIONS),
)

ARGUMENT_SPEC = dict(
    config=dict(type="list", elements="dict", options=_ENTRY_OPTIONS),
    state=dict(
        type="str",
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    for entry in have:
        cast_by_spec(entry, _ENTRY_OPTIONS)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have, after=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after_raw = get_running_config(vyos)
        after = _device_to_argspec(after_raw)
        for entry in after:
            cast_by_spec(entry, _ENTRY_OPTIONS)
        module.exit_json(
            changed=True,
            before=have,
            after=after,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
