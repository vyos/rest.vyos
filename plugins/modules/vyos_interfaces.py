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
  - Manages L2 interface configuration (description, MTU, speed, duplex,
    enabled, VRF assignment, VLAN sub-interfaces) on VyOS devices using the
    HTTPS REST API.
  - IP address configuration is handled by M(vyos.rest.vyos_l3_interfaces).
  - >-
    Covers 11 interface types (ethernet, bonding, loopback, tunnel,
    wireguard, vti, dummy, openvpn, pppoe, wireless, bridge), resolved from
    the interface name. The current CLI collection module documents a
    narrower, deliberate scope of 5 types (ethernet, bonding, vxlan,
    loopback, vti) -- this module's broader coverage is a deliberate
    choice, not an oversight, and the additional types beyond CLI's
    documented set are not independently re-verified against the device
    schema here (matching the original module's own scope, carried over
    unchanged).
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
      vrf:
        description: VRF instance to bind this interface to.
        type: str
      vifs:
        description: 802.1Q VLAN sub-interfaces.
        type: list
        elements: dict
        suboptions:
          vlan_id:
            description: VLAN ID for this sub-interface.
            type: int
            required: true
          description:
            description: Sub-interface description.
            type: str
          enabled:
            description: Whether the sub-interface is enabled.
            type: bool
            default: true
          mtu:
            description: Sub-interface MTU.
            type: int
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
        vrf: mgmt
        vifs:
          - vlan_id: 200
            description: VIF 200
    state: merged

- name: Disable an interface
  vyos.rest.vyos_interfaces:
    config:
      - name: eth1
        enabled: false
    state: merged

- name: Delete interface config
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    to_tag_dict,
)


_BASE = ["interfaces"]

# Interface name prefix -> device type-category key. Carried over
# unchanged from the original module (11 types) -- kept as-is per
# explicit direction, not independently re-verified against the
# device schema for this rework (unlike the fields below, which are
# newly confirmed).
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
    """Prefer the real type from the device's own raw response
    (organized by type at the top level) over a name-prefix guess --
    only fall back to guessing for a brand-new interface that doesn't
    exist on the device yet, where the real type genuinely can't be
    determined any other way.

    Confirmed real bug in the original: the prefix guess was applied
    unconditionally, even for interfaces already known to the device,
    where the type is directly and reliably available without any
    guessing at all.
    """
    for itype, ifaces in (raw_have or {}).items():
        if isinstance(ifaces, dict) and name in ifaces:
            return itype
    return _guess_iface_type(name)


def _iface_base(name, raw_have):
    return _BASE + [_resolve_iface_type(name, raw_have), name]


def _kebab_fields(d):
    """autoclean, then kebab-convert the resulting keys.

    Needed because dict_op requires have's keys to already be genuine
    device kebab-case -- it only normalizes underscores to dashes for
    its own lookup index, but uses have's key verbatim for the output
    path. autoclean deliberately leaves keys exactly as given (dict_op
    is meant to convert during its own want-vs-have comparison), which
    only works when have comes straight from the device. Here, have is
    reconstructed by round-tripping through this module's own entry-
    transforms, so any field passed through unconverted would stay
    snake_case and dict_op would have no way to recover the real
    device key -- confirmed as a real bug during vyos_ospfv2's build.
    """
    cleaned = autoclean(d)
    return {k.replace("_", "-"): v for k, v in cleaned.items()}


