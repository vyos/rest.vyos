#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv2
short_description: Manage OSPFv2 configuration on VyOS devices using REST API
description:
  - Manages OSPFv2 configuration on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - 'In VyOS 1.5+, passive interfaces use per-interface config rather than passive-interface.'
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: OSPFv2 configuration.
    type: dict
    suboptions:
      areas:
        description: OSPFv2 areas.
        type: list
        elements: dict
        suboptions:
          area_id:
            description: Area ID.
            type: str
            required: true
          area_type:
            description: Area type.
            type: dict
            suboptions:
              normal:
                description: Normal area.
                type: bool
              nssa:
                description: NSSA area.
                type: dict
                suboptions:
                  set:
                    description: Enable NSSA.
                    type: bool
                  default_cost:
                    description: Default cost for NSSA.
                    type: int
                  no_summary:
                    description: Do not inject inter-area routes.
                    type: bool
                  translate:
                    description: NSSA-ABR translate setting.
                    type: str
                    choices: [always, candidate, never]
              stub:
                description: Stub area.
                type: dict
                suboptions:
                  set:
                    description: Enable stub.
                    type: bool
                  default_cost:
                    description: Default cost for stub.
                    type: int
                  no_summary:
                    description: Do not inject inter-area routes.
                    type: bool
          authentication:
            description: Area authentication type.
            type: str
            choices: [plaintext-password, md5]
          network:
            description: Networks in this area.
            type: list
            elements: dict
            suboptions:
              address:
                description: Network address.
                type: str
                required: true
          range:
            description: Area ranges.
            type: list
            elements: dict
            suboptions:
              address:
                description: Range address.
                type: str
                required: true
              cost:
                description: Cost for this range.
                type: int
              not_advertise:
                description: Do not advertise this range.
                type: bool
              substitute:
                description: Substitute prefix.
                type: str
          shortcut:
            description: Shortcut mode.
            type: str
            choices: [default, disable, enable]
      auto_cost:
        description: Auto-cost reference bandwidth.
        type: dict
        suboptions:
          reference_bandwidth:
            description: Reference bandwidth in Mbps.
            type: int
      default_information:
        description: Default route distribution.
        type: dict
        suboptions:
          originate:
            description: Originate default route.
            type: dict
            suboptions:
              always:
                description: Always advertise default route.
                type: bool
              metric:
                description: Metric for default route.
                type: int
              metric_type:
                description: Metric type.
                type: int
              route_map:
                description: Route map.
                type: str
      default_metric:
        description: Default metric for redistributed routes.
        type: int
      distance:
        description: Administrative distances.
        type: dict
        suboptions:
          global:
            description: Global OSPFv2 distance.
            type: int
          ospf:
            description: Per-route-type distances.
            type: dict
            suboptions:
              external:
                description: External route distance.
                type: int
              inter_area:
                description: Inter-area route distance.
                type: int
              intra_area:
                description: Intra-area route distance.
                type: int
      log_adjacency_changes:
        description: Log adjacency changes.
        type: str
        choices: [detail]
      neighbor:
        description: OSPF neighbors.
        type: list
        elements: dict
        suboptions:
          neighbor_id:
            description: Neighbor IP.
            type: str
            required: true
          poll_interval:
            description: Poll interval.
            type: int
          priority:
            description: Neighbor priority.
            type: int
      parameters:
        description: OSPFv2 parameters.
        type: dict
        suboptions:
          abr_type:
            description: ABR type.
            type: str
            choices: [cisco, ibm, shortcut, standard]
          opaque_lsa:
            description: Enable opaque LSA.
            type: bool
          rfc1583_compatibility:
            description: Enable RFC1583 compatibility.
            type: bool
          router_id:
            description: Router ID.
            type: str
      passive_interface:
        description: >
          Passive interfaces (VyOS 1.5+: configured via
          C(protocols ospf interface <name> passive)).
        type: list
        elements: str
      redistribute:
        description: Route redistribution.
        type: list
        elements: dict
        suboptions:
          route_type:
            description: Protocol to redistribute.
            type: str
            choices: [bgp, connected, kernel, rip, static]
          metric:
            description: Metric.
            type: int
          metric_type:
            description: Metric type.
            type: int
          route_map:
            description: Route map.
            type: str
  state:
    description:
      - Desired state.
      - C(merged) adds/updates without removing existing config.
      - C(replaced) replaces the entire OSPFv2 configuration.
      - C(deleted) removes OSPFv2 configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - VyOS 1.5+ uses per-interface passive configuration rather than
    the global C(passive-interface) command used in VyOS 1.4.
