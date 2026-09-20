#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_vrf
short_description: Manage VRF configuration on VyOS devices using REST API
description:
  - Manages Virtual Routing and Forwarding (VRF) instances on VyOS devices
    via the REST API.
  - Supports merged, replaced, overridden, deleted, and gathered states.
  - Protocol configuration within VRFs (BGP, OSPFv2, static routes) is
    managed inline with focused scope (core fields only).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: VRF configuration.
    type: dict
    suboptions:
      bind_to_all:
        description:
          - Enable binding services to all VRFs.
          - Omit this option entirely to leave the current device setting
            untouched. Only set it explicitly (C(true) or C(false)) when you
            want this module to manage it.
        type: bool
      instances:
        description: List of VRF instances.
        type: list
        elements: dict
        suboptions:
          name:
            description: VRF instance name.
            type: str
            required: true
          description:
            description: VRF description.
            type: str
          disable:
            description: Administratively disable this VRF.
            type: bool
            default: false
          table_id:
            description:
              - Routing table ID associated with this VRF.
              - The device enforces the valid range and rejects an invalid
                value with its own error message.
              - VyOS does not support changing an existing VRF's table ID
                in place -- it must be deleted and recreated. C(state=merged)
                and C(state=replaced) fail with a clear error if this
                differs from the current device value, rather than
                silently deleting and recreating the VRF. Use
                C(state=overridden) (which deletes and recreates the VRF,
                re-applying every other desired field, since it already
                replaces everything to match C(config)), or explicitly run
                C(state=deleted) followed by C(state=merged)/C(replaced)
                as separate tasks.
            type: int
          vni:
            description: Virtual Network Identifier.
            type: int
          address_family:
            description: Address family configuration.
            type: list
            elements: dict
            suboptions:
              afi:
                description: Address family identifier.
                type: str
                required: true
                choices: [ipv4, ipv6]
              disable_forwarding:
                description: Disable IP forwarding for this address family.
                type: bool
                default: false
              nht_no_resolve_via_default:
                description: Disable next-hop resolution via default route.
                type: bool
                default: false
              route_maps:
                description: Route maps applied per protocol.
                type: list
                elements: dict
                suboptions:
                  protocol:
                    description: Protocol to which the route map applies.
                    type: str
                    required: true
                    choices: [any, babel, bgp, eigrp, isis, ospf, rip, static]
                  rm_name:
                    description: Route map name.
                    type: str
                    required: true
          protocols:
            description: Protocol configuration within this VRF instance.
            type: dict
            suboptions:
              bgp:
                description: BGP protocol configuration (core fields only).
                type: dict
                suboptions:
                  system_as:
                    description: BGP autonomous system number.
                    type: int
                  neighbor:
                    description: BGP neighbors.
                    type: list
                    elements: dict
                    suboptions:
                      address:
                        description: Neighbor IP address.
                        type: str
                        required: true
                      remote_as:
                        description: Neighbor AS number.
                        type: int
                      description:
                        description: Neighbor description.
                        type: str
              ospf:
                description: OSPFv2 protocol configuration (core fields only).
                type: dict
                suboptions:
                  areas:
                    description: OSPF areas.
                    type: list
                    elements: dict
                    suboptions:
                      area_id:
                        description: OSPF area identifier.
                        type: str
                        required: true
                      networks:
                        description: Networks in this area.
                        type: list
                        elements: str
                  parameters:
                    description: OSPF parameters.
                    type: dict
                    suboptions:
                      router_id:
                        description: OSPF router ID.
                        type: str
              static:
                description: Static routes configuration.
                type: dict
                suboptions:
                  routes:
                    description: Static routes.
                    type: list
                    elements: dict
                    suboptions:
                      dest:
                        description: Destination prefix.
                        type: str
                        required: true
                      next_hops:
                        description: Next-hop IP addresses.
                        type: list
                        elements: str
  state:
    description: Desired state of the VRF configuration.
    type: str
    default: merged
    choices: [merged, replaced, overridden, deleted, gathered]
