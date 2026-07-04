#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_rules
short_description: Manage firewall rule sets on VyOS devices using REST API
description:
  - Manages named firewall rule sets on VyOS devices via the REST API.
  - Supports both IPv4 (C(ipv4)) and IPv6 (C(ipv6)) rule sets.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - In VyOS 1.5+, firewall uses named rule sets under C(firewall.ipv4.name)
    and C(firewall.ipv6.name).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: Firewall rule set configuration.
    type: list
    elements: dict
    suboptions:
      afi:
        description: Address family.
        type: str
        choices: [ipv4, ipv6]
        required: true
      rule_sets:
        description: Named rule sets for this address family.
        type: list
        elements: dict
        suboptions:
          name:
            description: Rule set name.
            type: str
            required: true
          default_action:
            description: Default action when no rule matches.
            type: str
            choices: [accept, drop, reject]
          description:
            description: Rule set description.
            type: str
          rules:
            description: Firewall rules in this rule set.
            type: list
            elements: dict
            suboptions:
              number:
                description: Rule number.
                type: int
                required: true
              action:
                description: Rule action.
                type: str
                choices: [accept, drop, reject, return, queue, continue]
              description:
                description: Rule description.
                type: str
              disable:
                description: Disable this rule.
                type: bool
              protocol:
                description: Protocol to match.
                type: str
              state:
                description: Connection state to match.
                type: str
                choices: [established, invalid, new, related]
              source:
                description: Source match criteria.
                type: dict
                suboptions:
                  address:
                    description: Source IP address or prefix.
                    type: str
                  group:
                    description: Source group name.
                    type: str
                  port:
                    description: Source port or range.
                    type: str
              destination:
                description: Destination match criteria.
                type: dict
                suboptions:
                  address:
                    description: Destination IP address or prefix.
                    type: str
                  group:
                    description: Destination group name.
                    type: str
                  port:
                    description: Destination port or range.
                    type: str
              log:
                description: Enable logging for this rule.
                type: bool
              icmp:
                description: ICMP type/code to match.
                type: dict
                suboptions:
                  type:
                    description: ICMP type.
                    type: int
                  code:
                    description: ICMP code.
                    type: int
  state:
    description:
      - Desired state of the firewall rules configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces rule sets for named rule sets in config.
      - C(overridden) replaces all firewall rule sets.
      - C(deleted) removes firewall rule sets.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - Rule sets are identified by AFI and name. Deleting a rule set removes
    all its rules.
"""

EXAMPLES = r"""
- name: Merge firewall rules
  vyos.rest.vyos_firewall_rules:
    config:
      - afi: ipv4
        rule_sets:
          - name: RULE-SET1
            default_action: drop
            rules:
              - number: 10
                action: accept
                protocol: tcp
                source:
                  address: 192.168.1.0/24
                destination:
                  port: "80"
              - number: 20
                action: drop
                state: invalid
      - afi: ipv6
        rule_sets:
          - name: RULE-SET6
            default_action: accept
            rules:
              - number: 10
                action: accept
    state: merged

- name: Delete all firewall rules
  vyos.rest.vyos_firewall_rules:
    state: deleted

- name: Gather firewall rules
  vyos.rest.vyos_firewall_rules:
    state: gathered
"""

RETURN = r"""
before:
  description: Firewall rules configuration before this module ran.
  returned: always
  type: list
after:
  description: Firewall rules configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current firewall rules configuration as structured data.
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


_BASE = ["firewall"]
_AFIS = ["ipv4", "ipv6"]


