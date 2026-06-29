#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospf_interfaces
short_description: Manage OSPF interface configuration on VyOS devices using REST API
description:
  - Manages OSPF and OSPFv3 interface configuration on VyOS devices via the REST API.
  - IPv4 OSPF maps to C(protocols ospf interface).
  - IPv6 OSPFv3 maps to C(protocols ospfv3 interface).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of OSPF interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Interface name.
        type: str
        required: true
      address_family:
        description: OSPF settings per address family.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family identifier.
            type: str
            choices: [ipv4, ipv6]
            required: true
          authentication:
            description: Authentication settings (IPv4 only).
            type: dict
            suboptions:
              plaintext_password:
                description: Plaintext password.
                type: str
              md5_key:
                description: MD5 authentication key.
                type: dict
                suboptions:
                  key_id:
                    description: MD5 key ID.
                    type: int
                  key:
                    description: MD5 key string.
                    type: str
          bandwidth:
            description: Interface bandwidth in kbps (IPv4 only).
            type: int
          cost:
            description: Interface cost metric.
            type: int
          dead_interval:
            description: Dead router detection interval in seconds.
            type: int
          hello_interval:
            description: Hello packet interval in seconds.
            type: int
          ifmtu:
            description: Interface MTU (IPv6 only).
            type: int
          instance:
            description: OSPFv3 instance ID (IPv6 only).
            type: str
          mtu_ignore:
            description: Disable MTU check (IPv4 only).
            type: bool
          network:
            description: Network type (IPv4 only).
            type: str
            choices: [broadcast, non-broadcast, point-to-multipoint, point-to-point]
          passive:
            description: Disable adjacency formation (IPv6 only).
            type: bool
          priority:
            description: Interface priority.
            type: int
          retransmit_interval:
            description: LSA retransmit interval in seconds.
            type: int
          transmit_delay:
            description: LSA transmit delay in seconds.
            type: int
  state:
    description:
      - Desired state of the OSPF interface configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces per-interface OSPF config for named interfaces.
      - C(overridden) replaces all OSPF interface config.
      - C(deleted) removes OSPF interface config.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Merge OSPF interface configuration
  vyos.rest.vyos_ospf_interfaces:
    config:
      - name: eth1
        address_family:
          - afi: ipv4
            cost: 100
            transmit_delay: 50
            priority: 26
          - afi: ipv6
            dead_interval: 39
            passive: true
    state: merged

- name: Delete OSPF interface configuration
  vyos.rest.vyos_ospf_interfaces:
    config:
      - name: eth1
    state: deleted

- name: Delete all OSPF interface configuration
  vyos.rest.vyos_ospf_interfaces:
    state: deleted

- name: Gather current OSPF interface configuration
  vyos.rest.vyos_ospf_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: OSPF interface configuration before this module ran.
  returned: always
  type: list
after:
  description: OSPF interface configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current OSPF interface configuration as structured data.
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


_BASE4 = ["protocols", "ospf", "interface"]
_BASE6 = ["protocols", "ospfv3", "interface"]

# IPv4 scalar fields: argspec_key -> api_key
_IPV4_SCALARS = {
    "bandwidth": "bandwidth",
    "cost": "cost",
    "dead_interval": "dead-interval",
    "hello_interval": "hello-interval",
    "mtu_ignore": "mtu-ignore",
    "network": "network",
    "priority": "priority",
    "retransmit_interval": "retransmit-interval",
    "transmit_delay": "transmit-delay",
}

# IPv6 scalar fields
_IPV6_SCALARS = {
    "cost": "cost",
    "dead_interval": "dead-interval",
    "hello_interval": "hello-interval",
    "ifmtu": "ifmtu",
    "instance": "instance-id",
    "passive": "passive",
    "priority": "priority",
    "retransmit_interval": "retransmit-interval",
    "transmit_delay": "transmit-delay",
}

# bool fields that use presence (no value)
_IPV4_BOOL_PRESENCE = {"mtu_ignore"}
_IPV6_BOOL_PRESENCE = {"passive"}


