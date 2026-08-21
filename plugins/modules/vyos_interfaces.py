#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_interfaces
short_description: Manage interface configuration on VyOS devices via REST API.
description:
  - Manages L2 interface configuration (description, MTU, speed, duplex, enabled)
    on VyOS devices using the HTTPS REST API.
  - IP address configuration is handled by M(vyos.rest.vyos_l3_interfaces).
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
        description: Full interface name (e.g. eth0, bond0, lo).
        type: str
        required: true
      description:
        description: Interface description.
        type: str
      enabled:
        description: Whether the interface is enabled. False sets the disable flag.
        type: bool
        default: true
      mtu:
        description: Interface MTU.
        type: int
      duplex:
        description: Interface duplex setting.
        type: str
        choices: [auto, full, half]
      speed:
        description: Interface speed setting.
        type: str
        choices: [auto, "10", "100", "1000", "2500", "10000"]
  state:
    description:
      - C(merged) - Merge config with existing interface settings.
      - C(replaced) - Replace config for listed interfaces.
      - C(overridden) - Replace config for all interfaces.
      - C(deleted) - Remove listed interface config or all interface config.
      - C(gathered) - Read interface config from device without changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
seealso:
  - module: vyos.vyos.vyos_interfaces
  - module: vyos.rest.vyos_l3_interfaces
"""

EXAMPLES = r"""
- name: Merge interface configuration
  vyos.rest.vyos_interfaces:
    config:
      - name: eth0
        description: Management interface
        mtu: 1500
        enabled: true
    state: merged

- name: Disable an interface
  vyos.rest.vyos_interfaces:
    config:
      - name: eth1
        enabled: false
    state: merged

- name: Delete interface description
  vyos.rest.vyos_interfaces:
    config:
      - name: eth0
    state: deleted

- name: Gather current interface configuration
  vyos.rest.vyos_interfaces:
    state: gathered
"""

RETURN = r"""
before:
  description: Interface configuration before this module ran.
  returned: always
  type: list
after:
  description: Interface configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current interface configuration as structured data.
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


# Interface name prefix → API type key
_IFACE_TYPE = {
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

# L2 fields managed by this module — excludes address, hw-id etc.
_L2_FIELDS = ["description", "mtu", "duplex", "speed"]


def _iface_type(name):
    for prefix, itype in _IFACE_TYPE.items():
        if name.startswith(prefix):
            return itype
    return "ethernet"


def _iface_base(name):
    return ["interfaces", _iface_type(name), name]


def get_running_config(vyos):
    raw = vyos.get_config(["interfaces"])
    if not raw or not isinstance(raw, dict):
        return []

    result = []
    for itype, ifaces in sorted(raw.items()):
        if not isinstance(ifaces, dict):
            continue
        for iname, idata in sorted(ifaces.items()):
            idata = idata or {}
            entry = {"name": iname}
            if idata.get("description"):
                entry["description"] = idata["description"]
            if "mtu" in idata:
                entry["mtu"] = int(idata["mtu"])
            if "duplex" in idata:
                entry["duplex"] = idata["duplex"]
            if "speed" in idata:
                entry["speed"] = idata["speed"]
            entry["enabled"] = "disable" not in idata
            result.append(entry)

    return result


def _normalize(config):
    """Convert argspec list to dict keyed by interface name."""
    return {entry["name"]: entry for entry in (config or [])}


def _iface_cmds(name, want, have):
    """Generate set/delete commands to bring have → want for one interface."""
    cmds = []
    base = _iface_base(name)
    have = have or {}

    # description
    want_desc = want.get("description")
    have_desc = have.get("description")
    if want_desc is not None and want_desc != have_desc:
        cmds.append(("set", base + ["description", want_desc]))
    elif want_desc is None and have_desc is not None:
        cmds.append(("delete", base + ["description"]))

    # mtu
    want_mtu = want.get("mtu")
    have_mtu = have.get("mtu")
    if want_mtu is not None and want_mtu != have_mtu:
        cmds.append(("set", base + ["mtu", str(want_mtu)]))

    # duplex
    want_duplex = want.get("duplex")
    have_duplex = have.get("duplex")
    if want_duplex is not None and want_duplex != have_duplex:
        cmds.append(("set", base + ["duplex", want_duplex]))

    # speed
    want_speed = want.get("speed")
    have_speed = have.get("speed")
    if want_speed is not None and want_speed != have_speed:
        cmds.append(("set", base + ["speed", want_speed]))

    # enabled / disable flag
    want_enabled = want.get("enabled", True)
    have_enabled = have.get("enabled", True)
    if not want_enabled and have_enabled:
        cmds.append(("set", base + ["disable"]))
    elif want_enabled and not have_enabled:
        cmds.append(("delete", base + ["disable"]))

    return cmds


def _delete_iface_config(name, have):
    """Generate delete commands to remove L2 config from an interface."""
    cmds = []
    base = _iface_base(name)
    have = have or {}

    for field in _L2_FIELDS:
        if field in have:
            cmds.append(("delete", base + [field]))
    if not have.get("enabled", True):
        cmds.append(("delete", base + ["disable"]))

    return cmds


def build_commands(config, have_raw, state):
    cmds = []
    have_map = _normalize(have_raw)

    if state == "deleted":
        if not config:
            for name, have in have_map.items():
                cmds += _delete_iface_config(name, have)
        else:
            for entry in config:
                name = entry["name"]
                cmds += _delete_iface_config(name, have_map.get(name, {}))
        return cmds

    want_map = _normalize(config)

    if state == "overridden":
        # delete L2 config from interfaces not in want
        for name in set(have_map) - set(want_map):
            cmds += _delete_iface_config(name, have_map[name])

    for name, want in want_map.items():
        have = have_map.get(name, {})

        if state == "replaced":
            # pre-check — only act if something differs
            test_cmds = _iface_cmds(name, want, have)
            if not test_cmds:
                continue
            # delete L2 fields then rebuild
            cmds += _delete_iface_config(name, have)
            have = {}

        cmds += _iface_cmds(name, want, have if state != "replaced" else {})

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            description=dict(type="str"),
            enabled=dict(type="bool", default=True),
            mtu=dict(type="int"),
            duplex=dict(type="str", choices=["auto", "full", "half"]),
            speed=dict(type="str", choices=["auto", "10", "100", "1000", "2500", "10000"]),
        ),
    ),
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
