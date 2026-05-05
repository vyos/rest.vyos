#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_bgp_address_family
short_description: BGP Address Family resource module via REST API.
description:
  - Manages BGP address-family configuration (networks, redistribute,
    aggregate-address, per-neighbor AFI settings) via the VyOS HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: BGP address-family configuration.
    type: dict
    suboptions:
      as_number:
        description: Local AS number.
        type: int
        required: true
      address_family:
        description: Global address-family parameters.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family (ipv4 or ipv6).
            type: str
            choices: [ipv4, ipv6]
          aggregate_address:
            description: List of BGP aggregate networks.
            type: list
            elements: dict
            suboptions:
              prefix:
                type: str
              as_set:
                type: bool
              summary_only:
                type: bool
          networks:
            description: Networks to originate.
            type: list
            elements: dict
            suboptions:
              prefix:
                type: str
              path_limit:
                type: int
              backdoor:
                type: bool
              route_map:
                type: str
          redistribute:
            description: Protocols to redistribute.
            type: list
            elements: dict
            suboptions:
              protocol:
                type: str
                choices: [connected, kernel, ospf, ospfv3, rip, ripng, static]
              table:
                type: str
              route_map:
                type: str
              metric:
                type: int
      neighbors:
        description: Per-neighbor address-family settings.
        type: list
        elements: dict
        suboptions:
          neighbor_address:
            description: Neighbor IP.
            type: str
          address_family:
            type: list
            elements: dict
            suboptions:
              afi:
                type: str
                choices: [ipv4, ipv6]
              allowas_in:
                type: int
              as_override:
                type: bool
              route_map:
                description: Route-map settings.
                type: dict
                suboptions:
                  import_map:
                    type: str
                  export_map:
                    type: str
              soft_reconfiguration:
                type: bool
              nexthop_self:
                type: bool
              remove_private_as:
                type: bool
  state:
    description: Desired state.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
  hostname:
    description: Device IP or FQDN.
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
  description: Config before module ran.
  returned: always
  type: dict
after:
  description: Config after module ran.
  returned: when changed
  type: dict
commands:
  description: Commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def _get_bgp(client):
    try:
        result = client.retrieve_show_config(["protocols", "bgp"])
        return result.get("data") or {}
    except VyOSRestError:
        return {}


def _afi_unicast_key(afi):
    return "ipv4-unicast" if afi == "ipv4" else "ipv6-unicast"


def _apply(client, config, commands):
    asn = str(config["as_number"])
    base = ["protocols", "bgp", asn]

    for af in config.get("address_family") or []:
        afi = af["afi"]
        af_base = base + ["address-family", _afi_unicast_key(afi)]

        for agg in af.get("aggregate_address") or []:
            p = agg["prefix"]
            agg_base = af_base + ["aggregate-address", p]
            client.configure_set(agg_base)
            commands.append("set {b}".format(b=" ".join(agg_base)))
            if agg.get("as_set"):
                client.configure_set(agg_base + ["as-set"])
            if agg.get("summary_only"):
                client.configure_set(agg_base + ["summary-only"])

        for net in af.get("networks") or []:
            net_base = af_base + ["network", net["prefix"]]
            client.configure_set(net_base)
            commands.append("set {b}".format(b=" ".join(net_base)))
            if net.get("route_map"):
                client.configure_set(net_base + ["route-map"], net["route_map"])
            if net.get("backdoor"):
                client.configure_set(net_base + ["backdoor"])

        for redist in af.get("redistribute") or []:
            r_base = af_base + ["redistribute", redist["protocol"]]
            client.configure_set(r_base)
            commands.append("set {b}".format(b=" ".join(r_base)))
            if redist.get("metric"):
                client.configure_set(r_base + ["metric"], str(redist["metric"]))
            if redist.get("route_map"):
                client.configure_set(r_base + ["route-map"], redist["route_map"])

    for nbr in config.get("neighbors") or []:
        n_base = base + ["neighbor", nbr["neighbor_address"]]
        for af in nbr.get("address_family") or []:
            afi = af["afi"]
            n_af_base = n_base + ["address-family", _afi_unicast_key(afi)]
            client.configure_set(n_af_base)
            commands.append("set {b}".format(b=" ".join(n_af_base)))
            if af.get("allowas_in"):
                client.configure_set(n_af_base + ["allowas-in", "number"], str(af["allowas_in"]))
            if af.get("as_override"):
                client.configure_set(n_af_base + ["as-override"])
            if af.get("nexthop_self"):
                client.configure_set(n_af_base + ["nexthop-self"])
            if af.get("remove_private_as"):
                client.configure_set(n_af_base + ["remove-private-as"])
            if af.get("soft_reconfiguration"):
                client.configure_set(n_af_base + ["soft-reconfiguration", "inbound"])
            rm = af.get("route_map") or {}
            if rm.get("import_map"):
                client.configure_set(n_af_base + ["route-map", "import"], rm["import_map"])
            if rm.get("export_map"):
                client.configure_set(n_af_base + ["route-map", "export"], rm["export_map"])


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                as_number=dict(type="int", required=True),
                address_family=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        afi=dict(type="str", choices=["ipv4", "ipv6"]),
                        aggregate_address=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                prefix=dict(type="str"),
                                as_set=dict(type="bool"),
                                summary_only=dict(type="bool"),
                            ),
                        ),
                        networks=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                prefix=dict(type="str"),
                                path_limit=dict(type="int"),
                                backdoor=dict(type="bool"),
                                route_map=dict(type="str"),
                            ),
                        ),
                        redistribute=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                protocol=dict(
                                    type="str",
                                    choices=[
                                        "connected",
                                        "kernel",
                                        "ospf",
                                        "ospfv3",
                                        "rip",
                                        "ripng",
                                        "static",
                                    ],
                                ),
                                table=dict(type="str"),
                                route_map=dict(type="str"),
                                metric=dict(type="int"),
                            ),
                        ),
                    ),
                ),
                neighbors=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        neighbor_address=dict(type="str"),
                        address_family=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                afi=dict(type="str", choices=["ipv4", "ipv6"]),
                                allowas_in=dict(type="int"),
                                as_override=dict(type="bool"),
                                nexthop_self=dict(type="bool"),
                                remove_private_as=dict(type="bool"),
                                soft_reconfiguration=dict(type="bool"),
                                route_map=dict(
                                    type="dict",
                                    options=dict(
                                        import_map=dict(type="str"),
                                        export_map=dict(type="str"),
                                    ),
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
    before = _get_bgp(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])
    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "deleted":
            if before:
                client.configure_delete(["protocols", "bgp"])
                commands.append("delete protocols bgp")
                changed = True
        elif state in ("merged", "replaced"):
            if state == "replaced" and before:
                client.configure_delete(["protocols", "bgp"])
                commands.append("delete protocols bgp")
            _apply(client, config, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_bgp(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
