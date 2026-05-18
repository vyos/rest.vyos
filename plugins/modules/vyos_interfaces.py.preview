#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_interfaces
short_description: Manage interface attributes on a VyOS device via the REST API.
description:
  - Manages interface base attributes (description, MTU, enabled state, VIFs,
    duplex, speed) on VyOS devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_interfaces) but uses HTTP API.
  - Supports Ethernet, Bonding, VXLAN, Loopback, and Virtual Tunnel interfaces.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: >
          Full interface name (e.g. C(eth0), C(bond0), C(vti1), C(vxlan2)).
        type: str
        required: true
      description:
        description: Interface description.
        type: str
      enabled:
        description: >
          Administrative state. C(true) = up, C(false) = admin-down.
        type: bool
        default: true
      mtu:
        description: MTU in bytes. Applicable for Ethernet, Bonding, VXLAN, VTI.
        type: int
      duplex:
        description: Duplex mode. Only for Ethernet interfaces.
        type: str
        choices: [auto, full, half]
      speed:
        description: Link speed. Only for Ethernet interfaces.
        type: str
      vifs:
        description: List of VLAN sub-interface configurations.
        type: list
        elements: dict
        suboptions:
          vlan_id:
            description: 802.1Q VLAN ID.
            type: int
            required: true
          description:
            description: VIF description.
            type: str
          enabled:
            description: Administrative state of the VIF.
            type: bool
            default: true
  state:
    description:
      - C(merged): Merge the provided config with existing interface config.
      - C(replaced): Replace per-interface config with provided values.
      - C(overridden): Override all interface config with provided values.
      - C(deleted): Delete interface config for listed interfaces (or all).
      - C(gathered): Read current interface config from device.
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
  - module: vyos.vyos.vyos_interfaces
  - module: vyos.rest.vyos_l3_interfaces
examples: |
  - name: Set description and MTU on eth1
    vyos.rest.vyos_interfaces:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - name: eth1
          description: "WAN uplink"
          mtu: 1500
          enabled: true
      state: merged

  - name: Disable eth2
    vyos.rest.vyos_interfaces:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - name: eth2
          enabled: false
      state: merged

  - name: Create a VLAN sub-interface
    vyos.rest.vyos_interfaces:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - name: eth1
          vifs:
            - vlan_id: 100
              description: "VLAN 100"
      state: merged
"""

RETURN = r"""
before:
  description: Interface configuration before the module ran.
  returned: always
  type: list
after:
  description: Interface configuration after the module ran.
  returned: when changed
  type: list
gathered:
  description: Interface config read from device (state=gathered).
  returned: when state is gathered
  type: list
commands:
  description: REST API set/delete commands issued.
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
    "peth": "pseudo-ethernet",
    "vtun": "openvpn",
    "wg": "wireguard",
    "br": "bridge",
    "macsec": "macsec",
    "tun": "tunnel",
}


def _iface_type(name):
    """Infer the VyOS interface type from its name prefix."""
    for prefix, itype in _IFACE_TYPES.items():
        if name.startswith(prefix):
            return itype
    return "ethernet"


def _iface_base_path(name):
    return ["interfaces", _iface_type(name), name]


def _get_interfaces(client):
    try:
        result = client.retrieve_show_config(["interfaces"])
        ifaces_raw = result.get("data") or {}
        interfaces = []
        for itype, itype_data in ifaces_raw.items():
            if not isinstance(itype_data, dict):
                continue
            for iname, idata in itype_data.items():
                if not isinstance(idata, dict):
                    continue
                entry = {"name": iname}
                if "description" in idata:
                    entry["description"] = idata["description"]
                if "mtu" in idata:
                    entry["mtu"] = int(idata["mtu"])
                entry["enabled"] = "disable" not in idata
                if "duplex" in idata:
                    entry["duplex"] = idata["duplex"]
                if "speed" in idata:
                    entry["speed"] = idata["speed"]
                if "vif" in idata:
                    vifs = []
                    for vid, vdata in idata["vif"].items():
                        vif_entry = {"vlan_id": int(vid)}
                        if isinstance(vdata, dict):
                            if "description" in vdata:
                                vif_entry["description"] = vdata["description"]
                            vif_entry["enabled"] = "disable" not in vdata
                        vifs.append(vif_entry)
                    entry["vifs"] = vifs
                interfaces.append(entry)
        return interfaces
    except VyOSRestError:
        return []