"""

EXAMPLES = r"""
- name: Merge VRF instances
  vyos.rest.vyos_vrf:
    config:
      bind_to_all: true
      instances:
        - name: vrf1
          description: Red VRF
          table_id: 101
          vni: 501
          protocols:
            bgp:
              system_as: 65001
              neighbor:
                - address: 10.0.0.1
                  remote_as: 65002
            ospf:
              areas:
                - area_id: "0"
                  networks:
                    - 10.0.0.0/24
              parameters:
                router_id: 10.0.0.1
            static:
              routes:
                - dest: 192.168.10.0/24
                  next_hops:
                    - 10.0.0.254
    state: merged

- name: Delete specific VRF
  vyos.rest.vyos_vrf:
    config:
      instances:
        - name: vrf1
    state: deleted

- name: Delete all VRF configuration
  vyos.rest.vyos_vrf:
    state: deleted

- name: Gather current VRF configuration
  vyos.rest.vyos_vrf:
    state: gathered
"""

RETURN = r"""
before:
  description: VRF configuration before this module ran.
  returned: state is not gathered
  type: dict
after:
  description: VRF configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: state is not gathered
  type: list
gathered:
  description: Current VRF configuration as structured data.
  returned: when state is gathered
  type: dict
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
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


_BASE = ["vrf"]

# ---------------------------------------------------------------------------
# Field name renames: argspec key -> device key.
# Only entries that cannot be derived by mechanical snake_case <-> kebab-case
# conversion, or where the device uses a completely different name.
#
#   table_id  -> table        argspec uses _id suffix, device does not
#   system_as -> system-as    hyphen in middle (mechanical would also work,
#                             declared here for explicitness)
#   remote_as -> remote-as    same
#   rm_name   -> route-map    completely different device leaf name
#   next_hops -> next-hop     plural vs singular + hyphen
#   areas     -> area         device uses singular tag-node name
#   routes    -> route        device uses singular tag-node name
# ---------------------------------------------------------------------------
_DEVICE_RENAMES = {
    "table_id": "table",
    "system_as": "system-as",
    "remote_as": "remote-as",
    "rm_name": "route-map",
    "next_hops": "next-hop",
    "areas": "area",
    "routes": "route",
    "bind_to_all": "bind-to-all",
    "router_id": "router-id",
}


# ---------------------------------------------------------------------------
# Generic helpers — same pattern as vyos_snmp_server
# ---------------------------------------------------------------------------


def _derive_key_field(options_spec):
    """Derive the tag-node key field — the one required=True suboption."""
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption, found: {0}".format(required),
        )
    return required[0]


def _keyed_list_to_device(items, key_field, entry_transform=None):
    """Convert argspec list of dicts to device tag-node dict keyed by key_field."""
    result = {}
    for item in items or []:
        if not item.get(key_field):
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        entry = entry_transform(rest) if entry_transform else autoclean(rest)
        result[item[key_field]] = entry
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None):
    """Convert device tag-node dict to argspec list of dicts with key_field."""
    return [
        (
            {key_field: key, **entry_transform(data or {})}
            if entry_transform
            else {key_field: key, **from_device(data or {})}
        )
        for key, data in sorted(to_tag_dict(raw).items())
    ]


# ---------------------------------------------------------------------------
# Structural entry overrides: sections where the device layout requires
# something beyond a field rename. Each entry:
#   argspec_key -> (to_device_fn, from_device_fn)
# The to/from functions receive/return the entry dict WITHOUT the key field.
# ---------------------------------------------------------------------------

# neighbor entries: fields use _DEVICE_RENAMES (remote_as -> remote-as),
# so we need _spec_to_device recursion, not plain autoclean.
# Defined after _spec_to_device is declared — see _ENTRY_OVERRIDES assignment.


# area entries: networks is a plain sorted list leaf, not a tag node.
def _area_to_device(rest):
    d = {}
    if rest.get("networks"):
        d["network"] = sorted(rest["networks"])
    return d


