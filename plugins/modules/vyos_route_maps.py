#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_route_maps
short_description: Route Map resource module via REST API.
description:
  - Manages route maps on VyOS via the HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of route-map configurations.
    type: list
    elements: dict
    suboptions:
      route_map:
        description: Route map name.
        type: str
      entries:
        description: Route map rules.
        type: list
        elements: dict
        suboptions:
          sequence:
            description: Rule number (1-65535).
            type: int
          action:
            description: permit or deny.
            type: str
            choices: [permit, deny]
          description:
            type: str
          call:
            description: Call another route map.
            type: str
          continue_sequence:
            description: Continue at a different sequence.
            type: int
          match:
            description: Match conditions.
            type: dict
            suboptions:
              prefix_list:
                type: str
              prefix_list6:
                type: str
              interface:
                type: str
              metric:
                type: int
              origin:
                type: str
              ip:
                type: dict
                suboptions:
                  nexthop_address:
                    type: str
                  nexthop_prefix_list:
                    type: str
              ipv6:
                type: dict
                suboptions:
                  nexthop_address:
                    type: str
          set:
            description: Route parameters to set.
            type: dict
            suboptions:
              aggregator:
                type: dict
                suboptions:
                  as:
                    type: str
                  ip:
                    type: str
              as_path_prepend:
                type: str
              atomic_aggregate:
                type: bool
              bgp_extcommunity_rt:
                type: str
              community:
                type: dict
                suboptions:
                  value:
                    type: str
              ip_next_hop:
                type: str
              ipv6_next_hop:
                type: dict
                suboptions:
                  ip_type:
                    type: str
                    choices: [global, local]
                  value:
                    type: str
              large_community:
                type: str
              local_preference:
                type: int
              metric:
                type: str
              metric_type:
                type: str
              origin:
                type: str
              originator_id:
                type: str
              src:
                type: str
              tag:
                type: str
              weight:
                type: int
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


def _get(client):
    try:
        r = client.retrieve_show_config(["policy", "route-map"])
        data = r.get("data") or {}
        return [{"route_map": name, "raw": rdata} for name, rdata in data.items()]
    except VyOSRestError:
        return []


def _apply(client, rm_cfg, commands):
    rm_name = rm_cfg["route_map"]
    for rule in rm_cfg.get("entries") or []:
        seq = str(rule["sequence"])
        base = ["policy", "route-map", rm_name, "rule", seq]
        client.configure_set(base)
        commands.append("set policy route-map {n} rule {s}".format(n=rm_name, s=seq))

        if rule.get("action"):
            client.configure_set(base + ["action"], rule["action"])
            commands.append(
                "set policy route-map {n} rule {s} action {a}".format(
                    n=rm_name,
                    s=seq,
                    a=rule["action"],
                ),
            )
        if rule.get("description"):
            client.configure_set(base + ["description"], rule["description"])
        if rule.get("call"):
            client.configure_set(base + ["call"], rule["call"])
        if rule.get("continue_sequence"):
            client.configure_set(base + ["continue"], str(rule["continue_sequence"]))

        # Match conditions
        match = rule.get("match") or {}
        if match.get("prefix_list"):
            client.configure_set(
                base + ["match", "ip", "address", "prefix-list"],
                match["prefix_list"],
            )
        if match.get("interface"):
            client.configure_set(base + ["match", "interface"], match["interface"])
        if match.get("metric") is not None:
            client.configure_set(base + ["match", "metric"], str(match["metric"]))
        ip_match = match.get("ip") or {}
        if ip_match.get("nexthop_address"):
            client.configure_set(
                base + ["match", "ip", "nexthop", "address"],
                ip_match["nexthop_address"],
            )

        # Set actions
        setv = rule.get("set") or {}
        if setv.get("ip_next_hop"):
            client.configure_set(base + ["set", "ip-next-hop"], setv["ip_next_hop"])
            commands.append(
                "set policy route-map {n} rule {s} set ip-next-hop {nh}".format(
                    n=rm_name,
                    s=seq,
                    nh=setv["ip_next_hop"],
                ),
            )
        if setv.get("local_preference") is not None:
            client.configure_set(
                base + ["set", "local-preference"],
                str(setv["local_preference"]),
            )
        if setv.get("metric"):
            client.configure_set(base + ["set", "metric"], str(setv["metric"]))
        if setv.get("origin"):
            client.configure_set(base + ["set", "origin"], setv["origin"])
        if setv.get("weight") is not None:
            client.configure_set(base + ["set", "weight"], str(setv["weight"]))
        if setv.get("as_path_prepend"):
            client.configure_set(base + ["set", "as-path-prepend"], setv["as_path_prepend"])
        comm = setv.get("community") or {}
        if comm.get("value"):
            client.configure_set(base + ["set", "community", comm["value"]])
        if setv.get("tag"):
            client.configure_set(base + ["set", "tag"], setv["tag"])
        if setv.get("src"):
            client.configure_set(base + ["set", "src"], setv["src"])
        nh6 = setv.get("ipv6_next_hop") or {}
        if nh6.get("value"):
            ip_type = nh6.get("ip_type", "global")
            client.configure_set(base + ["set", "ipv6-next-hop", ip_type], nh6["value"])


