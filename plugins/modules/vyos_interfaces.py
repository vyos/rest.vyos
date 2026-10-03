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
    wireguard, vti, dummy, openvpn, pppoe, wireless, bridge), resolved
    from the device response when present, otherwise guessed from the
    interface name. The current CLI collection module documents a
    narrower scope of 5 types (ethernet, bonding, vxlan, loopback,
    vti).
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
    cast_by_spec,
    dict_op,
    to_tag_dict,
)


_BASE = ["interfaces"]

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
    exist on the device yet.
    """
    for itype, ifaces in (raw_have or {}).items():
        if name in to_tag_dict(ifaces):
            return itype
    return _guess_iface_type(name)


def _iface_base(name, raw_have):
    return _BASE + [_resolve_iface_type(name, raw_have), name]


_DEVICE_RENAMES = {
    "vifs": "vif",
}

_ENABLED_FIELD = "enabled"
_DISABLE_DEVICE_KEY = "disable"


def _derive_key_field(options_spec):
    """The field identifying each entry in a keyed-list section is
    never inferable from a generic walk alone -- but it doesn't need
    to be hand-declared either: every such section in this argspec
    already marks exactly one suboption required=True (you can't
    create a VIF without a vlan_id). Deriving it here means the key
    field is asserted to exist by the argspec itself, not duplicated
    in a place that could drift out of sync with it.
    """
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption to serve as the key field, "
            "found: {0}".format(required),
        )
    return required[0]


def _keyed_list_to_device(items, key_field, entry_transform):
    result = {}
    for item in items or []:
        if item.get(key_field) is None:
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[str(item[key_field])] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform, key_cast=None):
    key_cast = key_cast or (lambda k: k)
    return [
        {key_field: key_cast(key), **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


def _spec_to_device(value, options_spec):
    if not isinstance(value, dict):
        return value
    result = {}
    for arg_key, sub_spec in options_spec.items():
        if arg_key == _ENABLED_FIELD:
            if value.get(arg_key) is False:
                result[_DISABLE_DEVICE_KEY] = {}
            continue

        val = value.get(arg_key)
        if val is None or val is False:
            continue

        device_key = _DEVICE_RENAMES.get(arg_key, arg_key.replace("_", "-"))
        sub_type = sub_spec.get("type")
        sub_options = sub_spec.get("options")

        if sub_type == "dict" and sub_options:
            converted = _spec_to_device(val, sub_options)
            if converted:
                result[device_key] = converted
        elif sub_type == "list" and sub_options:
            key_field = _derive_key_field(sub_options)
            result[device_key] = _keyed_list_to_device(
                val,
                key_field,
                lambda rest, spec=sub_options: _spec_to_device(rest, spec),
            )
        elif val is True:
            result[device_key] = {}
        elif sub_type == "list":
            result[device_key] = list(val)
        else:
            result[device_key] = val
    return result


def _device_to_spec(raw, options_spec):
    if not raw or not isinstance(raw, dict):
        return {}
    have_idx = {k.replace("-", "_"): k for k in raw}
    result = {}

    if _ENABLED_FIELD in options_spec and _DISABLE_DEVICE_KEY in raw:
        result[_ENABLED_FIELD] = False

    for arg_key, sub_spec in options_spec.items():
        if arg_key == _ENABLED_FIELD:
            continue
        device_key = _DEVICE_RENAMES.get(arg_key, arg_key.replace("_", "-"))
        orig_key = device_key if device_key in raw else have_idx.get(arg_key)
        if orig_key is None:
            continue
        raw_val = raw[orig_key]
        sub_type = sub_spec.get("type")
        sub_options = sub_spec.get("options")

        if sub_type == "dict" and sub_options:
            converted = _device_to_spec(raw_val, sub_options)
            if converted:
                result[arg_key] = converted
        elif sub_type == "list" and sub_options:
            key_field = _derive_key_field(sub_options)
            key_cast = int if sub_options[key_field].get("type") == "int" else None
            entries = _keyed_list_from_device(
                raw_val,
                key_field,
                lambda d, spec=sub_options: _device_to_spec(d, spec),
                key_cast=key_cast,
            )
            if entries:
                result[arg_key] = entries
        elif sub_type == "list":
            if raw_val:
                result[arg_key] = sorted(to_tag_dict(raw_val).keys())
        elif isinstance(raw_val, dict) and not raw_val:
            result[arg_key] = True
        else:
            result[arg_key] = raw_val
    return result


def get_running_config(vyos):
    """VyOS's REST API collapses a single-child tag node to a plain
    string (or a list for multiple) -- normalizing through to_tag_dict
    unconditionally means callers always receive a genuine dict.
    """
    return to_tag_dict(vyos.get_config(_BASE) or {})


def _device_to_argspec(raw):
    result = []
    for itype, ifaces in sorted((raw or {}).items()):
        for name, data in sorted(to_tag_dict(ifaces).items()):
            entry = {"name": name}
            entry.update(_device_to_spec(data or {}, _ENTRY_OPTIONS))
            result.append(entry)
    return result


def _shadow_vif_entries(want_device, have_device):
    """Ensure want_device has a (possibly empty) placeholder for every
    VLAN ID present in have_device's own "vif" dict, so a dict_op
    purge recurses into each VIF individually rather than treating the
    whole "vif" key, or any single VLAN entry, as one unit.
    """
    have_vifs = have_device.get("vif")
    if not have_vifs:
        return want_device
    shadowed = dict(want_device)
    want_vifs = dict(shadowed.get("vif") or {})
    for vlan_id in have_vifs:
        want_vifs.setdefault(vlan_id, {})
    shadowed["vif"] = want_vifs
    return shadowed


def _purge_commands(want_device, have_device, base):
    return dict_op(_shadow_vif_entries(want_device, have_device), have_device, base, op="purge")


def _entry_to_device(entry, options_spec):
    """to-device conversion for a keyed entry whose own key field
    (e.g. "name" for an interface, same role "vlan_id" plays for a
    VIF) is present in the input but must never be treated as a
    regular child leaf -- it identifies the entry itself and is
    already expressed in the API path (_iface_base), not a field to
    set/purge under it. _keyed_list_to_device already strips a VIF's
    "vlan_id" the same way before conversion; interface entries need
    the same treatment here since build_commands handles the top
    level manually rather than through that helper.
    """
    key_field = _derive_key_field(options_spec)
    rest = {k: v for k, v in (entry or {}).items() if k != key_field}
    return _spec_to_device(rest, options_spec)


def _scoped_purge_commands(name, have_entry, raw_have):
    """Remove every field this module manages for one interface --
    scoped to this module's own fields only, never a whole-subtree
    delete for the VIF container shared with vyos_l3_interfaces.
    """
    have_device = _entry_to_device(have_entry, _ENTRY_OPTIONS)
    base = _iface_base(name, raw_have)
    return _purge_commands({}, have_device, base)


def _enabled_leaves(device):
    result = {}
    if _DISABLE_DEVICE_KEY in device:
        result[_DISABLE_DEVICE_KEY] = device[_DISABLE_DEVICE_KEY]
    vif = device.get("vif")
    if vif:
        vif_result = {
            vlan_id: {_DISABLE_DEVICE_KEY: v[_DISABLE_DEVICE_KEY]}
            for vlan_id, v in vif.items()
            if _DISABLE_DEVICE_KEY in v
        }
        if vif_result:
            result["vif"] = vif_result
    return result


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or []

    have_list = _device_to_argspec(raw_have)
    have_by_name = {e["name"]: e for e in have_list}
    want_by_name = {e["name"]: e for e in config if e.get("name")}

    if state == "deleted":
        cmds = []
        targets = (
            have_by_name
            if not config
            else {n: have_by_name[n] for n in want_by_name if n in have_by_name}
        )
        for name, have_entry in targets.items():
            cmds += _scoped_purge_commands(name, have_entry, raw_have)
        return cmds

    commands = []
    if state == "overridden":
        for name in set(have_by_name) - set(want_by_name):
            commands += _scoped_purge_commands(name, have_by_name[name], raw_have)

    for name, want_entry in want_by_name.items():
        have_entry = have_by_name.get(name, {})
        want_device = _entry_to_device(want_entry, _ENTRY_OPTIONS)
        have_device = _entry_to_device(have_entry, _ENTRY_OPTIONS)
        base = _iface_base(name, raw_have)

        if state in ("replaced", "overridden"):
            commands += _purge_commands(want_device, have_device, base)
        else:
            want_enabled = _enabled_leaves(want_device)
            have_enabled = _enabled_leaves(have_device)
            commands += _purge_commands(want_enabled, have_enabled, base)
        commands += dict_op(want_device, have_device, base, op="set")

    return commands


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
            vrf=dict(type="str"),
            vifs=dict(
                type="list",
                elements="dict",
                options=dict(
                    vlan_id=dict(type="int", required=True),
                    description=dict(type="str"),
                    enabled=dict(type="bool", default=True),
                    mtu=dict(type="int"),
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

_ENTRY_OPTIONS = ARGUMENT_SPEC["config"]["options"]
_VIF_OPTIONS = _ENTRY_OPTIONS["vifs"]["options"]


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
