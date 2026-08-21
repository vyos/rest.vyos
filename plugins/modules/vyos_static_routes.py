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
  - >-
    Covers blackhole routes (distance) and next-hop routes (distance,
    disable, outgoing interface). VyOS's static-route schema is
    considerably larger than this -- reject routes (an ICMP-unreachable
    counterpart to blackhole), a top-level per-route interface (a route
    resolved via an outgoing interface with no next-hop address at
    all), route tags, route descriptions, ECMP segment weighting, VRF
    leaking, and BFD monitoring on next-hops are not modeled here.
    That is a real, documented limitation, not an oversight.
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
            description: Blackhole route configuration (silently discard matching packets).
            type: dict
            suboptions:
              distance:
                description: Administrative distance (1-255).
                type: int
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
                description: Administrative distance for this next-hop (1-255).
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
      - C(replaced) - Replace each named route (by afi + dest) exactly as specified.
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    to_tag_dict,
)


_BASE = ["protocols", "static"]
_ROUTE_KEY = {"ipv4": "route", "ipv6": "route6"}


def _derive_key_field(options_spec):
    """The field identifying each entry in a named-list section is
    never inferable from a generic walk alone -- but it doesn't need
    to be hand-declared either: every named-list section in this
    argspec (routes, next_hops) already marks exactly one suboption
    required=True.
    """
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption to serve as the key field, "
            "found: {0}".format(required),
        )
    return required[0]


