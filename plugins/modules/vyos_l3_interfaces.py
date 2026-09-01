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
  - >-
    L2 attributes (description, mtu, duplex, speed, vrf) and VIF
    presence/L2 attributes are owned by M(vyos.rest.vyos_interfaces), not
    this module -- confirmed by design: a VIF's device path is shared
    between the two modules, and this module's own commands only ever
    touch the C(address) leaf within it, never the VIF subtree as a whole
    or any of vyos_interfaces' own fields.
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
  state:
    description:
      - C(merged) - Add addresses without removing existing ones.
      - C(replaced) - Replace addresses for listed interfaces.
      - C(overridden) - Replace addresses for all interfaces.
      - C(deleted) - Remove listed or all interface addresses.
      - C(gathered) - Read interface addresses from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule, to_tag_dict


_BASE = ["interfaces"]

# Aligned with vyos_interfaces' own 11-type table -- confirmed
# inconsistent in the original (missing ppp/wlan here specifically),
# corrected for consistency between the two modules that share the
# same interface namespace.
_IFACE_TYPE_PREFIX = {
    "eth": "ethernet",
    "bond": "bonding",
    "lo": "loopback",
    "tun": "tunnel",
    "wg": "wireguard",
    "vti": "vti",
    "dum": "dummy",
    "vtun": "openvpn",
    "ppp": "pppoe",
    "wlan": "wireless",
    "br": "bridge",
}


def _guess_iface_type(name):
    for prefix, itype in _IFACE_TYPE_PREFIX.items():
        if name.startswith(prefix):
            return itype
    return "ethernet"


def _resolve_iface_type(name, raw_have):
    """Prefer the real type from the device's own raw response over a
    name-prefix guess -- only fall back to guessing for a brand-new
    interface that doesn't exist on the device yet. Same fix as
    vyos_interfaces' own confirmed bug: the original guessed
    unconditionally, even for interfaces the device already knows the
    real type of.
    """
    for itype, ifaces in (raw_have or {}).items():
        if isinstance(ifaces, dict) and name in ifaces:
            return itype
    return _guess_iface_type(name)


def _iface_base(name, raw_have):
    return _BASE + [_resolve_iface_type(name, raw_have), name]


