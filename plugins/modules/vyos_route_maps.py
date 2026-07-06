#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_route_maps
short_description: Manage route-map configuration on VyOS devices using REST API
description:
  - Manages route maps on VyOS via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - >-
    Covers the commonly used match/set fields (as documented below). VyOS's
    route-map schema is considerably larger than this (EVPN attributes,
    extended communities, RPKI matching, on-match goto/next, route-source,
    source-peer, source-vrf, and more) -- those are not modeled by this
    module and are a real, documented limitation, not an oversight.
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
        required: true
      entries:
        description: Route map rules.
        type: list
        elements: dict
        suboptions:
          sequence:
            description: Rule sequence number (1-65535).
            type: int
            required: true
          action:
            description: Permit or deny.
            type: str
            choices: [permit, deny]
          description:
            description: Rule description.
            type: str
          call:
            description: Call another route map.
            type: str
          continue_sequence:
            description: Continue at a different sequence number.
            type: int
          match:
            description: Match conditions.
            type: dict
            suboptions:
              interface:
                description: Interface to match.
                type: str
              metric:
                description: Metric of route to match.
                type: int
              origin:
                description: BGP origin code to match.
                type: str
                choices: [egp, igp, incomplete]
              peer:
                description: Peer address to match.
                type: str
              protocol:
                description: Match protocol via which the route was learnt.
                type: str
                choices:
                  [
                    babel, bgp, connected, isis, kernel, ospf, ospfv3,
                    rip, ripng, static, table, vnc,
                  ]
              prefix_list:
                description: IPv4 prefix-list to match.
                type: str
              prefix_list6:
                description: IPv6 prefix-list to match.
                type: str
              ip:
                description: IPv4 next-hop match parameters.
                type: dict
                suboptions:
                  nexthop_address:
                    description: IPv4 next-hop address to match.
                    type: str
                  nexthop_prefix_list:
                    description: IPv4 next-hop prefix-list to match.
                    type: str
              ipv6:
                description: IPv6 next-hop match parameters.
                type: dict
                suboptions:
                  nexthop_address:
                    description: IPv6 next-hop address to match.
                    type: str
          set:
            description: Route parameters to set.
            type: dict
            suboptions:
              metric:
                description: Metric of route.
                type: int
              metric_type:
                description: Metric type.
                type: str
              origin:
                description: BGP origin code to set.
                type: str
                choices: [egp, igp, incomplete]
              originator_id:
                description: BGP originator ID.
                type: str
              src:
                description: Source address for route.
                type: str
              tag:
                description: Route tag value.
                type: int
              weight:
                description: BGP weight.
                type: int
              distance:
                description: Locally significant administrative distance.
                type: int
              table:
                description: Non-main kernel routing table.
                type: int
              local_preference:
                description: BGP local preference.
                type: int
              ip_next_hop:
                description: IPv4 next-hop address to set.
                type: str
              atomic_aggregate:
                description: Set the BGP atomic aggregate attribute.
                type: bool
              as_path_exclude:
                description: AS number(s) to remove from the as-path attribute.
                type: str
              as_path_prepend:
                description: AS number(s) to prepend to the as-path attribute.
                type: str
              as_path_prepend_last_as:
                description: Number of times to prepend the last AS number in the as-path.
                type: int
              aggregator:
                description: BGP aggregator attribute.
                type: dict
                suboptions:
                  as_:
                    description: AS number of an aggregation.
                    type: int
                    aliases: [as]
                  ip:
                    description: IP address of an aggregation.
                    type: str
              community:
                description: BGP community attribute.
                type: dict
                suboptions:
                  add:
                    description: Communities to add to a prefix.
                    type: list
                    elements: str
                  replace:
                    description: Communities to set for a prefix.
                    type: list
                    elements: str
                  none:
                    description: Completely remove the communities attribute from a prefix.
                    type: bool
                  delete:
                    description: Remove communities defined in a list from a prefix.
                    type: str
              large_community:
                description: BGP large community attribute.
                type: dict
                suboptions:
                  add:
                    description: Large communities to add to a prefix.
                    type: list
                    elements: str
                  replace:
                    description: Large communities to set for a prefix.
                    type: list
                    elements: str
                  none:
                    description: Completely remove the large-community attribute from a prefix.
                    type: bool
                  delete:
                    description: Remove large communities defined in a list from a prefix.
                    type: str
              ipv6_next_hop:
                description: IPv6 next-hop to set.
                type: dict
                suboptions:
                  global:
                    description: Nexthop IPv6 global address.
                    type: str
                  local:
                    description: Nexthop IPv6 local address.
                    type: str
                  peer_address:
                    description: Use the peer address (BGP only) as the nexthop.
                    type: bool
                  prefer_global:
                    description: Prefer the global address as the nexthop.
                    type: bool

  state:
    description:
      - Desired state of the route-map configuration.
      - C(merged) adds or updates entries without removing existing ones.
      - C(replaced) replaces each named route map mentioned in config.
      - C(overridden) replaces all route maps.
      - C(deleted) removes route maps. Without config removes all.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged

notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Merge route map configuration
  vyos.rest.vyos_route_maps:
    config:
      - route_map: RM-TEST-EXPORT-POLICY
        entries:
          - sequence: 10
            action: permit
            match:
              peer: 192.0.2.32
            set:
              metric: 5
              as_path_exclude: "111"
              aggregator:
                as_: 100
    state: merged

- name: Delete all route maps
  vyos.rest.vyos_route_maps:
    state: deleted

- name: Delete a specific route map
  vyos.rest.vyos_route_maps:
    config:
      - route_map: RM-TEST-EXPORT-POLICY
    state: deleted

- name: Gather current route map configuration
  vyos.rest.vyos_route_maps:
    state: gathered
"""

RETURN = r"""
before:
  description: Route map configuration before this module ran.
  returned: always
  type: list
after:
  description: Route map configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current route map configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
response:
  description: Raw API response.
  returned: always
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


_BASE = ["policy", "route-map"]


def _derive_key_field(options_spec):
    """The field identifying each entry in a named-list section is
    never inferable from a generic walk alone -- but it doesn't need
    to be hand-declared either: both named-list sections in this
    argspec (route maps, rules) already mark exactly one suboption
    required=True. Deriving it here means the key field is asserted to
    exist by the argspec itself, not duplicated in a place that could
    drift out of sync with it.
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
    every named-list section in this module needs. entry_transform
    supplies whatever else is genuinely irreducible for a given section
    (a nested reshape) -- defaulting to the generic recursive walker.
    """
    entry_transform = entry_transform or autoclean
    result = {}
    for item in items or []:
        if not item.get(key_field):
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[str(item[key_field])] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None, key_cast=None):
    entry_transform = entry_transform or from_device
    key_cast = key_cast or (lambda k: k)
    return [
        {key_field: key_cast(key), **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


# ---------------------------------------------------------------------------
# match.prefix_list / match.prefix_list6 -- confirmed genuine structural
# insertions: the argspec has these as flat fields, but the device
# nests them two levels down (ip.address.prefix-list /
# ipv6.address.prefix-list).
#
# match.ip.nexthop_address / nexthop_prefix_list, match.ipv6.
# nexthop_address -- confirmed the device nests these ONE level
# deeper than the argspec (ip.nexthop.address / ip.nexthop.prefix-list),
# under a "nexthop" node the argspec doesn't have (commented out in
# vyos-1x itself, T3304/T3976, since a plain leaf there would collide
# with the node).
# ---------------------------------------------------------------------------


def _match_to_device(match):
    if not match:
        return {}
    exclude = {"prefix_list", "prefix_list6", "ip", "ipv6"}
    device = autoclean({k: v for k, v in match.items() if k not in exclude})

    if match.get("prefix_list"):
        device.setdefault("ip", {}).setdefault("address", {})["prefix-list"] = match["prefix_list"]
    if match.get("prefix_list6"):
        ipv6_addr = device.setdefault("ipv6", {}).setdefault("address", {})
        ipv6_addr["prefix-list"] = match["prefix_list6"]

    ip = match.get("ip") or {}
    if ip.get("nexthop_address"):
        device.setdefault("ip", {}).setdefault("nexthop", {})["address"] = ip["nexthop_address"]
    if ip.get("nexthop_prefix_list"):
        ip_nh = device.setdefault("ip", {}).setdefault("nexthop", {})
        ip_nh["prefix-list"] = ip["nexthop_prefix_list"]

    ipv6 = match.get("ipv6") or {}
    if ipv6.get("nexthop_address"):
        device.setdefault("ipv6", {}).setdefault("nexthop", {})["address"] = ipv6["nexthop_address"]

    return device


def _match_from_device(data):
    if not data:
        return {}
    ip_raw = data.get("ip") or {}
    ipv6_raw = data.get("ipv6") or {}
    exclude = {"ip", "ipv6"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})

    prefix_list = (ip_raw.get("address") or {}).get("prefix-list")
    if prefix_list:
        entry["prefix_list"] = prefix_list
    prefix_list6 = (ipv6_raw.get("address") or {}).get("prefix-list")
    if prefix_list6:
        entry["prefix_list6"] = prefix_list6

    ip_nexthop = ip_raw.get("nexthop") or {}
    ip_sub = {}
    if ip_nexthop.get("address"):
        ip_sub["nexthop_address"] = ip_nexthop["address"]
    if ip_nexthop.get("prefix-list"):
        ip_sub["nexthop_prefix_list"] = ip_nexthop["prefix-list"]
    if ip_sub:
        entry["ip"] = ip_sub

    ipv6_nexthop = ipv6_raw.get("nexthop") or {}
    if ipv6_nexthop.get("address"):
        entry["ipv6"] = {"nexthop_address": ipv6_nexthop["address"]}

    return entry


# ---------------------------------------------------------------------------
# set.as_path_* -- confirmed structural collapse: three flat argspec
# keys (as_path_exclude/prepend/prepend_last_as) collapse onto one
# nested device node (as-path.{exclude,prepend,prepend-last-as}) with
# different sub-key names -- no mechanical transform gets from
# "as_path_exclude" to that shape.
#
# set.community / set.large_community / set.ipv6_next_hop are fully
# generic once modeled as real nested dicts (confirmed against schema:
# community/large-community are add/replace/none/delete nodes;
# ipv6-next-hop is global/local/peer-address/prefer-global) -- no
# entry-transform needed for them at all, the top-level community_to_
# device call handles them via ordinary recursion.
# ---------------------------------------------------------------------------
_AS_PATH_FIELDS = {
    "as_path_exclude": "exclude",
    "as_path_prepend": "prepend",
    "as_path_prepend_last_as": "prepend-last-as",
}


# Both renames in this module are position-specific -- confirmed
# against vyos-1x: "as" and "continue" are Python keywords and can't
# be used as dict() kwargs at all, so "as_"/"continue_sequence" are
# unavoidable argspec names, renamed to the device's real leaf names
# "as"/"continue". Neither fits a shared flat rename map: "as_" is
# nested inside "aggregator" specifically, and "continue_sequence" is
# a rule-level field, not a set-level one -- each is handled directly
# at its own point below instead.


def _set_to_device(setv):
    if not setv:
        return {}
    exclude = set(_AS_PATH_FIELDS) | {"aggregator"}
    device = autoclean({k: v for k, v in setv.items() if k not in exclude})

    as_path = {
        device_key: setv[arg_key]
        for arg_key, device_key in _AS_PATH_FIELDS.items()
        if setv.get(arg_key) is not None
    }
    if as_path:
        device["as-path"] = as_path

    agg = setv.get("aggregator")
    if agg:
        agg_device = autoclean({k: v for k, v in agg.items() if k != "as_"})
        if agg.get("as_") is not None:
            agg_device["as"] = agg["as_"]
        if agg_device:
            device["aggregator"] = agg_device

    return device


def _set_from_device(data):
    if not data:
        return {}
    as_path_raw = data.get("as-path") or {}
    agg_raw = data.get("aggregator") or {}
    exclude = {"as-path", "aggregator"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})

    for arg_key, device_key in _AS_PATH_FIELDS.items():
        if as_path_raw.get(device_key) is not None:
            entry[arg_key] = as_path_raw[device_key]
    if "as_path_prepend_last_as" in entry:
        entry["as_path_prepend_last_as"] = int(entry["as_path_prepend_last_as"])

    if agg_raw:
        agg_entry = from_device({k: v for k, v in agg_raw.items() if k != "as"})
        if agg_raw.get("as") is not None:
            agg_entry["as_"] = int(agg_raw["as"])
        if agg_entry:
            entry["aggregator"] = agg_entry

    return entry


