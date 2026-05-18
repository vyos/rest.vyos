#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_interfaces
short_description: Firewall interfaces resource module via REST API.
description:
  - Attaches or detaches named firewall rule sets to/from interface
    directions (in/out/local) using the VyOS HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of interface firewall attachment configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Interface name.
        type: str
        required: true
      access_rules:
        description: Firewall rule sets per AFI.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family.
            type: str
            choices: [ipv4, ipv6]
            required: true
          rules:
            description: Rule sets and directions.
            type: list
            elements: dict
            suboptions:
              name:
                description: Rule set name.
                type: str
              direction:
                description: Traffic direction.
                type: str
                choices: [in, local, out]
                required: true
  state:
    description: Desired state.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
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
before:
  returned: always
  type: list
after:
  returned: when changed
  type: list
commands:
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_IFACE_TYPES = {
    "eth": "ethernet",
    "bond": "bonding",
    "vti": "vti",
    "vxlan": "vxlan",
    "lo": "loopback",
    "dummy": "dummy",
    "br": "bridge",
    "wg": "wireguard",
    "tun": "tunnel",
}


def _itype(name):
    for p, t in _IFACE_TYPES.items():
        if name.startswith(p):
            return t
    return "ethernet"


def _fw_direction_key(afi, direction):
    if afi == "ipv4":
        return {"in": "in", "out": "out", "local": "local"}[direction]
    return {"in": "in", "out": "out", "local": "local"}[direction]


def _apply(client, iface_cfg, commands):
    name = iface_cfg["name"]
    itype = _itype(name)
    ibase = ["interfaces", itype, name, "firewall"]

    for ar in iface_cfg.get("access_rules") or []:
        afi = ar["afi"]
        fw_key = "firewall" if afi == "ipv4" else "ipv6"
        for rule in ar.get("rules") or []:
            direction = rule["direction"]
            rs_name = rule.get("name")
            if rs_name:
                path = ibase + [direction, fw_key if afi == "ipv6" else "name"]
                client.configure_set(path, rs_name)
                commands.append(
                    "set interfaces {t} {n} firewall {d} {k} '{rs}'".format(
                        t=itype,
                        n=name,
                        d=direction,
                        k="ipv6-name" if afi == "ipv6" else "name",
                        rs=rs_name,
                    ),
                )


def _delete_iface_fw(client, name, commands):
    itype = _itype(name)
    path = ["interfaces", itype, name, "firewall"]
    try:
        client.configure_delete(path)
        commands.append("delete interfaces {t} {n} firewall".format(t=itype, n=name))
    except VyOSRestError:
        pass


def _get(client):
    try:
        result = client.retrieve_show_config(["interfaces"])
        raw = result.get("data") or {}
        out = []
        for itype, itype_data in raw.items():
            if not isinstance(itype_data, dict):
                continue
            for iname, idata in itype_data.items():
                fw = idata.get("firewall") if isinstance(idata, dict) else None
                if fw:
                    out.append({"name": iname, "firewall": fw})
        return out
    except VyOSRestError:
        return []


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                access_rules=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                        rules=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                name=dict(type="str"),
                                direction=dict(
                                    type="str",
                                    required=True,
                                    choices=["in", "local", "out"],
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "replaced", "overridden", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config") or []
    commands = []
    changed = False
    before = _get(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])
    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "deleted":
            targets = {i["name"] for i in config} if config else {i["name"] for i in before}
            for iface in before:
                if iface["name"] in targets:
                    _delete_iface_fw(client, iface["name"], commands)
                    changed = True
        elif state in ("merged", "replaced", "overridden"):
            if state in ("replaced", "overridden"):
                for cfg in config:
                    _delete_iface_fw(client, cfg["name"], commands)
            for cfg in config:
                _apply(client, cfg, commands)
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