def _keyed_list_to_device(items, key_field, entry_transform=None):
    """A list of dicts, each identified by key_field's value, becomes a
    device dict keyed by that value -- the one structural mechanic
    every named-list section in this module needs.
    """
    entry_transform = entry_transform or (lambda rest: rest)
    result = {}
    for item in items or []:
        if not item.get(key_field):
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[str(item[key_field])] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None):
    entry_transform = entry_transform or (lambda d: d or {})
    return [
        {key_field: key, **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


# ---------------------------------------------------------------------------
# blackhole_config -- confirmed against vyos-1x: the device node has
# ONLY "distance" (1-255) and "tag" (not modeled, see module scope
# note). There is no "type" leaf anywhere in the schema -- the
# original module's blackhole_config.type field was a genuine,
# confirmed hallucination and has been removed.
# ---------------------------------------------------------------------------


def _blackhole_to_device(bc):
    return autoclean(bc or {})


def _blackhole_from_device(data):
    if data is None:
        return None
    return from_device(data if isinstance(data, dict) else {})


# ---------------------------------------------------------------------------
# next_hops -- confirmed against vyos-1x: keyed by the next-hop
# address, with disable (presence), distance (1-255), and interface
# (plain leaf) as children. segments/vrf/bfd are real but out of scope
# (see module docstring).
# ---------------------------------------------------------------------------


# admin_distance -> distance is a plain rename (not mechanical kebab).
# enabled -> disable is a genuine, irreducible boolean inversion: the
# device tracks presence of "disable" for an OFF next-hop, the
# argspec tracks an "enabled" bool defaulting True -- autoclean's own
# bool handling (True -> presence) doesn't fit an inverted, default-
# true flag, so it's handled explicitly rather than forced through
# the generic path. "interface" is a plain, direct-match leaf and
# goes through autoclean/from_device like everywhere else.
_NEXT_HOP_RENAMES = {"admin_distance": "distance"}


def _next_hop_entry_to_device(rest):
    exclude = set(_NEXT_HOP_RENAMES) | {"enabled"}
    device = autoclean({k: v for k, v in rest.items() if k not in exclude})
    for arg_key, device_key in _NEXT_HOP_RENAMES.items():
        if rest.get(arg_key) is not None:
            device[device_key] = rest[arg_key]
    if rest.get("enabled") is False:
        device["disable"] = {}
    return device


def _next_hop_entry_from_device(data):
    exclude = set(_NEXT_HOP_RENAMES.values()) | {"disable"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})
    for arg_key, device_key in _NEXT_HOP_RENAMES.items():
        if data.get(device_key) is not None:
            entry[arg_key] = int(data[device_key])
    if "disable" in data:
        entry["enabled"] = False
    return entry


def _route_entry_to_device(rest):
    device = {}
    bc = rest.get("blackhole_config")
    if bc is not None:
        device["blackhole"] = _blackhole_to_device(bc)
    next_hops = rest.get("next_hops") or []
    if next_hops:
        device["next-hop"] = _keyed_list_to_device(
            next_hops,
            "forward_router_address",
            _next_hop_entry_to_device,
        )
    return device


def _route_entry_from_device(data):
    entry = {}
    bh = _blackhole_from_device(data.get("blackhole"))
    if bh is not None:
        entry["blackhole_config"] = bh
    nh_raw = data.get("next-hop")
    if nh_raw:
        entry["next_hops"] = _keyed_list_from_device(
            nh_raw,
            "forward_router_address",
            _next_hop_entry_from_device,
        )
    return entry


def _want_to_device(config):
    result = {}
    for entry in config or []:
        afi = entry.get("afi")
        route_key = _ROUTE_KEY.get(afi)
        if not route_key:
            continue
        routes = entry.get("routes") or []
        if not routes:
            continue
        result[route_key] = _keyed_list_to_device(routes, "dest", _route_entry_to_device)
    return result


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    if not raw:
        return []
    result = []
    for afi, route_key in _ROUTE_KEY.items():
        raw_routes = raw.get(route_key)
        if not raw_routes:
            continue
        routes = _keyed_list_from_device(raw_routes, "dest", _route_entry_from_device)
        if routes:
            result.append({"afi": afi, "routes": routes})
    return result


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    if state == "deleted":
        if not config:
            return [("delete", _BASE)] if raw_have else []
        cmds = []
        for entry in config:
            route_key = _ROUTE_KEY.get(entry.get("afi"))
            if not route_key:
                continue
            have_routes = raw_have.get(route_key) or {}
            routes = entry.get("routes") or []
            if not routes:
                if route_key in raw_have:
                    cmds.append(("delete", _BASE + [route_key]))
                continue
            for route in routes:
                dest = route.get("dest")
                if dest and dest in have_routes:
                    cmds.append(("delete", _BASE + [route_key, dest]))
        return cmds

    want = _want_to_device(config)
    norm_have = _want_to_device(_device_to_argspec(raw_have))

    commands = []
    if state == "overridden":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        # Scoped per individual route (afi + dest), matching every
        # other module's "replaced only touches what's named" semantic
        # -- not per address-family, which would incorrectly behave
        # like overridden for the whole AFI. This also directly fixes
        # the confirmed bug in the original implementation: dict_op's
        # purge naturally detects and clears any omitted attribute
        # (a next-hop's distance/interface, a route's blackhole
        # entirely), rather than the original's hand-rolled "does
        # anything differ" heuristic, which only inspected generated
        # set-commands and therefore could never notice an omitted
        # (cleared) value, since clearing never produced a command in
        # the first place.
        for entry in config:
            route_key = _ROUTE_KEY.get(entry.get("afi"))
            if not route_key:
                continue
            for route in entry.get("routes") or []:
                dest = route.get("dest")
                if not dest:
                    continue
                section_want = (want.get(route_key) or {}).get(dest, {})
                section_have = (norm_have.get(route_key) or {}).get(dest, {})
                commands += dict_op(
                    section_want,
                    section_have,
                    _BASE + [route_key, dest],
                    op="purge",
                )
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


_NEXT_HOP_OPTIONS = dict(
    forward_router_address=dict(type="str", required=True),
    admin_distance=dict(type="int"),
    enabled=dict(type="bool", default=True),
    interface=dict(type="str"),
)

_ROUTE_OPTIONS = dict(
    dest=dict(type="str", required=True),
    blackhole_config=dict(
        type="dict",
        options=dict(
            distance=dict(type="int"),
        ),
    ),
    next_hops=dict(
        type="list",
        elements="dict",
        options=_NEXT_HOP_OPTIONS,
    ),
)

ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
            routes=dict(
                type="list",
                elements="dict",
                options=_ROUTE_OPTIONS,
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

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    for entry in have:
        for route in entry.get("routes") or []:
            cast_by_spec(route, _ROUTE_OPTIONS)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after_raw = get_running_config(vyos)
        after = _device_to_argspec(after_raw)
        for entry in after:
            for route in entry.get("routes") or []:
                cast_by_spec(route, _ROUTE_OPTIONS)
        module.exit_json(
            changed=True,
            before=have,
            after=after,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