# ---------------------------------------------------------------------------
# Rules (keyed by sequence) and route maps (keyed by name) -- both are
# named-list sections like any other in this collection, so they go
# through the same _keyed_list_to_device/_keyed_list_from_device
# mechanic as everything else, with key_field derived from ARGSPEC
# rather than hand-declared, instead of the hand-rolled loops this had
# before. _ROUTE_MAP_KEY/_RULE_KEY are derived after ARGUMENT_SPEC is
# built (near the bottom of this file) since they need it to exist.
# ---------------------------------------------------------------------------


def _rule_entry_to_device(rest):
    exclude = {"match", "set", "continue_sequence"}
    device = autoclean({k: v for k, v in rest.items() if k not in exclude})
    if rest.get("continue_sequence") is not None:
        device["continue"] = rest["continue_sequence"]
    if rest.get("match"):
        m = _match_to_device(rest["match"])
        if m:
            device["match"] = m
    if rest.get("set"):
        s = _set_to_device(rest["set"])
        if s:
            device["set"] = s
    return device


def _rule_entry_from_device(data):
    data = dict(data or {})
    continue_raw = data.pop("continue", None)
    match_raw = data.pop("match", None)
    set_raw = data.pop("set", None)
    entry = from_device(data)
    if continue_raw is not None:
        entry["continue_sequence"] = int(continue_raw)
    match = _match_from_device(match_raw)
    if match:
        entry["match"] = match
    setv = _set_from_device(set_raw)
    if setv:
        entry["set"] = setv
    return entry


