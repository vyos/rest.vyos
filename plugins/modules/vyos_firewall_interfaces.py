#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_interfaces
short_description: Manage firewall hook filters on VyOS devices using REST API
description:
  - Manages firewall hook filter configuration on VyOS devices via the REST API.
  - In VyOS 1.5+, firewall hook filters (input/output/forward) replace the
    per-interface firewall assignments used in VyOS 1.4.
  - Hook filters apply globally to all traffic traversing that hook point.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: Firewall hook filter configuration.
    type: list
    elements: dict
    suboptions:
      afi:
        description: Address family.
        type: str
        choices: [ipv4, ipv6]
        required: true
      hooks:
        description: Hook filter configurations for this address family.
        type: list
        elements: dict
        suboptions:
          hook:
            description: Netfilter hook point.
            type: str
            choices: [input, output, forward]
            required: true
          default_action:
            description: Default action when no rule matches.
            type: str
            choices: [accept, drop, reject]
          description:
            description: Filter description.
            type: str
          rules:
            description: Rules in this hook filter.
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
              log:
                description: Enable logging.
                type: bool
              source:
                description: Source match criteria.
                type: dict
                suboptions:
                  address:
                    description: Source IP address or prefix.
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
                  port:
                    description: Destination port or range.
                    type: str
  state:
    description:
      - Desired state of the firewall hook filter configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces hook filter config for named hooks in config.
      - C(overridden) replaces all firewall hook filter config.
      - C(deleted) removes firewall hook filter config.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - In VyOS 1.5+, hook filters apply globally rather than per-interface.
    Use named rule sets (M(vyos.rest.vyos_firewall_rules)) for more granular
    per-traffic control.
"""

EXAMPLES = r"""
- name: Merge firewall hook filter configuration
  vyos.rest.vyos_firewall_interfaces:
    config:
      - afi: ipv4
        hooks:
          - hook: input
            default_action: accept
            rules:
              - number: 10
                action: accept
                state: established
              - number: 20
                action: drop
                state: invalid
          - hook: forward
            default_action: accept
          - hook: output
            default_action: accept
      - afi: ipv6
        hooks:
          - hook: input
            default_action: accept
    state: merged

- name: Delete all firewall hook filter configuration
  vyos.rest.vyos_firewall_interfaces:
    state: deleted

- name: Gather firewall hook filter configuration
  vyos.rest.vyos_firewall_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: Firewall hook filter configuration before this module ran.
  returned: always
  type: list
after:
  description: Firewall hook filter configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current firewall hook filter configuration as structured data.
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
_HOOKS = ["input", "output", "forward"]


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

    for endpoint in ["source", "destination"]:
        ep = data.get(endpoint, {}) or {}
        if ep:
            rule[endpoint] = {}
            if "address" in ep:
                rule[endpoint]["address"] = ep["address"]
            if "port" in ep:
                rule[endpoint]["port"] = ep["port"]

    return rule


def _parse_hook_filter(hook, data):
    entry = {"hook": hook}
    data = data or {}
    filter_data = data.get("filter", {}) or {}
    if "default-action" in filter_data:
        entry["default_action"] = filter_data["default-action"]
    if "description" in filter_data:
        entry["description"] = filter_data["description"]
    rules_raw = filter_data.get("rule", {}) or {}
    if rules_raw and isinstance(rules_raw, dict):
        rules = [
            _parse_rule(num, rdata)
            for num, rdata in sorted(
                rules_raw.items(),
                key=lambda x: int(x[0]),
            )
        ]
        if rules:
            entry["rules"] = rules
    return entry


def get_running_config(vyos):
    result = []
    for afi in _AFIS:
        raw = vyos.get_config(_BASE + [afi])
        if not raw or not isinstance(raw, dict):
            continue
        hooks = []
        for hook in _HOOKS:
            if hook in raw:
                parsed = _parse_hook_filter(hook, raw[hook])
                if len(parsed) > 1:  # more than just hook key
                    hooks.append(parsed)
        if hooks:
            result.append({"afi": afi, "hooks": hooks})
    return result


def _rule_cmds(afi, hook, rule, have_rule):
    cmds = []
    rbase = _BASE + [afi, hook, "filter", "rule", str(rule["number"])]
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

    return cmds


def _hook_cmds(afi, hook_entry, have_hook, state):
    cmds = []
    hook = hook_entry["hook"]
    hbase = _BASE + [afi, hook, "filter"]
    have_hook = have_hook or {}

    if hook_entry.get("default_action") and hook_entry["default_action"] != have_hook.get(
        "default_action",
    ):
        cmds.append(("set", hbase + ["default-action", hook_entry["default_action"]]))
    if hook_entry.get("description") and hook_entry["description"] != have_hook.get("description"):
        cmds.append(("set", hbase + ["description", hook_entry["description"]]))

    have_rules = {r["number"]: r for r in (have_hook.get("rules") or [])}
    want_rules = {r["number"]: r for r in (hook_entry.get("rules") or [])}

    if state == "replaced":
        for num in set(have_rules) - set(want_rules):
            cmds.append(("delete", hbase + ["rule", str(num)]))

    for num, rule in want_rules.items():
        cmds += _rule_cmds(afi, hook, rule, have_rules.get(num))

    return cmds


def build_commands(config, have_list, state):
    cmds = []

    if state == "deleted":
        if not config:
            if have_list:
                for entry in have_list:
                    afi = entry["afi"]
                    for hook_entry in entry.get("hooks", []):
                        cmds.append(("delete", _BASE + [afi, hook_entry["hook"], "filter"]))
        else:
            have_map = {(e["afi"], h["hook"]): h for e in have_list for h in e.get("hooks", [])}
            for entry in config:
                afi = entry["afi"]
                for hook_entry in entry.get("hooks") or []:
                    if (afi, hook_entry["hook"]) in have_map:
                        cmds.append(("delete", _BASE + [afi, hook_entry["hook"], "filter"]))
        return cmds

    have_map = {e["afi"]: {h["hook"]: h for h in e.get("hooks", [])} for e in have_list}

    if state == "overridden":
        want_keys = {(e["afi"], h["hook"]) for e in (config or []) for h in e.get("hooks", [])}
        for e in have_list:
            for h in e.get("hooks", []):
                if (e["afi"], h["hook"]) not in want_keys:
                    cmds.append(("delete", _BASE + [e["afi"], h["hook"], "filter"]))

    for entry in config or []:
        afi = entry["afi"]
        have_afi = have_map.get(afi, {})

        for hook_entry in entry.get("hooks") or []:
            hook = hook_entry["hook"]
            have_hook = have_afi.get(hook)

            if state == "replaced" and have_hook:
                want_cmds = _hook_cmds(afi, hook_entry, {}, "merged")
                have_hook_entry = {
                    "hook": hook,
                    "default_action": have_hook.get("default_action"),
                    "rules": have_hook.get("rules", []),
                }
                have_cmds = _hook_cmds(afi, have_hook_entry, {}, "merged")
                if want_cmds != have_cmds:
                    cmds.append(("delete", _BASE + [afi, hook, "filter"]))
                    have_hook = None

            effective_state = state if state not in ("replaced", "overridden") else "merged"
            cmds += _hook_cmds(afi, hook_entry, have_hook, effective_state)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
            hooks=dict(
                type="list",
                elements="dict",
                options=dict(
                    hook=dict(
                        type="str",
                        choices=["input", "output", "forward"],
                        required=True,
                    ),
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
                                    port=dict(type="str"),
                                ),
                            ),
                            destination=dict(
                                type="dict",
                                options=dict(
                                    address=dict(type="str"),
                                    port=dict(type="str"),
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
