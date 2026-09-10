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
  - Protocol configuration within VRFs (BGP, OSPFv2, OSPFv3, static routes)
    is managed inline using the same logic as the dedicated protocol modules.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: VRF configuration.
    type: dict
    suboptions:
      bind_to_all:
        description: Enable binding services to all VRFs.
        type: bool
        default: false
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
            description: Routing table ID associated with this VRF.
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
                choices: ['ipv4', 'ipv6']
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
                    choices:
                      - any
                      - babel
                      - bgp
                      - eigrp
                      - isis
                      - ospf
                      - rip
                      - static
                  rm_name:
                    description: Route map name.
                    type: str
                    required: true
          protocols:
            description: Protocol configuration within this VRF instance.
            type: dict
            suboptions:
              bgp:
                description: BGP protocol configuration. Same options as vyos_bgp_global.
                type: dict
              ospf:
                description: OSPFv2 protocol configuration. Same options as vyos_ospfv2.
                type: dict
              ospfv3:
                description: OSPFv3 protocol configuration. Same options as vyos_ospfv3.
                type: dict
              static:
                description: Static routes configuration. Same options as vyos_static_routes.
                type: list
                elements: dict
  state:
    description: Desired state of the VRF configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
"""

EXAMPLES = r"""
- name: Merge VRF with BGP
  vyos.rest.vyos_vrf:
    config:
      instances:
        - name: vrf-blue
          table_id: 100
          protocols:
            bgp:
              system_as: 65001
              neighbor:
                - address: 10.0.0.1
                  remote_as: 65002
    state: merged

- name: Merge VRF with OSPFv2
  vyos.rest.vyos_vrf:
    config:
      instances:
        - name: vrf-red
          table_id: 101
          protocols:
            ospf:
              areas:
                - area_id: "0"
                  network:
                    - address: 10.1.0.0/24
    state: merged

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
  returned: always
  type: dict
after:
  description: VRF configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
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
    dict_op,
)


_BASE = ["vrf"]
_AFI_MAP = {"ipv4": "ip", "ipv6": "ipv6"}
_AFI_REVERSE = {"ip": "ipv4", "ipv6": "ipv6"}


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            bind_to_all=dict(type="bool", default=False),
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
                            afi=dict(
                                type="str",
                                required=True,
                                choices=["ipv4", "ipv6"],
                            ),
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
                                            next_hops=dict(
                                                type="list",
                                                elements="str",
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
    ),
    state=dict(
        type="str",
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered"],
    ),
)


def _af_to_device(af):
    result = {}
    if af.get("disable_forwarding"):
        result["disable-forwarding"] = {}
    if af.get("nht_no_resolve_via_default"):
        result["nht"] = {"no-resolve-via-default": {}}
    if af.get("route_maps"):
        protocol = {}
        for rm in af["route_maps"]:
            if rm.get("protocol") and rm.get("rm_name"):
                protocol[rm["protocol"]] = {"route-map": rm["rm_name"]}
        if protocol:
            result["protocol"] = protocol
    return result


def _af_from_device(afi_key, raw):
    if not raw or not isinstance(raw, dict):
        return None
    entry = {"afi": _AFI_REVERSE.get(afi_key, afi_key)}
    if "disable-forwarding" in raw:
        entry["disable_forwarding"] = True
    nht = raw.get("nht", {})
    if isinstance(nht, dict) and "no-resolve-via-default" in nht:
        entry["nht_no_resolve_via_default"] = True
    proto_raw = raw.get("protocol", {})
    if proto_raw and isinstance(proto_raw, dict):
        route_maps = []
        for proto, proto_data in proto_raw.items():
            if isinstance(proto_data, dict):
                rm_name = proto_data.get("route-map")
                if rm_name:
                    route_maps.append({"protocol": proto, "rm_name": rm_name})
        if route_maps:
            entry["route_maps"] = route_maps
    return entry


def _instance_to_device(instance):
    result = {}
    if instance.get("description"):
        result["description"] = instance["description"]
    if instance.get("disable"):
        result["disable"] = {}
    if instance.get("table_id") is not None:
        result["table"] = str(instance["table_id"])
    if instance.get("vni") is not None:
        result["vni"] = str(instance["vni"])
    for af in instance.get("address_family") or []:
        afi = af.get("afi")
        if not afi:
            continue
        device_afi_key = _AFI_MAP.get(afi, afi)
        af_data = _af_to_device(af)
        if af_data:
            result[device_afi_key] = af_data
    return result


