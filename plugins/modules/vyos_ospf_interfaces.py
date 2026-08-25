#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospf_interfaces
short_description: Manage OSPF interface configuration on VyOS devices using REST API
description:
  - Manages OSPFv2 (IPv4) and OSPFv3 (IPv6) per-interface configuration on
    VyOS devices via the REST API.
  - IPv4 maps to C(protocols ospf interface) -- a genuinely separate device
    subtree from IPv6's C(protocols ospfv3 interface), not two views onto
    one shared tree.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - >-
    Scope matches the current vyos.vyos.vyos_ospf_interfaces (CLI
    collection) module. Confirmed against vyos-1x: C(cost), C(priority),
    C(dead_interval), C(hello_interval), C(retransmit_interval),
    C(transmit_delay), C(network), and C(mtu_ignore) are genuinely shared
    across both address families (this module's previous documentation
    incorrectly labeled C(mtu_ignore) and C(passive) as address-family
    exclusive -- corrected here). C(authentication) and C(bandwidth) are
    confirmed IPv4-only; C(ifmtu) and C(instance) are confirmed IPv6-only.
    C(network)'s valid values genuinely differ by address family (IPv4
    additionally allows C(non-broadcast)/C(point-to-multipoint)) --
    argspec C(choices) can't express a per-AFI restriction, so an invalid
    combination is only caught by the device itself, not ahead of time.
    C(hello_multiplier) and C(retransmit_window) (IPv4-only device
    options) are not modeled, matching the CLI module's own scope.
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
            description: Interface bandwidth in Mbit/s (IPv4 only).
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
            description: Disable MTU mismatch detection.
            type: bool
          network:
            description: >-
              Network type. IPv6 only allows C(broadcast)/C(point-to-point);
              C(non-broadcast)/C(point-to-multipoint) are IPv4-only, but
              this isn't enforced at the argspec level -- an invalid
              combination is rejected by the device itself.
            type: str
            choices: [broadcast, non-broadcast, point-to-multipoint, point-to-point]
          passive:
            description: Suppress adjacency formation on this interface.
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
seealso:
  - module: vyos.vyos.vyos_ospf_interfaces
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    to_tag_dict,
)


_BASE4 = ["protocols", "ospf", "interface"]
_BASE6 = ["protocols", "ospfv3", "interface"]

# Confirmed against vyos-1x: the only genuine renames needed. Everything
# else shared between AFIs (cost, priority, dead_interval, hello_interval,
# retransmit_interval, transmit_delay, network, mtu_ignore) is mechanical
# kebab -- "instance" -> "instance-id" is IPv6-only and irreducible.
_IPV6_RENAMES = {"instance": "instance-id"}


def _derive_key_field(options_spec):
    """The field identifying each entry in a named-list section is
    never inferable from a generic walk alone -- but it doesn't need
    to be hand-declared either: every named-list section in this
    argspec already marks exactly one suboption required=True.
    """
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption to serve as the key field, "
            "found: {0}".format(required),
        )
    return required[0]


