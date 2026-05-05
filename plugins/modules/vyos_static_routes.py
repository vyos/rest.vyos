#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_static_routes
short_description: Manage static routes on VyOS via the REST API.
description:
  - Manages IPv4 and IPv6 static routes on VyOS devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_static_routes) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of static route address-family configurations.
    type: list
    elements: dict
    suboptions:
      address_families:
        description: List of address family route groups.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family indicator.
            type: str
            choices: [ipv4, ipv6]
            required: true
          routes:
            description: List of static route entries.
            type: list
            elements: dict
            suboptions:
              dest:
                description: Destination prefix in CIDR notation.
                type: str
                required: true
              blackhole_config:
                description: Blackhole route configuration.
                type: dict
                suboptions:
                  distance:
                    description: Administrative distance (1-255).
                    type: int
                  type:
                    description: Blackhole type.
                    type: str
              next_hops:
                description: List of next-hop addresses.
                type: list
                elements: dict
                suboptions:
                  forward_router_address:
                    description: Next-hop IP address.
                    type: str
                    required: true
                  admin_distance:
                    description: Administrative distance for this next-hop.
                    type: int
                  enabled:
                    description: Whether this next-hop is enabled.
                    type: bool
                    default: true
                  interface:
                    description: Outgoing interface name.
                    type: str
  state:
    description:
      - C(merged): Add routes (preserve existing).
      - C(replaced): Replace routes for listed destinations.
      - C(overridden): Replace the entire static route table.
      - C(deleted): Remove listed (or all) static routes.
      - C(gathered): Read static routes from device.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
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
  - module: vyos.vyos.vyos_static_routes
examples: |
  - name: Add IPv4 static routes
    vyos.rest.vyos_static_routes:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - address_families:
            - afi: ipv4
              routes:
                - dest: 192.0.2.0/24
                  next_hops:
                    - forward_router_address: 10.0.0.1
                - dest: 203.0.113.0/24
                  blackhole_config:
                    distance: 200
      state: merged

  - name: Delete all static routes
    vyos.rest.vyos_static_routes:
      hostname: 192.168.1.1
      api_key: MY-KEY
      state: deleted
"""

RETURN = r"""
before:
  description: Static route config before the module ran.
  returned: always
  type: list
after:
  description: Static route config after the module ran.
  returned: when changed
  type: list
gathered:
  description: Static routes read from device (state=gathered).
  returned: when state is gathered
  type: list
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


_ROUTE_BASE = {
    "ipv4": ["protocols", "static", "route"],
    "ipv6": ["protocols", "static", "route6"],
}


def _get_static_routes(client):
    try:
        result = client.retrieve_show_config(["protocols", "static"])
        data = result.get("data") or {}
        out = []
        for afi, route_key in [("ipv4", "route"), ("ipv6", "route6")]:
            routes_data = data.get(route_key, {})
            if not isinstance(routes_data, dict):
                continue
            routes = []
            for dest, rdata in routes_data.items():
                route_entry = {"dest": dest}
                if isinstance(rdata, dict):
                    if "blackhole" in rdata:
                        bh = rdata["blackhole"]
                        bc = {}
                        if isinstance(bh, dict) and "distance" in bh:
                            bc["distance"] = int(bh["distance"])
                        route_entry["blackhole_config"] = bc
                    next_hops = []
                    for nh_key in ("next-hop", "next_hop"):
                        nh_data = rdata.get(nh_key, {})
                        if isinstance(nh_data, dict):
                            for nh_addr, nh_opts in nh_data.items():
                                nh = {"forward_router_address": nh_addr}
                                if isinstance(nh_opts, dict):
                                    if "distance" in nh_opts:
                                        nh["admin_distance"] = int(nh_opts["distance"])
                                    nh["enabled"] = "disable" not in nh_opts
                                next_hops.append(nh)
                    if next_hops:
                        route_entry["next_hops"] = next_hops
                routes.append(route_entry)
            if routes:
                out.append({"address_families": [{"afi": afi, "routes": routes}]})
        return out
    except VyOSRestError:
        return []


