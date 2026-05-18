#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv2
short_description: OSPFv2 resource module via REST API.
description:
  - Manages OSPFv2 (OSPF for IPv4) configuration on VyOS via HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: OSPFv2 configuration.
    type: dict
    suboptions:
      areas:
        type: list
        elements: dict
        suboptions:
          area_id:
            type: str
          area_type:
            type: dict
            suboptions:
              normal:
                type: bool
              nssa:
                type: dict
                suboptions:
                  set:
                    type: bool
                  default_cost:
                    type: int
                  no_summary:
                    type: bool
                  translate:
                    type: str
                    choices: [always, candidate, never]
              stub:
                type: dict
                suboptions:
                  set:
                    type: bool
                  default_cost:
                    type: int
                  no_summary:
                    type: bool
          authentication:
            type: str
            choices: [plaintext-password, md5]
          network:
            type: list
            elements: dict
            suboptions:
              address:
                type: str
          range:
            type: list
            elements: dict
            suboptions:
              address:
                type: str
              cost:
                type: int
              not_advertise:
                type: bool
              substitute:
                type: str
          shortcut:
            type: str
            choices: [default, disable, enable]
      auto_cost:
        type: dict
        suboptions:
          reference_bandwidth:
            type: int
      default_information:
        type: dict
        suboptions:
          originate:
            type: dict
            suboptions:
              always:
                type: bool
              metric:
                type: int
              metric_type:
                type: int
              route_map:
                type: str
      log_adjacency_changes:
        type: str
        choices: [detail]
      max_metric:
        type: dict
        suboptions:
          router_lsa:
            type: dict
            suboptions:
              administrative:
                type: bool
              on_shutdown:
                type: int
              on_startup:
                type: int
      mpls_te:
        type: dict
        suboptions:
          enabled:
            type: bool
          router_address:
            type: str
      neighbor:
        type: list
        elements: dict
        suboptions:
          neighbor_id:
            type: str
          poll_interval:
            type: int
          priority:
            type: int
      parameters:
        type: dict
        suboptions:
          router_id:
            type: str
          opaque_lsa:
            type: bool
          rfc1583_compatibility:
            type: bool
          abr_type:
            type: str
            choices: [cisco, ibm, shortcut, standard]
      passive_interface:
        type: list
        elements: str
      redistribute:
        type: list
        elements: dict
        suboptions:
          route_type:
            type: str
            choices: [bgp, connected, kernel, rip, static]
          metric:
            type: int
          metric_type:
            type: int
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