def _keyed_list_to_device(items, key_field, entry_transform=None):
    entry_transform = entry_transform or _kebab_fields
    result = {}
    for item in items or []:
        if item.get(key_field) is None:
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[str(item[key_field])] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None, key_cast=None):
    entry_transform = entry_transform or from_device
    key_cast = key_cast or (lambda k: k)
    return [
        {key_field: key_cast(key), **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


# ---------------------------------------------------------------------------
# vif -- confirmed against vyos-1x/official docs: description, mtu, and a
# disable presence leaf, keyed by VLAN ID.
# ---------------------------------------------------------------------------


def _vif_entry_to_device(rest):
    exclude = {"enabled"}
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    if rest.get("enabled") is False:
        device["disable"] = {}
    return device


def _vif_entry_from_device(data):
    entry = {}
    if "description" in data:
        entry["description"] = data["description"]
    if "mtu" in data:
        entry["mtu"] = data["mtu"]
    if "disable" in data:
        entry["enabled"] = False
    return entry


def _iface_entry_to_device(rest):
    exclude = {"enabled", "vifs"}
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    if rest.get("enabled") is False:
        device["disable"] = {}
    vifs = rest.get("vifs") or []
    if vifs:
        device["vif"] = _keyed_list_to_device(vifs, "vlan_id", _vif_entry_to_device)
    return device


def _iface_entry_from_device(data):
    """Explicit allowlist of only the fields this module owns.

    Confirmed severe bug otherwise: a blanket from_device() pass-
    through of the entire raw device dict picks up every field VyOS
    happens to return for this interface -- address, hw-id, and
    anything else -- not just description/mtu/duplex/speed/vrf/vif/
    disable. Since this module's "deleted" state and replaced/
    overridden's dict_op purge both operate against the reconstructed
    have, an unmanaged field like "address" (owned by
    vyos_l3_interfaces, not this module) would be treated as "present
    in have, absent from want" and get deleted right alongside the
    L2 fields this module is actually meant to manage. Confirmed via
    real hardware: this could delete an interface's IP address --
    including the one the REST API itself is reachable through.
    """
    entry = {}
    for arg_key, device_key in (
        ("description", "description"),
        ("mtu", "mtu"),
        ("duplex", "duplex"),
        ("speed", "speed"),
        ("vrf", "vrf"),
    ):
        if device_key in data:
            entry[arg_key] = data[device_key]
    if "disable" in data:
        entry["enabled"] = False
    vif_raw = data.get("vif")
    if vif_raw:
        entry["vifs"] = _keyed_list_from_device(
            vif_raw,
            "vlan_id",
            _vif_entry_from_device,
            key_cast=int,
        )
    return entry


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
        for name, data in sorted(to_tag_dict(ifaces).items()):
            entry = {"name": name}
            entry.update(_iface_entry_from_device(data or {}))
            result.append(entry)
    return result


def _scoped_purge_commands(name, have_entry, raw_have):
    """Delete only the fields this module manages for one interface,
    via dict_op purge against an empty want -- never a whole-subtree
    delete. Safe specifically because have_device is built from the
    now-allowlisted _iface_entry_from_device/_vif_entry_from_device,
    so it can never contain an unmanaged field like address to begin
    with.
    """
    have_device = _iface_entry_to_device(
        {k: v for k, v in have_entry.items() if k != "name"},
    )
    base = _iface_base(name, raw_have)
    return dict_op({}, have_device, base, op="purge")


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    have_list = _device_to_argspec(raw_have)
    have_by_name = {e["name"]: e for e in have_list}
    want_by_name = {e["name"]: e for e in config if e.get("name")}

    if state == "deleted":
        cmds = []
        if not config:
            for name, have_entry in have_by_name.items():
                cmds += _scoped_purge_commands(name, have_entry, raw_have)
            return cmds
        for entry in config:
            name = entry.get("name")
            if name and name in have_by_name:
                cmds += _scoped_purge_commands(name, have_by_name[name], raw_have)
        return cmds

    commands = []
    if state == "overridden":
        for name in set(have_by_name) - set(want_by_name):
            commands += _scoped_purge_commands(name, have_by_name[name], raw_have)

    for name, want_entry in want_by_name.items():
        have_entry = have_by_name.get(name, {})
        want_device = _iface_entry_to_device(
            {k: v for k, v in want_entry.items() if k != "name"},
        )
        have_device = _iface_entry_to_device(
            {k: v for k, v in have_entry.items() if k != "name"},
        )
        base = _iface_base(name, raw_have)

        if state in ("replaced", "overridden"):
            commands += dict_op(want_device, have_device, base, op="purge")
        commands += dict_op(want_device, have_device, base, op="set")

    return commands


_VIF_OPTIONS = dict(
    vlan_id=dict(type="int", required=True),
    description=dict(type="str"),
    enabled=dict(type="bool", default=True),
    mtu=dict(type="int"),
)

_ENTRY_OPTIONS = dict(
    name=dict(type="str", required=True),
    description=dict(type="str"),
    enabled=dict(type="bool", default=True),
    mtu=dict(type="int"),
    duplex=dict(type="str", choices=["auto", "full", "half"]),
    speed=dict(type="str", choices=["auto", "10", "100", "1000", "2500", "10000"]),
    vrf=dict(type="str"),
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