def _addr_list(raw):
    """VyOS's address leaf collapses to a bare string for a single
    value, or a list for multiple -- confirmed device behavior,
    handled explicitly here since it's a plain multi-value leaf, not
    a tag-node (to_tag_dict doesn't apply)."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return sorted(raw)
    return []


def _split_addresses(addresses):
    ipv4 = []
    ipv6 = []
    for addr in addresses:
        if addr == "dhcp":
            ipv4.append(addr)
        elif addr in ("dhcpv6", "auto-config") or ":" in addr:
            ipv6.append(addr)
        else:
            ipv4.append(addr)
    return sorted(ipv4), sorted(ipv6)


def _parse_addr_entry(idata):
    """Returns (ipv4_argspec_list, ipv6_argspec_list) for one address
    leaf's raw value -- shared by both interface-level and vif-level
    parsing."""
    addrs = _addr_list((idata or {}).get("address"))
    if not addrs:
        return [], []
    ipv4, ipv6 = _split_addresses(addrs)
    return (
        [{"address": a} for a in ipv4],
        [{"address": a} for a in ipv6],
    )


def get_running_config(vyos):
    """VyOS's REST API collapses a single-child tag node to a plain
    string (or a list for multiple) -- confirmed as a real failure
    mode during vyos_ospf_interfaces's build. Normalizing through
    to_tag_dict unconditionally means callers always receive a
    genuine dict.
    """
    return to_tag_dict(vyos.get_config(_BASE) or {})


def _device_to_argspec(raw):
    result = []
    for itype, ifaces in sorted((raw or {}).items()):
        if not isinstance(ifaces, dict):
            continue
        for name, idata in sorted(to_tag_dict(ifaces).items()):
            idata = idata or {}
            entry = {"name": name}

            ipv4, ipv6 = _parse_addr_entry(idata)
            if ipv4:
                entry["ipv4"] = ipv4
            if ipv6:
                entry["ipv6"] = ipv6

            vif_raw = idata.get("vif")
            if vif_raw:
                vifs = []
                for vlan_id, vdata in sorted(to_tag_dict(vif_raw).items(), key=lambda x: int(x[0])):
                    vipv4, vipv6 = _parse_addr_entry(vdata)
                    if vipv4 or vipv6:
                        vif = {"vlan_id": int(vlan_id)}
                        if vipv4:
                            vif["ipv4"] = vipv4
                        if vipv6:
                            vif["ipv6"] = vipv6
                        vifs.append(vif)
                if vifs:
                    entry["vifs"] = vifs

            if entry.get("ipv4") or entry.get("ipv6") or entry.get("vifs"):
                result.append(entry)
    return result


def _normalize(config):
    """Argspec list -> dict keyed by interface name, with address
    lists flattened to plain sorted string lists for set-diffing."""
    result = {}
    for entry in config or []:
        name = entry.get("name")
        if not name:
            continue
        ipv4 = sorted(a["address"] for a in (entry.get("ipv4") or []) if a.get("address"))
        ipv6 = sorted(a["address"] for a in (entry.get("ipv6") or []) if a.get("address"))
        vifs = {}
        for vif in entry.get("vifs") or []:
            vid = vif.get("vlan_id")
            if vid is None:
                continue
            vipv4 = sorted(a["address"] for a in (vif.get("ipv4") or []) if a.get("address"))
            vipv6 = sorted(a["address"] for a in (vif.get("ipv6") or []) if a.get("address"))
            vifs[vid] = {"ipv4": vipv4, "ipv6": vipv6}
        result[name] = {"ipv4": ipv4, "ipv6": ipv6, "vifs": vifs}
    return result


def _addr_cmds(base, want_addrs, have_addrs, state):
    """Address is a plain multi-value leaf, not a keyed/tag-node
    section -- a set-diff is the correct, direct mechanism here
    (dict_op's keyed-entry model doesn't fit a bare value list).
    Confirmed scoped to exactly the "address" leaf under base,
    never anything else -- base may be an interface or a vif, and
    in neither case does this function ever touch a sibling leaf.
    """
    cmds = []
    want_set = set(want_addrs)
    have_set = set(have_addrs)

    for addr in want_set - have_set:
        cmds.append(("set", base + ["address", addr]))

    if state in ("replaced", "deleted", "overridden"):
        for addr in have_set - want_set:
            cmds.append(("delete", base + ["address", addr]))

    return cmds


def _vif_addr_cmds(iface_base, want_vifs, have_vifs, state):
    """VIF address commands, explicitly scoped to only the address
    leaf within each VIF -- never the VIF subtree as a whole.

    Confirmed severe bug in the original: an omitted VIF under
    replaced/overridden/deleted generated a whole-VIF delete
    (`delete ... vif <id>`), which would also destroy the VIF's own
    description/mtu/disable settings -- fields owned by
    vyos_interfaces, not this module. The same class of bug just
    confirmed and fixed in vyos_interfaces for interface-level
    "address" leaking the other way. Here, an omitted VIF under any
    state only ever has its own known addresses individually deleted;
    the VIF's own presence/other fields are never touched.
    """
    cmds = []

    all_vids = set(have_vifs) | set(want_vifs)
    for vid in all_vids:
        want_vif = want_vifs.get(vid, {"ipv4": [], "ipv6": []})
        have_vif = have_vifs.get(vid, {"ipv4": [], "ipv6": []})
        vif_base = iface_base + ["vif", str(vid)]
        cmds += _addr_cmds(vif_base, want_vif["ipv4"], have_vif["ipv4"], state)
        cmds += _addr_cmds(vif_base, want_vif["ipv6"], have_vif["ipv6"], state)

    return cmds


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    have_list = _device_to_argspec(raw_have)
    have_map = _normalize(have_list)

    if state == "deleted":
        cmds = []
        if not config:
            for name, have in have_map.items():
                base = _iface_base(name, raw_have)
                cmds += _addr_cmds(base, [], have["ipv4"], "deleted")
                cmds += _addr_cmds(base, [], have["ipv6"], "deleted")
                cmds += _vif_addr_cmds(base, {}, have["vifs"], "deleted")
            return cmds
        for entry in config or []:
            name = entry.get("name")
            if not name:
                continue
            have = have_map.get(name, {"ipv4": [], "ipv6": [], "vifs": {}})
            base = _iface_base(name, raw_have)
            named_addrs = entry.get("ipv4") or entry.get("ipv6") or entry.get("vifs")
            if not named_addrs:
                # No specific addresses/vifs named -- clear everything
                # this module owns for the interface.
                cmds += _addr_cmds(base, [], have["ipv4"], "deleted")
                cmds += _addr_cmds(base, [], have["ipv6"], "deleted")
                cmds += _vif_addr_cmds(base, {}, have["vifs"], "deleted")
            else:
                want = _normalize([entry])[name]
                for addr in want["ipv4"] + want["ipv6"]:
                    if addr in have["ipv4"] + have["ipv6"]:
                        cmds.append(("delete", base + ["address", addr]))
                for vid, want_vif in want["vifs"].items():
                    have_vif = have["vifs"].get(vid, {"ipv4": [], "ipv6": []})
                    vif_base = base + ["vif", str(vid)]
                    for addr in want_vif["ipv4"] + want_vif["ipv6"]:
                        if addr in have_vif["ipv4"] + have_vif["ipv6"]:
                            cmds.append(("delete", vif_base + ["address", addr]))
        return cmds

    want_map = _normalize(config)
    commands = []

    if state == "overridden":
        for name in set(have_map) - set(want_map):
            have = have_map[name]
            base = _iface_base(name, raw_have)
            commands += _addr_cmds(base, [], have["ipv4"], "overridden")
            commands += _addr_cmds(base, [], have["ipv6"], "overridden")
            commands += _vif_addr_cmds(base, {}, have["vifs"], "overridden")

    for name, want in want_map.items():
        have = have_map.get(name, {"ipv4": [], "ipv6": [], "vifs": {}})
        base = _iface_base(name, raw_have)
        commands += _addr_cmds(base, want["ipv4"], have["ipv4"], state)
        commands += _addr_cmds(base, want["ipv6"], have["ipv6"], state)
        commands += _vif_addr_cmds(base, want["vifs"], have["vifs"], state)

    return commands


_ADDR_OPTIONS = dict(address=dict(type="str"))

_VIF_OPTIONS = dict(
    vlan_id=dict(type="int", required=True),
    ipv4=dict(type="list", elements="dict", options=_ADDR_OPTIONS),
    ipv6=dict(type="list", elements="dict", options=_ADDR_OPTIONS),
)

_ENTRY_OPTIONS = dict(
    name=dict(type="str", required=True),
    ipv4=dict(type="list", elements="dict", options=_ADDR_OPTIONS),
    ipv6=dict(type="list", elements="dict", options=_ADDR_OPTIONS),
    vifs=dict(type="list", elements="dict", options=_VIF_OPTIONS),
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