def _route_map_entry_to_device(rest):
    entries = rest.get("entries") or []
    if not entries:
        return {}
    return {"rule": _keyed_list_to_device(entries, _RULE_KEY, _rule_entry_to_device)}


def _route_map_entry_from_device(data):
    rule_raw = (data or {}).get("rule")
    if not rule_raw:
        return {"entries": []}
    entries = _keyed_list_from_device(rule_raw, _RULE_KEY, _rule_entry_from_device, key_cast=int)
    # _keyed_list_from_device sorts by the raw device key as a string,
    # which orders sequence numbers wrong across a digit-count boundary
    # (e.g. "10" < "9" lexicographically) -- re-sort numerically now
    # that key_cast has already converted each key to a real int.
    return {"entries": sorted(entries, key=lambda e: e[_RULE_KEY])}


def _want_to_device(config):
    with_entries = [rm for rm in (config or []) if rm.get("entries")]
    return _keyed_list_to_device(with_entries, _ROUTE_MAP_KEY, _route_map_entry_to_device)


def get_running_config(vyos):
    raw = vyos.get_config(_BASE) or {}
    if isinstance(raw, dict) and "route-map" in raw:
        return raw["route-map"] or {}
    return raw


def _device_to_argspec(raw):
    if not raw:
        return []
    return _keyed_list_from_device(raw, _ROUTE_MAP_KEY, _route_map_entry_from_device)