def _area_from_device(raw):
    raw = raw or {}
    entry = {}
    networks_raw = raw.get("network")
    if networks_raw:
        if isinstance(networks_raw, str):
            entry["networks"] = [networks_raw]
        elif isinstance(networks_raw, list):
            entry["networks"] = sorted(networks_raw)
        elif isinstance(networks_raw, dict):
            entry["networks"] = sorted(networks_raw.keys())
    return entry


# route entries: next-hop is a tag node keyed by address, value is presence {}.
def _route_to_device(rest):
    d = {}
    if rest.get("next_hops"):
        d["next-hop"] = {nh: {} for nh in rest["next_hops"]}
    return d


def _route_from_device(raw):
    raw = raw or {}
    entry = {}
    next_hops_raw = raw.get("next-hop") or {}
    if isinstance(next_hops_raw, dict):
        nhs = sorted(next_hops_raw.keys())
        if nhs:
            entry["next_hops"] = nhs
    elif isinstance(next_hops_raw, str):
        entry["next_hops"] = [next_hops_raw]
    return entry


# ---------------------------------------------------------------------------
# Generic recursive walkers — driven by ARGUMENT_SPEC + _DEVICE_RENAMES
# + _ENTRY_OVERRIDES. Same pattern as vyos_snmp_server.
# ---------------------------------------------------------------------------


def _spec_to_device(value, options_spec):
    """Recursively convert argspec dict to device dict."""
    if not isinstance(value, dict):
        return value
    result = {}
    for arg_key, sub_spec in options_spec.items():
        val = value.get(arg_key)
        if val is None or val is False:
            continue
        device_key = _DEVICE_RENAMES.get(arg_key, arg_key)
        sub_type = sub_spec.get("type")
        sub_options = sub_spec.get("options")
        if sub_type == "dict" and sub_options:
            converted = _spec_to_device(val, sub_options)
            if converted:
                result[device_key] = converted
        elif sub_type == "list" and sub_options:
            key_field = _derive_key_field(sub_options)
            entry_to, entry_from_unused = _ENTRY_OVERRIDES.get(arg_key, (None, None))
            entry_transform = entry_to or (
                lambda rest, spec=sub_options: _spec_to_device(rest, spec)
            )
            result[device_key] = _keyed_list_to_device(val, key_field, entry_transform)
        elif val is True:
            result[device_key] = {}
        elif sub_type == "list":
            result[device_key] = list(val)
        else:
            result[device_key] = val
    return result


def _device_to_spec(raw, options_spec):
    """Recursively convert device dict to argspec dict."""
    if not raw or not isinstance(raw, dict):
        return {}
    have_idx = {k.replace("-", "_"): k for k in raw}
    result = {}
    for arg_key, sub_spec in options_spec.items():
        device_key = _DEVICE_RENAMES.get(arg_key, arg_key)
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
            entry_to_unused, entry_from = _ENTRY_OVERRIDES.get(arg_key, (None, None))
            entry_transform = entry_from or (lambda d, spec=sub_options: _device_to_spec(d, spec))
            entries = _keyed_list_from_device(raw_val, key_field, entry_transform)
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


# Entry overrides — defined after _spec_to_device so neighbor can use it.
# neighbor uses _spec_to_device recursion to apply _DEVICE_RENAMES
# (remote_as -> remote-as) inside each neighbor entry.
_ENTRY_OVERRIDES = {
    "areas": (_area_to_device, _area_from_device),
    "routes": (_route_to_device, _route_from_device),
}
# neighbor: use generic _spec_to_device with neighbor sub-options.
# Cannot declare inline above because _spec_to_device not yet defined.
# Assigned after ARGUMENT_SPEC is defined (see bottom of file).


# ---------------------------------------------------------------------------
# VRF address_family — bespoke because device uses ip/ipv6 as keys
# (not a standard tag node with argspec-named keys)
# nht_no_resolve_via_default maps to nested nht.no-resolve-via-default
# ---------------------------------------------------------------------------

_AFI_TO_DEVICE = {"ipv4": "ip", "ipv6": "ipv6"}
_AFI_FROM_DEVICE = {"ip": "ipv4", "ipv6": "ipv6"}