def _instance_from_device(name, raw):
    if not raw or not isinstance(raw, dict):
        return {"name": name}
    instance = {"name": name}
    if raw.get("description"):
        instance["description"] = raw["description"]
    if "disable" in raw:
        instance["disable"] = True
    if raw.get("table"):
        instance["table_id"] = int(raw["table"])
    if raw.get("vni"):
        instance["vni"] = int(raw["vni"])
    address_family = []
    for afi_key in ("ip", "ipv6"):
        if afi_key in raw:
            af_entry = _af_from_device(afi_key, raw[afi_key])
            if af_entry:
                address_family.append(af_entry)
    if address_family:
        instance["address_family"] = address_family
    # protocols are handled separately in build_commands / gathered
    return instance


def _want_to_device(config):
    config = config or {}
    result = {}
    if config.get("bind_to_all"):
        result["bind-to-all"] = {}
    instances = config.get("instances") or []
    if instances:
        name_dict = {}
        for inst in instances:
            vrf_name = inst.get("name")
            if not vrf_name:
                continue
            name_dict[vrf_name] = _instance_to_device(inst)
        if name_dict:
            result["name"] = name_dict
    return result


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "bind-to-all" in raw:
        result["bind_to_all"] = True
    name_raw = raw.get("name", {})
    if name_raw and isinstance(name_raw, dict):
        instances = []
        for vrf_name, vrf_data in sorted(name_raw.items()):
            instances.append(_instance_from_device(vrf_name, vrf_data or {}))
        if instances:
            result["instances"] = instances
    return result


def _bgp_from_device(raw):
    """Convert BGP gathered data from device format to argspec format."""
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if raw.get("system-as"):
        result["system_as"] = int(raw["system-as"])
    neighbors_raw = raw.get("neighbor", {})
    if neighbors_raw and isinstance(neighbors_raw, dict):
        neighbors = []
        for addr, data in sorted(neighbors_raw.items()):
            entry = {"address": addr}
            data = data or {}
            if data.get("remote-as"):
                entry["remote_as"] = int(data["remote-as"])
            if data.get("description"):
                entry["description"] = data["description"]
            neighbors.append(entry)
        if neighbors:
            result["neighbor"] = neighbors
    return result


def _bgp_build_commands(vrf_name, want_bgp, have_bgp, state):
    """Generate BGP commands for a VRF instance using dict_op."""
    bgp_base = _BASE + ["name", vrf_name, "protocols", "bgp"]
    want_bgp = want_bgp or {}
    have_bgp = have_bgp or {}

    want = {}
    if want_bgp.get("system_as") is not None:
        want["system_as"] = want_bgp["system_as"]
    if want_bgp.get("neighbor"):
        want["neighbor"] = {
            n["address"]: {k: v for k, v in n.items() if k != "address"}
            for n in want_bgp["neighbor"]
            if n.get("address")
        }

    have = {}
    if have_bgp.get("system-as"):
        have["system_as"] = int(have_bgp["system-as"])
    if have_bgp.get("neighbor"):
        have["neighbor"] = {
            addr: {
                "remote_as": int(data["remote-as"]) if (data or {}).get("remote-as") else None,
                "description": (data or {}).get("description"),
            }
            for addr, data in (have_bgp.get("neighbor") or {}).items()
        }

    # Seed neighbor placeholders for new entries
    for addr in want.get("neighbor") or {}:
        have.setdefault("neighbor", {}).setdefault(addr, {})

    commands = []
    if state in ("overridden", "replaced"):
        commands += dict_op(want, have, bgp_base, op="purge")
    commands += dict_op(want, have, bgp_base, op="set")
    return commands


def _ospf_from_device(raw):
    """Convert OSPFv2 config from device format to argspec."""
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    areas_raw = raw.get("area", {})
    if areas_raw and isinstance(areas_raw, dict):
        areas = []
        for area_id, area_data in sorted(areas_raw.items()):
            entry = {"area_id": str(area_id)}
            area_data = area_data or {}
            networks_raw = area_data.get("network")
            if networks_raw:
                if isinstance(networks_raw, str):
                    entry["networks"] = [networks_raw]
                elif isinstance(networks_raw, dict):
                    entry["networks"] = sorted(networks_raw.keys())
                else:
                    entry["networks"] = list(networks_raw)
            areas.append(entry)
        if areas:
            result["areas"] = areas
    params_raw = raw.get("parameters", {})
    if params_raw and isinstance(params_raw, dict):
        params = {}
        if params_raw.get("router-id"):
            params["router_id"] = params_raw["router-id"]
        if params:
            result["parameters"] = params
    return result


