#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_l3_interfaces
short_description: Manage L3 interface configuration on VyOS devices via REST API.
description:
  - Manages IPv4 and IPv6 address configuration on VyOS interfaces using the
    HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_l3_interfaces) but uses the HTTP API instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of L3 interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Full name of the interface, e.g. eth0, lo.
        type: str
        required: true
      ipv4:
        description: List of IPv4 addresses of the interface.
        type: list
        elements: dict
        suboptions:
          address:
            description:
              - IPv4 address in CIDR notation or C(dhcp).
            type: str
      ipv6:
        description: List of IPv6 addresses of the interface.
        type: list
        elements: dict
        suboptions:
          address:
            description:
              - IPv6 address in CIDR notation, C(dhcpv6), or C(auto-config).
            type: str
      vifs:
        description: List of virtual sub-interfaces (VLANs).
        type: list
        elements: dict
        suboptions:
          vlan_id:
            description: VLAN identifier.
            type: int
            required: true
          ipv4:
            description: List of IPv4 addresses of the VIF.
            type: list
            elements: dict
            suboptions:
              address:
                description: IPv4 address in CIDR notation or C(dhcp).
                type: str
          ipv6:
            description: List of IPv6 addresses of the VIF.
            type: list
            elements: dict
            suboptions:
              address:
                description: IPv6 address in CIDR notation, C(dhcpv6), or C(auto-config).
                type: str
  running_config:
    description: Used only with state C(parsed).
    type: str
  state:
    description:
      - C(merged) - Add addresses without removing existing ones.
      - C(replaced) - Replace addresses for listed interfaces.
      - C(overridden) - Replace addresses for all interfaces.
      - C(deleted) - Remove listed or all interface addresses.
      - C(gathered) - Read interface addresses from device without changes.
      - C(rendered) - Return commands for provided config without connecting.
      - C(parsed) - Parse running_config into structured data.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered, rendered, parsed]
    default: merged
seealso:
  - module: vyos.vyos.vyos_l3_interfaces
  - module: vyos.rest.vyos_interfaces
"""

EXAMPLES = r"""
- name: Merge L3 interface configuration
  vyos.rest.vyos_l3_interfaces:
    config:
      - name: eth0
        ipv4:
          - address: 192.0.2.1/24
          - address: dhcp
      - name: lo
        ipv4:
          - address: 10.0.0.1/32
        ipv6:
          - address: 2001:db8::1/128
    state: merged

- name: Add VLAN subinterface addresses
  vyos.rest.vyos_l3_interfaces:
    config:
      - name: eth0
        vifs:
          - vlan_id: 100
            ipv4:
              - address: 192.0.2.100/24
    state: merged

- name: Delete all interface addresses
  vyos.rest.vyos_l3_interfaces:
    state: deleted

- name: Gather current L3 interface configuration
  vyos.rest.vyos_l3_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: L3 interface configuration before this module ran.
  returned: always
  type: list
after:
  description: L3 interface configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current L3 interface configuration as structured data.
  returned: when state is gathered
  type: list
rendered:
  description: Commands for the provided config (state=rendered).
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


_IFACE_TYPE = {
    "eth": "ethernet",
    "bond": "bonding",
    "lo": "loopback",
    "tun": "tunnel",
    "wg": "wireguard",
    "vti": "vti",
    "dum": "dummy",
    "vtun": "openvpn",
    "br": "bridge",
}


def _iface_type(name):
    for prefix, itype in _IFACE_TYPE.items():
        if name.startswith(prefix):
            return itype
    return "ethernet"


def _iface_base(name):
    return ["interfaces", _iface_type(name), name]