def _parse_ipv4_iface(data):
    af = {"afi": "ipv4"}
    data = data or {}
    for arg_key, api_key in _IPV4_SCALARS.items():
        if api_key in data:
            if arg_key in _IPV4_BOOL_PRESENCE:
                af[arg_key] = True
            else:
                val = data[api_key]
                if arg_key in (
                    "bandwidth",
                    "cost",
                    "dead_interval",
                    "hello_interval",
                    "priority",
                    "retransmit_interval",
                    "transmit_delay",
                ):
                    try:
                        af[arg_key] = int(val)
                    except (TypeError, ValueError):
                        af[arg_key] = val
                else:
                    af[arg_key] = val
    # authentication
    auth = data.get("authentication", {})
    if auth:
        auth_entry = {}
        if "plaintext-password" in auth:
            auth_entry["plaintext_password"] = auth["plaintext-password"]
        md5 = auth.get("md5", {})
        if md5:
            key_id_data = md5.get("key-id", {})
            if key_id_data:
                key_id = list(key_id_data.keys())[0]
                md5_key = key_id_data[key_id].get("md5-key")
                auth_entry["md5_key"] = {"key_id": int(key_id), "key": md5_key}
        if auth_entry:
            af["authentication"] = auth_entry
    return af


def _parse_ipv6_iface(data):
    af = {"afi": "ipv6"}
    data = data or {}
    for arg_key, api_key in _IPV6_SCALARS.items():
        if api_key in data:
            if arg_key in _IPV6_BOOL_PRESENCE:
                af[arg_key] = True
            else:
                val = data[api_key]
                if arg_key in (
                    "cost",
                    "dead_interval",
                    "hello_interval",
                    "ifmtu",
                    "priority",
                    "retransmit_interval",
                    "transmit_delay",
                ):
                    try:
                        af[arg_key] = int(val)
                    except (TypeError, ValueError):
                        af[arg_key] = val
                else:
                    af[arg_key] = val
    return af


def get_running_config(vyos):
    raw4 = vyos.get_config(_BASE4) or {}
    raw4 = raw4.get("interface", raw4)
    raw6 = vyos.get_config(_BASE6) or {}
    raw6 = raw6.get("interface", raw6)

    ifaces = {}

    for iface_name, data in raw4.items():
        if iface_name not in ifaces:
            ifaces[iface_name] = {"name": iface_name, "address_family": []}
        af = _parse_ipv4_iface(data)
        if len(af) > 1:  # more than just afi key
            ifaces[iface_name]["address_family"].append(af)

    for iface_name, data in raw6.items():
        if iface_name not in ifaces:
            ifaces[iface_name] = {"name": iface_name, "address_family": []}
        af = _parse_ipv6_iface(data)
        if len(af) > 1:
            ifaces[iface_name]["address_family"].append(af)

    result = sorted(ifaces.values(), key=lambda x: x["name"])
    # Remove empty address_family lists
    for iface in result:
        if not iface["address_family"]:
            del iface["address_family"]
    return result


def _ipv4_af_cmds(iface_name, af, have_af, op="set"):
    cmds = []
    base = _BASE4 + [iface_name]
    have_af = have_af or {}

    for arg_key, api_key in _IPV4_SCALARS.items():
        want_val = af.get(arg_key)
        have_val = have_af.get(arg_key)
        if want_val is not None and want_val != have_val:
            if arg_key in _IPV4_BOOL_PRESENCE:
                cmds.append(("set", base + [api_key]))
            else:
                cmds.append(("set", base + [api_key, str(want_val)]))
        elif op == "replace" and have_val is not None and want_val != have_val:
            cmds.append(("delete", base + [api_key]))

    # authentication
    want_auth = af.get("authentication") or {}
    have_auth = have_af.get("authentication") or {}
    if want_auth.get("plaintext_password") and want_auth["plaintext_password"] != have_auth.get(
        "plaintext_password",
    ):
        cmds.append(
            (
                "set",
                base
                + [
                    "authentication",
                    "plaintext-password",
                    want_auth["plaintext_password"],
                ],
            ),
        )
    md5 = want_auth.get("md5_key") or {}
    if md5 and md5 != have_auth.get("md5_key"):
        cmds.append(
            (
                "set",
                base
                + [
                    "authentication",
                    "md5",
                    "key-id",
                    str(md5["key_id"]),
                    "md5-key",
                    md5["key"],
                ],
            ),
        )

    return cmds