def _parse_rule(rule_num, data):
    rule = {"number": int(rule_num)}
    data = data or {}
    if "action" in data:
        rule["action"] = data["action"]
    if "description" in data:
        rule["description"] = data["description"]
    if "disable" in data:
        rule["disable"] = True
    if "protocol" in data:
        rule["protocol"] = data["protocol"]
    if "state" in data:
        rule["state"] = data["state"]
    if "log" in data:
        rule["log"] = True

    src = data.get("source", {}) or {}
    if src:
        rule["source"] = {}
        if "address" in src:
            rule["source"]["address"] = src["address"]
        if "group" in src:
            grp = src["group"]
            if isinstance(grp, dict):
                rule["source"]["group"] = list(grp.values())[0] if grp else None
            else:
                rule["source"]["group"] = grp
        if "port" in src:
            rule["source"]["port"] = src["port"]

    dst = data.get("destination", {}) or {}
    if dst:
        rule["destination"] = {}
        if "address" in dst:
            rule["destination"]["address"] = dst["address"]
        if "group" in dst:
            grp = dst["group"]
            if isinstance(grp, dict):
                rule["destination"]["group"] = list(grp.values())[0] if grp else None
            else:
                rule["destination"]["group"] = grp
        if "port" in dst:
            rule["destination"]["port"] = dst["port"]

    icmp = data.get("icmp", {}) or {}
    if icmp:
        rule["icmp"] = {}
        if "type" in icmp:
            rule["icmp"]["type"] = int(icmp["type"])
        if "code" in icmp:
            rule["icmp"]["code"] = int(icmp["code"])

    return rule


def _parse_rule_set(rs_name, data):
    rs = {"name": rs_name}
    data = data or {}
    if "default-action" in data:
        rs["default_action"] = data["default-action"]
    if "description" in data:
        rs["description"] = data["description"]
    rules_raw = data.get("rule", {}) or {}
    if rules_raw and isinstance(rules_raw, dict):
        rules = [
            _parse_rule(num, rdata)
            for num, rdata in sorted(
                rules_raw.items(),
                key=lambda x: int(x[0]),
            )
        ]
        if rules:
            rs["rules"] = rules
    return rs


def get_running_config(vyos):
    result = []
    for afi in _AFIS:
        raw = vyos.get_config(_BASE + [afi, "name"])
        if not raw or not isinstance(raw, dict):
            continue
        # unwrap "name" key if present
        raw = raw.get("name", raw)
        if not raw or not isinstance(raw, dict):
            continue
        rule_sets = [_parse_rule_set(name, data) for name, data in sorted(raw.items())]
        if rule_sets:
            result.append({"afi": afi, "rule_sets": rule_sets})
    return result


def _rule_cmds(rs_name, afi, rule, have_rule):
    cmds = []
    rbase = _BASE + [afi, "name", rs_name, "rule", str(rule["number"])]
    have_rule = have_rule or {}

    if rule.get("action") and rule["action"] != have_rule.get("action"):
        cmds.append(("set", rbase + ["action", rule["action"]]))
    if rule.get("description") and rule["description"] != have_rule.get("description"):
        cmds.append(("set", rbase + ["description", rule["description"]]))
    if rule.get("disable") and not have_rule.get("disable"):
        cmds.append(("set", rbase + ["disable"]))
    if rule.get("protocol") and rule["protocol"] != have_rule.get("protocol"):
        cmds.append(("set", rbase + ["protocol", rule["protocol"]]))
    if rule.get("state") and rule["state"] != have_rule.get("state"):
        cmds.append(("set", rbase + ["state", rule["state"]]))
    if rule.get("log") and not have_rule.get("log"):
        cmds.append(("set", rbase + ["log"]))

    for endpoint in ["source", "destination"]:
        want_ep = rule.get(endpoint) or {}
        have_ep = have_rule.get(endpoint) or {}
        if want_ep.get("address") and want_ep["address"] != have_ep.get("address"):
            cmds.append(("set", rbase + [endpoint, "address", want_ep["address"]]))
        if want_ep.get("port") and want_ep["port"] != have_ep.get("port"):
            cmds.append(("set", rbase + [endpoint, "port", str(want_ep["port"])]))
        if want_ep.get("group") and want_ep["group"] != have_ep.get("group"):
            cmds.append(
                (
                    "set",
                    rbase
                    + [
                        endpoint,
                        "group",
                        "address-group",
                        want_ep["group"],
                    ],
                ),
            )

    icmp = rule.get("icmp") or {}
    have_icmp = have_rule.get("icmp") or {}
    if icmp.get("type") and icmp["type"] != have_icmp.get("type"):
        cmds.append(("set", rbase + ["icmp", "type", str(icmp["type"])]))
    if icmp.get("code") and icmp["code"] != have_icmp.get("code"):
        cmds.append(("set", rbase + ["icmp", "code", str(icmp["code"])]))

    return cmds


