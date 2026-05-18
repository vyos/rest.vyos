#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_lag_interfaces
short_description: LAG/bonding interfaces resource module via REST API.
description:
  - Manages Link Aggregation Group (LAG/bond) interfaces on VyOS via REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of LAG interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Bond interface name (e.g. bond0).
        type: str
        required: true
      mode:
        description: Bonding mode.
        type: str
        choices: [802.3ad, active-backup, broadcast, round-robin,
                  transmit-load-balance, adaptive-load-balance, xor-hash]
      members:
        description: Member interfaces.
        type: list
        elements: dict
        suboptions:
          member:
            description: Interface name.
            type: str
      primary:
        description: Primary interface name.
        type: str
      hash_policy:
        description: Transmit hash policy.
        type: str
        choices: [layer2, layer2+3, layer3+4]
      arp_monitor:
        description: ARP monitoring settings.
        type: dict
        suboptions:
          interval:
            description: Monitoring interval in ms.
            type: int
          target:
            description: Target IP addresses.
            type: list
            elements: str
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


_MODE_MAP = {
    "802.3ad": "802.3ad",
    "active-backup": "active-backup",
    "broadcast": "broadcast",
    "round-robin": "round-robin",
    "transmit-load-balance": "transmit-load-balance",
    "adaptive-load-balance": "adaptive-load-balance",
    "xor-hash": "xor-hash",
}


def _get(client):
    try:
        r = client.retrieve_show_config(["interfaces", "bonding"])
        data = r.get("data") or {}
        out = []
        for bname, bdata in data.items():
            entry = {"name": bname}
            if isinstance(bdata, dict):
                if "mode" in bdata:
                    entry["mode"] = bdata["mode"]
                if "primary" in bdata:
                    entry["primary"] = bdata["primary"]
                if "hash-policy" in bdata:
                    entry["hash_policy"] = bdata["hash-policy"]
                members = []
                for m in (
                    bdata.get("member", {}).keys() if isinstance(bdata.get("member"), dict) else []
                ):
                    members.append({"member": m})
                if members:
                    entry["members"] = members
            out.append(entry)
        return out
    except VyOSRestError:
        return []


def _apply(client, cfg, commands):
    name = cfg["name"]
    base = ["interfaces", "bonding", name]
    client.configure_set(base)
    commands.append("set interfaces bonding {n}".format(n=name))

    if cfg.get("mode"):
        client.configure_set(base + ["mode"], cfg["mode"])
        commands.append("set interfaces bonding {n} mode {m}".format(n=name, m=cfg["mode"]))
    if cfg.get("primary"):
        client.configure_set(base + ["primary"], cfg["primary"])
    if cfg.get("hash_policy"):
        client.configure_set(base + ["hash-policy"], cfg["hash_policy"])
    for m in cfg.get("members") or []:
        client.configure_set(["interfaces", "ethernet", m["member"], "bond-group"], name)
        commands.append("set interfaces ethernet {m} bond-group {n}".format(m=m["member"], n=name))
    arp = cfg.get("arp_monitor") or {}
    if arp.get("interval"):
        client.configure_set(base + ["arp-monitor", "interval"], str(arp["interval"]))
    for t in arp.get("target") or []:
        client.configure_set(base + ["arp-monitor", "target"], t)


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                mode=dict(type="str", choices=list(_MODE_MAP.keys())),
                members=dict(
                    type="list",
                    elements="dict",
                    options=dict(member=dict(type="str")),
                ),
                primary=dict(type="str"),
                hash_policy=dict(type="str", choices=["layer2", "layer2+3", "layer3+4"]),
                arp_monitor=dict(
                    type="dict",
                    options=dict(
                        interval=dict(type="int"),
                        target=dict(type="list", elements="str"),
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
            for b in before:
                if b["name"] in targets:
                    client.configure_delete(["interfaces", "bonding", b["name"]])
                    commands.append("delete interfaces bonding {n}".format(n=b["name"]))
                    changed = True
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