def _apply_interface(client, iface_cfg, commands):
    name = iface_cfg["name"]
    base = _iface_base_path(name)

    if iface_cfg.get("description") is not None:
        client.configure_set(base + ["description"], iface_cfg["description"])
        commands.append(
            "set interfaces {t} {n} description '{d}'".format(
                t=_iface_type(name),
                n=name,
                d=iface_cfg["description"],
            ),
        )
    if iface_cfg.get("mtu") is not None:
        client.configure_set(base + ["mtu"], str(iface_cfg["mtu"]))
        commands.append(
            "set interfaces {t} {n} mtu {m}".format(
                t=_iface_type(name),
                n=name,
                m=iface_cfg["mtu"],
            ),
        )
    if "enabled" in iface_cfg:
        if not iface_cfg["enabled"]:
            client.configure_set(base + ["disable"])
            commands.append(
                "set interfaces {t} {n} disable".format(t=_iface_type(name), n=name),
            )
        else:
            try:
                client.configure_delete(base + ["disable"])
                commands.append(
                    "delete interfaces {t} {n} disable".format(
                        t=_iface_type(name),
                        n=name,
                    ),
                )
            except VyOSRestError:
                pass
    if iface_cfg.get("duplex"):
        client.configure_set(base + ["duplex"], iface_cfg["duplex"])
        commands.append(
            "set interfaces {t} {n} duplex {d}".format(
                t=_iface_type(name),
                n=name,
                d=iface_cfg["duplex"],
            ),
        )
    if iface_cfg.get("speed"):
        client.configure_set(base + ["speed"], iface_cfg["speed"])
        commands.append(
            "set interfaces {t} {n} speed {s}".format(
                t=_iface_type(name),
                n=name,
                s=iface_cfg["speed"],
            ),
        )
    for vif in iface_cfg.get("vifs") or []:
        vid = str(vif["vlan_id"])
        vif_base = base + ["vif", vid]
        client.configure_set(vif_base)
        commands.append(
            "set interfaces {t} {n} vif {v}".format(
                t=_iface_type(name),
                n=name,
                v=vid,
            ),
        )
        if vif.get("description"):
            client.configure_set(vif_base + ["description"], vif["description"])
            commands.append(
                "set interfaces {t} {n} vif {v} description '{d}'".format(
                    t=_iface_type(name),
                    n=name,
                    v=vid,
                    d=vif["description"],
                ),
            )
        if "enabled" in vif and not vif["enabled"]:
            client.configure_set(vif_base + ["disable"])
            commands.append(
                "set interfaces {t} {n} vif {v} disable".format(
                    t=_iface_type(name),
                    n=name,
                    v=vid,
                ),
            )


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                description=dict(type="str"),
                enabled=dict(type="bool", default=True),
                mtu=dict(type="int"),
                duplex=dict(type="str", choices=["auto", "full", "half"]),
                speed=dict(type="str"),
                vifs=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        vlan_id=dict(type="int", required=True),
                        description=dict(type="str"),
                        enabled=dict(type="bool", default=True),
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

    before = _get_interfaces(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "deleted":
            targets = {i["name"] for i in config} if config else {i["name"] for i in before}
            for iface in before:
                if iface["name"] in targets:
                    base = _iface_base_path(iface["name"])
                    # Only delete mutable attributes, not the interface itself
                    for attr in ["description", "mtu", "duplex", "speed"]:
                        if attr in iface:
                            try:
                                client.configure_delete(base + [attr])
                                commands.append(
                                    "delete interfaces {t} {n} {a}".format(
                                        t=_iface_type(iface["name"]),
                                        n=iface["name"],
                                        a=attr,
                                    ),
                                )
                            except VyOSRestError:
                                pass
                    changed = True

        elif state in ("merged", "replaced", "overridden"):
            for iface_cfg in config:
                _apply_interface(client, iface_cfg, commands)
                changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_interfaces(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
