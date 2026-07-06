#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_vlan
short_description: Manage VLAN (vif) configuration on VyOS devices using REST API
description:
  - Manages VLAN sub-interface configuration on VyOS Ethernet interfaces
    via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of VLAN configurations.
    type: list
    elements: dict
    suboptions:
      vlan_id:
        description: VLAN ID (0-4094).
        type: int
        required: true
      description:
        description: VLAN description.
        type: str
      address:
        description: IP address for the VLAN interface.
        type: str
      interfaces:
        description: List of Ethernet interfaces to configure this VLAN on.
        type: list
        elements: str
        required: true
  state:
    description:
      - C(present) creates or updates VLANs.
      - C(absent) removes VLANs.
      - C(gathered) returns current VLAN configuration.
    type: str
    choices: [present, absent, gathered]
    default: present
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Configure VLANs
  vyos.rest.vyos_vlan:
    config:
      - vlan_id: 10
        description: VLAN10
        address: 192.168.10.1/24
        interfaces:
          - eth1
      - vlan_id: 20
        description: VLAN20
        interfaces:
          - eth1
          - eth2
    state: present

- name: Remove a VLAN
  vyos.rest.vyos_vlan:
    config:
      - vlan_id: 10
        interfaces:
          - eth1
    state: absent

- name: Gather VLAN configuration
  vyos.rest.vyos_vlan:
    state: gathered
"""

RETURN = r"""
before:
  description: VLAN configuration before this module ran.
  returned: always
  type: list
after:
  description: VLAN configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current VLAN configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
response:
  description: Raw API response.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    dict_op,
)


_BASE = ["interfaces", "ethernet"]

# Keys that define structure (path construction) vs passthrough (diff engine)
_STRUCTURAL_KEYS = {"vlan_id", "interfaces"}


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return []

    eth_data = raw.get("ethernet", raw)
    if not isinstance(eth_data, dict):
        return []

    # Structural reshape: ethernet.<iface>.vif.<id> -> flat list per vlan_id
    # Raw device keys preserved — dict_op handles - <-> _ normalization
    vlan_map = {}
    for iface_name, iface_data in sorted(eth_data.items()):
        iface_data = iface_data or {}
        vif_data = iface_data.get("vif", {}) or {}
        for vlan_id_str, vif_cfg in sorted(
            vif_data.items(),
            key=lambda x: int(x[0]),
        ):
            vif_cfg = vif_cfg or {}
            vlan_id = int(vlan_id_str)
            if vlan_id not in vlan_map:
                vlan_map[vlan_id] = {"vlan_id": vlan_id, "interfaces": [], "_raw": {}}
            vlan_map[vlan_id]["interfaces"].append(iface_name)
            vlan_map[vlan_id]["_raw"].update(vif_cfg)

    result = []
    for vid, entry in sorted(vlan_map.items()):
        item = {"vlan_id": entry["vlan_id"], "interfaces": entry["interfaces"]}
        for k, v in entry["_raw"].items():
            item[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
        result.append(item)
    return result


def build_commands(config, have_list, state):
    cmds = []

    have_map = {(e["vlan_id"], iface): e for e in have_list for iface in e.get("interfaces", [])}

    for want in config or []:
        vlan_id = str(want["vlan_id"])
        for iface in want.get("interfaces") or []:
            vif_base = _BASE + [iface, "vif", vlan_id]
            have_entry = have_map.get((want["vlan_id"], iface), {})

            if state == "absent":
                if have_entry:
                    cmds.append(("delete", vif_base))
                continue

            # Passthrough fields — dict_op handles - <-> _ normalization
            want_vif = {
                k: v for k, v in want.items() if k not in _STRUCTURAL_KEYS and v is not None
            }
            have_vif = {k: v for k, v in have_entry.items() if k not in _STRUCTURAL_KEYS}

            new_cmds = dict_op(want_vif, have_vif, vif_base, op="set")
            if not new_cmds and not have_entry:
                cmds.append(("set", vif_base))
            else:
                cmds += new_cmds

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            vlan_id=dict(type="int", required=True),
            description=dict(type="str"),
            address=dict(type="str"),
            interfaces=dict(type="list", elements="str", required=True),
        ),
    ),
    state=dict(
        type="str",
        default="present",
        choices=["present", "absent", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

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
