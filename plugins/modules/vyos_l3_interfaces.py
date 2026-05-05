#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_l3_interfaces
short_description: Manage L3 interface attributes on VyOS via the REST API.
description:
  - Manages IPv4 and IPv6 addresses on VyOS interfaces via the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_l3_interfaces) but uses the HTTP API.
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
        description: Full interface name (e.g. C(eth0), C(eth1)).
        type: str
        required: true
      ipv4:
        description: List of IPv4 address assignments.
        type: list
        elements: dict
        suboptions:
          address:
            description: IPv4 address in CIDR notation or C(dhcp).
            type: str
            required: true
      ipv6:
        description: List of IPv6 address assignments.
        type: list
        elements: dict
        suboptions:
          address:
            description: IPv6 address in CIDR notation or C(dhcpv6) or C(autoconf).
            type: str
            required: true
      vifs:
        description: VLAN sub-interface L3 settings.
        type: list
        elements: dict
        suboptions:
          vlan_id:
            description: 802.1Q VLAN ID.
            type: int
            required: true
          ipv4:
            description: IPv4 addresses for this VIF.
            type: list
            elements: dict
            suboptions:
              address:
                type: str
                required: true
          ipv6:
            description: IPv6 addresses for this VIF.
            type: list
            elements: dict
            suboptions:
              address:
                type: str
                required: true
  state:
    description:
      - C(merged): Add addresses to the interface (preserve existing).
      - C(replaced): Replace all addresses on each listed interface.
      - C(overridden): Replace all addresses on all interfaces.
      - C(deleted): Remove all addresses from listed (or all) interfaces.
      - C(gathered): Read L3 config from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
  hostname:
    description: IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description: HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description: API key configured on the device.
    type: str
    required: true
    no_log: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.vyos.vyos_l3_interfaces
  - module: vyos.rest.vyos_interfaces
examples: |
  - name: Assign addresses to eth1 and eth2
    vyos.rest.vyos_l3_interfaces:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - name: eth1
          ipv4:
            - address: 10.0.1.1/24
          ipv6:
            - address: "2001:db8::1/64"
        - name: eth2
          ipv4:
            - address: dhcp
      state: merged

  - name: Remove all addresses from eth1
    vyos.rest.vyos_l3_interfaces:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - name: eth1
      state: deleted
"""

RETURN = r"""
before:
  description: L3 interface config before the module ran.
  returned: always
  type: list
after:
  description: L3 interface config after the module ran.
  returned: when changed
  type: list
gathered:
  description: L3 config read from device (state=gathered).
  returned: when state is gathered
  type: list
commands:
  description: set/delete commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_IFACE_TYPES = {
    "eth": "ethernet",
    "bond": "bonding",
    "vti": "vti",
    "vxlan": "vxlan",
    "lo": "loopback",
    "dummy": "dummy",
    "br": "bridge",
    "wg": "wireguard",
    "tun": "tunnel",
}


def _iface_type(name):
    for prefix, t in _IFACE_TYPES.items():
        if name.startswith(prefix):
            return t
    return "ethernet"


def _base(name):
    return ["interfaces", _iface_type(name), name]


def _get_l3_interfaces(client):
    try:
        result = client.retrieve_show_config(["interfaces"])
        raw = result.get("data") or {}
        out = []
        for itype, itype_data in raw.items():
            if not isinstance(itype_data, dict):
                continue
            for iname, idata in itype_data.items():
                if not isinstance(idata, dict):
                    continue
                entry = {"name": iname, "ipv4": [], "ipv6": []}
                for addr in _listify(idata.get("address")):
                    if ":" in addr:
                        entry["ipv6"].append({"address": addr})
                    elif addr == "dhcp":
                        entry["ipv4"].append({"address": addr})
                    else:
                        entry["ipv4"].append({"address": addr})
                # VIFs
                if "vif" in idata:
                    vifs = []
                    for vid, vdata in idata["vif"].items():
                        vif_e = {"vlan_id": int(vid), "ipv4": [], "ipv6": []}
                        if isinstance(vdata, dict):
                            for addr in _listify(vdata.get("address")):
                                if ":" in addr:
                                    vif_e["ipv6"].append({"address": addr})
                                else:
                                    vif_e["ipv4"].append({"address": addr})
                        vifs.append(vif_e)
                    entry["vifs"] = vifs
                if entry["ipv4"] or entry["ipv6"] or entry.get("vifs"):
                    out.append(entry)
        return out
    except VyOSRestError:
        return []


def _listify(val):
    """Return val as a list regardless of whether it's a str or list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _set_addresses(client, name, ipv4, ipv6, commands):
    base = _base(name)
    itype = _iface_type(name)
    for a in ipv4 or []:
        client.configure_set(base + ["address"], a["address"])
        commands.append(
            "set interfaces {t} {n} address '{a}'".format(
                t=itype,
                n=name,
                a=a["address"],
            ),
        )
    for a in ipv6 or []:
        client.configure_set(base + ["address"], a["address"])
        commands.append(
            "set interfaces {t} {n} address '{a}'".format(
                t=itype,
                n=name,
                a=a["address"],
            ),
        )


def _delete_addresses(client, name, commands):
    base = _base(name)
    itype = _iface_type(name)
    try:
        client.configure_delete(base + ["address"])
        commands.append(
            "delete interfaces {t} {n} address".format(t=itype, n=name),
        )
    except VyOSRestError:
        pass


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                ipv4=dict(
                    type="list",
                    elements="dict",
                    options=dict(address=dict(type="str", required=True)),
                ),
                ipv6=dict(
                    type="list",
                    elements="dict",
                    options=dict(address=dict(type="str", required=True)),
                ),
                vifs=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        vlan_id=dict(type="int", required=True),
                        ipv4=dict(
                            type="list",
                            elements="dict",
                            options=dict(address=dict(type="str", required=True)),
                        ),
                        ipv6=dict(
                            type="list",
                            elements="dict",
                            options=dict(address=dict(type="str", required=True)),
                        ),
                    ),
                ),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "replaced", "overridden", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config") or []
    commands = []
    changed = False

    before = _get_l3_interfaces(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "deleted":
            targets = {i["name"] for i in config} if config else {i["name"] for i in before}
            for iface in before:
                if iface["name"] in targets:
                    _delete_addresses(client, iface["name"], commands)
                    changed = True

        elif state in ("merged", "replaced", "overridden"):
            if state in ("replaced", "overridden"):
                # First remove existing addresses on targeted interfaces
                targets = {i["name"] for i in config}
                if state == "overridden":
                    targets = {i["name"] for i in before}
                for iface in before:
                    if iface["name"] in targets:
                        _delete_addresses(client, iface["name"], commands)

            for iface_cfg in config:
                name = iface_cfg["name"]
                _set_addresses(
                    client,
                    name,
                    iface_cfg.get("ipv4"),
                    iface_cfg.get("ipv6"),
                    commands,
                )
                for vif in iface_cfg.get("vifs") or []:
                    vid = str(vif["vlan_id"])
                    base = _base(name) + ["vif", vid]
                    itype = _iface_type(name)
                    for a in (vif.get("ipv4") or []) + (vif.get("ipv6") or []):
                        client.configure_set(base + ["address"], a["address"])
                        commands.append(
                            "set interfaces {t} {n} vif {v} address '{a}'".format(
                                t=itype,
                                n=name,
                                v=vid,
                                a=a["address"],
                            ),
                        )
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_l3_interfaces(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