def _af_to_device(af):
    """Single address_family entry -> device ip/ipv6 subtree."""
    d = {}
    if af.get("disable_forwarding"):
        d["disable-forwarding"] = {}
    if af.get("nht_no_resolve_via_default"):
        d["nht"] = {"no-resolve-via-default": {}}
    for rm in af.get("route_maps") or []:
        proto = rm.get("protocol")
        rm_name = rm.get("rm_name")
        if proto and rm_name:
            d.setdefault("protocol", {})[proto] = {"route-map": rm_name}
    return d


def _af_from_device(afi_key, raw):
    """Device ip/ipv6 subtree -> single address_family entry."""
    raw = raw or {}
    entry = {"afi": _AFI_FROM_DEVICE.get(afi_key, afi_key)}
    if "disable-forwarding" in raw:
        entry["disable_forwarding"] = True
    nht = raw.get("nht") or {}
    if isinstance(nht, dict) and "no-resolve-via-default" in nht:
        entry["nht_no_resolve_via_default"] = True
    proto_raw = raw.get("protocol") or {}
    if isinstance(proto_raw, dict):
        rms = [
            {"protocol": p, "rm_name": (d or {}).get("route-map")}
            for p, d in proto_raw.items()
            if (d or {}).get("route-map")
        ]
        if rms:
            entry["route_maps"] = rms
    return entry


# ---------------------------------------------------------------------------
# VRF instance converters
# ---------------------------------------------------------------------------


def _instance_to_device(inst):
    """argspec instance -> device VRF entry (non-protocol fields)."""
    d = _spec_to_device(
        {k: v for k, v in inst.items() if k not in ("name", "address_family", "protocols")},
        _INSTANCE_OPTIONS,
    )
    for af in inst.get("address_family") or []:
        afi = af.get("afi")
        if afi:
            dev_key = _AFI_TO_DEVICE.get(afi, afi)
            af_data = _af_to_device(af)
            if af_data:
                d[dev_key] = af_data
    return d


def _instance_from_device(name, raw):
    """Device VRF entry -> argspec instance (non-protocol fields)."""
    raw_base = {k: v for k, v in raw.items() if k not in ("ip", "ipv6", "protocols")}
    inst = {"name": name}
    d = _device_to_spec(raw_base, _INSTANCE_OPTIONS)
    cast_by_spec(d, _INSTANCE_OPTIONS)
    inst.update({k: v for k, v in d.items() if k not in ("address_family", "protocols")})
    afs = [_af_from_device(key, raw[key]) for key in ("ip", "ipv6") if key in raw and raw[key]]
    if afs:
        inst["address_family"] = afs
    return inst


# ---------------------------------------------------------------------------
# Top-level config converters
# ---------------------------------------------------------------------------


def _config_to_device(config):
    """Top-level argspec config -> device dict."""
    config = config or {}
    result = _spec_to_device(
        {k: v for k, v in config.items() if k != "instances"},
        _TOP_OPTIONS,
    )
    name_dict = {
        inst["name"]: _instance_to_device(inst)
        for inst in config.get("instances") or []
        if inst.get("name")
    }
    if name_dict:
        result["name"] = name_dict
    return result


def _device_to_argspec(raw):
    """Device raw config -> argspec (non-protocol fields)."""
    raw = raw or {}
    result = _device_to_spec(
        {k: v for k, v in raw.items() if k != "name"},
        _TOP_OPTIONS,
    )
    name_raw = raw.get("name") or {}
    if isinstance(name_raw, dict):
        instances = [
            _instance_from_device(vrf_name, vrf_data or {})
            for vrf_name, vrf_data in sorted(name_raw.items())
        ]
        if instances:
            result["instances"] = instances
    return result


# ---------------------------------------------------------------------------
# Protocol converters — generic walkers with protocol sub-specs
# ---------------------------------------------------------------------------


