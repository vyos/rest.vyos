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

# The only hook filter keys this module owns under firewall.<afi>. Sibling
# top-level keys under the same afi (e.g. firewall.<afi>.name, owned by
# vyos_firewall_rules) are never enumerated or touched -- this module
# only ever builds paths as _BASE + [afi, hook, "filter", ...] for hook
# drawn from this fixed set, never a blanket op at _BASE + [afi] itself.
_HOOKS = ("input", "output", "forward")
_AFIS = ("ipv4", "ipv6")

# "rule" is a genuine tag node (keyed by rule number) that VyOS's REST API
# can collapse to a bare value for a single rule with no other config.
_TAG_KEYS = {"rule"}


# ---------------------------------------------------------------------------
# want -> device / device -> argspec
#
# Every leaf here is a direct structural match between argspec and device
# shape (protocol, description, disable, state, log, source/destination
# both flowing through autoclean/from_device generically). The only
# unavoidable structural work: the "rule" tag-node reshape (keyed by
# number) and inserting the literal "filter" wrapper key that VyOS
# requires one level under each hook but the argspec omits (hook_entry's
# fields live directly on it, not nested under a "filter" key).
# ---------------------------------------------------------------------------


def _rules_to_device(rules):
    return {
        str(r["number"]): autoclean({k: v for k, v in r.items() if k != "number"})
        for r in rules or []
    }


def _rules_from_device(raw):
    result = []
    for num, data in sorted((raw or {}).items(), key=lambda kv: int(kv[0])):
        entry = {"number": int(num), **from_device(data or {})}
        result.append(entry)
    return result


def _hook_filter_to_device(hook_entry):
    entry = autoclean({k: v for k, v in hook_entry.items() if k not in ("hook", "rules")})
    if hook_entry.get("rules"):
        entry["rule"] = _rules_to_device(hook_entry["rules"])
    return entry


def _hook_filter_from_device(hook, filter_data):
    filter_data = dict(filter_data or {})
    rules_raw = filter_data.pop("rule", None) or {}
    entry = {"hook": hook, **from_device(filter_data)}
    if rules_raw:
        entry["rules"] = _rules_from_device(rules_raw)
    return entry


def _want_to_device(config):
    result = {}
    for entry in config or []:
        afi = entry["afi"]
        hooks = entry.get("hooks") or []
        if not hooks:
            continue
        result[afi] = {h["hook"]: {"filter": _hook_filter_to_device(h)} for h in hooks}
    return result


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    raw = raw or {}
    result = []
    for afi in _AFIS:
        afi_raw = raw.get(afi) or {}
        hooks = []
        for hook in _HOOKS:
            filter_data = (afi_raw.get(hook) or {}).get("filter")
            if filter_data:
                hooks.append(_hook_filter_from_device(hook, filter_data))
        if hooks:
            result.append({"afi": afi, "hooks": hooks})
    return result


# ---------------------------------------------------------------------------
# Command building — dict_op scoped to _BASE + [afi, hook, "filter"] only,
# per hook, never a blanket op at _BASE + [afi] or _BASE itself (which
# would risk vyos_firewall_rules's firewall.<afi>.name subtree, even
# though today the keys happen to differ -- staying scoped to the exact
# owned path is the same discipline established for the BGP modules).
# ---------------------------------------------------------------------------


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []
    norm_have = normalize_have(raw_have, _TAG_KEYS)

    if state == "deleted":
        commands = []
        # No config given -> delete every hook filter currently present.
        # Config given -> delete only the (afi, hook) pairs it names.
        targets = (
            [(afi, hook) for afi in _AFIS for hook in _HOOKS]
            if not config
            else [(e["afi"], h["hook"]) for e in config for h in (e.get("hooks") or [])]
        )
        for afi, hook in targets:
            if ((raw_have.get(afi) or {}).get(hook) or {}).get("filter"):
                commands.append(("delete", _BASE + [afi, hook, "filter"]))
        return commands

    want = _want_to_device(config)
    commands = []

    if state == "overridden":
        want_pairs = {(afi, hook) for afi, hooks in want.items() for hook in hooks}
        for afi in _AFIS:
            for hook in _HOOKS:
                if (afi, hook) not in want_pairs and (
                    (raw_have.get(afi) or {}).get(hook) or {}
                ).get(
                    "filter",
                ):
                    commands.append(("delete", _BASE + [afi, hook, "filter"]))

    for afi, hooks in want.items():
        for hook, want_hook in hooks.items():
            hbase = _BASE + [afi, hook, "filter"]
            have_filter = ((norm_have.get(afi) or {}).get(hook) or {}).get("filter") or {}
            want_filter = want_hook.get("filter", {})

            if state in ("replaced", "overridden"):
                commands += dict_op(want_filter, have_filter, hbase, op="purge")
            commands += dict_op(want_filter, have_filter, hbase, op="set")

    return commands


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