"""

EXAMPLES = r"""
- name: Merge OSPFv2 configuration
  vyos.rest.vyos_ospfv2:
    config:
      parameters:
        router_id: 192.0.1.1
        abr_type: cisco
      auto_cost:
        reference_bandwidth: 2
      areas:
        - area_id: "2"
          area_type:
            normal: true
          network:
            - address: 192.0.2.0/24
        - area_id: "3"
          area_type:
            nssa:
              set: true
        - area_id: "4"
          area_type:
            stub:
              default_cost: 20
          range:
            - address: 192.0.3.0/24
              cost: 10
      redistribute:
        - route_type: bgp
          metric: 10
      passive_interface:
        - eth1
    state: merged

- name: Delete all OSPFv2 configuration
  vyos.rest.vyos_ospfv2:
    state: deleted

- name: Gather current OSPFv2 configuration
  vyos.rest.vyos_ospfv2:
    state: gathered
"""

RETURN = r"""
before:
  description: OSPFv2 configuration before this module ran.
  returned: always
  type: dict
after:
  description: OSPFv2 configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current OSPFv2 configuration as structured data.
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["protocols", "ospf"]


def _parse_areas(raw_areas):
    if not raw_areas or not isinstance(raw_areas, dict):
        return []
    areas = []
    for area_id, data in sorted(raw_areas.items()):
        area = {"area_id": area_id}
        data = data or {}

        # area-type
        at = data.get("area-type", {})
        if at:
            area_type = {}
            if "normal" in at:
                area_type["normal"] = True
            if "nssa" in at:
                nssa_data = at["nssa"] or {}
                nssa = {"set": True}
                if "default-cost" in nssa_data:
                    nssa["default_cost"] = int(nssa_data["default-cost"])
                if "no-summary" in nssa_data:
                    nssa["no_summary"] = True
                if "translate" in nssa_data:
                    nssa["translate"] = nssa_data["translate"]
                area_type["nssa"] = nssa
            if "stub" in at:
                stub_data = at["stub"] or {}
                stub = {"set": True}
                if "default-cost" in stub_data:
                    stub["default_cost"] = int(stub_data["default-cost"])
                if "no-summary" in stub_data:
                    stub["no_summary"] = True
                area_type["stub"] = stub
            if area_type:
                area["area_type"] = area_type

        if "authentication" in data:
            area["authentication"] = data["authentication"]

        if "shortcut" in data:
            area["shortcut"] = data["shortcut"]

        # network
        net = data.get("network")
        if net:
            if isinstance(net, str):
                area["network"] = [{"address": net}]
            elif isinstance(net, dict):
                area["network"] = [{"address": a} for a in sorted(net.keys())]
            elif isinstance(net, list):
                area["network"] = [{"address": a} for a in sorted(net)]

        # range
        rng = data.get("range", {})
        if rng and isinstance(rng, dict):
            ranges = []
            for addr, rdata in sorted(rng.items()):
                r = {"address": addr}
                rdata = rdata or {}
                if "cost" in rdata:
                    r["cost"] = int(rdata["cost"])
                if "not-advertise" in rdata:
                    r["not_advertise"] = True
                if "substitute" in rdata:
                    r["substitute"] = rdata["substitute"]
                ranges.append(r)
            if ranges:
                area["range"] = ranges

        areas.append(area)
    return areas


