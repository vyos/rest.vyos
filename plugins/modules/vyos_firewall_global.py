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


_BASE = ["firewall", "group"]

# argspec_key -> (device_key, member_key). A genuinely minimal, unavoidable
# mapping: VyOS's 5 group types have different kebab-case device names and
# different member-list field names (address/network/port/interface), none
# of which is a mechanical snake<->kebab transform of the other.
_GROUP_TYPES = {
    "address_group": ("address-group", "address"),
    "network_group": ("network-group", "network"),
    "port_group": ("port-group", "port"),
    "interface_group": ("interface-group", "interface"),
    "ipv6_network_group": ("ipv6-network-group", "network"),
}

# Each of the 5 device_keys above is itself a tag node (keyed by group
# name) that can collapse to a bare string for a single group with no
# other config. The member fields (address/network/port/interface) are
# NOT tag nodes -- confirmed against vyos-1x (leafNode with <multi/>) --
# they're plain multi-value leaves, so dict_op's own native list handling
# applies to them directly; no reshaping needed.
_TAG_KEYS = {device_key for device_key, _member_key in _GROUP_TYPES.values()}


def _group_to_device(g, member_key):
    entry = autoclean({k: v for k, v in g.items() if k not in ("name", member_key)})
    members = g.get(member_key)
    if members:
        entry[member_key] = [str(m) for m in members]
    return entry


def _groups_to_device(groups, member_key):
    return {g["name"]: _group_to_device(g, member_key) for g in groups or []}


def _want_to_device(config):
    group = (config or {}).get("group") or {}
    want = {}
    for arg_key, (device_key, member_key) in _GROUP_TYPES.items():
        groups = group.get(arg_key) or []
        if groups:
            want[device_key] = _groups_to_device(groups, member_key)
    return want


def _group_from_device(name, data, member_key):
    data = dict(data or {})
    members = data.pop(member_key, None)
    entry = {"name": name, **from_device(data)}
    if members is not None:
        member_list = [members] if isinstance(members, str) else members
        entry[member_key] = sorted(str(m) for m in member_list)
    return entry


def _groups_from_device(raw_groups, member_key):
    if not raw_groups or not isinstance(raw_groups, dict):
        return []
    return [_group_from_device(name, data, member_key) for name, data in sorted(raw_groups.items())]


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    group = {}
    for arg_key, (device_key, member_key) in _GROUP_TYPES.items():
        groups = _groups_from_device(raw.get(device_key), member_key)
        if groups:
            group[arg_key] = groups
    return {"group": group} if group else {}


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    want = _want_to_device(config)
    norm_have = normalize_have(raw_have, _TAG_KEYS)

    if state == "deleted":
        return [("delete", _BASE)] if raw_have else []

    commands = []
    if state == "replaced":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


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