def _apply_route(client, afi, route, commands):
    base = _ROUTE_BASE[afi]
    dest = route["dest"]

    if route.get("blackhole_config") is not None:
        bh_path = base + [dest, "blackhole"]
        client.configure_set(bh_path)
        commands.append("set {p}".format(p=" ".join(bh_path)))
        dist = route["blackhole_config"].get("distance")
        if dist:
            client.configure_set(bh_path + ["distance"], str(dist))
            commands.append(
                "set {p} distance {d}".format(p=" ".join(bh_path), d=dist),
            )

    for nh in route.get("next_hops") or []:
        nh_addr = nh["forward_router_address"]
        nh_path = base + [dest, "next-hop", nh_addr]
        client.configure_set(nh_path)
        commands.append("set {p}".format(p=" ".join(nh_path)))
        if nh.get("admin_distance"):
            client.configure_set(nh_path + ["distance"], str(nh["admin_distance"]))
            commands.append(
                "set {p} distance {d}".format(
                    p=" ".join(nh_path),
                    d=nh["admin_distance"],
                ),
            )
        if "enabled" in nh and not nh["enabled"]:
            client.configure_set(nh_path + ["disable"])
            commands.append("set {p} disable".format(p=" ".join(nh_path)))
        if nh.get("interface"):
            client.configure_set(nh_path + ["interface"], nh["interface"])
            commands.append(
                "set {p} interface {i}".format(
                    p=" ".join(nh_path),
                    i=nh["interface"],
                ),
            )


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                address_families=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                        routes=dict(
                            type="list",
                            elements="dict",
                            options=dict(
                                dest=dict(type="str", required=True),
                                blackhole_config=dict(
                                    type="dict",
                                    options=dict(
                                        distance=dict(type="int"),
                                        type=dict(type="str"),
                                    ),
                                ),
                                next_hops=dict(
                                    type="list",
                                    elements="dict",
                                    options=dict(
                                        forward_router_address=dict(
                                            type="str",
                                            required=True,
                                        ),
                                        admin_distance=dict(type="int"),
                                        enabled=dict(type="bool", default=True),
                                        interface=dict(type="str"),
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
            choices=["merged", "replaced", "overridden", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config") or []
    commands = []
    changed = False

    before = _get_static_routes(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state in ("overridden", "deleted") and not config:
            # Delete all static routes
            for afi_key in ("route", "route6"):
                try:
                    client.configure_delete(["protocols", "static", afi_key])
                    commands.append(
                        "delete protocols static {k}".format(k=afi_key),
                    )
                except VyOSRestError:
                    pass
            changed = True

        elif state == "deleted" and config:
            for entry in config:
                for af in entry.get("address_families") or []:
                    afi = af["afi"]
                    base = _ROUTE_BASE[afi]
                    for route in af.get("routes") or []:
                        try:
                            client.configure_delete(base + [route["dest"]])
                            commands.append(
                                "delete {p} {d}".format(
                                    p=" ".join(base),
                                    d=route["dest"],
                                ),
                            )
                        except VyOSRestError:
                            pass
                    changed = True

        elif state in ("merged", "replaced", "overridden"):
            if state in ("replaced", "overridden"):
                # Remove existing routes for affected destinations
                dests_by_afi = {}
                for entry in config:
                    for af in entry.get("address_families") or []:
                        afi = af["afi"]
                        dests_by_afi.setdefault(afi, set())
                        for route in af.get("routes") or []:
                            dests_by_afi[afi].add(route["dest"])
                if state == "overridden":
                    for afi_key in ("route", "route6"):
                        try:
                            client.configure_delete(
                                ["protocols", "static", afi_key],
                            )
                            commands.append(
                                "delete protocols static {k}".format(k=afi_key),
                            )
                        except VyOSRestError:
                            pass
                else:
                    for afi, dests in dests_by_afi.items():
                        base = _ROUTE_BASE[afi]
                        for dest in dests:
                            try:
                                client.configure_delete(base + [dest])
                                commands.append(
                                    "delete {p} {d}".format(
                                        p=" ".join(base),
                                        d=dest,
                                    ),
                                )
                            except VyOSRestError:
                                pass

            for entry in config:
                for af in entry.get("address_families") or []:
                    afi = af["afi"]
                    for route in af.get("routes") or []:
                        _apply_route(client, afi, route, commands)
                        changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_static_routes(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