def _parse_redistribute(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for rt, data in sorted(raw.items()):
        entry = {"route_type": rt}
        data = data or {}
        if "metric" in data:
            entry["metric"] = int(data["metric"])
        if "metric-type" in data:
            entry["metric_type"] = int(data["metric-type"])
        if "route-map" in data:
            entry["route_map"] = data["route-map"]
        result.append(entry)
    return result


def _parse_neighbor(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for nb_id, data in sorted(raw.items()):
        entry = {"neighbor_id": nb_id}
        data = data or {}
        if "poll-interval" in data:
            entry["poll_interval"] = int(data["poll-interval"])
        if "priority" in data:
            entry["priority"] = int(data["priority"])
        result.append(entry)
    return result


def _parse_parameters(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "router-id" in raw:
        result["router_id"] = raw["router-id"]
    if "abr-type" in raw:
        result["abr_type"] = raw["abr-type"]
    if "opaque-lsa" in raw:
        result["opaque_lsa"] = True
    if "rfc1583-compatibility" in raw:
        result["rfc1583_compatibility"] = True
    return result


def _parse_default_information(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    orig = raw.get("originate", {}) or {}
    result = {}
    if "always" in orig:
        result["always"] = True
    if "metric" in orig:
        result["metric"] = int(orig["metric"])
    if "metric-type" in orig:
        result["metric_type"] = int(orig["metric-type"])
    if "route-map" in orig:
        result["route_map"] = orig["route-map"]
    if result:
        return {"originate": result}
    return {}


def _parse_distance(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "global" in raw:
        result["global"] = int(raw["global"])
    ospf = raw.get("ospf", {}) or {}
    if ospf:
        od = {}
        if "external" in ospf:
            od["external"] = int(ospf["external"])
        if "inter-area" in ospf:
            od["inter_area"] = int(ospf["inter-area"])
        if "intra-area" in ospf:
            od["intra_area"] = int(ospf["intra-area"])
        if od:
            result["ospf"] = od
    return result


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}

    areas = _parse_areas(raw.get("area"))
    if areas:
        result["areas"] = areas

    ac = raw.get("auto-cost", {})
    if ac and "reference-bandwidth" in ac:
        result["auto_cost"] = {"reference_bandwidth": int(ac["reference-bandwidth"])}

    di = _parse_default_information(raw.get("default-information", {}))
    if di:
        result["default_information"] = di

    if "default-metric" in raw:
        result["default_metric"] = int(raw["default-metric"])

    dist = _parse_distance(raw.get("distance", {}))
    if dist:
        result["distance"] = dist

    lac = raw.get("log-adjacency-changes", {})
    if lac:
        if isinstance(lac, dict) and "detail" in lac:
            result["log_adjacency_changes"] = "detail"
        elif lac == "detail":
            result["log_adjacency_changes"] = "detail"

    neighbors = _parse_neighbor(raw.get("neighbor"))
    if neighbors:
        result["neighbor"] = neighbors

    params = _parse_parameters(raw.get("parameters"))
    if params:
        result["parameters"] = params

    # passive interfaces — VyOS 1.5 uses interface <name> passive
    iface_raw = raw.get("interface", {}) or {}
    passive = sorted(
        [name for name, data in iface_raw.items() if isinstance(data, dict) and "passive" in data],
    )
    if passive:
        result["passive_interface"] = passive

    redist = _parse_redistribute(raw.get("redistribute"))
    if redist:
        result["redistribute"] = redist

    return result


def _area_type_cmds(abase, area_type, have_at):
    cmds = []
    have_at = have_at or {}
    if area_type.get("normal") and not have_at.get("normal"):
        cmds.append(("set", abase + ["area-type", "normal"]))
    nssa = area_type.get("nssa") or {}
    if nssa:
        have_nssa = have_at.get("nssa") or {}
        if not have_nssa:
            cmds.append(("set", abase + ["area-type", "nssa"]))
        if nssa.get("default_cost") and nssa["default_cost"] != have_nssa.get("default_cost"):
            cmds.append(
                (
                    "set",
                    abase
                    + [
                        "area-type",
                        "nssa",
                        "default-cost",
                        str(nssa["default_cost"]),
                    ],
                ),
            )
        if nssa.get("no_summary") and not have_nssa.get("no_summary"):
            cmds.append(("set", abase + ["area-type", "nssa", "no-summary"]))
        if nssa.get("translate") and nssa["translate"] != have_nssa.get("translate"):
            cmds.append(("set", abase + ["area-type", "nssa", "translate", nssa["translate"]]))
    stub = area_type.get("stub") or {}
    if stub:
        have_stub = have_at.get("stub") or {}
        if not have_stub:
            if stub.get("default_cost"):
                cmds.append(
                    (
                        "set",
                        abase
                        + [
                            "area-type",
                            "stub",
                            "default-cost",
                            str(stub["default_cost"]),
                        ],
                    ),
                )
            else:
                cmds.append(("set", abase + ["area-type", "stub"]))
        elif stub.get("default_cost") and stub["default_cost"] != have_stub.get("default_cost"):
            cmds.append(
                (
                    "set",
                    abase
                    + [
                        "area-type",
                        "stub",
                        "default-cost",
                        str(stub["default_cost"]),
                    ],
                ),
            )
    return cmds


def _area_cmds(area, have_area):
    cmds = []
    area_id = area["area_id"]
    abase = _BASE + ["area", area_id]
    have_area = have_area or {}

    if area.get("area_type"):
        cmds += _area_type_cmds(abase, area["area_type"], have_area.get("area_type"))

    if area.get("authentication") and area["authentication"] != have_area.get("authentication"):
        cmds.append(("set", abase + ["authentication", area["authentication"]]))

    if area.get("shortcut") and area["shortcut"] != have_area.get("shortcut"):
        cmds.append(("set", abase + ["shortcut", area["shortcut"]]))

    want_nets = {n["address"] for n in (area.get("network") or [])}
    have_nets = {n["address"] for n in (have_area.get("network") or [])}
    for addr in want_nets - have_nets:
        cmds.append(("set", abase + ["network", addr]))

    want_ranges = {r["address"]: r for r in (area.get("range") or [])}
    have_ranges = {r["address"]: r for r in (have_area.get("range") or [])}
    for addr, rng in want_ranges.items():
        have_rng = have_ranges.get(addr, {})
        if addr not in have_ranges:
            cmds.append(("set", abase + ["range", addr]))
        if rng.get("cost") and rng["cost"] != have_rng.get("cost"):
            cmds.append(("set", abase + ["range", addr, "cost", str(rng["cost"])]))
        if rng.get("not_advertise") and not have_rng.get("not_advertise"):
            cmds.append(("set", abase + ["range", addr, "not-advertise"]))
        if rng.get("substitute") and rng["substitute"] != have_rng.get("substitute"):
            cmds.append(("set", abase + ["range", addr, "substitute", rng["substitute"]]))

    return cmds


def _parameters_cmds(params, have_params):
    cmds = []
    have_params = have_params or {}
    pbase = _BASE + ["parameters"]
    if params.get("router_id") and params["router_id"] != have_params.get("router_id"):
        cmds.append(("set", pbase + ["router-id", params["router_id"]]))
    if params.get("abr_type") and params["abr_type"] != have_params.get("abr_type"):
        cmds.append(("set", pbase + ["abr-type", params["abr_type"]]))
    if params.get("opaque_lsa") and not have_params.get("opaque_lsa"):
        cmds.append(("set", pbase + ["opaque-lsa"]))
    if params.get("rfc1583_compatibility") and not have_params.get("rfc1583_compatibility"):
        cmds.append(("set", pbase + ["rfc1583-compatibility"]))
    return cmds


def _redistribute_cmds(redist_list, have_redist_list):
    cmds = []
    want = {r["route_type"]: r for r in (redist_list or [])}
    have = {r["route_type"]: r for r in (have_redist_list or [])}
    for rt, entry in want.items():
        have_entry = have.get(rt, {})
        rbase = _BASE + ["redistribute", rt]
        if rt not in have:
            cmds.append(("set", rbase))
        if entry.get("metric") and entry["metric"] != have_entry.get("metric"):
            cmds.append(("set", rbase + ["metric", str(entry["metric"])]))
        if entry.get("metric_type") and entry["metric_type"] != have_entry.get("metric_type"):
            cmds.append(("set", rbase + ["metric-type", str(entry["metric_type"])]))
        if entry.get("route_map") and entry["route_map"] != have_entry.get("route_map"):
            cmds.append(("set", rbase + ["route-map", entry["route_map"]]))
    return cmds


def _neighbor_cmds(neighbors, have_neighbors):
    cmds = []
    want = {n["neighbor_id"]: n for n in (neighbors or [])}
    have = {n["neighbor_id"]: n for n in (have_neighbors or [])}
    for nb_id, entry in want.items():
        have_entry = have.get(nb_id, {})
        nbase = _BASE + ["neighbor", nb_id]
        if nb_id not in have:
            cmds.append(("set", nbase))
        if entry.get("priority") and entry["priority"] != have_entry.get("priority"):
            cmds.append(("set", nbase + ["priority", str(entry["priority"])]))
        if entry.get("poll_interval") and entry["poll_interval"] != have_entry.get("poll_interval"):
            cmds.append(("set", nbase + ["poll-interval", str(entry["poll_interval"])]))
    return cmds


def _default_info_cmds(di, have_di):
    cmds = []
    have_di = have_di or {}
    orig = (di or {}).get("originate") or {}
    have_orig = have_di.get("originate") or {}
    if not orig:
        return cmds
    dbase = _BASE + ["default-information", "originate"]
    if orig.get("always") and not have_orig.get("always"):
        cmds.append(("set", dbase + ["always"]))
    if orig.get("metric") and orig["metric"] != have_orig.get("metric"):
        cmds.append(("set", dbase + ["metric", str(orig["metric"])]))
    if orig.get("metric_type") and orig["metric_type"] != have_orig.get("metric_type"):
        cmds.append(("set", dbase + ["metric-type", str(orig["metric_type"])]))
    if orig.get("route_map") and orig["route_map"] != have_orig.get("route_map"):
        cmds.append(("set", dbase + ["route-map", orig["route_map"]]))
    return cmds


def build_commands(config, have, state):
    cmds = []

    if state == "deleted":
        if have:
            cmds.append(("delete", _BASE))
        return cmds

    if state == "replaced":
        would_set = build_commands(config, {}, "merged")
        have_set = build_commands(have, {}, "merged")
        if would_set == have_set:
            return []
        if have:
            cmds.append(("delete", _BASE))
        have = {}

    config = config or {}

    # parameters
    if config.get("parameters"):
        cmds += _parameters_cmds(config["parameters"], have.get("parameters"))

    # auto_cost
    ac = config.get("auto_cost") or {}
    have_ac = have.get("auto_cost") or {}
    if ac.get("reference_bandwidth") and ac["reference_bandwidth"] != have_ac.get(
        "reference_bandwidth",
    ):
        cmds.append(
            (
                "set",
                _BASE
                + [
                    "auto-cost",
                    "reference-bandwidth",
                    str(ac["reference_bandwidth"]),
                ],
            ),
        )

    # default_information
    if config.get("default_information"):
        cmds += _default_info_cmds(
            config["default_information"],
            have.get("default_information"),
        )

    # default_metric
    if config.get("default_metric") and config["default_metric"] != have.get("default_metric"):
        cmds.append(("set", _BASE + ["default-metric", str(config["default_metric"])]))

    # distance
    dist = config.get("distance") or {}
    have_dist = have.get("distance") or {}
    if dist.get("global") and dist["global"] != have_dist.get("global"):
        cmds.append(("set", _BASE + ["distance", "global", str(dist["global"])]))
    ospf_dist = dist.get("ospf") or {}
    have_ospf_dist = have_dist.get("ospf") or {}
    for key, api_key in [
        ("external", "external"),
        ("inter_area", "inter-area"),
        ("intra_area", "intra-area"),
    ]:
        if ospf_dist.get(key) and ospf_dist[key] != have_ospf_dist.get(key):
            cmds.append(("set", _BASE + ["distance", "ospf", api_key, str(ospf_dist[key])]))

    # log_adjacency_changes
    if config.get("log_adjacency_changes") and config["log_adjacency_changes"] != have.get(
        "log_adjacency_changes",
    ):
        cmds.append(("set", _BASE + ["log-adjacency-changes", config["log_adjacency_changes"]]))

    # neighbor
    if config.get("neighbor"):
        cmds += _neighbor_cmds(config["neighbor"], have.get("neighbor"))

    # redistribute
    if config.get("redistribute"):
        cmds += _redistribute_cmds(config["redistribute"], have.get("redistribute"))

    # passive_interface — VyOS 1.5 per-interface style
    want_passive = set(config.get("passive_interface") or [])
    have_passive = set(have.get("passive_interface") or [])
    for iface in want_passive - have_passive:
        cmds.append(("set", _BASE + ["interface", iface, "passive"]))

    # areas
    have_areas = {a["area_id"]: a for a in (have.get("areas") or [])}
    for area in config.get("areas") or []:
        have_area = have_areas.get(area["area_id"], {})
        cmds += _area_cmds(area, have_area)

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            areas=dict(
                type="list",
                elements="dict",
                options=dict(
                    area_id=dict(type="str", required=True),
                    area_type=dict(
                        type="dict",
                        options=dict(
                            normal=dict(type="bool"),
                            nssa=dict(
                                type="dict",
                                options=dict(
                                    set=dict(type="bool"),
                                    default_cost=dict(type="int"),
                                    no_summary=dict(type="bool"),
                                    translate=dict(
                                        type="str",
                                        choices=["always", "candidate", "never"],
                                    ),
                                ),
                            ),
                            stub=dict(
                                type="dict",
                                options=dict(
                                    set=dict(type="bool"),
                                    default_cost=dict(type="int"),
                                    no_summary=dict(type="bool"),
                                ),
                            ),
                        ),
                    ),
                    authentication=dict(
                        type="str",
                        choices=["plaintext-password", "md5"],
                    ),
                    network=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str", required=True),
                        ),
                    ),
                    range=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str", required=True),
                            cost=dict(type="int"),
                            not_advertise=dict(type="bool"),
                            substitute=dict(type="str"),
                        ),
                    ),
                    shortcut=dict(type="str", choices=["default", "disable", "enable"]),
                ),
            ),
            auto_cost=dict(
                type="dict",
                options=dict(
                    reference_bandwidth=dict(type="int"),
                ),
            ),
            default_information=dict(
                type="dict",
                options=dict(
                    originate=dict(
                        type="dict",
                        options=dict(
                            always=dict(type="bool"),
                            metric=dict(type="int"),
                            metric_type=dict(type="int"),
                            route_map=dict(type="str"),
                        ),
                    ),
                ),
            ),
            default_metric=dict(type="int"),
            distance=dict(
                type="dict",
                options=dict(
                    **{"global": dict(type="int")},
                    ospf=dict(
                        type="dict",
                        options=dict(
                            external=dict(type="int"),
                            inter_area=dict(type="int"),
                            intra_area=dict(type="int"),
                        ),
                    ),
                ),
            ),
            log_adjacency_changes=dict(type="str", choices=["detail"]),
            neighbor=dict(
                type="list",
                elements="dict",
                options=dict(
                    neighbor_id=dict(type="str", required=True),
                    poll_interval=dict(type="int"),
                    priority=dict(type="int"),
                ),
            ),
            parameters=dict(
                type="dict",
                options=dict(
                    abr_type=dict(
                        type="str",
                        choices=["cisco", "ibm", "shortcut", "standard"],
                    ),
                    opaque_lsa=dict(type="bool"),
                    rfc1583_compatibility=dict(type="bool"),
                    router_id=dict(type="str"),
                ),
            ),
            passive_interface=dict(type="list", elements="str"),
            redistribute=dict(
                type="list",
                elements="dict",
                options=dict(
                    route_type=dict(
                        type="str",
                        choices=["bgp", "connected", "kernel", "rip", "static"],
                    ),
                    metric=dict(type="int"),
                    metric_type=dict(type="int"),
                    route_map=dict(type="str"),
                ),
            ),
        ),
    ),
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
