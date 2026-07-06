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
  - The C(group) suboption can only reference an address-group. VyOS also
    supports network-group/port-group/domain-group references, which this
    module can read back (via C(gathered)) if already configured by other
    means, but cannot create -- the argspec has no group-type discriminator.
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
    dict_op,
    from_device,
    normalize_have,
)


_BASE = ["firewall"]
_AFIS = ("ipv4", "ipv6")

# Tag nodes VyOS's REST API can collapse to a bare string/list for a
# single entry with no other config -- "name" (rule sets, keyed by name)
# and "rule" (rules, keyed by number).
_TAG_KEYS = {"name", "rule"}


# ---------------------------------------------------------------------------
# want -> device / device -> argspec
#
# Every leaf here matches the device shape directly (action, description,
# disable, protocol, state, log, icmp.type/code) except one: "group".
# VyOS wraps a group reference under a literal group-kind key
# (address-group/network-group/...), not a flat value -- see the module
# note above on why this module can only ever *write* address-group.
# Rule-set/rule tag-node reshaping (keyed by name/number) is the other
# unavoidable structural work.
# ---------------------------------------------------------------------------


def _endpoint_to_device(ep):
    entry = autoclean({k: v for k, v in ep.items() if k != "group"})
    if ep.get("group"):
        entry["group"] = {"address-group": ep["group"]}
    return entry


def _endpoint_from_device(data):
    data = dict(data or {})
    group = data.pop("group", None)
    entry = from_device(data)
    if isinstance(group, dict) and group:
        entry["group"] = list(group.values())[0]
    elif isinstance(group, str):
        entry["group"] = group
    return entry


def _rules_to_device(rules):
    result = {}
    for r in rules or []:
        entry = autoclean(
            {k: v for k, v in r.items() if k not in ("number", "source", "destination")},
        )
        for endpoint in ("source", "destination"):
            if r.get(endpoint):
                entry[endpoint] = _endpoint_to_device(r[endpoint])
        result[str(r["number"])] = entry
    return result


def _rules_from_device(raw):
    result = []
    for num, data in sorted((raw or {}).items(), key=lambda kv: int(kv[0])):
        data = dict(data or {})
        src = data.pop("source", None)
        dst = data.pop("destination", None)
        entry = {"number": int(num), **from_device(data)}
        if src:
            entry["source"] = _endpoint_from_device(src)
        if dst:
            entry["destination"] = _endpoint_from_device(dst)
        result.append(entry)
    return result


def _rule_set_to_device(rs):
    entry = autoclean({k: v for k, v in rs.items() if k not in ("name", "rules")})
    if rs.get("rules"):
        entry["rule"] = _rules_to_device(rs["rules"])
    return entry


def _rule_set_from_device(name, data):
    data = dict(data or {})
    rules_raw = data.pop("rule", None) or {}
    entry = {"name": name, **from_device(data)}
    if rules_raw:
        entry["rules"] = _rules_from_device(rules_raw)
    return entry


def _want_to_device(config):
    result = {}
    for entry in config or []:
        afi = entry["afi"]
        rule_sets = entry.get("rule_sets") or []
        if not rule_sets:
            continue
        result[afi] = {rs["name"]: _rule_set_to_device(rs) for rs in rule_sets}
    return result


def get_running_config(vyos):
    """Fetch each AFI's rule-set subtree directly at firewall.<afi>.name --
    the most targeted path available, deliberately not a broader fetch at
    firewall.<afi> or firewall itself (which would pull in the hook-filter
    and group subtrees owned by sibling modules for no benefit here).
    """
    result = {}
    for afi in _AFIS:
        raw = vyos.get_config(_BASE + [afi, "name"])
        if raw and isinstance(raw, dict):
            # Some VyOS REST responses wrap the result in an extra "name"
            # key even when fetched at a path already ending in "name";
            # unwrap defensively either way.
            raw = raw.get("name", raw)
            if raw and isinstance(raw, dict):
                result[afi] = raw
    return result


def _device_to_argspec(raw):
    raw = raw or {}
    result = []
    for afi in _AFIS:
        afi_raw = raw.get(afi) or {}
        rule_sets = [_rule_set_from_device(name, data) for name, data in sorted(afi_raw.items())]
        if rule_sets:
            result.append({"afi": afi, "rule_sets": rule_sets})
    return result


# ---------------------------------------------------------------------------
# Command building — dict_op scoped to _BASE + [afi, "name", rs_name] per
# rule set, never a blanket op at _BASE + [afi] or _BASE itself (which
# would risk vyos_firewall_interfaces's hook-filter subtree and
# vyos_firewall_global's group subtree under the same "firewall" root).
# ---------------------------------------------------------------------------


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []
    norm_have = {afi: normalize_have(data, _TAG_KEYS) for afi, data in raw_have.items()}

    if state == "deleted":
        commands = []
        if not config:
            for afi, rule_sets in raw_have.items():
                for name in rule_sets:
                    commands.append(("delete", _BASE + [afi, "name", name]))
        else:
            for entry in config:
                afi = entry["afi"]
                for rs in entry.get("rule_sets") or []:
                    if rs["name"] in (raw_have.get(afi) or {}):
                        commands.append(("delete", _BASE + [afi, "name", rs["name"]]))
        return commands

    want = _want_to_device(config)
    commands = []

    if state == "overridden":
        want_keys = {(afi, name) for afi, rule_sets in want.items() for name in rule_sets}
        for afi, rule_sets in raw_have.items():
            for name in rule_sets:
                if (afi, name) not in want_keys:
                    commands.append(("delete", _BASE + [afi, "name", name]))

    for afi, rule_sets in want.items():
        for name, want_rs in rule_sets.items():
            rsbase = _BASE + [afi, "name", name]
            have_rs = (norm_have.get(afi) or {}).get(name) or {}

            if state in ("replaced", "overridden"):
                commands += dict_op(want_rs, have_rs, rsbase, op="purge")
            commands += dict_op(want_rs, have_rs, rsbase, op="set")

    return commands


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

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=_device_to_argspec(get_running_config(vyos)),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