def _ospf_build_commands(vrf_name, want_ospf, have_ospf, state):
    """Generate OSPFv2 commands for a VRF instance using dict_op."""
    ospf_base = _BASE + ["name", vrf_name, "protocols", "ospf"]
    want_ospf = want_ospf or {}
    have_ospf = have_ospf or {}

    want = {}
    if want_ospf.get("areas"):
        want["area"] = {}
        for a in want_ospf["areas"]:
            area_id = a.get("area_id")
            if not area_id:
                continue
            area_entry = {}
            if a.get("networks"):
                area_entry["network"] = sorted(a["networks"])
            want["area"][str(area_id)] = area_entry
    if want_ospf.get("parameters", {}).get("router_id"):
        want["parameters"] = {"router_id": want_ospf["parameters"]["router_id"]}

    have = {}
    areas_raw = have_ospf.get("area", {})
    if areas_raw and isinstance(areas_raw, dict):
        have["area"] = {}
        for area_id, area_data in areas_raw.items():
            area_data = area_data or {}
            area_entry = {}
            networks_raw = area_data.get("network")
            if networks_raw:
                if isinstance(networks_raw, str):
                    area_entry["network"] = [networks_raw]
                elif isinstance(networks_raw, list):
                    area_entry["network"] = sorted(networks_raw)
                elif isinstance(networks_raw, dict):
                    area_entry["network"] = sorted(networks_raw.keys())
            have["area"][str(area_id)] = area_entry
    params_raw = have_ospf.get("parameters", {})
    if params_raw and isinstance(params_raw, dict) and params_raw.get("router-id"):
        have["parameters"] = {"router_id": params_raw["router-id"]}

    # Seed area placeholders
    for area_id in want.get("area") or {}:
        have.setdefault("area", {}).setdefault(area_id, {})

    commands = []
    if state in ("overridden", "replaced"):
        commands += dict_op(want, have, ospf_base, op="purge")
    commands += dict_op(want, have, ospf_base, op="set")
    return commands


def _static_from_device(raw):
    """Convert static routes config from device format to argspec."""
    if not raw or not isinstance(raw, dict):
        return {}
    routes_raw = raw.get("route", {})
    if not routes_raw or not isinstance(routes_raw, dict):
        return {}
    routes = []
    for dest, route_data in sorted(routes_raw.items()):
        entry = {"dest": dest}
        route_data = route_data or {}
        next_hops_raw = route_data.get("next-hop", {})
        if next_hops_raw and isinstance(next_hops_raw, dict):
            entry["next_hops"] = sorted(next_hops_raw.keys())
        routes.append(entry)
    return {"routes": routes} if routes else {}


def _static_build_commands(vrf_name, want_static, have_static, state):
    """Generate static route commands for a VRF instance using dict_op."""
    static_base = _BASE + ["name", vrf_name, "protocols", "static"]
    want_static = want_static or {}
    have_static = have_static or {}

    want = {}
    if want_static.get("routes"):
        want["route"] = {}
        for r in want_static["routes"]:
            dest = r.get("dest")
            if not dest:
                continue
            route_entry = {}
            if r.get("next_hops"):
                route_entry["next-hop"] = {nh: {} for nh in r["next_hops"]}
            want["route"][dest] = route_entry

    have = {}
    routes_raw = have_static.get("route", {})
    if routes_raw and isinstance(routes_raw, dict):
        have["route"] = {}
        for dest, route_data in routes_raw.items():
            route_data = route_data or {}
            route_entry = {}
            next_hops_raw = route_data.get("next-hop", {})
            if next_hops_raw and isinstance(next_hops_raw, dict):
                route_entry["next-hop"] = {k: {} for k in next_hops_raw}
            have["route"][dest] = route_entry

    # Seed route placeholders
    for dest in want.get("route") or {}:
        have.setdefault("route", {}).setdefault(dest, {})

    commands = []
    if state in ("overridden", "replaced"):
        commands += dict_op(want, have, static_base, op="purge")
    commands += dict_op(want, have, static_base, op="set")
    return commands


def _protocols_from_device(raw_vrf):
    """Extract and convert protocol configs from raw VRF device data."""
    proto_raw = (raw_vrf or {}).get("protocols", {})
    if not proto_raw:
        return None
    result = {}
    if proto_raw.get("bgp"):
        bgp = _bgp_from_device(proto_raw["bgp"])
        if bgp:
            result["bgp"] = bgp
    if proto_raw.get("ospf"):
        ospf = _ospf_from_device(proto_raw["ospf"])
        if ospf:
            result["ospf"] = ospf
    if proto_raw.get("static"):
        static = _static_from_device(proto_raw["static"])
        if static:
            result["static"] = static
    return result or None