def _rule_set_cmds(afi, rs, have_rs, state):
    cmds = []
    rs_name = rs["name"]
    rsbase = _BASE + [afi, "name", rs_name]
    have_rs = have_rs or {}

    if rs.get("default_action") and rs["default_action"] != have_rs.get("default_action"):
        cmds.append(("set", rsbase + ["default-action", rs["default_action"]]))
    if rs.get("description") and rs["description"] != have_rs.get("description"):
        cmds.append(("set", rsbase + ["description", rs["description"]]))

    have_rules = {r["number"]: r for r in (have_rs.get("rules") or [])}
    want_rules = {r["number"]: r for r in (rs.get("rules") or [])}

    if state == "replaced":
        for num in set(have_rules) - set(want_rules):
            cmds.append(("delete", rsbase + ["rule", str(num)]))

    for num, rule in want_rules.items():
        cmds += _rule_cmds(rs_name, afi, rule, have_rules.get(num))

    return cmds


def build_commands(config, have_list, state):
    cmds = []

    if state == "deleted":
        if not config:
            if have_list:
                cmds.append(("delete", _BASE))
        else:
            have_map = {
                (e["afi"], rs["name"]): rs for e in have_list for rs in e.get("rule_sets", [])
            }
            for entry in config:
                afi = entry["afi"]
                for rs in entry.get("rule_sets") or []:
                    if (afi, rs["name"]) in have_map:
                        cmds.append(("delete", _BASE + [afi, "name", rs["name"]]))
        return cmds

    have_map = {e["afi"]: {rs["name"]: rs for rs in e.get("rule_sets", [])} for e in have_list}

    if state == "overridden":
        want_keys = {
            (e["afi"], rs["name"]) for e in (config or []) for rs in e.get("rule_sets", [])
        }
        for e in have_list:
            for rs in e.get("rule_sets", []):
                if (e["afi"], rs["name"]) not in want_keys:
                    cmds.append(("delete", _BASE + [e["afi"], "name", rs["name"]]))

    for entry in config or []:
        afi = entry["afi"]
        have_afi = have_map.get(afi, {})

        for rs in entry.get("rule_sets") or []:
            have_rs = have_afi.get(rs["name"])

            if state == "replaced" and have_rs:
                # delete and rebuild if different
                want_cmds = _rule_set_cmds(afi, rs, {}, "merged")
                have_cmds = _rule_set_cmds(
                    afi,
                    {
                        "name": rs["name"],
                        "default_action": have_rs.get("default_action"),
                        "rules": have_rs.get("rules", []),
                    },
                    {},
                    "merged",
                )
                if want_cmds != have_cmds:
                    cmds.append(("delete", _BASE + [afi, "name", rs["name"]]))
                    have_rs = None

            cmds += _rule_set_cmds(
                afi,
                rs,
                have_rs,
                state if state not in ("replaced", "overridden") else "merged",
            )

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
            rule_sets=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    default_action=dict(
                        type="str",
                        choices=["accept", "drop", "reject"],
                    ),
                    description=dict(type="str"),
                    rules=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            number=dict(type="int", required=True),
                            action=dict(
                                type="str",
                                choices=[
                                    "accept",
                                    "drop",
                                    "reject",
                                    "return",
                                    "queue",
                                    "continue",
                                ],
                            ),
                            description=dict(type="str"),
                            disable=dict(type="bool"),
                            protocol=dict(type="str"),
                            state=dict(
                                type="str",
                                choices=[
                                    "established",
                                    "invalid",
                                    "new",
                                    "related",
                                ],
                            ),
                            log=dict(type="bool"),
                            source=dict(
                                type="dict",
                                options=dict(
                                    address=dict(type="str"),
                                    group=dict(type="str"),
                                    port=dict(type="str"),
                                ),
                            ),
                            destination=dict(
                                type="dict",
                                options=dict(
                                    address=dict(type="str"),
                                    group=dict(type="str"),
                                    port=dict(type="str"),
                                ),
                            ),
                            icmp=dict(
                                type="dict",
                                options=dict(
                                    type=dict(type="int"),
                                    code=dict(type="int"),
                                ),
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