def main():
    set_spec = dict(
        type="dict",
        options=dict(
            aggregator=dict(type="dict", options=dict(as_=dict(type="str"), ip=dict(type="str"))),
            as_path_prepend=dict(type="str"),
            atomic_aggregate=dict(type="bool"),
            bgp_extcommunity_rt=dict(type="str"),
            community=dict(type="dict", options=dict(value=dict(type="str"))),
            ip_next_hop=dict(type="str"),
            ipv6_next_hop=dict(
                type="dict",
                options=dict(
                    ip_type=dict(type="str", choices=["global", "local"]),
                    value=dict(type="str"),
                ),
            ),
            large_community=dict(type="str"),
            local_preference=dict(type="int"),
            metric=dict(type="str"),
            metric_type=dict(type="str"),
            origin=dict(type="str"),
            originator_id=dict(type="str"),
            src=dict(type="str"),
            tag=dict(type="str"),
            weight=dict(type="int"),
        ),
    )
    match_spec = dict(
        type="dict",
        options=dict(
            prefix_list=dict(type="str"),
            prefix_list6=dict(type="str"),
            interface=dict(type="str"),
            metric=dict(type="int"),
            origin=dict(type="str"),
            ip=dict(
                type="dict",
                options=dict(
                    nexthop_address=dict(type="str"),
                    nexthop_prefix_list=dict(type="str"),
                ),
            ),
            ipv6=dict(type="dict", options=dict(nexthop_address=dict(type="str"))),
        ),
    )

    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                route_map=dict(type="str"),
                entries=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        sequence=dict(type="int"),
                        action=dict(type="str", choices=["permit", "deny"]),
                        description=dict(type="str"),
                        call=dict(type="str"),
                        continue_sequence=dict(type="int"),
                        match=match_spec,
                        set=set_spec,
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
            try:
                client.configure_delete(["policy", "route-map"])
                commands.append("delete policy route-map")
                changed = True
            except VyOSRestError:
                pass
        elif state == "deleted" and config:
            for rm in config:
                try:
                    client.configure_delete(["policy", "route-map", rm["route_map"]])
                    commands.append("delete policy route-map {n}".format(n=rm["route_map"]))
                    changed = True
                except VyOSRestError:
                    pass
        elif state in ("merged", "replaced", "overridden"):
            if state in ("replaced", "overridden"):
                for rm in config:
                    try:
                        client.configure_delete(["policy", "route-map", rm["route_map"]])
                    except VyOSRestError:
                        pass
            for rm in config:
                _apply(client, rm, commands)
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