_BASE = ["protocols", "ospf"]


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
        commands.append("set protocols ospf parameters router-id {r}".format(r=params["router_id"]))
    if params.get("opaque_lsa"):
        client.configure_set(_BASE + ["parameters", "opaque-lsa"])
    if params.get("rfc1583_compatibility"):
        client.configure_set(_BASE + ["parameters", "rfc1583-compatibility"])
    if params.get("abr_type"):
        client.configure_set(_BASE + ["parameters", "abr-type"], params["abr_type"])

    ac = config.get("auto_cost") or {}
    if ac.get("reference_bandwidth"):
        client.configure_set(
            _BASE + ["auto-cost", "reference-bandwidth"],
            str(ac["reference_bandwidth"]),
        )
        commands.append(
            "set protocols ospf auto-cost reference-bandwidth {b}".format(
                b=ac["reference_bandwidth"],
            ),
        )

    if config.get("log_adjacency_changes"):
        client.configure_set(_BASE + ["log-adjacency-changes", config["log_adjacency_changes"]])

    for nbr in config.get("neighbor") or []:
        nb = _BASE + ["neighbor", nbr["neighbor_id"]]
        client.configure_set(nb)
        if nbr.get("poll_interval"):
            client.configure_set(nb + ["poll-interval"], str(nbr["poll_interval"]))
        if nbr.get("priority"):
            client.configure_set(nb + ["priority"], str(nbr["priority"]))

    for pi in config.get("passive_interface") or []:
        client.configure_set(_BASE + ["passive-interface"], pi)
        commands.append("set protocols ospf passive-interface {i}".format(i=pi))

    for redist in config.get("redistribute") or []:
        rb = _BASE + ["redistribute", redist["route_type"]]
        client.configure_set(rb)
        commands.append("set protocols ospf redistribute {r}".format(r=redist["route_type"]))
        if redist.get("metric"):
            client.configure_set(rb + ["metric"], str(redist["metric"]))
        if redist.get("metric_type"):
            client.configure_set(rb + ["metric-type"], str(redist["metric_type"]))
        if redist.get("route_map"):
            client.configure_set(rb + ["route-map"], redist["route_map"])

    di = (config.get("default_information") or {}).get("originate") or {}
    if di:
        dib = _BASE + ["default-information", "originate"]
        client.configure_set(dib)
        commands.append("set protocols ospf default-information originate")
        if di.get("always"):
            client.configure_set(dib + ["always"])
        if di.get("metric"):
            client.configure_set(dib + ["metric"], str(di["metric"]))
        if di.get("metric_type"):
            client.configure_set(dib + ["metric-type"], str(di["metric_type"]))
        if di.get("route_map"):
            client.configure_set(dib + ["route-map"], di["route_map"])

    for area in config.get("areas") or []:
        aid = area["area_id"]
        ab = _BASE + ["area", aid]
        client.configure_set(ab)
        commands.append("set protocols ospf area {a}".format(a=aid))

        at = area.get("area_type") or {}
        if at.get("normal"):
            pass  # default
        nssa = at.get("nssa") or {}
        if nssa.get("set"):
            client.configure_set(ab + ["area-type", "nssa"])
            if nssa.get("default_cost"):
                client.configure_set(
                    ab + ["area-type", "nssa", "default-cost"],
                    str(nssa["default_cost"]),
                )
            if nssa.get("no_summary"):
                client.configure_set(ab + ["area-type", "nssa", "no-summary"])
        stub = at.get("stub") or {}
        if stub.get("set"):
            client.configure_set(ab + ["area-type", "stub"])
            if stub.get("default_cost"):
                client.configure_set(
                    ab + ["area-type", "stub", "default-cost"],
                    str(stub["default_cost"]),
                )

        if area.get("authentication"):
            client.configure_set(ab + ["authentication"], area["authentication"])

        for net in area.get("network") or []:
            client.configure_set(ab + ["network"], net["address"])
            commands.append(
                "set protocols ospf area {a} network {n}".format(
                    a=aid,
                    n=net["address"],
                ),
            )

        for rng in area.get("range") or []:
            rb2 = ab + ["range", rng["address"]]
            client.configure_set(rb2)
            if rng.get("cost"):
                client.configure_set(rb2 + ["cost"], str(rng["cost"]))
            if rng.get("not_advertise"):
                client.configure_set(rb2 + ["not-advertise"])
            if rng.get("substitute"):
                client.configure_set(rb2 + ["substitute"], rng["substitute"])

        if area.get("shortcut"):
            client.configure_set(ab + ["shortcut"], area["shortcut"])


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
                        area_type=dict(
                            type="dict",
                            options=dict(
                                normal=dict(type="bool"),
                                nssa=dict(
                                    type="dict",
                                    options=dict(
                                        set=dict(type="bool"),
                                        default_cost=dict(type="int"),
                                        no_summary=dict(type="bool"),
                                        translate=dict(
                                            type="str",
                                            choices=["always", "candidate", "never"],
                                        ),
                                    ),
                                ),
                                stub=dict(
                                    type="dict",
                                    options=dict(
                                        set=dict(type="bool"),
                                        default_cost=dict(type="int"),
                                        no_summary=dict(type="bool"),
                                    ),
                                ),
                            ),
                        ),
                        authentication=dict(type="str", choices=["plaintext-password", "md5"]),
                        network=dict(
                            type="list",
                            elements="dict",
                            options=dict(address=dict(type="str")),
                        ),
                        range=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                address=dict(type="str"),
                                cost=dict(type="int"),
                                not_advertise=dict(type="bool"),
                                substitute=dict(type="str"),
                            ),
                        ),
                        shortcut=dict(type="str", choices=["default", "disable", "enable"]),
                    ),
                ),
                auto_cost=dict(type="dict", options=dict(reference_bandwidth=dict(type="int"))),
                default_information=dict(
                    type="dict",
                    options=dict(
                        originate=dict(
                            type="dict",
                            options=dict(
                                always=dict(type="bool"),
                                metric=dict(type="int"),
                                metric_type=dict(type="int"),
                                route_map=dict(type="str"),
                            ),
                        ),
                    ),
                ),
                log_adjacency_changes=dict(type="str", choices=["detail"]),
                max_metric=dict(type="dict"),
                mpls_te=dict(
                    type="dict",
                    options=dict(
                        enabled=dict(type="bool"),
                        router_address=dict(type="str"),
                    ),
                ),
                neighbor=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        neighbor_id=dict(type="str"),
                        poll_interval=dict(type="int"),
                        priority=dict(type="int"),
                    ),
                ),
                parameters=dict(
                    type="dict",
                    options=dict(
                        router_id=dict(type="str"),
                        opaque_lsa=dict(type="bool"),
                        rfc1583_compatibility=dict(type="bool"),
                        abr_type=dict(type="str", choices=["cisco", "ibm", "shortcut", "standard"]),
                    ),
                ),
                passive_interface=dict(type="list", elements="str"),
                redistribute=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        route_type=dict(
                            type="str",
                            choices=["bgp", "connected", "kernel", "rip", "static"],
                        ),
                        metric=dict(type="int"),
                        metric_type=dict(type="int"),
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
                commands.append("delete protocols ospf")
                changed = True
        elif state in ("merged", "replaced"):
            if state == "replaced" and before:
                client.configure_delete(_BASE)
                commands.append("delete protocols ospf")
            _apply(client, config, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