def _routes_to_device(routes):
    """Split routes by address family -- VyOS requires IPv4 static
    routes under "route" and IPv6 under "route6" as genuinely separate
    device subtrees (confirmed against VyOS's own interface-definitions
    schema: static-route.xml.i and static-route6.xml.i are distinct
    includes, not a single shared "route" path for both families).
    """
    device = {}
    for entry in routes or []:
        dest = entry.get("dest")
        if not dest:
            continue
        container = "route6" if ":" in dest else "route"
        route_device = _route_to_device({k: v for k, v in entry.items() if k != "dest"})
        device.setdefault(container, {})[dest] = route_device
    return device


def _routes_from_device(raw):
    """Inverse of _routes_to_device -- merge the route and route6
    device subtrees back into a single argspec routes list."""
    entries = []
    for container in ("route", "route6"):
        raw_container = (raw or {}).get(container)
        if raw_container:
            entries += _keyed_list_from_device(raw_container, "dest", _route_from_device)
    return sorted(entries, key=lambda e: e["dest"])


def _proto_to_device(proto_config, proto_key):
    """argspec protocol config -> device protocol dict."""
    if proto_key == "static":
        return _routes_to_device((proto_config or {}).get("routes"))
    result = _spec_to_device(proto_config or {}, _PROTO_OPTIONS[proto_key]["options"])
    return result


def _proto_from_device(raw, proto_key):
    """Device protocol dict -> argspec protocol config."""
    if proto_key == "static":
        routes = _routes_from_device(raw)
        return {"routes": routes} if routes else {}
    result = _device_to_spec(raw or {}, _PROTO_OPTIONS[proto_key]["options"])
    cast_by_spec(result, _PROTO_OPTIONS[proto_key]["options"])
    return result


# ---------------------------------------------------------------------------
# Protocol dispatch — single source of truth.
# Adding a new protocol: one entry in _PROTO_HANDLERS + argspec only.
# ---------------------------------------------------------------------------

_PROTO_HANDLERS = ["bgp", "ospf", "static"]

# Tag-node containers per protocol (device key name) — used for placeholder seeding.
_PROTO_TAG_CONTAINERS = {
    "bgp": ["neighbor"],
    "ospf": ["area"],
    "static": ["route", "route6"],
}


def _protocols_from_device(raw_vrf):
    """Extract and convert all protocol configs from raw VRF device data."""
    proto_raw = (raw_vrf or {}).get("protocols") or {}
    result = {}
    for proto_key in _PROTO_HANDLERS:
        if proto_raw.get(proto_key):
            converted = _proto_from_device(proto_raw[proto_key], proto_key)
            if converted:
                result[proto_key] = converted
    return result or None


def _seed_tag_node_placeholders(want, have, proto_key):
    """Seed empty placeholders for new tag-node entries so dict_op uses
    verbatim keys rather than guessing a kebab-case translation."""
    for container in _PROTO_TAG_CONTAINERS.get(proto_key, []):
        want_entries = want.get(container) or {}
        if isinstance(want_entries, dict):
            have.setdefault(container, {})
            for entry_key in want_entries:
                have[container].setdefault(entry_key, {})


def _protocol_commands(vrf_name, protocols, raw_proto, state):
    """Generate protocol commands for a VRF instance."""
    cmds = []
    for proto_key in _PROTO_HANDLERS:
        want_proto = (protocols or {}).get(proto_key)
        raw_have_proto = (raw_proto or {}).get(proto_key) or {}

        if want_proto is None and state not in ("overridden", "replaced"):
            continue

        if want_proto is None:
            if raw_have_proto:
                cmds.append(("delete", _BASE + ["name", vrf_name, "protocols", proto_key]))
            continue

        proto_base = _BASE + ["name", vrf_name, "protocols", proto_key]
        want = _proto_to_device(want_proto, proto_key)
        norm_have = _proto_to_device(
            _proto_from_device(raw_have_proto, proto_key),
            proto_key,
        )
        _seed_tag_node_placeholders(want, norm_have, proto_key)

        if state in ("overridden", "replaced"):
            cmds += dict_op(want, norm_have, proto_base, op="purge")
        cmds += dict_op(want, norm_have, proto_base, op="set")
    return cmds


# ---------------------------------------------------------------------------
# Running config
# ---------------------------------------------------------------------------


