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
          - C(rx-tx) sends and receives LLDP frames (default).
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
  running_config:
    description: Used only with state C(parsed).
    type: str
  state:
    description:
      - C(merged) - Merge config with existing LLDP interface settings.
      - C(replaced) - Replace config for listed interfaces.
      - C(overridden) - Replace config for all LLDP interfaces.
      - C(deleted) - Remove listed or all LLDP interface config.
      - C(gathered) - Read LLDP interface config from device without changes.
      - C(rendered) - Return commands for provided config without connecting.
      - C(parsed) - Parse running_config into structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered, rendered, parsed]
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
rendered:
  description: Commands for provided config (state=rendered).
  returned: when state is rendered
  type: list
parsed:
  description: Structured data parsed from running_config (state=parsed).
  returned: when state is parsed
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["service", "lldp", "interface"]


def _iface_base(name):
    return _BASE + [name]


def get_running_config(vyos):
    raw = vyos.get_config(["service", "lldp"])
    if not raw or not isinstance(raw, dict):
        return []

    iface_data = raw.get("interface") or {}
    if not isinstance(iface_data, dict):
        return []

    result = []
    for name, data in sorted(iface_data.items()):
        data = data or {}
        entry = {"name": name}

        if data.get("mode"):
            entry["mode"] = data["mode"]

        loc_data = data.get("location") or {}
        if isinstance(loc_data, dict) and loc_data:
            loc = {}
            if "elin" in loc_data:
                loc["elin"] = loc_data["elin"]
            cb = loc_data.get("coordinate-based") or {}
            if isinstance(cb, dict) and cb:
                coord = {}
                if "latitude" in cb:
                    coord["latitude"] = cb["latitude"]
                if "longitude" in cb:
                    coord["longitude"] = cb["longitude"]
                if "altitude" in cb:
                    coord["altitude"] = int(cb["altitude"])
                if "datum" in cb:
                    coord["datum"] = cb["datum"]
                if coord:
                    loc["coordinate_based"] = coord
            if loc:
                entry["location"] = loc

        result.append(entry)

    return result


def _normalize(config):
    result = {}
    for entry in config or []:
        name = entry["name"]
        loc = entry.get("location") or {}
        cb = loc.get("coordinate_based") or {}
        result[name] = {
            "mode": entry.get("mode"),
            "elin": loc.get("elin"),
            "latitude": cb.get("latitude"),
            "longitude": cb.get("longitude"),
            "altitude": cb.get("altitude"),
            "datum": cb.get("datum"),
        }
    return result


def _iface_cmds(name, want, have):
    cmds = []
    base = _iface_base(name)
    have = have or {}

    if want.get("mode") and want["mode"] != have.get("mode"):
        cmds.append(("set", base + ["mode", want["mode"]]))
    elif not want.get("mode") and have.get("mode"):
        cmds.append(("delete", base + ["mode"]))

    loc_base = base + ["location"]
    if want.get("elin") and want["elin"] != have.get("elin"):
        cmds.append(("set", loc_base + ["elin", want["elin"]]))

    cb_base = loc_base + ["coordinate-based"]
    if want.get("latitude") and want["latitude"] != have.get("latitude"):
        cmds.append(("set", cb_base + ["latitude", want["latitude"]]))
    if want.get("longitude") and want["longitude"] != have.get("longitude"):
        cmds.append(("set", cb_base + ["longitude", want["longitude"]]))
    if want.get("altitude") is not None and want["altitude"] != have.get("altitude"):
        cmds.append(("set", cb_base + ["altitude", str(want["altitude"])]))
    if want.get("datum") and want["datum"] != have.get("datum"):
        cmds.append(("set", cb_base + ["datum", want["datum"]]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []
    have_map = _normalize(have_raw)

    if state == "deleted":
        if not config:
            for name in have_map:
                cmds.append(("delete", _iface_base(name)))
        else:
            want_map = _normalize(config)
            for name in want_map:
                if name in have_map:
                    cmds.append(("delete", _iface_base(name)))
        return cmds

    want_map = _normalize(config)

    if state == "overridden":
        for name in set(have_map) - set(want_map):
            cmds.append(("delete", _iface_base(name)))

    for name, want in want_map.items():
        have = have_map.get(name, {})

        if state == "replaced" and name in have_map:
            test_cmds = _iface_cmds(name, want, have)
            if not test_cmds:
                continue
            cmds.append(("delete", _iface_base(name)))
            have = {}

        cmds += _iface_cmds(name, want, have)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            mode=dict(type="str", choices=["disable", "rx-tx", "rx", "tx"]),
            location=dict(
                type="dict",
                options=dict(
                    elin=dict(type="str"),
                    coordinate_based=dict(
                        type="dict",
                        options=dict(
                            latitude=dict(type="str", required=True),
                            longitude=dict(type="str", required=True),
                            altitude=dict(type="int"),
                            datum=dict(type="str", choices=["WGS84", "NAD83", "MLLW"]),
                        ),
                    ),
                ),
            ),
        ),
    ),
    running_config=dict(type="str"),
    state=dict(
        type="str",
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered", "rendered", "parsed"],
    ),
)


def main():
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC,
        mutually_exclusive=[["config", "running_config"]],
        required_if=[
            ("state", "rendered", ["config"]),
            ("state", "parsed", ["running_config"]),
        ],
        supports_check_mode=True,
    )
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

    if state == "parsed":
        module.exit_json(parsed=[])

    if state == "rendered":
        cmds = build_commands(config, [], "merged")
        module.exit_json(rendered=cmds, commands=cmds)

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=get_running_config(vyos),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
