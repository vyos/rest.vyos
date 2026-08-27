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
  - >-
    A bonding interface's device path (C(interfaces bonding <name>)) is
    shared with M(vyos.rest.vyos_interfaces) (L2 attributes: description,
    mtu, vrf) and M(vyos.rest.vyos_l3_interfaces) (addresses) -- every
    command this module generates is scoped to exactly C(mode)/
    C(primary)/C(hash-policy)/C(member)/C(arp-monitor), never the bond's
    subtree as a whole, so it never touches those other modules' fields.
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
  state:
    description:
      - C(merged) - Merge config with existing LAG settings.
      - C(replaced) - Replace config for listed LAG interfaces.
      - C(overridden) - Replace config for all LAG interfaces.
      - C(deleted) - Remove listed or all LAG interface config.
      - C(gathered) - Read LAG config from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
seealso:
  - module: vyos.vyos.vyos_lag_interfaces
  - module: vyos.rest.vyos_interfaces
  - module: vyos.rest.vyos_l3_interfaces
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
    _snake_to_kebab,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    scope_to_spec,
    to_tag_dict,
)


_BASE = ["interfaces", "bonding"]


def _bond_base(name):
    return _BASE + [name]


def _bond_entry_to_device(rest):
    """Explicit allowlist -- confirmed critical given bond0's device
    path is shared with vyos_interfaces and vyos_l3_interfaces. Only
    mode/primary/hash_policy/members/arp_monitor are modeled here.

    members and arp_monitor.target are built as keyed-presence
    structures (name/address -> {}) separately from the simple scalar
    fields, and merged in without going through autoclean: confirmed
    real bug otherwise -- autoclean recursively drops nested
    empty-dict values, treating a presence-only leaf like
    {"eth1": {}} as "nothing to see here" and silently stripping it,
    when it's actually a meaningful member-interface reference. Their
    keys are opaque interface names/IP addresses needing no
    underscore-to-kebab conversion regardless.
    """
    simple = autoclean({k: v for k, v in rest.items() if k not in ("members", "arp_monitor")})
    device = {_snake_to_kebab(k): v for k, v in simple.items()}

    members = rest.get("members") or []
    member_names = [m.get("member") for m in members if m.get("member")]
    if member_names:
        device["member"] = {"interface": {m: {} for m in member_names}}

    arp = rest.get("arp_monitor") or {}
    arp_simple = autoclean({k: v for k, v in arp.items() if k != "target"})
    arp_device = {_snake_to_kebab(k): v for k, v in arp_simple.items()}
    targets = arp.get("target") or []
    if targets:
        arp_device["target"] = {t: {} for t in targets}
    if arp_device:
        device["arp-monitor"] = arp_device

    return device


def _bond_entry_from_device(data):
    """scope_to_spec derives the allowlist directly from this
    module's own argspec (mode/primary/hash_policy), so bond0's
    device path being shared with vyos_interfaces (description/mtu/
    vrf) and vyos_l3_interfaces (address) is never a leak risk --
    confirmed existing utility in module_utils/vyos.py for exactly
    this cross-module scope problem, used here instead of a second,
    manually-maintained field list.

    members and arp_monitor are excluded from that call and handled
    separately: "members" (argspec) doesn't match the device's actual
    key "member" (singular), and arp_monitor's nested target needs its
    own keyed-dict-to-list conversion that scope_to_spec (a top-level
    filter only) doesn't do.
    """
    scoped = scope_to_spec(data, _ENTRY_OPTIONS, exclude=("name", "members", "arp_monitor"))
    entry = from_device(scoped)

    iface_raw = (data.get("member") or {}).get("interface")
    if iface_raw:
        entry["members"] = [{"member": m} for m in sorted(to_tag_dict(iface_raw))]

    arp = data.get("arp-monitor") or {}
    arp_entry = {}
    if "interval" in arp:
        arp_entry["interval"] = int(arp["interval"])
    target_raw = arp.get("target")
    if target_raw:
        arp_entry["target"] = sorted(to_tag_dict(target_raw))
    if arp_entry:
        entry["arp_monitor"] = arp_entry

    return entry


def get_running_config(vyos):
    """VyOS's REST API collapses a single-child tag node to a plain
    string (or a list for multiple) -- confirmed as a real failure
    mode during vyos_ospf_interfaces's build. Normalizing through
    to_tag_dict unconditionally means callers always receive a
    genuine dict.

    The original module also defensively unwrapped a possible extra
    "bonding" wrapper key around the response -- kept here rather
    than dropped, since that defensive check was never independently
    disproven, matching the same wrapper-key pattern confirmed real
    elsewhere in this collection (e.g. vyos_route_maps).
    """
    raw = to_tag_dict(vyos.get_config(_BASE) or {})
    if isinstance(raw, dict) and len(raw) == 1 and "bonding" in raw:
        raw = to_tag_dict(raw["bonding"])
    return raw


def _device_to_argspec(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        entry = {"name": name}
        entry.update(_bond_entry_from_device(data or {}))
        result.append(entry)
    return result


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    have_list = _device_to_argspec(raw_have)
    have_by_name = {e["name"]: e for e in have_list}
    want_by_name = {e["name"]: e for e in config if e.get("name")}

    def _scoped_purge(name, have_entry):
        have_device = _bond_entry_to_device(
            {k: v for k, v in have_entry.items() if k != "name"},
        )
        return dict_op({}, have_device, _bond_base(name), op="purge")

    if state == "deleted":
        cmds = []
        if not config:
            for name, have_entry in have_by_name.items():
                cmds += _scoped_purge(name, have_entry)
            return cmds
        for entry in config:
            name = entry.get("name")
            if name and name in have_by_name:
                cmds += _scoped_purge(name, have_by_name[name])
        return cmds

    commands = []
    if state == "overridden":
        for name in set(have_by_name) - set(want_by_name):
            commands += _scoped_purge(name, have_by_name[name])

    for name, want_entry in want_by_name.items():
        have_entry = have_by_name.get(name, {})
        want_device = _bond_entry_to_device(
            {k: v for k, v in want_entry.items() if k != "name"},
        )
        have_device = _bond_entry_to_device(
            {k: v for k, v in have_entry.items() if k != "name"},
        )
        base = _bond_base(name)

        if state in ("replaced", "overridden"):
            commands += dict_op(want_device, have_device, base, op="purge")
        commands += dict_op(want_device, have_device, base, op="set")

    return commands


_MEMBER_OPTIONS = dict(member=dict(type="str"))

_ARP_MONITOR_OPTIONS = dict(
    interval=dict(type="int"),
    target=dict(type="list", elements="str"),
)

_ENTRY_OPTIONS = dict(
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
    members=dict(type="list", elements="dict", options=_MEMBER_OPTIONS),
    primary=dict(type="str"),
    hash_policy=dict(type="str", choices=["layer2", "layer2+3", "layer3+4"]),
    arp_monitor=dict(type="dict", options=_ARP_MONITOR_OPTIONS),
)

ARGUMENT_SPEC = dict(
    config=dict(type="list", elements="dict", options=_ENTRY_OPTIONS),
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
        cast_by_spec(entry, _ENTRY_OPTIONS)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have, after=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after_raw = get_running_config(vyos)
        after = _device_to_argspec(after_raw)
        for entry in after:
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
