#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_static_routes
short_description: Manage static routes on VyOS devices via REST API.
description:
  - Manages IPv4 and IPv6 static routes on VyOS devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_static_routes) but uses the HTTP API instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of static route configurations grouped by address family.
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
      - C(merged) - Add routes without removing existing ones.
      - C(replaced) - Replace routes for listed destinations.
      - C(overridden) - Replace the entire static route table.
      - C(deleted) - Remove listed or all static routes.
      - C(gathered) - Read static routes from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
seealso:
  - module: vyos.vyos.vyos_static_routes
"""

EXAMPLES = r"""
- name: Merge IPv4 and IPv6 static routes
  vyos.rest.vyos_static_routes:
    config:
      - afi: ipv4
        routes:
          - dest: 192.0.2.0/24
            next_hops:
              - forward_router_address: 10.0.0.1
          - dest: 203.0.113.0/24
            blackhole_config:
              distance: 200
      - afi: ipv6
        routes:
          - dest: 2001:db8::/32
            next_hops:
              - forward_router_address: 2001:db8::1
    state: merged

- name: Delete all static routes
  vyos.rest.vyos_static_routes:
    state: deleted

- name: Gather current static routes
  vyos.rest.vyos_static_routes:
    state: gathered
"""

RETURN = r"""
before:
  description: Static route configuration before this module ran.
  returned: always
  type: list
after:
  description: Static route configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current static route configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
response:
  description: Raw API response.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_ROUTE_KEY = {"ipv4": "route", "ipv6": "route6"}
_BASE = ["protocols", "static"]


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return []

    result = []
    for afi, route_key in [("ipv4", "route"), ("ipv6", "route6")]:
        routes_data = raw.get(route_key) or {}
        if not isinstance(routes_data, dict):
            continue

        routes = []
        for dest, rdata in sorted(routes_data.items()):
            rdata = rdata or {}
            route = {"dest": dest}

            if "blackhole" in rdata:
                bh = rdata["blackhole"]
                bc = {}
                if isinstance(bh, dict) and "distance" in bh:
                    bc["distance"] = int(bh["distance"])
                route["blackhole_config"] = bc

            nh_data = rdata.get("next-hop") or {}
            if isinstance(nh_data, dict) and nh_data:
                next_hops = []
                for nh_addr, nh_opts in sorted(nh_data.items()):
                    nh = {"forward_router_address": nh_addr}
                    nh_opts = nh_opts or {}
                    if "distance" in nh_opts:
                        nh["admin_distance"] = int(nh_opts["distance"])
                    if "disable" in nh_opts:
                        nh["enabled"] = False
                    if "interface" in nh_opts:
                        nh["interface"] = nh_opts["interface"]
                    next_hops.append(nh)
                route["next_hops"] = next_hops

            routes.append(route)

        if routes:
            result.append({"afi": afi, "routes": routes})

    return result


def _normalize(config):
    """Convert argspec list to nested dict for diffing.
    {
      "ipv4": {"192.0.2.0/24": {"next_hops": {...}, "blackhole_config": {...}}},
      "ipv6": {...}
    }
    """
    result = {"ipv4": {}, "ipv6": {}}
    for entry in config or []:
        afi = entry.get("afi")
        if afi not in result:
            continue
        for route in entry.get("routes") or []:
            dest = route["dest"]
            result[afi][dest] = {
                "blackhole_config": route.get("blackhole_config"),
                "next_hops": {
                    nh["forward_router_address"]: nh for nh in (route.get("next_hops") or [])
                },
            }
    return result


def _route_cmds(afi, dest, want_route, have_route):
    """Generate set commands for a single route."""
    cmds = []
    base = _BASE + [_ROUTE_KEY[afi], dest]
    have_route = have_route or {}

    # blackhole
    if want_route.get("blackhole_config") is not None:
        bh_base = base + ["blackhole"]
        if "blackhole_config" not in have_route:
            cmds.append(("set", bh_base))
        dist = (want_route["blackhole_config"] or {}).get("distance")
        have_dist = (have_route.get("blackhole_config") or {}).get("distance")
        if dist is not None and dist != have_dist:
            cmds.append(("set", bh_base + ["distance", str(dist)]))

    # next-hops
    want_nhs = want_route.get("next_hops") or {}
    have_nhs = have_route.get("next_hops") or {}

    for nh_addr, want_nh in want_nhs.items():
        nh_base = base + ["next-hop", nh_addr]
        have_nh = have_nhs.get(nh_addr, {})

        if nh_addr not in have_nhs:
            cmds.append(("set", nh_base))

        dist = want_nh.get("admin_distance")
        have_dist = have_nh.get("admin_distance")
        if dist is not None and dist != have_dist:
            cmds.append(("set", nh_base + ["distance", str(dist)]))

        enabled = want_nh.get("enabled", True)
        have_enabled = have_nh.get("enabled", True)
        if not enabled and have_enabled:
            cmds.append(("set", nh_base + ["disable"]))
        elif enabled and not have_enabled:
            cmds.append(("delete", nh_base + ["disable"]))

        iface = want_nh.get("interface")
        have_iface = have_nh.get("interface")
        if iface and iface != have_iface:
            cmds.append(("set", nh_base + ["interface", iface]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []

    if state == "deleted":
        if not config:
            for afi, route_key in _ROUTE_KEY.items():
                if any(e.get("afi") == afi for e in have_raw):
                    cmds.append(("delete", _BASE + [route_key]))
        else:
            for entry in config:
                afi = entry.get("afi")
                route_key = _ROUTE_KEY[afi]
                for route in entry.get("routes") or []:
                    cmds.append(("delete", _BASE + [route_key, route["dest"]]))
        return cmds

    want = _normalize(config)
    have = _normalize(have_raw)

    for afi, route_key in _ROUTE_KEY.items():
        want_afi = want.get(afi, {})
        have_afi = have.get(afi, {})

        if state == "overridden":
            for dest in set(have_afi) - set(want_afi):
                cmds.append(("delete", _BASE + [route_key, dest]))

        for dest, want_route in want_afi.items():
            have_route = have_afi.get(dest, {})

            if state == "replaced" and dest in have_afi:
                # check if anything differs before deleting
                test_cmds = _route_cmds(afi, dest, want_route, have_route)
                want_nhs = set(want_route.get("next_hops") or {})
                have_nhs = set(have_route.get("next_hops") or {})
                extra_nhs = have_nhs - want_nhs
                want_bh = want_route.get("blackhole_config")
                have_bh = have_route.get("blackhole_config")
                have_bh_now = have_bh is not None
                want_bh_now = want_bh is not None
                if test_cmds or extra_nhs or have_bh_now != want_bh_now:
                    cmds.append(("delete", _BASE + [route_key, dest]))
                    have_route = {}
                else:
                    continue  # already matches — idempotent

            cmds += _route_cmds(afi, dest, want_route, have_route)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
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
                            forward_router_address=dict(type="str", required=True),
                            admin_distance=dict(type="int"),
                            enabled=dict(type="bool", default=True),
                            interface=dict(type="str"),
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


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=get_running_config(vyos),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
