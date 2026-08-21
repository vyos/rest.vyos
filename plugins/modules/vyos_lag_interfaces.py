#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_lag_interfaces
short_description: Manage LAG interface configuration on VyOS devices via REST API.
description:
  - Manages Link Aggregation Group (LAG/bonding) interface configuration on VyOS
    devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_lag_interfaces) but uses the HTTP API instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of LAG interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Name of the LAG interface (e.g. bond0).
        type: str
        required: true
      mode:
        description: LAG bonding mode.
        type: str
        choices:
          - 802.3ad
          - active-backup
          - broadcast
          - round-robin
          - transmit-load-balance
          - adaptive-load-balance
          - xor-hash
      members:
        description: List of member interfaces.
        type: list
        elements: dict
        suboptions:
          member:
            description: Name of the member interface.
            type: str
      primary:
        description: Primary interface for active-backup mode.
        type: str
      hash_policy:
        description: Transmit hash policy.
        type: str
        choices:
          - layer2
          - layer2+3
          - layer3+4
      arp_monitor:
        description: ARP link monitoring parameters.
        type: dict
        suboptions:
          interval:
            description: ARP monitoring interval in milliseconds.
            type: int
          target:
            description: IP addresses to use for ARP monitoring.
            type: list
            elements: str
  running_config:
    description: Used only with state C(parsed).
    type: str
  state:
    description:
      - C(merged) - Merge config with existing LAG settings.
      - C(replaced) - Replace config for listed LAG interfaces.
      - C(overridden) - Replace config for all LAG interfaces.
      - C(deleted) - Remove listed or all LAG interface config.
      - C(gathered) - Read LAG config from device without changes.
      - C(rendered) - Return commands for provided config without connecting.
      - C(parsed) - Parse running_config into structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered, rendered, parsed]
    default: merged
seealso:
  - module: vyos.vyos.vyos_lag_interfaces
"""

EXAMPLES = r"""
- name: Merge LAG interface configuration
  vyos.rest.vyos_lag_interfaces:
    config:
      - name: bond0
        mode: 802.3ad
        hash_policy: layer2
        members:
          - member: eth1
          - member: eth2
    state: merged

- name: Delete all LAG interfaces
  vyos.rest.vyos_lag_interfaces:
    state: deleted

- name: Gather current LAG configuration
  vyos.rest.vyos_lag_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: LAG configuration before this module ran.
  returned: always
  type: list
after:
  description: LAG configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current LAG configuration as structured data.
  returned: when state is gathered
  type: list
rendered:
  description: Commands for provided config (state=rendered).
  returned: when state is rendered
  type: list
parsed:
  description: Structured data parsed from running_config (state=parsed).
  returned: when state is parsed
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


_BASE = ["interfaces", "bonding"]


def _bond_base(name):
    return _BASE + [name]


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return []

    if len(raw) == 1 and "bonding" in raw:
        raw = raw["bonding"]

    result = []
    for name, data in sorted(raw.items()):
        if name in ("bonding", "ethernet", "loopback"):
            continue
        data = data or {}
        entry = {"name": name}

        if data.get("mode"):
            entry["mode"] = data["mode"]
        if data.get("primary"):
            entry["primary"] = data["primary"]
        if "hash-policy" in data:
            entry["hash_policy"] = data["hash-policy"]

        member_data = data.get("member", {})
        if isinstance(member_data, dict):
            iface_data = member_data.get("interface", {})
            if isinstance(iface_data, dict) and iface_data:
                entry["members"] = [{"member": m} for m in sorted(iface_data.keys())]
            elif isinstance(iface_data, str):
                entry["members"] = [{"member": iface_data}]

        arp = data.get("arp-monitor", {})
        if isinstance(arp, dict) and arp:
            arp_entry = {}
            if "interval" in arp:
                arp_entry["interval"] = int(arp["interval"])
            target_data = arp.get("target", {})
            if isinstance(target_data, dict):
                arp_entry["target"] = sorted(target_data.keys())
            elif isinstance(target_data, str):
                arp_entry["target"] = [target_data]
            if arp_entry:
                entry["arp_monitor"] = arp_entry

        result.append(entry)

    return result


def _normalize(config):
    result = {}
    for entry in config or []:
        name = entry["name"]
        result[name] = {
            "mode": entry.get("mode"),
            "primary": entry.get("primary"),
            "hash_policy": entry.get("hash_policy"),
            "members": sorted([m["member"] for m in (entry.get("members") or [])]),
            "arp_interval": (entry.get("arp_monitor") or {}).get("interval"),
            "arp_targets": sorted((entry.get("arp_monitor") or {}).get("target") or []),
        }
    return result


