#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_bgp_global
short_description: Manage BGP global configuration on VyOS via the REST API.
description:
  - Manages BGP global parameters on VyOS devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_bgp_global) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: BGP global configuration.
    type: dict
    suboptions:
      as_number:
        description: Local BGP AS number.
        type: int
        required: true
      router_id:
        description: BGP router ID (IPv4 address).
        type: str
      neighbors:
        description: List of BGP neighbor configurations.
        type: list
        elements: dict
        suboptions:
          neighbor:
            description: Neighbor IP address.
            type: str
            required: true
          remote_as:
            description: Neighbor's AS number.
            type: int
          description:
            description: Neighbor description.
            type: str
          password:
            description: MD5 authentication password.
            type: str
            no_log: true
          update_source:
            description: Local interface or address for BGP session.
            type: str
          ebgp_multihop:
            description: Maximum hops for eBGP sessions.
            type: int
          shutdown:
            description: Whether to administratively shut down the neighbor.
            type: bool
      networks:
        description: List of networks to originate.
        type: list
        elements: dict
        suboptions:
          prefix:
            description: Network prefix to advertise.
            type: str
            required: true
          route_map:
            description: Route map to apply.
            type: str
      redistribute:
        description: List of protocols to redistribute into BGP.
        type: list
        elements: dict
        suboptions:
          protocol:
            description: Protocol to redistribute.
            type: str
            choices: [connected, kernel, ospf, ospfv3, rip, ripng, static]
            required: true
          metric:
            description: Metric for redistributed routes.
            type: int
          route_map:
            description: Route map to apply.
            type: str
  state:
    description:
      - C(merged): Merge BGP config with existing.
      - C(replaced): Replace entire BGP config.
      - C(deleted): Remove BGP configuration.
      - C(gathered): Read BGP config from device.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
  hostname:
    description: IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description: HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description: API key configured on the device.
    type: str
    required: true
    no_log: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.vyos.vyos_bgp_global
examples: |
  - name: Configure BGP
    vyos.rest.vyos_bgp_global:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        as_number: 65001
        router_id: 192.168.1.1
        neighbors:
          - neighbor: 192.168.2.1
            remote_as: 65002
            description: "Peer AS65002"
        networks:
          - prefix: 10.0.0.0/8
        redistribute:
          - protocol: connected
      state: merged

  - name: Remove BGP configuration
    vyos.rest.vyos_bgp_global:
      hostname: 192.168.1.1
      api_key: MY-KEY
      state: deleted
"""

RETURN = r"""
before:
  description: BGP config before the module ran.
  returned: always
  type: dict
after:
  description: BGP config after the module ran.
  returned: when changed
  type: dict
gathered:
  description: BGP config read from device (state=gathered).
  returned: when state is gathered
  type: dict
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


_BGP_BASE = ["protocols", "bgp"]


def _get_bgp(client):
    try:
        result = client.retrieve_show_config(_BGP_BASE)
        return result.get("data") or {}
    except VyOSRestError:
        return {}


def _apply_bgp(client, config, commands):
    asn = str(config["as_number"])
    base = _BGP_BASE + [asn]
    client.configure_set(base)
    commands.append("set protocols bgp {a}".format(a=asn))

    if config.get("router_id"):
        client.configure_set(base + ["parameters", "router-id"], config["router_id"])
        commands.append(
            "set protocols bgp {a} parameters router-id {r}".format(
                a=asn,
                r=config["router_id"],
            ),
        )

    for nbr in config.get("neighbors") or []:
        nbase = base + ["neighbor", nbr["neighbor"]]
        client.configure_set(nbase)
        commands.append("set protocols bgp {a} neighbor {n}".format(a=asn, n=nbr["neighbor"]))
        if nbr.get("remote_as"):
            client.configure_set(nbase + ["remote-as"], str(nbr["remote_as"]))
            commands.append(
                "set protocols bgp {a} neighbor {n} remote-as {r}".format(
                    a=asn,
                    n=nbr["neighbor"],
                    r=nbr["remote_as"],
                ),
            )
        if nbr.get("description"):
            client.configure_set(nbase + ["description"], nbr["description"])
        if nbr.get("password"):
            client.configure_set(nbase + ["password"], nbr["password"])
        if nbr.get("update_source"):
            client.configure_set(nbase + ["update-source"], nbr["update_source"])
        if nbr.get("ebgp_multihop"):
            client.configure_set(nbase + ["ebgp-multihop"], str(nbr["ebgp_multihop"]))
        if nbr.get("shutdown"):
            client.configure_set(nbase + ["shutdown"])
            commands.append(
                "set protocols bgp {a} neighbor {n} shutdown".format(
                    a=asn,
                    n=nbr["neighbor"],
                ),
            )

    for net in config.get("networks") or []:
        nbase = base + ["address-family", "ipv4-unicast", "network", net["prefix"]]
        client.configure_set(nbase)
        commands.append(
            "set protocols bgp {a} address-family ipv4-unicast network {p}".format(
                a=asn,
                p=net["prefix"],
            ),
        )
        if net.get("route_map"):
            client.configure_set(nbase + ["route-map"], net["route_map"])

    for redist in config.get("redistribute") or []:
        rbase = base + [
            "address-family",
            "ipv4-unicast",
            "redistribute",
            redist["protocol"],
        ]
        client.configure_set(rbase)
        commands.append(
            "set protocols bgp {a} address-family ipv4-unicast redistribute {p}".format(
                a=asn,
                p=redist["protocol"],
            ),
        )
        if redist.get("metric"):
            client.configure_set(rbase + ["metric"], str(redist["metric"]))
        if redist.get("route_map"):
            client.configure_set(rbase + ["route-map"], redist["route_map"])


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                as_number=dict(type="int", required=True),
                router_id=dict(type="str"),
                neighbors=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        neighbor=dict(type="str", required=True),
                        remote_as=dict(type="int"),
                        description=dict(type="str"),
                        password=dict(type="str", no_log=True),
                        update_source=dict(type="str"),
                        ebgp_multihop=dict(type="int"),
                        shutdown=dict(type="bool"),
                    ),
                ),
                networks=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        prefix=dict(type="str", required=True),
                        route_map=dict(type="str"),
                    ),
                ),
                redistribute=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        protocol=dict(
                            type="str",
                            required=True,
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
                        metric=dict(type="int"),
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
        required_if=[
            ("state", "merged", ["config"]),
            ("state", "replaced", ["config"]),
        ],
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
                client.configure_delete(_BGP_BASE)
                commands.append("delete protocols bgp")
                changed = True

        elif state in ("merged", "replaced"):
            if state == "replaced" and before:
                client.configure_delete(_BGP_BASE)
                commands.append("delete protocols bgp")
            _apply_bgp(client, config, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_bgp(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
