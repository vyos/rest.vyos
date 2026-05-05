#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_vlan
short_description: Manage VLANs on VyOS network devices via REST API.
description:
  - Manages 802.1Q VLAN sub-interfaces on VyOS Ethernet interfaces using
    the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_vlan) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  vlan_id:
    description: VLAN ID (0-4094).
    type: int
  name:
    description: VLAN name (used as description on the VIF).
    type: str
  address:
    description: IP address for the VLAN interface.
    type: str
  interfaces:
    description: List of physical interfaces to configure the VLAN on.
    type: list
    elements: str
  aggregate:
    description: List of VLAN definitions.
    type: list
    elements: dict
    suboptions:
      vlan_id:
        type: int
        required: true
      name:
        type: str
      address:
        type: str
      interfaces:
        type: list
        elements: str
        required: true
      state:
        type: str
        choices: [present, absent]
  state:
    description: C(present) to configure, C(absent) to remove.
    type: str
    choices: [present, absent]
    default: present
  purge:
    description: Remove VLANs not defined in aggregate.
    type: bool
    default: false
  hostname:
    type: str
    required: true
  port:
    type: int
    default: 443
  api_key:
    type: str
    required: true
    no_log: true
  timeout:
    type: int
    default: 30
  verify_ssl:
    type: bool
    default: false
"""

RETURN = r"""
commands:
  description: set/delete commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def _apply_vlan(client, vlan, commands):
    vid = str(vlan["vlan_id"])
    for iface in vlan.get("interfaces") or []:
        # Detect interface type
        if iface.startswith("bond"):
            itype = "bonding"
        else:
            itype = "ethernet"
        vif_base = ["interfaces", itype, iface, "vif", vid]
        client.configure_set(vif_base)
        commands.append("set interfaces {t} {i} vif {v}".format(t=itype, i=iface, v=vid))
        if vlan.get("name"):
            client.configure_set(vif_base + ["description"], vlan["name"])
            commands.append(
                "set interfaces {t} {i} vif {v} description '{n}'".format(
                    t=itype,
                    i=iface,
                    v=vid,
                    n=vlan["name"],
                ),
            )
        if vlan.get("address"):
            client.configure_set(vif_base + ["address"], vlan["address"])
            commands.append(
                "set interfaces {t} {i} vif {v} address {a}".format(
                    t=itype,
                    i=iface,
                    v=vid,
                    a=vlan["address"],
                ),
            )


def _delete_vlan(client, vlan, commands):
    vid = str(vlan["vlan_id"])
    for iface in vlan.get("interfaces") or []:
        itype = "bonding" if iface.startswith("bond") else "ethernet"
        try:
            client.configure_delete(["interfaces", itype, iface, "vif", vid])
            commands.append("delete interfaces {t} {i} vif {v}".format(t=itype, i=iface, v=vid))
        except VyOSRestError:
            pass


def main():
    vlan_spec = dict(
        vlan_id=dict(type="int", required=True),
        name=dict(type="str"),
        address=dict(type="str"),
        interfaces=dict(type="list", elements="str"),
        state=dict(type="str", choices=["present", "absent"]),
    )
    argument_spec = dict(
        vlan_id=dict(type="int"),
        name=dict(type="str"),
        address=dict(type="str"),
        interfaces=dict(type="list", elements="str"),
        aggregate=dict(type="list", elements="dict", options=vlan_spec),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        purge=dict(type="bool", default=False),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["aggregate", "vlan_id"]],
        supports_check_mode=True,
    )
    if module.check_mode:
        module.exit_json(changed=True, commands=["(check mode)"])

    client = VyOSRestClient(module)
    commands = []
    changed = False

    vlans = module.params.get("aggregate") or []
    if module.params.get("vlan_id"):
        vlans = [
            {
                "vlan_id": module.params["vlan_id"],
                "name": module.params.get("name"),
                "address": module.params.get("address"),
                "interfaces": module.params.get("interfaces") or [],
                "state": module.params.get("state", "present"),
            },
        ]

    try:
        for vlan in vlans:
            v_state = vlan.get("state") or module.params.get("state", "present")
            if v_state == "absent":
                _delete_vlan(client, vlan, commands)
            else:
                _apply_vlan(client, vlan, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, commands=commands)


if __name__ == "__main__":
    main()
