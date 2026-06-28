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
            description: Match conditions (passed through to VyOS API).
            type: dict
          set:
            description: Route parameters to set (passed through to VyOS API).
            type: dict

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
  - Input validation is delegated to the VyOS API.
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
              metric: "5"
              as_path_exclude: "111"
              aggregator:
                as: 100
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
  returned: when changes are applied
  type: bool

response:
  description: Raw API response.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["policy", "route-map"]

_SET_MAP = {
    "as_path_prepend": ["as-path", "prepend"],
    "as_path_exclude": ["as-path", "exclude"],
    "as_path_prepend_last_as": ["as-path", "prepend-last-as"],
    "ip_next_hop": ["ip-next-hop"],
    "local_preference": ["local-preference"],
    "metric": ["metric"],
    "metric_type": ["metric-type"],
    "origin": ["origin"],
    "originator_id": ["originator-id"],
    "src": ["src"],
    "tag": ["tag"],
    "weight": ["weight"],
    "distance": ["distance"],
    "table": ["table"],
}

_MATCH_MAP = {
    "interface": ["interface"],
    "metric": ["metric"],
    "origin": ["origin"],
    "peer": ["peer"],
    "protocol": ["protocol"],
}


def get_running_config(vyos):
    raw = vyos.get_config(["policy", "route-map"])
    if not raw or not isinstance(raw, dict):
        return []

    rm_data = raw.get("route-map", raw)
    if not isinstance(rm_data, dict):
        return []

    result = []
    for rm_name, rm_info in sorted(rm_data.items()):
        entry = {"route_map": rm_name, "entries": []}
        rm_info = rm_info or {}

        for seq, rule_data in sorted(
            (rm_info.get("rule") or {}).items(),
            key=lambda x: int(x[0]),
        ):
            rule_data = rule_data or {}
            rule = {"sequence": int(seq)}
            if rule_data.get("action"):
                rule["action"] = rule_data["action"]
            if rule_data.get("description"):
                rule["description"] = rule_data["description"]
            if rule_data.get("call"):
                rule["call"] = rule_data["call"]
            if rule_data.get("continue"):
                rule["continue_sequence"] = int(rule_data["continue"])
            if rule_data.get("match"):
                rule["match"] = rule_data["match"]
            if rule_data.get("set"):
                rule["set"] = rule_data["set"]
            entry["entries"].append(rule)

        result.append(entry)

    return result


def _match_cmds(rbase, match):
    cmds = []
    if not match:
        return cmds

    mbase = rbase + ["match"]

    for key, path_suffix in _MATCH_MAP.items():
        if match.get(key) is not None:
            cmds.append(("set", mbase + path_suffix + [str(match[key])]))

    if match.get("prefix_list"):
        cmds.append(("set", mbase + ["ip", "address", "prefix-list", match["prefix_list"]]))
    if match.get("prefix_list6"):
        cmds.append(("set", mbase + ["ipv6", "address", "prefix-list", match["prefix_list6"]]))

    ip = match.get("ip") or {}
    if ip.get("nexthop_address"):
        cmds.append(("set", mbase + ["ip", "nexthop", "address", ip["nexthop_address"]]))
    if ip.get("nexthop_prefix_list"):
        cmds.append(("set", mbase + ["ip", "nexthop", "prefix-list", ip["nexthop_prefix_list"]]))

    ipv6 = match.get("ipv6") or {}
    if ipv6.get("nexthop_address"):
        cmds.append(("set", mbase + ["ipv6", "nexthop", "address", ipv6["nexthop_address"]]))

    return cmds


def _set_cmds(rbase, setv):
    cmds = []
    if not setv:
        return cmds

    sbase = rbase + ["set"]

    for key, path_suffix in _SET_MAP.items():
        if setv.get(key) is not None:
            cmds.append(("set", sbase + path_suffix + [str(setv[key])]))

    if setv.get("atomic_aggregate"):
        cmds.append(("set", sbase + ["atomic-aggregate"]))

    comm = setv.get("community") or {}
    if comm.get("value"):
        cmds.append(("set", sbase + ["community", comm["value"]]))

    large_comm = setv.get("large_community")
    if large_comm is not None:
        cmds.append(("set", sbase + ["large-community", str(large_comm)]))

    agg = setv.get("aggregator") or {}
    agg_as = agg.get("as") or agg.get("as_")
    if agg_as and agg.get("ip"):
        cmds.append(("set", sbase + ["aggregator", "as", str(agg_as), "address", agg["ip"]]))
    elif agg_as:
        cmds.append(("set", sbase + ["aggregator", "as", str(agg_as)]))

    nh6 = setv.get("ipv6_next_hop") or {}
    if nh6.get("value"):
        ip_type = nh6.get("ip_type") or "global"
        cmds.append(("set", sbase + ["ipv6-next-hop", ip_type, nh6["value"]]))

    return cmds


