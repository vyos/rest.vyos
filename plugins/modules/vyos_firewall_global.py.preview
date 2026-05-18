#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_global
short_description: Firewall global resource module via REST API.
description:
  - Manages global VyOS firewall parameters (groups, ICMP redirect policy,
    source validation, ping policy) via the HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: Global firewall configuration.
    type: dict
    suboptions:
      validation:
        description: Source-validation policy (strict/loose/disable).
        type: str
        choices: [strict, loose, disable]
      config_trap:
        description: SNMP trap on firewall config changes.
        type: bool
      ping:
        description: ICMP echo policy.
        type: dict
        suboptions:
          all:
            type: bool
          broadcast:
            type: bool
      route_redirects:
        description: ICMP redirect / source-route options per AFI.
        type: list
        elements: dict
        suboptions:
          afi:
            type: str
            choices: [ipv4, ipv6]
            required: true
          icmp_redirects:
            type: dict
            suboptions:
              send:
                type: bool
              receive:
                type: bool
          ip_src_route:
            type: bool
      group:
        description: Firewall object groups.
        type: dict
        suboptions:
          address_group:
            type: list
            elements: dict
            suboptions:
              name:
                type: str
                required: true
              description:
                type: str
              members:
                description: List of IP addresses or ranges.
                type: list
                elements: dict
                suboptions:
                  address:
                    type: str
              afi:
                type: str
                default: ipv4
                choices: [ipv4, ipv6]
          network_group:
            type: list
            elements: dict
            suboptions:
              name:
                type: str
                required: true
              description:
                type: str
              members:
                description: List of network prefixes.
                type: list
                elements: dict
                suboptions:
                  address:
                    type: str
          port_group:
            type: list
            elements: dict
            suboptions:
              name:
                type: str
                required: true
              description:
                type: str
              members:
                description: List of port numbers or ranges.
                type: list
                elements: dict
                suboptions:
                  port:
                    type: str
  state:
    description: Desired state.
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


_FW_BASE = ["firewall"]


def _get(client):
    try:
        r = client.retrieve_show_config(_FW_BASE)
        return r.get("data") or {}
    except VyOSRestError:
        return {}


def _apply(client, config, commands):
    if config.get("validation"):
        path = (
            _FW_BASE + ["ip", "src-route"]
            if config["validation"] == "disable"
            else _FW_BASE + ["ip", "enable-default-log"]
        )
        # Use the proper path
        p = (
            ["firewall", "global-options", "source-validation"]
            if client.retrieve_exists(["firewall", "global-options"])
            else ["firewall", "ip", "src-route"]
        )
        client.configure_set(["firewall", "ip", "source-validation"], config["validation"])
        commands.append("set firewall ip source-validation {v}".format(v=config["validation"]))

    if config.get("config_trap") is not None:
        val = "enable" if config["config_trap"] else "disable"
        client.configure_set(["firewall", "config-trap"], val)
        commands.append("set firewall config-trap {v}".format(v=val))

    ping = config.get("ping") or {}
    if ping.get("all") is not None:
        action = "enable" if ping["all"] else "disable"
        client.configure_set(["firewall", "ip", "ping", "all"], action)
        commands.append("set firewall ip ping all {a}".format(a=action))
    if ping.get("broadcast") is not None:
        action = "enable" if ping["broadcast"] else "disable"
        client.configure_set(["firewall", "ip", "ping", "broadcast"], action)
        commands.append("set firewall ip ping broadcast {a}".format(a=action))

    for rr in config.get("route_redirects") or []:
        afi = rr["afi"]
        ip_key = "ip" if afi == "ipv4" else "ipv6"
        icmp = rr.get("icmp_redirects") or {}
        if icmp.get("send") is not None:
            p = ["firewall", ip_key, "send-redirects"]
            client.configure_set(p, "enable" if icmp["send"] else "disable")
            commands.append(
                "set {p} {v}".format(p=" ".join(p), v="enable" if icmp["send"] else "disable"),
            )
        if icmp.get("receive") is not None:
            p = ["firewall", ip_key, "disable-forwarding"]
            client.configure_set(p, "enable" if not icmp["receive"] else "disable")
        if rr.get("ip_src_route") is not None:
            p = ["firewall", ip_key, "source-route"]
            client.configure_set(p, "enable" if rr["ip_src_route"] else "disable")

    grp = config.get("group") or {}
    for ag in grp.get("address_group") or []:
        gpath = ["firewall", "group", "address-group", ag["name"]]
        client.configure_set(gpath)
        commands.append("set {p}".format(p=" ".join(gpath)))
        if ag.get("description"):
            client.configure_set(gpath + ["description"], ag["description"])
        for m in ag.get("members") or []:
            client.configure_set(gpath + ["address"], m["address"])
            commands.append("set {p} address {a}".format(p=" ".join(gpath), a=m["address"]))

    for ng in grp.get("network_group") or []:
        gpath = ["firewall", "group", "network-group", ng["name"]]
        client.configure_set(gpath)
        commands.append("set {p}".format(p=" ".join(gpath)))
        if ng.get("description"):
            client.configure_set(gpath + ["description"], ng["description"])
        for m in ng.get("members") or []:
            client.configure_set(gpath + ["network"], m["address"])

    for pg in grp.get("port_group") or []:
        gpath = ["firewall", "group", "port-group", pg["name"]]
        client.configure_set(gpath)
        commands.append("set {p}".format(p=" ".join(gpath)))
        if pg.get("description"):
            client.configure_set(gpath + ["description"], pg["description"])
        for m in pg.get("members") or []:
            client.configure_set(gpath + ["port"], str(m["port"]))


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                validation=dict(type="str", choices=["strict", "loose", "disable"]),
                config_trap=dict(type="bool"),
                ping=dict(
                    type="dict",
                    options=dict(all=dict(type="bool"), broadcast=dict(type="bool")),
                ),
                route_redirects=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                        icmp_redirects=dict(
                            type="dict",
                            options=dict(send=dict(type="bool"), receive=dict(type="bool")),
                        ),
                        ip_src_route=dict(type="bool"),
                    ),
                ),
                group=dict(
                    type="dict",
                    options=dict(
                        address_group=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                name=dict(type="str", required=True),
                                description=dict(type="str"),
                                afi=dict(type="str", default="ipv4"),
                                members=dict(
                                    type="list",
                                    elements="dict",
                                    options=dict(address=dict(type="str")),
                                ),
                            ),
                        ),
                        network_group=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                name=dict(type="str", required=True),
                                description=dict(type="str"),
                                members=dict(
                                    type="list",
                                    elements="dict",
                                    options=dict(address=dict(type="str")),
                                ),
                            ),
                        ),
                        port_group=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                name=dict(type="str", required=True),
                                description=dict(type="str"),
                                members=dict(
                                    type="list",
                                    elements="dict",
                                    options=dict(port=dict(type="str")),
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
                client.configure_delete(_FW_BASE)
                commands.append("delete firewall")
                changed = True
        elif state in ("merged", "replaced"):
            if state == "replaced" and before:
                client.configure_delete(_FW_BASE)
                commands.append("delete firewall")
            _apply(client, config, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
