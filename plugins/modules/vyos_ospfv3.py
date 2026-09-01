#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv3
short_description: Manage OSPFv3 configuration on VyOS devices using REST API
description:
  - Manages OSPFv3 configuration on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - >-
    Scope matches the current vyos.vyos.vyos_ospfv3 (CLI collection) module,
    confirmed against VyOS's official documentation (1.4+/1.5 LTS/rolling).
  - >-
    C(areas.interface) (an area-to-interface assignment list) exists in the
    CLI module's argspec but was deliberately NOT carried over here --
    confirmed via VyOS's official docs across multiple versions that
    C(set protocols ospfv3 area <id> interface <name>) is the superseded,
    1.3-era syntax. The current mechanism, C(set protocols ospfv3 interface
    <name> area <id>), is a per-interface setting and is modeled in
    M(vyos.rest.vyos_ospf_interfaces)'s C(area) field instead.
  - >-
    C(distance) and C(graceful-restart) are real, confirmed OSPFv3 features
    not modeled here, matching a genuine gap in the CLI module's own scope
    rather than an oversight.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: OSPFv3 configuration.
    type: dict
    suboptions:
      areas:
        description: OSPFv3 areas.
        type: list
        elements: dict
        suboptions:
          area_id:
            description: Area identity.
            type: str
            required: true
          export_list:
            description: Name of export-list.
            type: str
          import_list:
            description: Name of import-list.
            type: str
          range:
            description: Summarize routes matching prefix (border routers only).
            type: list
            elements: dict
            suboptions:
              address:
                description: IPv6 prefix.
                type: str
                required: true
              advertise:
                description: Advertise this range.
                type: bool
              not_advertise:
                description: Do not advertise this range.
                type: bool
      parameters:
        description: OSPFv3 global parameters.
        type: dict
        suboptions:
          router_id:
            description: Router ID (IPv4 address format).
            type: str
      redistribute:
        description: Redistribute routes from another protocol.
        type: list
        elements: dict
        suboptions:
          route_type:
            description: Protocol to redistribute.
            type: str
            choices: [bgp, connected, kernel, ripng, static]
          route_map:
            description: Route map to apply.
            type: str
  state:
    description:
      - Desired state of the OSPFv3 configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces the entire OSPFv3 configuration.
      - C(deleted) removes OSPFv3 configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
seealso:
  - module: vyos.vyos.vyos_ospfv3
  - module: vyos.rest.vyos_ospf_interfaces
"""

EXAMPLES = r"""
- name: Merge OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    config:
      parameters:
        router_id: 192.0.2.10
      redistribute:
        - route_type: bgp
      areas:
        - area_id: "2"
          export_list: export1
          import_list: import1
          range:
            - address: "2001:db10::/32"
            - address: "2001:db20::/32"
    state: merged

- name: Delete all OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    state: deleted

- name: Gather current OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    state: gathered
"""

RETURN = r"""
before:
  description: OSPFv3 configuration before this module ran.
  returned: always
  type: dict
after:
  description: OSPFv3 configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current OSPFv3 configuration as structured data.
  returned: when state is gathered
  type: dict
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


_BASE = ["protocols", "ospfv3"]


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
    Safe here since every call site is a leaf-level dict of schema
    field names, never an opaque tag-node value like an area ID used
    as a dict key.
    """
    cleaned = autoclean(d)
    return {k.replace("_", "-"): v for k, v in cleaned.items()}


def _derive_key_field(options_spec):
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


# ---------------------------------------------------------------------------
# range -- confirmed against CLI: advertise/not_advertise are presence-
# only opposite flags (not both meaningful at once, though the argspec
# doesn't enforce mutual exclusivity -- matching the CLI's own scope).
# Fully generic once keyed by address.
# ---------------------------------------------------------------------------

_RANGE_KEY = "address"


def _area_entry_to_device(rest):
    exclude = {"range"}
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    ranges = rest.get("range") or []
    if ranges:
        device["range"] = _keyed_list_to_device(ranges, _RANGE_KEY)
    return device


def _area_entry_from_device(data):
    exclude = {"range"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})
    range_raw = data.get("range")
    if range_raw:
        entry["range"] = _keyed_list_from_device(range_raw, _RANGE_KEY)
    return entry


_REDISTRIBUTE_KEY = "route_type"
_AREA_KEY = "area_id"


def _want_to_device(config):
    config = config or {}
    device = {}

    areas = config.get("areas") or []
    if areas:
        device["area"] = _keyed_list_to_device(areas, _AREA_KEY, _area_entry_to_device)

    params_device = _kebab_fields(config.get("parameters") or {})
    if params_device:
        device["parameters"] = params_device

    redist = config.get("redistribute") or []
    if redist:
        device["redistribute"] = _keyed_list_to_device(redist, _REDISTRIBUTE_KEY)

    return device


def get_running_config(vyos):
    """VyOS's REST API collapses a single-child tag node to a plain
    string (or a list for multiple) -- confirmed as a real failure
    mode during vyos_ospf_interfaces's build (an unguarded response
    iterated character-by-character). Normalizing through to_tag_dict
    unconditionally means callers always receive a genuine dict.
    """
    return to_tag_dict(vyos.get_config(_BASE) or {})


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    entry = {}

    area_raw = raw.get("area")
    if area_raw:
        areas = _keyed_list_from_device(area_raw, _AREA_KEY, _area_entry_from_device)
        if areas:
            entry["areas"] = areas

    params_raw = raw.get("parameters")
    if params_raw:
        entry["parameters"] = from_device(params_raw)

    redist_raw = raw.get("redistribute")
    if redist_raw:
        entry["redistribute"] = _keyed_list_from_device(redist_raw, _REDISTRIBUTE_KEY)

    return entry


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}

    if state == "deleted":
        return [("delete", _BASE)] if raw_have else []

    want = _want_to_device(config)
    norm_have = _want_to_device(_device_to_argspec(raw_have))

    commands = []
    if state == "replaced":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


_RANGE_OPTIONS = dict(
    address=dict(type="str", required=True),
    advertise=dict(type="bool"),
    not_advertise=dict(type="bool"),
)

_AREA_OPTIONS = dict(
    area_id=dict(type="str", required=True),
    export_list=dict(type="str"),
    import_list=dict(type="str"),
    range=dict(type="list", elements="dict", options=_RANGE_OPTIONS),
)

_PARAMETERS_OPTIONS = dict(
    router_id=dict(type="str"),
)

_REDISTRIBUTE_OPTIONS = dict(
    route_type=dict(type="str", choices=["bgp", "connected", "kernel", "ripng", "static"]),
    route_map=dict(type="str"),
)

_CONFIG_OPTIONS = dict(
    areas=dict(type="list", elements="dict", options=_AREA_OPTIONS),
    parameters=dict(type="dict", options=_PARAMETERS_OPTIONS),
    redistribute=dict(type="list", elements="dict", options=_REDISTRIBUTE_OPTIONS),
)

ARGUMENT_SPEC = dict(
    config=dict(type="dict", options=_CONFIG_OPTIONS),
    state=dict(
        default="merged",
        choices=["merged", "replaced", "deleted", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    cast_by_spec(have, _CONFIG_OPTIONS)

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
        cast_by_spec(after, _CONFIG_OPTIONS)
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
