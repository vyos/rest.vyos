#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_global
short_description: Manage global firewall configuration on VyOS devices using REST API
description:
  - Manages global firewall group configuration on VyOS devices via the REST API.
  - Covers address-groups, network-groups, port-groups, interface-groups,
    and IPv6 network-groups.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: Global firewall configuration.
    type: dict
    suboptions:
      group:
        description: Firewall groups.
        type: dict
        suboptions:
          address_group:
            description: IPv4 address groups.
            type: list
            elements: dict
            suboptions:
              name:
                description: Group name.
                type: str
                required: true
              description:
                description: Group description.
                type: str
              address:
                description: IP addresses or ranges in the group.
                type: list
                elements: str
          network_group:
            description: IPv4 network groups.
            type: list
            elements: dict
            suboptions:
              name:
                description: Group name.
                type: str
                required: true
              description:
                description: Group description.
                type: str
              network:
                description: Network prefixes in the group.
                type: list
                elements: str
          port_group:
            description: Port groups.
            type: list
            elements: dict
            suboptions:
              name:
                description: Group name.
                type: str
                required: true
              description:
                description: Group description.
                type: str
              port:
                description: Ports or port ranges in the group.
                type: list
                elements: str
          interface_group:
            description: Interface groups.
            type: list
            elements: dict
            suboptions:
              name:
                description: Group name.
                type: str
                required: true
              description:
                description: Group description.
                type: str
              interface:
                description: Interfaces in the group.
                type: list
                elements: str
          ipv6_network_group:
            description: IPv6 network groups.
            type: list
            elements: dict
            suboptions:
              name:
                description: Group name.
                type: str
                required: true
              description:
                description: Group description.
                type: str
              network:
                description: IPv6 network prefixes in the group.
                type: list
                elements: str
  state:
    description:
      - Desired state of the firewall global configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces the entire firewall global configuration.
      - C(deleted) removes firewall global configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Merge firewall global configuration
  vyos.rest.vyos_firewall_global:
    config:
      group:
        address_group:
          - name: SERVERS
            description: Web servers
            address:
              - 192.168.1.10
              - 192.168.1.11
        network_group:
          - name: LAN
            network:
              - 192.168.0.0/16
        port_group:
          - name: WEB-PORTS
            port:
              - "80"
              - "443"
        interface_group:
          - name: LAN-IFACES
            interface:
              - eth1
              - eth2
        ipv6_network_group:
          - name: IPV6-LAN
            network:
              - "2001:db8::/32"
    state: merged

- name: Delete all firewall global configuration
  vyos.rest.vyos_firewall_global:
    state: deleted

- name: Gather firewall global configuration
  vyos.rest.vyos_firewall_global:
    state: gathered
"""

RETURN = r"""
before:
  description: Firewall global configuration before this module ran.
  returned: always
  type: dict
after:
  description: Firewall global configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current firewall global configuration as structured data.
  returned: when state is gathered
  type: dict
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


_BASE = ["firewall", "group"]

# Map argspec key -> API key, value key
_GROUP_TYPES = {
    "address_group": ("address-group", "address"),
    "network_group": ("network-group", "network"),
    "port_group": ("port-group", "port"),
    "interface_group": ("interface-group", "interface"),
    "ipv6_network_group": ("ipv6-network-group", "network"),
}


def _parse_group_type(raw, val_key):
    """Parse a group dict from API raw data."""
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for name, data in sorted(raw.items()):
        entry = {"name": name}
        data = data or {}
        if data.get("description"):
            entry["description"] = data["description"]
        val = data.get(val_key)
        if val is not None:
            if isinstance(val, list):
                entry[val_key.replace("-", "_")] = val
            elif isinstance(val, str):
                entry[val_key.replace("-", "_")] = [val]
            elif isinstance(val, dict):
                entry[val_key.replace("-", "_")] = list(val.keys())
        result.append(entry)
    return result


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return {}
    result = {"group": {}}

    for arg_key, (api_key, val_key) in _GROUP_TYPES.items():
        groups = _parse_group_type(raw.get(api_key), val_key)
        if groups:
            result["group"][arg_key] = groups

    if not result["group"]:
        return {}
    return result


def _group_cmds(arg_key, groups, have_groups, state):
    cmds = []
    api_key, val_key = _GROUP_TYPES[arg_key]
    have_map = {g["name"]: g for g in (have_groups or [])}
    want_map = {g["name"]: g for g in (groups or [])}

    if state == "replaced":
        for name in set(have_map) - set(want_map):
            cmds.append(("delete", _BASE + [api_key, name]))

    for name, group in want_map.items():
        have_group = have_map.get(name, {})
        gbase = _BASE + [api_key, name]

        if group.get("description") and group["description"] != have_group.get("description"):
            cmds.append(("set", gbase + ["description", group["description"]]))

        # normalize val_key for argspec (underscores)
        arg_val_key = val_key.replace("-", "_")
        want_vals = set(group.get(arg_val_key) or [])
        have_vals = set(have_group.get(arg_val_key) or [])

        for val in want_vals - have_vals:
            cmds.append(("set", gbase + [val_key, val]))

        if state == "replaced":
            for val in have_vals - want_vals:
                cmds.append(("delete", gbase + [val_key, val]))

    return cmds


def build_commands(config, have, state):
    cmds = []

    if state == "deleted":
        if have:
            cmds.append(("delete", _BASE))
        return cmds

    if state == "replaced":
        # Check if anything differs
        would_set = build_commands(config, {}, "merged")
        have_set = build_commands(have, {}, "merged")
        if would_set == have_set:
            return []

    config = config or {}
    want_group = config.get("group") or {}
    have_group = have.get("group") or {}

    for arg_key in _GROUP_TYPES:
        want_groups = want_group.get(arg_key) or []
        have_groups = have_group.get(arg_key) or []
        if want_groups or (state == "replaced" and have_groups):
            cmds += _group_cmds(arg_key, want_groups, have_groups, state)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            group=dict(
                type="dict",
                options=dict(
                    address_group=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            description=dict(type="str"),
                            address=dict(type="list", elements="str"),
                        ),
                    ),
                    network_group=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            description=dict(type="str"),
                            network=dict(type="list", elements="str"),
                        ),
                    ),
                    port_group=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            description=dict(type="str"),
                            port=dict(type="list", elements="str"),
                        ),
                    ),
                    interface_group=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            description=dict(type="str"),
                            interface=dict(type="list", elements="str"),
                        ),
                    ),
                    ipv6_network_group=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            description=dict(type="str"),
                            network=dict(type="list", elements="str"),
                        ),
                    ),
                ),
            ),
        ),
    ),
    state=dict(
        default="merged",
        choices=["merged", "replaced", "deleted", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

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