def _keyed_list_to_device(items, key_field, entry_transform=None):
    entry_transform = entry_transform or _kebab_fields
    result = {}
    for item in items or []:
        if not item.get(key_field):
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[str(item[key_field])] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None):
    entry_transform = entry_transform or from_device
    return [
        {key_field: key, **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


def _kebab_fields(d):
    """autoclean, then kebab-convert the resulting keys.

    Needed because dict_op requires have's keys to already be genuine
    device kebab-case -- it only normalizes underscores to dashes for
    its own lookup index, but uses have's key verbatim for the output
    path. autoclean deliberately leaves keys exactly as given (dict_op
    is meant to convert during its own want-vs-have comparison), which
    only works when have comes straight from the device. Here, have is
    reconstructed by round-tripping through this module's own entry-
    transforms (needed for the confirmed structural exceptions below),
    so any field passed through unconverted would stay snake_case and
    dict_op would have no way to recover the real device key -- exactly
    the bug confirmed and fixed in vyos_ospfv2's build. Safe here since
    every call site is a leaf-level dict of schema field names, never
    an opaque tag-node value like an interface name used as a dict key.
    """
    cleaned = autoclean(d)
    return {k.replace("_", "-"): v for k, v in cleaned.items()}


# ---------------------------------------------------------------------------
# authentication -- IPv4 only. Confirmed against vyos-1x: plaintext-
# password is a plain leaf; md5 is a fixed "key-id" node containing a
# single tagNode entry (key-id value -> {md5-key: ...}) -- genuinely a
# single-entry structure, not a list, matching the argspec's own single
# md5_key dict rather than a list of them.
# ---------------------------------------------------------------------------


def _auth_to_device(auth):
    if not auth:
        return {}
    device = {}
    if auth.get("plaintext_password"):
        device["plaintext-password"] = auth["plaintext_password"]
    md5 = auth.get("md5_key") or {}
    if md5.get("key_id") is not None:
        device["md5"] = {"key-id": {str(md5["key_id"]): {"md5-key": md5.get("key")}}}
    return device


def _auth_from_device(data):
    if not data:
        return None
    entry = {}
    if data.get("plaintext-password"):
        entry["plaintext_password"] = data["plaintext-password"]
    key_id_raw = (data.get("md5") or {}).get("key-id")
    if key_id_raw:
        key_id, kdata = sorted(to_tag_dict(key_id_raw).items())[0]
        entry["md5_key"] = {"key_id": int(key_id), "key": (kdata or {}).get("md5-key")}
    return entry or None


def _af4_entry_to_device(rest):
    exclude = {"afi", "authentication"}
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    if rest.get("authentication"):
        auth_device = _auth_to_device(rest["authentication"])
        if auth_device:
            device["authentication"] = auth_device
    return device


def _af4_entry_from_device(data):
    exclude = {"authentication"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})
    auth = _auth_from_device(data.get("authentication"))
    if auth:
        entry["authentication"] = auth
    return entry


def _af6_entry_to_device(rest):
    exclude = set(_IPV6_RENAMES)
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    for arg_key, device_key in _IPV6_RENAMES.items():
        if rest.get(arg_key) is not None:
            device[device_key] = rest[arg_key]
    return device


def _af6_entry_from_device(data):
    exclude = set(_IPV6_RENAMES.values())
    entry = from_device({k: v for k, v in data.items() if k not in exclude})
    for arg_key, device_key in _IPV6_RENAMES.items():
        if data.get(device_key) is not None:
            entry[arg_key] = data[device_key]
    return entry


def _want_to_device(config):
    want4 = {}
    want6 = {}
    for entry in config or []:
        name = entry.get("name")
        if not name:
            continue
        for af in entry.get("address_family") or []:
            afi = af.get("afi")
            rest = {k: v for k, v in af.items() if k != "afi"}
            if afi == "ipv4":
                want4[name] = _af4_entry_to_device(rest)
            elif afi == "ipv6":
                want6[name] = _af6_entry_to_device(rest)
    return want4, want6


def get_running_config(vyos):
    raw4 = vyos.get_config(_BASE4) or {}
    raw4 = raw4.get("interface", raw4)
    raw6 = vyos.get_config(_BASE6) or {}
    raw6 = raw6.get("interface", raw6)
    return raw4, raw6


def _device_to_argspec(raw4, raw6):
    ifaces = {}
    for name, data in sorted(to_tag_dict(raw4 or {}).items()):
        entry = _af4_entry_from_device(data or {})
        if entry:
            ifaces.setdefault(name, {"name": name, "address_family": []})
            ifaces[name]["address_family"].append({"afi": "ipv4", **entry})
    for name, data in sorted(to_tag_dict(raw6 or {}).items()):
        entry = _af6_entry_from_device(data or {})
        if entry:
            ifaces.setdefault(name, {"name": name, "address_family": []})
            ifaces[name]["address_family"].append({"afi": "ipv6", **entry})
    return sorted(ifaces.values(), key=lambda i: i["name"])


def build_commands(config, raw_have, state):
    raw4, raw6 = raw_have
    config = config or []

    if state == "deleted":
        cmds = []
        if not config:
            for name in raw4 or {}:
                cmds.append(("delete", _BASE4 + [name]))
            for name in raw6 or {}:
                cmds.append(("delete", _BASE6 + [name]))
            return cmds
        for entry in config:
            name = entry.get("name")
            if not name:
                continue
            want_afis = {af.get("afi") for af in (entry.get("address_family") or [])}
            if not want_afis:
                if name in (raw4 or {}):
                    cmds.append(("delete", _BASE4 + [name]))
                if name in (raw6 or {}):
                    cmds.append(("delete", _BASE6 + [name]))
            else:
                if "ipv4" in want_afis and name in (raw4 or {}):
                    cmds.append(("delete", _BASE4 + [name]))
                if "ipv6" in want_afis and name in (raw6 or {}):
                    cmds.append(("delete", _BASE6 + [name]))
        return cmds

    want4, want6 = _want_to_device(config)
    have_argspec = _device_to_argspec(raw4, raw6)
    norm4, norm6 = _want_to_device(have_argspec)

    commands = []
    if state == "overridden":
        commands += dict_op(want4, norm4, _BASE4, op="purge")
        commands += dict_op(want6, norm6, _BASE6, op="purge")
    elif state == "replaced":
        # Scoped per named interface (matching every other module's
        # "replaced only touches what's named" semantic), and per AFI
        # within it, since IPv4/IPv6 are separate device subtrees.
        for entry in config:
            name = entry.get("name")
            if not name:
                continue
            for af in entry.get("address_family") or []:
                afi = af.get("afi")
                if afi == "ipv4":
                    commands += dict_op(
                        want4.get(name, {}),
                        norm4.get(name, {}),
                        _BASE4 + [name],
                        op="purge",
                    )
                elif afi == "ipv6":
                    commands += dict_op(
                        want6.get(name, {}),
                        norm6.get(name, {}),
                        _BASE6 + [name],
                        op="purge",
                    )
    commands += dict_op(want4, norm4, _BASE4, op="set")
    commands += dict_op(want6, norm6, _BASE6, op="set")
    return commands


_AUTH_OPTIONS = dict(
    plaintext_password=dict(type="str", no_log=True),
    md5_key=dict(
        type="dict",
        no_log=True,
        options=dict(
            key_id=dict(type="int"),
            key=dict(type="str", no_log=True),
        ),
    ),
)

_AF_OPTIONS = dict(
    afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
    authentication=dict(type="dict", options=_AUTH_OPTIONS),
    bandwidth=dict(type="int"),
    cost=dict(type="int"),
    dead_interval=dict(type="int"),
    hello_interval=dict(type="int"),
    ifmtu=dict(type="int"),
    instance=dict(type="str"),
    mtu_ignore=dict(type="bool"),
    network=dict(
        type="str",
        choices=["broadcast", "non-broadcast", "point-to-multipoint", "point-to-point"],
    ),
    passive=dict(type="bool"),
    priority=dict(type="int"),
    retransmit_interval=dict(type="int"),
    transmit_delay=dict(type="int"),
)

_ENTRY_OPTIONS = dict(
    name=dict(type="str", required=True),
    address_family=dict(type="list", elements="dict", options=_AF_OPTIONS),
)

ARGUMENT_SPEC = dict(
    config=dict(type="list", elements="dict", options=_ENTRY_OPTIONS),
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

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(*raw_have)
    for iface in have:
        for af in iface.get("address_family") or []:
            cast_by_spec(af, _AF_OPTIONS)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have, after=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after_raw = get_running_config(vyos)
        after = _device_to_argspec(*after_raw)
        for iface in after:
            for af in iface.get("address_family") or []:
                cast_by_spec(af, _AF_OPTIONS)
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
