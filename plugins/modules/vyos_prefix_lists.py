#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_prefix_lists
short_description: Prefix-Lists resource module via REST API.
description:
  - Manages IPv4 and IPv6 prefix lists on VyOS via the HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of prefix-list configurations.
    type: list
    elements: dict
    suboptions:
      afi:
        description: Address family.
        type: str
        choices: [ipv4, ipv6]
        required: true
      prefix_lists:
        description: Named prefix lists.
        type: list
        elements: dict
        suboptions:
          name:
            description: Prefix list name.
            type: str
            required: true
          description:
            description: Description.
            type: str
          entries:
            description: Prefix list rules.
            type: list
            elements: dict
            suboptions:
              sequence:
                description: Rule sequence number.
                type: int
                required: true
              description:
                type: str
              action:
                description: permit or deny.
                type: str
                choices: [permit, deny]
              ge:
                description: Minimum prefix length.
                type: int
              le:
                description: Maximum prefix length.
                type: int
              prefix:
                description: Network prefix to match.
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


_PL_KEY = {"ipv4": "prefix-list", "ipv6": "prefix-list6"}


def _get(client):
    try:
        r = client.retrieve_show_config(["policy"])
        data = r.get("data") or {}
        out = []
        for afi, key in [("ipv4", "prefix-list"), ("ipv6", "prefix-list6")]:
            pl_data = data.get(key) or {}
            if not isinstance(pl_data, dict):
                continue
            pls = []
            for pl_name, pl_info in pl_data.items():
                entry = {"name": pl_name}
                if isinstance(pl_info, dict):
                    if "description" in pl_info:
                        entry["description"] = pl_info["description"]
                    rules = []
                    for seq, rdata in (pl_info.get("rule") or {}).items():
                        if isinstance(rdata, dict):
                            rules.append({"sequence": int(seq), **rdata})
                    if rules:
                        entry["entries"] = rules
                pls.append(entry)
            if pls:
                out.append({"afi": afi, "prefix_lists": pls})
        return out
    except VyOSRestError:
        return []


def _apply(client, entry, commands):
    afi = entry["afi"]
    key = _PL_KEY[afi]
    for pl in entry.get("prefix_lists") or []:
        base = ["policy", key, pl["name"]]
        client.configure_set(base)
        commands.append("set policy {k} {n}".format(k=key, n=pl["name"]))
        if pl.get("description"):
            client.configure_set(base + ["description"], pl["description"])
        for rule in pl.get("entries") or []:
            rb = base + ["rule", str(rule["sequence"])]
            client.configure_set(rb)
            commands.append(
                "set policy {k} {n} rule {s}".format(
                    k=key,
                    n=pl["name"],
                    s=rule["sequence"],
                ),
            )
            if rule.get("action"):
                client.configure_set(rb + ["action"], rule["action"])
                commands.append(
                    "set policy {k} {n} rule {s} action {a}".format(
                        k=key,
                        n=pl["name"],
                        s=rule["sequence"],
                        a=rule["action"],
                    ),
                )
            if rule.get("prefix"):
                client.configure_set(rb + ["prefix"], rule["prefix"])
            if rule.get("ge") is not None:
                client.configure_set(rb + ["ge"], str(rule["ge"]))
            if rule.get("le") is not None:
                client.configure_set(rb + ["le"], str(rule["le"]))
            if rule.get("description"):
                client.configure_set(rb + ["description"], rule["description"])


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                prefix_lists=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        name=dict(type="str", required=True),
                        description=dict(type="str"),
                        entries=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                sequence=dict(type="int", required=True),
                                description=dict(type="str"),
                                action=dict(type="str", choices=["permit", "deny"]),
                                ge=dict(type="int"),
                                le=dict(type="int"),
                                prefix=dict(type="str"),
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
        if state == "deleted" and not config:
            for afi, key in [("ipv4", "prefix-list"), ("ipv6", "prefix-list6")]:
                try:
                    client.configure_delete(["policy", key])
                    commands.append("delete policy {k}".format(k=key))
                except VyOSRestError:
                    pass
            changed = True
        elif state == "deleted" and config:
            for entry in config:
                key = _PL_KEY[entry["afi"]]
                for pl in entry.get("prefix_lists") or []:
                    try:
                        client.configure_delete(["policy", key, pl["name"]])
                        commands.append("delete policy {k} {n}".format(k=key, n=pl["name"]))
                        changed = True
                    except VyOSRestError:
                        pass
        elif state in ("merged", "replaced", "overridden"):
            if state in ("replaced", "overridden"):
                for entry in config:
                    key = _PL_KEY[entry["afi"]]
                    for pl in entry.get("prefix_lists") or []:
                        try:
                            client.configure_delete(["policy", key, pl["name"]])
                        except VyOSRestError:
                            pass
            for entry in config:
                _apply(client, entry, commands)
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
