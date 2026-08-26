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
            description: Network type.
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
    state: merged
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

_IPV6_RENAMES = {"instance": "instance-id"}


def _derive_key_field(options_spec):
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption to serve as the key field, "
            "found: {0}".format(required),
        )
    return required[0]


def _kebab_fields(d):
    cleaned = autoclean(d)
    return {k.replace("_", "-"): v for k, v in cleaned.items()}


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


def _auth_to_device(auth):
    if not auth:
        return {}
    device = {}
    if auth.get("plaintext_password"):
        device["plaintext-password"] = auth["plaintext_password"]
    md5 = auth.get("md5_key") or {}
    if md5.get("key_id") is not None and md5.get("key") is not None:
        device["md5"] = {"key-id": {str(md5["key_id"]): {"md5-key": md5["key"]}}}
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
    """VyOS's REST API collapses a single-child tag node to a plain
    string (or a list for multiple) -- confirmed by reproduction: an
    unguarded .get("interface", ...) on a non-dict response raises
    AttributeError, and consuming an unnormalized raw4/raw6 downstream
    (e.g. in build_commands's deleted branch) iterates a collapsed
    string's individual characters as if they were interface names,
    producing corrupted delete paths. Guarding the unwrap and
    normalizing via to_tag_dict here means every caller always
    receives a genuine {name: {...}} dict, with no need to re-guard
    at each use site.
    """
    raw4 = vyos.get_config(_BASE4) or {}
    if isinstance(raw4, dict):
        raw4 = raw4.get("interface", raw4)
    raw4 = to_tag_dict(raw4)

    raw6 = vyos.get_config(_BASE6) or {}
    if isinstance(raw6, dict):
        raw6 = raw6.get("interface", raw6)
    raw6 = to_tag_dict(raw6)

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


def _validate_config(config):
    """Confirmed real bugs, both by reproduction:

    1. md5_key.key/key_id were checked by truthiness, not presence --
       key_id set without key reached _auth_to_device and produced
       {"md5-key": None} in the generated command (a broken device
       write, not a validation failure); an empty-string key without
       key_id silently passed validation and then got dropped
       entirely by _auth_to_device's own key_id is not None check
       (the original confirmed bug, just reachable via a second
       value). is not None checks catch both directions and don't
       treat a legitimately-empty (but explicitly set) value as
       "unset".

    2. authentication is documented and confirmed (via vyos-1x
       schema) as IPv4-only -- OSPFv3's interface config has no
       authentication node at all -- but the shared argspec doesn't
       enforce this, and _af6_entry_to_device would silently forward
       it into the ipv6 device path, where the real device would
       reject it at apply time instead of failing cleanly upfront.
    """
    for entry in config or []:
        name = entry.get("name")
        for af in entry.get("address_family") or []:
            afi = af.get("afi")
            auth = af.get("authentication") or {}

            if afi == "ipv6" and auth:
                return (
                    "address_family.authentication was set for interface "
                    "'{0}' with afi: ipv6 -- authentication is IPv4-only "
                    "and has no corresponding OSPFv3 device path.".format(name)
                )

            md5 = auth.get("md5_key") or {}
            has_key = md5.get("key") is not None
            has_key_id = md5.get("key_id") is not None
            if has_key != has_key_id:
                return (
                    "address_family.authentication.md5_key.key and .key_id "
                    "were not both set for interface '{0}' -- both are "
                    "required together.".format(name)
                )
    return None


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
        # Confirmed bug: an interface present on the raw device with
        # an entirely empty per-AFI entry (bare presence, nothing
        # configured under it) produces {} from _af*_entry_from_device,
        # which _device_to_argspec silently omits -- invisible to both
        # want and norm_have, so dict_op's purge above (which only
        # ever iterates have's own keys) can never generate a delete
        # for it. These names are, by construction, guaranteed absent
        # from norm4/norm6, so there's no risk of duplicating a delete
        # dict_op already issued.
        for name in raw4 or {}:
            if name not in norm4 and name not in want4:
                commands.append(("delete", _BASE4 + [name]))
        for name in raw6 or {}:
            if name not in norm6 and name not in want6:
                commands.append(("delete", _BASE6 + [name]))
    elif state == "replaced":
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

    validation_error = _validate_config(config)
    if validation_error:
        module.fail_json(msg=validation_error)

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
