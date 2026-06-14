#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_prefix_lists
short_description: Manage prefix-list configuration on VyOS devices using REST API
description:
  - Manages IPv4 and IPv6 prefix lists on VyOS via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)

options:
  config:
    description: List of prefix-list configurations grouped by address family.
    type: list
    elements: dict
    suboptions:
      afi:
        description: Address family identifier.
        type: str
        choices: [ipv4, ipv6]
        required: true
      prefix_lists:
        description: Named prefix lists.
        type: list
        elements: dict
        suboptions:
          name:
            description: Prefix list name.
            type: str
            required: true
          description:
            description: Prefix list description.
            type: str
          entries:
            description: Prefix list rules.
            type: list
            elements: dict
            suboptions:
              sequence:
                description: Rule sequence number.
                type: int
                required: true
              description:
                description: Rule description.
                type: str
              action:
                description: Permit or deny.
                type: str
                choices: [permit, deny]
              ge:
                description: Minimum prefix length.
                type: int
              le:
                description: Maximum prefix length.
                type: int
              prefix:
                description: Network prefix to match.
                type: str

  state:
    description:
      - Desired state of the prefix-list configuration.
      - C(merged) adds or updates entries without removing existing ones.
      - C(replaced) replaces each named prefix list mentioned in config.
      - C(overridden) replaces all prefix lists for the given AFIs.
      - C(deleted) removes prefix lists. Without config removes all.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged

notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Merge prefix list configuration
  vyos.rest.vyos_prefix_lists:
    config:
      - afi: ipv4
        prefix_lists:
          - name: AnsibleIPv4PrefixList
            description: PL configured by ansible
            entries:
              - sequence: 2
                action: permit
                prefix: 92.168.10.0/26
                le: 32
              - sequence: 3
                action: deny
                prefix: 72.168.2.0/24
                ge: 26
      - afi: ipv6
        prefix_lists:
          - name: AllowIPv6Prefix
            entries:
              - sequence: 5
                action: permit
                prefix: 2001:db8:8000::/35
                le: 37
    state: merged

- name: Delete all prefix lists
  vyos.rest.vyos_prefix_lists:
    state: deleted

- name: Gather current prefix list configuration
  vyos.rest.vyos_prefix_lists:
    state: gathered
"""

RETURN = r"""
before:
  description: Prefix list configuration before this module ran.
  returned: always
  type: list
after:
  description: Prefix list configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current prefix list configuration as structured data.
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


_PL_KEY = {"ipv4": "prefix-list", "ipv6": "prefix-list6"}


def get_running_config(vyos):
    raw = vyos.get_config(["policy"])
    if not raw or not isinstance(raw, dict):
        return []

    result = []
    for afi, api_key in [("ipv4", "prefix-list"), ("ipv6", "prefix-list6")]:
        pl_data = raw.get(api_key) or {}
        if not isinstance(pl_data, dict):
            continue

        pls = []
        for pl_name, pl_info in sorted(pl_data.items()):
            entry = {"name": pl_name}
            pl_info = pl_info or {}

            if pl_info.get("description"):
                entry["description"] = pl_info["description"]

            rules = []
            for seq, rdata in sorted(
                (pl_info.get("rule") or {}).items(),
                key=lambda x: int(x[0]),
            ):
                rdata = rdata or {}
                rule = {"sequence": int(seq)}
                if rdata.get("action"):
                    rule["action"] = rdata["action"]
                if rdata.get("prefix"):
                    rule["prefix"] = rdata["prefix"]
                if rdata.get("ge") is not None:
                    rule["ge"] = int(rdata["ge"])
                if rdata.get("le") is not None:
                    rule["le"] = int(rdata["le"])
                if rdata.get("description"):
                    rule["description"] = rdata["description"]
                rules.append(rule)

            if rules:
                entry["entries"] = rules
            pls.append(entry)

        if pls:
            result.append({"afi": afi, "prefix_lists": pls})

    return result


def _normalize(config):
    result = {"ipv4": {}, "ipv6": {}}
    for entry in config or []:
        afi = entry.get("afi")
        if afi not in result:
            continue
        for pl in entry.get("prefix_lists") or []:
            name = pl["name"]
            rules = {}
            for r in pl.get("entries") or []:
                seq = r["sequence"]
                rules[seq] = {k: v for k, v in r.items() if k != "sequence" and v is not None}
            result[afi][name] = {
                "description": pl.get("description"),
                "rules": rules,
            }
    return result


def _rule_cmds(base, seq, want_rule, have_rules, state):
    cmds = []
    rbase = base + ["rule", str(seq)]

    if seq not in (have_rules or {}):
        for field, api_key in [
            ("action", "action"),
            ("prefix", "prefix"),
            ("description", "description"),
        ]:
            if want_rule.get(field):
                cmds.append(("set", rbase + [api_key, want_rule[field]]))
        if want_rule.get("ge") is not None:
            cmds.append(("set", rbase + ["ge", str(want_rule["ge"])]))
        if want_rule.get("le") is not None:
            cmds.append(("set", rbase + ["le", str(want_rule["le"])]))
    else:
        h = have_rules[seq]
        for field, api_key in [
            ("action", "action"),
            ("prefix", "prefix"),
            ("description", "description"),
        ]:
            if want_rule.get(field) and want_rule[field] != h.get(field):
                cmds.append(("set", rbase + [api_key, want_rule[field]]))
        for field in ("ge", "le"):
            if want_rule.get(field) is not None and want_rule[field] != h.get(field):
                cmds.append(("set", rbase + [field, str(want_rule[field])]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []

    if state == "deleted":
        if not config:
            for afi, api_key in _PL_KEY.items():
                if any(e.get("afi") == afi for e in have_raw):
                    cmds.append(("delete", ["policy", api_key]))
        else:
            for entry in config:
                afi = entry["afi"]
                api_key = _PL_KEY[afi]
                for pl in entry.get("prefix_lists") or []:
                    cmds.append(("delete", ["policy", api_key, pl["name"]]))
        return cmds

    want = _normalize(config)
    have = _normalize(have_raw)

    for afi, api_key in _PL_KEY.items():
        want_afi = want.get(afi, {})
        have_afi = have.get(afi, {})

        if state == "overridden":
            for pl_name in set(have_afi) - set(want_afi):
                cmds.append(("delete", ["policy", api_key, pl_name]))

        for pl_name, want_pl in want_afi.items():
            have_pl = have_afi.get(pl_name, {})
            base = ["policy", api_key, pl_name]
            want_rules = want_pl.get("rules", {})
            have_rules = have_pl.get("rules", {})

            if state == "replaced" and pl_name in have_afi:
                # Only delete and rebuild if something actually differs
                want_desc = want_pl.get("description")
                have_desc = have_pl.get("description")
                extra_seqs = set(have_rules.keys()) - set(want_rules.keys())
                test_cmds = []
                for seq, want_rule in want_rules.items():
                    test_cmds += _rule_cmds(base, seq, want_rule, have_rules, state)
                if test_cmds or extra_seqs or want_desc != have_desc:
                    cmds.append(("delete", ["policy", api_key, pl_name]))
                    have_pl = {}
                    have_rules = {}
                else:
                    continue  # already matches — idempotent

            # Description
            if want_pl.get("description") and want_pl["description"] != have_pl.get("description"):
                cmds.append(("set", base + ["description", want_pl["description"]]))

            # Rules
            for seq, want_rule in want_rules.items():
                cmds += _rule_cmds(base, seq, want_rule, have_rules, state)

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