def get_running_config(vyos):
    try:
        return vyos.get_config(_BASE) or {}
    except Exception as exc:
        if "Configuration under specified path is empty" in str(exc):
            return {}
        raise


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or {}
    all_commands = []

    if state == "deleted":
        instances = (config.get("instances") or []) if config else []
        if not instances:
            return [("delete", _BASE)] if raw_have else []
        for inst in instances:
            vrf_name = inst.get("name")
            if vrf_name and raw_have.get("name", {}).get(vrf_name) is not None:
                all_commands.append(("delete", _BASE + ["name", vrf_name]))
        if (
            "bind_to_all" in (config or {})
            and config["bind_to_all"] is False
            and "bind-to-all" in raw_have
        ):
            all_commands.append(("delete", _BASE + ["bind-to-all"]))
        return all_commands

    want = _want_to_device(config)
    norm_have = _want_to_device(_device_to_argspec(raw_have))

    # Seed placeholders for new VRF instances
    want_names = want.get("name", {})
    have_names = norm_have.setdefault("name", {})
    for vrf_name in want_names:
        if vrf_name not in have_names:
            have_names[vrf_name] = {}

    if state == "overridden":
        all_commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        for vrf_name, vrf_want in (want.get("name") or {}).items():
            vrf_have = (norm_have.get("name") or {}).get(vrf_name, {})
            all_commands += dict_op(
                vrf_want,
                vrf_have,
                _BASE + ["name", vrf_name],
                op="purge",
            )
        if "bind-to-all" not in want and "bind-to-all" in norm_have:
            all_commands.append(("delete", _BASE + ["bind-to-all"]))

    all_commands += dict_op(want, norm_have, _BASE, op="set")

    # Protocol commands — per VRF instance
    for inst in config.get("instances") or []:
        vrf_name = inst.get("name")
        protocols = inst.get("protocols") or {}
        if not vrf_name or not protocols:
            continue

        raw_vrf = (raw_have.get("name") or {}).get(vrf_name, {})
        raw_proto = raw_vrf.get("protocols", {})

        # BGP
        if protocols.get("bgp") is not None or state in ("overridden", "replaced"):
            if protocols.get("bgp") is None and state in ("overridden", "replaced"):
                if raw_proto.get("bgp"):
                    all_commands.append(("delete", _BASE + ["name", vrf_name, "protocols", "bgp"]))
            elif protocols.get("bgp") is not None:
                all_commands += _bgp_build_commands(
                    vrf_name,
                    protocols["bgp"],
                    raw_proto.get("bgp", {}),
                    state,
                )
        # OSPFv2
        if protocols.get("ospf") is not None or state in ("overridden", "replaced"):
            if protocols.get("ospf") is None and state in ("overridden", "replaced"):
                if raw_proto.get("ospf"):
                    all_commands.append(("delete", _BASE + ["name", vrf_name, "protocols", "ospf"]))
            elif protocols.get("ospf") is not None:
                all_commands += _ospf_build_commands(
                    vrf_name,
                    protocols["ospf"],
                    raw_proto.get("ospf", {}),
                    state,
                )
        # Static routes
        if protocols.get("static") is not None or state in ("overridden", "replaced"):
            if protocols.get("static") is None and state in ("overridden", "replaced"):
                if raw_proto.get("static"):
                    all_commands.append(
                        ("delete", _BASE + ["name", vrf_name, "protocols", "static"]),
                    )
            elif protocols.get("static") is not None:
                all_commands += _static_build_commands(
                    vrf_name,
                    protocols["static"],
                    raw_proto.get("static", {}),
                    state,
                )
        return all_commands

    want = _want_to_device(config)
    norm_have = _want_to_device(_device_to_argspec(raw_have))

    # Seed placeholders for new VRF instances
    want_names = want.get("name", {})
    have_names = norm_have.setdefault("name", {})
    for vrf_name in want_names:
        if vrf_name not in have_names:
            have_names[vrf_name] = {}

    if state == "overridden":
        all_commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        for vrf_name, vrf_want in (want.get("name") or {}).items():
            vrf_have = (norm_have.get("name") or {}).get(vrf_name, {})
            all_commands += dict_op(
                vrf_want,
                vrf_have,
                _BASE + ["name", vrf_name],
                op="purge",
            )
        if "bind-to-all" not in want and "bind-to-all" in norm_have:
            all_commands.append(("delete", _BASE + ["bind-to-all"]))

    all_commands += dict_op(want, norm_have, _BASE, op="set")


def main():
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)
    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)
    for inst in have.get("instances") or []:
        raw_vrf = (raw_have.get("name") or {}).get(inst["name"], {})
        protocols = _protocols_from_device(raw_vrf)
        if protocols:
            inst["protocols"] = protocols

    if state == "gathered":
        for inst in have.get("instances") or []:
            vrf_name = inst["name"]
            raw_vrf = (raw_have.get("name") or {}).get(vrf_name, {})
            protocols = _protocols_from_device(raw_vrf)
            if protocols:
                inst["protocols"] = protocols
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        raw_after = get_running_config(vyos)
        after = _device_to_argspec(raw_after)
        for inst in after.get("instances") or []:
            raw_vrf = (raw_after.get("name") or {}).get(inst["name"], {})
            protocols = _protocols_from_device(raw_vrf)
            if protocols:
                inst["protocols"] = protocols
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