def get_running_config(vyos):
    try:
        return vyos.get_config(_BASE) or {}
    except Exception as exc:
        if "Configuration under specified path is empty" in str(exc):
            return {}
        raise


# ---------------------------------------------------------------------------
# Build commands
# ---------------------------------------------------------------------------


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or {}
    cmds = []

    if state == "deleted":
        instances = config.get("instances") or []
        if not instances:
            return [("delete", _BASE)] if raw_have else []
        for inst in instances:
            vrf_name = inst.get("name")
            if vrf_name and (raw_have.get("name") or {}).get(vrf_name) is not None:
                cmds.append(("delete", _BASE + ["name", vrf_name]))
        if "bind_to_all" in config and config["bind_to_all"] is False and "bind-to-all" in raw_have:
            cmds.append(("delete", _BASE + ["bind-to-all"]))
        return cmds

    want = _config_to_device(config)
    norm_have = _config_to_device(_device_to_argspec(raw_have))

    # Seed placeholders for new VRF instances (verbatim tag-node keys)
    for vrf_name in want.get("name") or {}:
        norm_have.setdefault("name", {}).setdefault(vrf_name, {})

    # VyOS's routing table ID cannot be modified in place once assigned --
    # confirmed via VyOS's own official documentation ("A routing table ID
    # can not be modified once it is assigned. It can only be changed by
    # deleting and re-adding the VRF instance") and its source
    # (ConfigError: "VRF ... table id modification not possible!"). This
    # module never does that destructive delete-and-recreate silently
    # under merged/replaced -- only overridden's own explicit contract
    # ("replace everything to match want, destructively if needed")
    # covers it; merged/replaced fail loudly instead, so a table_id
    # change is always something the user explicitly asked for via the
    # right state, not a surprise this module decided on their behalf.
    recreated_vrfs = set()
    for vrf_name, vrf_want in (want.get("name") or {}).items():
        vrf_have = (norm_have.get("name") or {}).get(vrf_name) or {}
        want_table = vrf_want.get("table")
        have_table = vrf_have.get("table")
        if want_table is None or have_table is None or str(want_table) == str(have_table):
            continue
        if state == "overridden":
            cmds.append(("delete", _BASE + ["name", vrf_name]))
            norm_have["name"][vrf_name] = {}
            recreated_vrfs.add(vrf_name)
        else:
            raise ValueError(
                "VRF '{name}': table_id cannot be changed in place under "
                "state={state} -- VyOS does not support modifying an "
                "existing VRF's routing table. Use state=overridden, or "
                "explicitly remove and recreate it with separate "
                "state=deleted and state=merged/replaced tasks.".format(
                    name=vrf_name,
                    state=state,
                ),
            )

    if state == "overridden":
        cmds += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        for vrf_name, vrf_want in (want.get("name") or {}).items():
            vrf_have = (norm_have.get("name") or {}).get(vrf_name) or {}
            cmds += dict_op(vrf_want, vrf_have, _BASE + ["name", vrf_name], op="purge")
        if "bind-to-all" not in want and "bind-to-all" in norm_have:
            cmds.append(("delete", _BASE + ["bind-to-all"]))

    cmds += dict_op(want, norm_have, _BASE, op="set")

    # Protocol commands per VRF instance
    for inst in config.get("instances") or []:
        vrf_name = inst.get("name")
        if not vrf_name:
            continue
        protocols = inst.get("protocols") or {}
        if vrf_name in recreated_vrfs:
            raw_vrf = {}
        else:
            raw_vrf = (raw_have.get("name") or {}).get(vrf_name) or {}
        raw_proto = raw_vrf.get("protocols") or {}
        if protocols or state in ("overridden", "replaced") or vrf_name in recreated_vrfs:
            cmds += _protocol_commands(vrf_name, protocols, raw_proto, state)

    return cmds


# ---------------------------------------------------------------------------
# Enrich have/after with protocol data
# ---------------------------------------------------------------------------


def _enrich_with_protocols(instances, raw_have):
    """Add protocol data to each instance dict in-place."""
    for inst in instances or []:
        raw_vrf = (raw_have.get("name") or {}).get(inst["name"]) or {}
        protocols = _protocols_from_device(raw_vrf)
        if protocols:
            inst["protocols"] = protocols


