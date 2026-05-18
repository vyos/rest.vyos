#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_lldp_interfaces
short_description: LLDP interfaces resource module via REST API.
description:
  - Manages per-interface LLDP settings (enable/disable, location) on VyOS
    via the HTTPS REST API.
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
        description: Interface name.
        type: str
        required: true
      enable:
        description: Enable LLDP on this interface (default true).
        type: bool
        default: true
      location:
        description: LLDP-MED location data.
        type: dict
        suboptions:
          coordinate_based:
            type: dict
            suboptions:
              altitude:
                type: int
              datum:
                type: str
                choices: [WGS84, NAD83, MLLW]
              latitude:
                type: str
                required: true
              longitude:
                type: str
                required: true
          elin:
            description: Emergency ELIN number (10-25 digits).
            type: str
  state:
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
    "lo": "loopback",
    "dummy": "dummy",
    "br": "bridge",
}


def _itype(name):
    for p, t in _IFACE_TYPES.items():
        if name.startswith(p):
            return t
    return "ethernet"


def _get(client):
    try:
        r = client.retrieve_show_config(["service", "lldp", "interface"])
        data = r.get("data") or {}
        out = []
        for iname, idata in data.items():
            entry = {"name": iname}
            if isinstance(idata, dict):
                entry["enable"] = "disable" not in idata
            out.append(entry)
        return out
    except VyOSRestError:
        return []


def _apply(client, cfg, commands):
    name = cfg["name"]
    base = ["service", "lldp", "interface", name]
    client.configure_set(base)
    commands.append("set service lldp interface {n}".format(n=name))

    if "enable" in cfg and not cfg["enable"]:
        client.configure_set(base + ["disable"])
        commands.append("set service lldp interface {n} disable".format(n=name))

    loc = cfg.get("location") or {}
    coord = loc.get("coordinate_based") or {}
    if coord:
        lbase = base + ["location", "coordinate-based"]
        if coord.get("latitude"):
            client.configure_set(lbase + ["latitude"], coord["latitude"])
        if coord.get("longitude"):
            client.configure_set(lbase + ["longitude"], coord["longitude"])
        if coord.get("altitude"):
            client.configure_set(lbase + ["altitude"], str(coord["altitude"]))
        if coord.get("datum"):
            client.configure_set(lbase + ["datum"], coord["datum"])
        commands.append(
            "set service lldp interface {n} location coordinate-based ...".format(n=name),
        )
    if loc.get("elin"):
        client.configure_set(base + ["location", "elin"], loc["elin"])
        commands.append(
            "set service lldp interface {n} location elin {e}".format(n=name, e=loc["elin"]),
        )


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                enable=dict(type="bool", default=True),
                location=dict(
                    type="dict",
                    options=dict(
                        coordinate_based=dict(
                            type="dict",
                            options=dict(
                                altitude=dict(type="int"),
                                datum=dict(type="str", choices=["WGS84", "NAD83", "MLLW"]),
                                latitude=dict(type="str", required=True),
                                longitude=dict(type="str", required=True),
                            ),
                        ),
                        elin=dict(type="str"),
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
            for cfg in config if config else before:
                name = cfg["name"] if isinstance(cfg, dict) else cfg
                try:
                    client.configure_delete(["service", "lldp", "interface", name])
                    commands.append("delete service lldp interface {n}".format(n=name))
                    changed = True
                except VyOSRestError:
                    pass
        elif state in ("merged", "replaced", "overridden"):
            for cfg in config:
                _apply(client, cfg, commands)
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
