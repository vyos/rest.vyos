#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv3
short_description: OSPFv3 resource module via REST API.
description:
  - Manages OSPFv3 (OSPF for IPv6) configuration on VyOS via HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: OSPFv3 configuration.
    type: dict
    suboptions:
      areas:
        type: list
        elements: dict
        suboptions:
          area_id:
            type: str
          export_list:
            type: str
          import_list:
            type: str
          interface:
            description: Interfaces in this area.
            type: list
            elements: dict
            suboptions:
              name:
                type: str
          range:
            type: list
            elements: dict
            suboptions:
              address:
                type: str
              advertise:
                type: bool
              not_advertise:
                type: bool
      parameters:
        type: dict
        suboptions:
          router_id:
            type: str
      redistribute:
        type: list
        elements: dict
        suboptions:
          route_type:
            type: str
            choices: [bgp, connected, kernel, ripng, static]
          route_map:
            type: str
  state:
    type: str
    choices: [merged, replaced, deleted, gathered]
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
  type: dict
after:
  returned: when changed
  type: dict
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


_BASE = ["protocols", "ospfv3"]


def _get(client):
    try:
        r = client.retrieve_show_config(_BASE)
        return r.get("data") or {}
    except VyOSRestError:
        return {}


def _apply(client, config, commands):
    params = config.get("parameters") or {}
    if params.get("router_id"):
        client.configure_set(_BASE + ["parameters", "router-id"], params["router_id"])
        commands.append(
            "set protocols ospfv3 parameters router-id {r}".format(r=params["router_id"]),
        )

    for redist in config.get("redistribute") or []:
        rb = _BASE + ["redistribute", redist["route_type"]]
        client.configure_set(rb)
        commands.append("set protocols ospfv3 redistribute {r}".format(r=redist["route_type"]))
        if redist.get("route_map"):
            client.configure_set(rb + ["route-map"], redist["route_map"])

    for area in config.get("areas") or []:
        aid = area["area_id"]
        ab = _BASE + ["area", aid]
        client.configure_set(ab)
        commands.append("set protocols ospfv3 area '{a}'".format(a=aid))
        if area.get("export_list"):
            client.configure_set(ab + ["export-list"], area["export_list"])
            commands.append(
                "set protocols ospfv3 area {a} export-list {e}".format(
                    a=aid,
                    e=area["export_list"],
                ),
            )
        if area.get("import_list"):
            client.configure_set(ab + ["import-list"], area["import_list"])
        for iface in area.get("interface") or []:
            client.configure_set(ab + ["interface"], iface["name"])
            commands.append(
                "set protocols ospfv3 area {a} interface {i}".format(
                    a=aid,
                    i=iface["name"],
                ),
            )
        for rng in area.get("range") or []:
            rb2 = ab + ["range", rng["address"]]
            client.configure_set(rb2)
            commands.append(
                "set protocols ospfv3 area {a} range {r}".format(
                    a=aid,
                    r=rng["address"],
                ),
            )
            if rng.get("advertise"):
                client.configure_set(rb2 + ["advertise"])
            if rng.get("not_advertise"):
                client.configure_set(rb2 + ["not-advertise"])


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                areas=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        area_id=dict(type="str"),
                        export_list=dict(type="str"),
                        import_list=dict(type="str"),
                        interface=dict(
                            type="list",
                            elements="dict",
                            options=dict(name=dict(type="str")),
                        ),
                        range=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                address=dict(type="str"),
                                advertise=dict(type="bool"),
                                not_advertise=dict(type="bool"),
                            ),
                        ),
                    ),
                ),
                parameters=dict(type="dict", options=dict(router_id=dict(type="str"))),
                redistribute=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        route_type=dict(
                            type="str",
                            choices=["bgp", "connected", "kernel", "ripng", "static"],
                        ),
                        route_map=dict(type="str"),
                    ),
                ),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "replaced", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "merged", ["config"]), ("state", "replaced", ["config"])],
        supports_check_mode=True,
    )
    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config")
    commands = []
    changed = False
    before = _get(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])
    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "deleted":
            if before:
                client.configure_delete(_BASE)
                commands.append("delete protocols ospfv3")
                changed = True
        elif state in ("merged", "replaced"):
            if state == "replaced" and before:
                client.configure_delete(_BASE)
                commands.append("delete protocols ospfv3")
            _apply(client, config, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