def _ipv6_af_cmds(iface_name, af, have_af, op="set"):
    cmds = []
    base = _BASE6 + [iface_name]
    have_af = have_af or {}

    for arg_key, api_key in _IPV6_SCALARS.items():
        want_val = af.get(arg_key)
        have_val = have_af.get(arg_key)
        if want_val is not None and want_val != have_val:
            if arg_key in _IPV6_BOOL_PRESENCE:
                cmds.append(("set", base + [api_key]))
            else:
                cmds.append(("set", base + [api_key, str(want_val)]))
        elif op == "replace" and have_val is not None and want_val != have_val:
            cmds.append(("delete", base + [api_key]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []
    have_map = {e["name"]: e for e in have_raw}

    if state == "deleted":
        if not config:
            # delete all
            if have_raw:
                for iface in have_raw:
                    name = iface["name"]
                    afs = {af["afi"] for af in iface.get("address_family", [])}
                    if "ipv4" in afs:
                        cmds.append(("delete", _BASE4 + [name]))
                    if "ipv6" in afs:
                        cmds.append(("delete", _BASE6 + [name]))
        else:
            for entry in config:
                name = entry["name"]
                if name in have_map:
                    have_afs = {af["afi"] for af in have_map[name].get("address_family", [])}
                    want_afis = {af["afi"] for af in (entry.get("address_family") or [])}
                    if not want_afis:
                        # delete all AFIs for this interface
                        if "ipv4" in have_afs:
                            cmds.append(("delete", _BASE4 + [name]))
                        if "ipv6" in have_afs:
                            cmds.append(("delete", _BASE6 + [name]))
                    else:
                        if "ipv4" in want_afis and "ipv4" in have_afs:
                            cmds.append(("delete", _BASE4 + [name]))
                        if "ipv6" in want_afis and "ipv6" in have_afs:
                            cmds.append(("delete", _BASE6 + [name]))
        return cmds

    if state == "overridden":
        want_names = {e["name"] for e in config}
        for name, have_iface in have_map.items():
            if name not in want_names:
                have_afs = {af["afi"] for af in have_iface.get("address_family", [])}
                if "ipv4" in have_afs:
                    cmds.append(("delete", _BASE4 + [name]))
                if "ipv6" in have_afs:
                    cmds.append(("delete", _BASE6 + [name]))

    for entry in config:
        name = entry["name"]
        have_iface = have_map.get(name, {})
        have_af_map = {af["afi"]: af for af in have_iface.get("address_family", [])}

        for af in entry.get("address_family", []):
            afi = af["afi"]
            have_af = have_af_map.get(afi, {})

            if state == "replaced":
                af_clean = {k: v for k, v in af.items() if v is not None}
                if have_af and have_af != af_clean:
                    if afi == "ipv4":
                        cmds.append(("delete", _BASE4 + [name]))
                        have_af = {}
                    else:
                        cmds.append(("delete", _BASE6 + [name]))
                        have_af = {}
                elif have_af == af_clean:
                    continue  # already matches — idempotent

            if afi == "ipv4":
                cmds += _ipv4_af_cmds(name, af, have_af)
            else:
                cmds += _ipv6_af_cmds(name, af, have_af)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            address_family=dict(
                type="list",
                elements="dict",
                options=dict(
                    afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
                    authentication=dict(
                        type="dict",
                        options=dict(
                            plaintext_password=dict(type="str", no_log=True),
                            md5_key=dict(
                                type="dict",
                                options=dict(
                                    key_id=dict(type="int"),
                                    key=dict(type="str", no_log=True),
                                ),
                            ),
                        ),
                    ),
                    bandwidth=dict(type="int"),
                    cost=dict(type="int"),
                    dead_interval=dict(type="int"),
                    hello_interval=dict(type="int"),
                    ifmtu=dict(type="int"),
                    instance=dict(type="str"),
                    mtu_ignore=dict(type="bool"),
                    network=dict(
                        type="str",
                        choices=[
                            "broadcast",
                            "non-broadcast",
                            "point-to-multipoint",
                            "point-to-point",
                        ],
                    ),
                    passive=dict(type="bool"),
                    priority=dict(type="int"),
                    retransmit_interval=dict(type="int"),
                    transmit_delay=dict(type="int"),
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