# ---------------------------------------------------------------------------
# ARGUMENT_SPEC
# ---------------------------------------------------------------------------

ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            bind_to_all=dict(type="bool"),
            instances=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    description=dict(type="str"),
                    disable=dict(type="bool", default=False),
                    table_id=dict(type="int"),
                    vni=dict(type="int"),
                    address_family=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                            disable_forwarding=dict(type="bool", default=False),
                            nht_no_resolve_via_default=dict(type="bool", default=False),
                            route_maps=dict(
                                type="list",
                                elements="dict",
                                options=dict(
                                    protocol=dict(
                                        type="str",
                                        required=True,
                                        choices=[
                                            "any",
                                            "babel",
                                            "bgp",
                                            "eigrp",
                                            "isis",
                                            "ospf",
                                            "rip",
                                            "static",
                                        ],
                                    ),
                                    rm_name=dict(type="str", required=True),
                                ),
                            ),
                        ),
                    ),
                    protocols=dict(
                        type="dict",
                        options=dict(
                            bgp=dict(
                                type="dict",
                                options=dict(
                                    system_as=dict(type="int"),
                                    neighbor=dict(
                                        type="list",
                                        elements="dict",
                                        options=dict(
                                            address=dict(type="str", required=True),
                                            remote_as=dict(type="int"),
                                            description=dict(type="str"),
                                        ),
                                    ),
                                ),
                            ),
                            ospf=dict(
                                type="dict",
                                options=dict(
                                    areas=dict(
                                        type="list",
                                        elements="dict",
                                        options=dict(
                                            area_id=dict(type="str", required=True),
                                            networks=dict(type="list", elements="str"),
                                        ),
                                    ),
                                    parameters=dict(
                                        type="dict",
                                        options=dict(
                                            router_id=dict(type="str"),
                                        ),
                                    ),
                                ),
                            ),
                            static=dict(
                                type="dict",
                                options=dict(
                                    routes=dict(
                                        type="list",
                                        elements="dict",
                                        options=dict(
                                            dest=dict(type="str", required=True),
                                            next_hops=dict(type="list", elements="str"),
                                        ),
                                    ),
                                ),
                            ),
                        ),
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


def _init_specs():
    """Initialize module-level spec references and entry overrides.
    Called once at import time via _init_specs(). Avoids module-level
    subscript expressions that confuse ansible-doc's AST walker.
    """
    top = ARGUMENT_SPEC["config"]["options"]
    instance_opts = top["instances"]["options"]
    proto_opts = instance_opts["protocols"]["options"]
    neighbor_opts = proto_opts["bgp"]["options"]["neighbor"]["options"]

    global _TOP_OPTIONS, _INSTANCE_OPTIONS, _PROTO_OPTIONS

    _TOP_OPTIONS = top
    _INSTANCE_OPTIONS = instance_opts
    _PROTO_OPTIONS = proto_opts

    def _neighbor_entry_to_device(rest):
        return _spec_to_device(rest, neighbor_opts)

    def _neighbor_entry_from_device(d):
        return _device_to_spec(d, neighbor_opts)

    _ENTRY_OVERRIDES["neighbor"] = (_neighbor_entry_to_device, _neighbor_entry_from_device)


_TOP_OPTIONS = {}
_INSTANCE_OPTIONS = {}
_PROTO_OPTIONS = {}
_init_specs()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)
    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    _enrich_with_protocols(have.get("instances"), raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    try:
        cmds = build_commands(config, raw_have, state)
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    if module.check_mode:
        module.exit_json(changed=bool(cmds), commands=cmds, before=have)

    if cmds:
        response = vyos.apply_commands(cmds)
        saved = vyos.save_config()
        raw_after = get_running_config(vyos)
        after = _device_to_argspec(raw_after)
        _enrich_with_protocols(after.get("instances"), raw_after)
        module.exit_json(
            changed=True,
            before=have,
            after=after,
            commands=cmds,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