def _addr_list(raw):
    """Normalize address field — string or list → sorted list."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return sorted(raw)
    return []


def _split_addresses(addresses):
    """Split address list into ipv4 and ipv6 lists."""
    ipv4 = []
    ipv6 = []
    for addr in addresses:
        if addr in ("dhcp", "dhcpv6"):
            if addr == "dhcp":
                ipv4.append(addr)
            else:
                ipv6.append(addr)
        elif ":" in addr:
            ipv6.append(addr)
        else:
            ipv4.append(addr)
    return sorted(ipv4), sorted(ipv6)


def _parse_iface(name, idata):
    """Parse raw API interface data into argspec format."""
    idata = idata or {}
    entry = {"name": name}

    addrs = _addr_list(idata.get("address"))
    if addrs:
        ipv4, ipv6 = _split_addresses(addrs)
        if ipv4:
            entry["ipv4"] = [{"address": a} for a in ipv4]
        if ipv6:
            entry["ipv6"] = [{"address": a} for a in ipv6]

    vif_data = idata.get("vif") or {}
    if isinstance(vif_data, dict) and vif_data:
        vifs = []
        for vlan_id, vdata in sorted(vif_data.items(), key=lambda x: int(x[0])):
            vdata = vdata or {}
            vif = {"vlan_id": int(vlan_id)}
            vaddrs = _addr_list(vdata.get("address"))
            if vaddrs:
                vipv4, vipv6 = _split_addresses(vaddrs)
                if vipv4:
                    vif["ipv4"] = [{"address": a} for a in vipv4]
                if vipv6:
                    vif["ipv6"] = [{"address": a} for a in vipv6]
            vifs.append(vif)
        if vifs:
            entry["vifs"] = vifs

    return entry


def get_running_config(vyos):
    raw = vyos.get_config(["interfaces"])
    if not raw or not isinstance(raw, dict):
        return []

    result = []
    for itype, ifaces in sorted(raw.items()):
        if not isinstance(ifaces, dict):
            continue
        for iname, idata in sorted(ifaces.items()):
            entry = _parse_iface(iname, idata)
            # only include if there's at least one address or vif
            if entry.get("ipv4") or entry.get("ipv6") or entry.get("vifs"):
                result.append(entry)

    return result


def _normalize(config):
    """Convert argspec list to dict keyed by interface name."""
    result = {}
    for entry in config or []:
        name = entry["name"]
        ipv4 = sorted([a["address"] for a in (entry.get("ipv4") or [])])
        ipv6 = sorted([a["address"] for a in (entry.get("ipv6") or [])])
        vifs = {}
        for vif in entry.get("vifs") or []:
            vid = vif["vlan_id"]
            vipv4 = sorted([a["address"] for a in (vif.get("ipv4") or [])])
            vipv6 = sorted([a["address"] for a in (vif.get("ipv6") or [])])
            vifs[vid] = {"ipv4": vipv4, "ipv6": vipv6}
        result[name] = {"ipv4": ipv4, "ipv6": ipv6, "vifs": vifs}
    return result


def _addr_cmds(base, want_addrs, have_addrs, state):
    """Generate set/delete commands for address lists."""
    cmds = []
    want_set = set(want_addrs)
    have_set = set(have_addrs)

    for addr in want_set - have_set:
        cmds.append(("set", base + ["address", addr]))

    if state in ("replaced", "deleted", "overridden"):
        for addr in have_set - want_set:
            cmds.append(("delete", base + ["address", addr]))

    return cmds


def _vif_cmds(iface_base, want_vifs, have_vifs, state):
    """Generate commands for VIF subinterfaces."""
    cmds = []

    if state in ("replaced", "overridden"):
        for vid in set(have_vifs) - set(want_vifs):
            cmds.append(("delete", iface_base + ["vif", str(vid)]))

    for vid, want_vif in want_vifs.items():
        have_vif = have_vifs.get(vid, {"ipv4": [], "ipv6": []})
        vif_base = iface_base + ["vif", str(vid)]
        cmds += _addr_cmds(vif_base, want_vif["ipv4"], have_vif["ipv4"], state)
        cmds += _addr_cmds(vif_base, want_vif["ipv6"], have_vif["ipv6"], state)

    return cmds


def build_commands(config, have_raw, state):
    cmds = []
    have_map = _normalize(have_raw)

    if state == "deleted":
        if not config:
            for name, have in have_map.items():
                base = _iface_base(name)
                for addr in have["ipv4"] + have["ipv6"]:
                    cmds.append(("delete", base + ["address", addr]))
                for vid in have["vifs"]:
                    cmds.append(("delete", base + ["vif", str(vid)]))
        else:
            want_map = _normalize(config)
            for name, want in want_map.items():
                have = have_map.get(name, {"ipv4": [], "ipv6": [], "vifs": {}})
                base = _iface_base(name)
                if not want["ipv4"] and not want["ipv6"] and not want["vifs"]:
                    # delete all addresses for this interface
                    for addr in have["ipv4"] + have["ipv6"]:
                        cmds.append(("delete", base + ["address", addr]))
                    for vid in have["vifs"]:
                        cmds.append(("delete", base + ["vif", str(vid)]))
                else:
                    for addr in want["ipv4"] + want["ipv6"]:
                        if addr in have["ipv4"] + have["ipv6"]:
                            cmds.append(("delete", base + ["address", addr]))
                    for vid in want["vifs"]:
                        if vid in have["vifs"]:
                            cmds.append(("delete", base + ["vif", str(vid)]))
        return cmds

    want_map = _normalize(config)

    if state == "overridden":
        for name in set(have_map) - set(want_map):
            have = have_map[name]
            base = _iface_base(name)
            for addr in have["ipv4"] + have["ipv6"]:
                cmds.append(("delete", base + ["address", addr]))
            for vid in have["vifs"]:
                cmds.append(("delete", base + ["vif", str(vid)]))

    for name, want in want_map.items():
        have = have_map.get(name, {"ipv4": [], "ipv6": [], "vifs": {}})
        base = _iface_base(name)
        cmds += _addr_cmds(base, want["ipv4"], have["ipv4"], state)
        cmds += _addr_cmds(base, want["ipv6"], have["ipv6"], state)
        cmds += _vif_cmds(base, want["vifs"], have["vifs"], state)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            ipv4=dict(
                type="list",
                elements="dict",
                options=dict(address=dict(type="str")),
            ),
            ipv6=dict(
                type="list",
                elements="dict",
                options=dict(address=dict(type="str")),
            ),
            vifs=dict(
                type="list",
                elements="dict",
                options=dict(
                    vlan_id=dict(type="int", required=True),
                    ipv4=dict(
                        type="list",
                        elements="dict",
                        options=dict(address=dict(type="str")),
                    ),
                    ipv6=dict(
                        type="list",
                        elements="dict",
                        options=dict(address=dict(type="str")),
                    ),
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
        # parsed is offline — just return empty for now
        module.exit_json(parsed=[])

    if state == "rendered":
        # build commands without connecting
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