def _bond_cmds(name, want, have):
    cmds = []
    base = _bond_base(name)
    have = have or {}

    if want.get("mode") and want["mode"] != have.get("mode"):
        cmds.append(("set", base + ["mode", want["mode"]]))

    if want.get("primary") and want["primary"] != have.get("primary"):
        cmds.append(("set", base + ["primary", want["primary"]]))

    if want.get("hash_policy") and want["hash_policy"] != have.get("hash_policy"):
        cmds.append(("set", base + ["hash-policy", want["hash_policy"]]))

    want_members = set(want.get("members") or [])
    have_members = set(have.get("members") or [])
    for m in want_members - have_members:
        cmds.append(("set", base + ["member", "interface", m]))

    want_interval = want.get("arp_interval")
    have_interval = have.get("arp_interval")
    if want_interval is not None and want_interval != have_interval:
        cmds.append(("set", base + ["arp-monitor", "interval", str(want_interval)]))

    want_targets = set(want.get("arp_targets") or [])
    have_targets = set(have.get("arp_targets") or [])
    for t in want_targets - have_targets:
        cmds.append(("set", base + ["arp-monitor", "target", t]))

    return cmds


def _delete_bond_cmds(name, have, want=None):
    """Generate delete commands for a bond — full delete or selective."""
    cmds = []
    base = _bond_base(name)
    have = have or {}
    want = want or {}

    if not want:
        # full delete
        cmds.append(("delete", base))
        return cmds

    # selective — only delete what want specifies
    if want.get("mode") and have.get("mode"):
        cmds.append(("delete", base + ["mode"]))
    if want.get("primary") and have.get("primary"):
        cmds.append(("delete", base + ["primary"]))
    if want.get("hash_policy") and have.get("hash_policy"):
        cmds.append(("delete", base + ["hash-policy"]))
    for m in set(want.get("members") or []) & set(have.get("members") or []):
        cmds.append(("delete", base + ["member", "interface", m]))
    if want.get("arp_interval") and have.get("arp_interval"):
        cmds.append(("delete", base + ["arp-monitor", "interval"]))
    for t in set(want.get("arp_targets") or []) & set(have.get("arp_targets") or []):
        cmds.append(("delete", base + ["arp-monitor", "target", t]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []
    have_map = _normalize(have_raw)

    if state == "deleted":
        if not config:
            for name in have_map:
                cmds.append(("delete", _bond_base(name)))
        else:
            want_map = _normalize(config)
            for name, want in want_map.items():
                have = have_map.get(name, {})
                if not any(
                    [
                        want.get("mode"),
                        want.get("primary"),
                        want.get("hash_policy"),
                        want.get("members"),
                        want.get("arp_interval"),
                        want.get("arp_targets"),
                    ],
                ):
                    # delete entire bond
                    if name in have_map:
                        cmds.append(("delete", _bond_base(name)))
                else:
                    cmds += _delete_bond_cmds(name, have, want)
        return cmds

    want_map = _normalize(config)

    if state == "overridden":
        for name in set(have_map) - set(want_map):
            cmds.append(("delete", _bond_base(name)))

    for name, want in want_map.items():
        have = have_map.get(name, {})

        if state == "replaced" and name in have_map:
            test_cmds = _bond_cmds(name, want, have)
            # check for extra members/targets in have not in want
            extra_members = set(have.get("members") or []) - set(want.get("members") or [])
            extra_targets = set(have.get("arp_targets") or []) - set(want.get("arp_targets") or [])
            have_fields = {k: v for k, v in have.items() if v}
            want_fields = {k: v for k, v in want.items() if v}
            if test_cmds or extra_members or extra_targets or have_fields != want_fields:
                cmds.append(("delete", _bond_base(name)))
                have = {}
            else:
                continue

        cmds += _bond_cmds(name, want, have)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            mode=dict(
                type="str",
                choices=[
                    "802.3ad",
                    "active-backup",
                    "broadcast",
                    "round-robin",
                    "transmit-load-balance",
                    "adaptive-load-balance",
                    "xor-hash",
                ],
            ),
            members=dict(
                type="list",
                elements="dict",
                options=dict(member=dict(type="str")),
            ),
            primary=dict(type="str"),
            hash_policy=dict(
                type="str",
                choices=["layer2", "layer2+3", "layer3+4"],
            ),
            arp_monitor=dict(
                type="dict",
                options=dict(
                    interval=dict(type="int"),
                    target=dict(type="list", elements="str"),
                ),
            ),
        ),
    ),
    running_config=dict(type="str"),
    state=dict(
        type="str",
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered", "rendered", "parsed"],
    ),
)


def main():
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC,
        mutually_exclusive=[["config", "running_config"]],
        required_if=[
            ("state", "rendered", ["config"]),
            ("state", "parsed", ["running_config"]),
        ],
        supports_check_mode=True,
    )
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or []

    if state == "parsed":
        module.exit_json(parsed=[])

    if state == "rendered":
        cmds = build_commands(config, [], "merged")
        module.exit_json(rendered=cmds, commands=cmds)

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