def _want_to_api_set(setv):
    if not setv:
        return {}
    api = {}
    for key, path in _SET_MAP.items():
        if setv.get(key) is not None:
            d = api
            for p in path[:-1]:
                d = d.setdefault(p, {})
            d[path[-1]] = str(setv[key])
    agg = setv.get("aggregator") or {}
    agg_as = agg.get("as") or agg.get("as_")
    if agg_as:
        api.setdefault("aggregator", {})["as"] = str(agg_as)
    large_comm = setv.get("large_community")
    if large_comm is not None:
        api["large-community"] = {str(large_comm): {}}
    return api


def _want_to_api_match(match):
    if not match:
        return {}
    api = {}
    for key in _MATCH_MAP:
        if match.get(key) is not None:
            api[key] = str(match[key])
    if match.get("prefix_list"):
        api.setdefault("ip", {}).setdefault("address", {})["prefix-list"] = match["prefix_list"]
    if match.get("prefix_list6"):
        api.setdefault("ipv6", {}).setdefault("address", {})["prefix-list"] = match["prefix_list6"]
    return api


def _rule_cmds(rm_name, rule, have_rule, state="merged"):
    cmds = []
    seq = str(rule["sequence"])
    rbase = _BASE + [rm_name, "rule", seq]

    if rule.get("action") and rule["action"] != have_rule.get("action"):
        cmds.append(("set", rbase + ["action", rule["action"]]))
    if rule.get("description") and rule["description"] != have_rule.get("description"):
        cmds.append(("set", rbase + ["description", rule["description"]]))
    if rule.get("call") and rule["call"] != have_rule.get("call"):
        cmds.append(("set", rbase + ["call", rule["call"]]))
    if rule.get("continue_sequence") is not None and rule["continue_sequence"] != have_rule.get(
        "continue_sequence",
    ):
        cmds.append(("set", rbase + ["continue", str(rule["continue_sequence"])]))

    want_match_api = _want_to_api_match(rule.get("match"))
    have_match = have_rule.get("match") or {}
    changed_match = {k: v for k, v in want_match_api.items() if have_match.get(k) != v}
    if changed_match:
        match = rule.get("match") or {}
        changed_keys = set(changed_match.keys())
        partial_match = {
            k: v
            for k, v in match.items()
            if k in changed_keys
            or (k == "prefix_list" and "ip" in changed_keys)
            or (k == "prefix_list6" and "ipv6" in changed_keys)
        }
        if not partial_match:
            partial_match = match
        cmds += _match_cmds(rbase, partial_match)

    want_set_api = _want_to_api_set(rule.get("set"))
    have_set = have_rule.get("set") or {}
    if state in ("replaced", "overridden"):
        if want_set_api != have_set:
            cmds += _set_cmds(rbase, rule.get("set"))
    else:
        have_subset = {k: have_set[k] for k in want_set_api if k in have_set}
        if want_set_api != have_subset:
            cmds += _set_cmds(rbase, rule.get("set"))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []

    if state == "deleted":
        if not config:
            if have_raw:
                cmds.append(("delete", _BASE))
        else:
            for rm in config:
                cmds.append(("delete", _BASE + [rm["route_map"]]))
        return cmds

    have_map = {e["route_map"]: e for e in have_raw}

    if state == "overridden":
        want_names = {rm["route_map"] for rm in config}
        for name in set(have_map) - want_names:
            cmds.append(("delete", _BASE + [name]))

    for rm in config:
        rm_name = rm["route_map"]
        have_rm = have_map.get(rm_name, {})

        if state == "replaced" and rm_name in have_map:
            # Only delete and rebuild if something actually differs
            have_entries = {str(r["sequence"]): r for r in (have_rm.get("entries") or [])}
            want_seqs = {str(r["sequence"]) for r in (rm.get("entries") or [])}
            extra_seqs = set(have_entries) - want_seqs
            test_cmds = []
            for rule in rm.get("entries") or []:
                have_rule = have_entries.get(str(rule["sequence"]), {})
                test_cmds += _rule_cmds(rm_name, rule, have_rule, state)
            if test_cmds or extra_seqs:
                cmds.append(("delete", _BASE + [rm_name]))
                have_rm = {}
            else:
                continue  # already matches — idempotent

        have_entries = {str(r["sequence"]): r for r in (have_rm.get("entries") or [])}

        for rule in rm.get("entries") or []:
            have_rule = have_entries.get(str(rule["sequence"]), {})
            cmds += _rule_cmds(rm_name, rule, have_rule, state)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(type="list", elements="dict"),
    state=dict(
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