def _seed_route_map_placeholders(want, have):
    """dict_op's fallback guesses a translated device key whenever a
    want key is missing from have entirely (a brand-new route map or
    rule). That guess is correct for a schema field name but wrong for
    a route-map name, which is an opaque value that may legitimately
    contain an underscore (confirmed against vyos-1x: "Name of
    route-map can only contain alpha-numeric letters, hyphen and
    underscores") -- confirmed as a real bug via direct reproduction,
    the same class found in vyos_snmp_server's "admin_user" case:
    "my_route_map" was silently becoming "my-route-map" in the
    generated command on first creation.

    Seeds an empty placeholder into have (mutated in place) for every
    route-map name present in want but not yet in have, using the
    exact verbatim value -- dict_op's own unmodified exact-match lookup
    then finds it directly and never reaches its guessing fallback.
    Also seeds each rule's own tag-node level with None (not {}), since
    a rule with no other fields set is a presence-only entry -- seeding
    {} there would make dict_op think it already matches and skip
    emitting the needed set command (the same mistake caught and fixed
    once already this session).
    """
    for rm_name, rm_val in (want or {}).items():
        rm_have = have.setdefault(rm_name, {})
        if not isinstance(rm_have, dict):
            continue
        rule_want = (rm_val or {}).get("rule") or {}
        if rule_want:
            rule_have = rm_have.setdefault("rule", {})
            if isinstance(rule_have, dict):
                for seq in rule_want:
                    if seq not in rule_have:
                        rule_have[seq] = None


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    if state == "deleted":
        if not config:
            return [("delete", _BASE)] if raw_have else []
        cmds = []
        for rm in config:
            if rm.get("route_map") in raw_have:
                cmds.append(("delete", _BASE + [rm["route_map"]]))
        return cmds

    want = _want_to_device(config)
    norm_have = _want_to_device(_device_to_argspec(raw_have))
    _seed_route_map_placeholders(want, norm_have)

    commands = []
    if state == "overridden":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        want_names = {rm.get("route_map") for rm in config if rm.get("route_map")}
        for name in want_names:
            section_want = want.get(name, {})
            section_have = norm_have.get(name, {})
            commands += dict_op(section_want, section_have, _BASE + [name], op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            route_map=dict(type="str", required=True),
            entries=dict(
                type="list",
                elements="dict",
                options=dict(
                    sequence=dict(type="int", required=True),
                    action=dict(type="str", choices=["permit", "deny"]),
                    description=dict(type="str"),
                    call=dict(type="str"),
                    continue_sequence=dict(type="int"),
                    match=dict(
                        type="dict",
                        options=dict(
                            interface=dict(type="str"),
                            metric=dict(type="int"),
                            origin=dict(type="str", choices=["egp", "igp", "incomplete"]),
                            peer=dict(type="str"),
                            protocol=dict(
                                type="str",
                                choices=[
                                    "babel",
                                    "bgp",
                                    "connected",
                                    "isis",
                                    "kernel",
                                    "ospf",
                                    "ospfv3",
                                    "rip",
                                    "ripng",
                                    "static",
                                    "table",
                                    "vnc",
                                ],
                            ),
                            prefix_list=dict(type="str"),
                            prefix_list6=dict(type="str"),
                            ip=dict(
                                type="dict",
                                options=dict(
                                    nexthop_address=dict(type="str"),
                                    nexthop_prefix_list=dict(type="str"),
                                ),
                            ),
                            ipv6=dict(
                                type="dict",
                                options=dict(
                                    nexthop_address=dict(type="str"),
                                ),
                            ),
                        ),
                    ),
                    set=dict(
                        type="dict",
                        options=dict(
                            metric=dict(type="int"),
                            metric_type=dict(type="str"),
                            origin=dict(type="str", choices=["egp", "igp", "incomplete"]),
                            originator_id=dict(type="str"),
                            src=dict(type="str"),
                            tag=dict(type="int"),
                            weight=dict(type="int"),
                            distance=dict(type="int"),
                            table=dict(type="int"),
                            local_preference=dict(type="int"),
                            ip_next_hop=dict(type="str"),
                            atomic_aggregate=dict(type="bool"),
                            as_path_exclude=dict(type="str"),
                            as_path_prepend=dict(type="str"),
                            as_path_prepend_last_as=dict(type="int"),
                            aggregator=dict(
                                type="dict",
                                options=dict(
                                    as_=dict(type="int", aliases=["as"]),
                                    ip=dict(type="str"),
                                ),
                            ),
                            community=dict(
                                type="dict",
                                options=dict(
                                    add=dict(type="list", elements="str"),
                                    replace=dict(type="list", elements="str"),
                                    none=dict(type="bool"),
                                    delete=dict(type="str"),
                                ),
                            ),
                            large_community=dict(
                                type="dict",
                                options=dict(
                                    add=dict(type="list", elements="str"),
                                    replace=dict(type="list", elements="str"),
                                    none=dict(type="bool"),
                                    delete=dict(type="str"),
                                ),
                            ),
                            ipv6_next_hop=dict(
                                type="dict",
                                options={
                                    "global": dict(type="str"),
                                    "local": dict(type="str"),
                                    "peer_address": dict(type="bool"),
                                    "prefer_global": dict(type="bool"),
                                },
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    state=dict(
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered"],
    ),
)

_ENTRY_OPTIONS = ARGUMENT_SPEC["config"]["options"]["entries"]["options"]
_ROUTE_MAP_KEY = _derive_key_field(ARGUMENT_SPEC["config"]["options"])
_RULE_KEY = _derive_key_field(_ENTRY_OPTIONS)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    for rm in have:
        for entry in rm.get("entries") or []:
            cast_by_spec(entry, _ENTRY_OPTIONS)

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
        for rm in after:
            for entry in rm.get("entries") or []:
                cast_by_spec(entry, _ENTRY_OPTIONS)
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
