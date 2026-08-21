#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_bgp_address_family
short_description: Manage BGP address-family configuration on VyOS devices using REST API
description:
  - Manages BGP address-family configuration on VyOS devices via the REST API.
  - Covers global address-family (networks, redistribution) and
    per-neighbor address-family settings.
  - BGP must be configured first using M(vyos.rest.vyos_bgp_global).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: BGP address-family configuration.
    type: dict
    suboptions:
      as_number:
        description: BGP autonomous system number (required for context).
        type: int
        required: true
      address_family:
        description: Global BGP address-family settings.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family identifier.
            type: str
            choices: [ipv4, ipv6]
            required: true
          networks:
            description: Networks to advertise.
            type: list
            elements: dict
            suboptions:
              prefix:
                description: Network prefix.
                type: str
                required: true
              route_map:
                description: Route map to apply.
                type: str
              backdoor:
                description: Network backdoor.
                type: bool
          redistribute:
            description: Redistribute routes from other protocols.
            type: list
            elements: dict
            suboptions:
              protocol:
                description: Protocol to redistribute.
                type: str
                choices: [connected, kernel, ospf, ospfv3, rip, ripng, static]
                required: true
              metric:
                description: Metric for redistributed routes.
                type: int
              route_map:
                description: Route map to apply.
                type: str
      neighbors:
        description: Per-neighbor address-family settings.
        type: list
        elements: dict
        suboptions:
          neighbor_address:
            description: Neighbor IP address.
            type: str
            required: true
          address_family:
            description: Address-family settings for this neighbor.
            type: list
            elements: dict
            suboptions:
              afi:
                description: Address family identifier.
                type: str
                choices: [ipv4, ipv6]
                required: true
              allowas_in:
                description: Accept as-path with my AS present.
                type: int
              attribute_unchanged:
                description: BGP attributes to leave unchanged.
                type: dict
                suboptions:
                  as_path:
                    description: Leave as-path unchanged.
                    type: bool
                  med:
                    description: Leave MED unchanged.
                    type: bool
                  next_hop:
                    description: Leave next-hop unchanged.
                    type: bool
              capability:
                description: Advertise capability to the peer.
                type: dict
                suboptions:
                  orf:
                    description: ORF capability.
                    type: str
                    choices: [receive, send]
              default_originate:
                description: Send default route to neighbor.
                type: bool
              distribute_list:
                description: Filter updates using access-list.
                type: dict
                suboptions:
                  import:
                    description: Access-list to filter inbound updates.
                    type: int
                  export:
                    description: Access-list to filter outbound updates.
                    type: int
              maximum_prefix:
                description: Maximum number of prefixes to accept.
                type: int
              nexthop_self:
                description: Set next-hop to self.
                type: bool
              prefix_list:
                description: Filter updates using prefix-list.
                type: dict
                suboptions:
                  import:
                    description: Prefix-list to filter inbound updates.
                    type: str
                  export:
                    description: Prefix-list to filter outbound updates.
                    type: str
              route_map:
                description: Route map to apply.
                type: dict
                suboptions:
                  import:
                    description: Route map for inbound updates.
                    type: str
                  export:
                    description: Route map for outbound updates.
                    type: str
              route_reflector_client:
                description: Configure as route reflector client.
                type: bool
              route_server_client:
                description: Configure as route server client.
                type: bool
              soft_reconfiguration:
                description: Enable soft reconfiguration inbound.
                type: bool
              unsuppress_map:
                description: Route-map to selectively unsuppress suppressed routes.
                type: str
              weight:
                description: Default weight for routes from this neighbor.
                type: int
  state:
    description:
      - Desired state of the BGP address-family configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces the entire BGP address-family configuration.
      - C(deleted) removes BGP address-family configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - BGP must be configured first using M(vyos.rest.vyos_bgp_global).
"""

EXAMPLES = r"""
- name: Merge BGP address-family configuration
  vyos.rest.vyos_bgp_address_family:
    config:
      as_number: 65000
      address_family:
        - afi: ipv4
          networks:
            - prefix: 192.0.2.0/24
          redistribute:
            - protocol: connected
              metric: 10
      neighbors:
        - neighbor_address: 192.0.2.1
          address_family:
            - afi: ipv4
              soft_reconfiguration: true
              nexthop_self: true
            - afi: ipv6
              soft_reconfiguration: true
    state: merged

- name: Delete all BGP address-family configuration
  vyos.rest.vyos_bgp_address_family:
    config:
      as_number: 65000
    state: deleted

- name: Gather BGP address-family configuration
  vyos.rest.vyos_bgp_address_family:
    state: gathered
"""

RETURN = r"""
before:
  description: BGP address-family configuration before this module ran.
  returned: always
  type: dict
after:
  description: BGP address-family configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current BGP address-family configuration as structured data.
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


_BASE = ["protocols", "bgp"]
_AFI_MAP = {"ipv4": "ipv4-unicast", "ipv6": "ipv6-unicast"}
_AFI_RMAP = {"ipv4-unicast": "ipv4", "ipv6-unicast": "ipv6"}


def _parse_global_af(raw_afs):
    if not raw_afs or not isinstance(raw_afs, dict):
        return []
    result = []
    for af_key, af_data in sorted(raw_afs.items()):
        afi = _AFI_RMAP.get(af_key)
        if not afi:
            continue
        af_data = af_data or {}
        entry = {"afi": afi}

        nets = af_data.get("network", {})
        if nets and isinstance(nets, dict):
            entry["networks"] = [{"prefix": p} for p in sorted(nets.keys())]

        redist = af_data.get("redistribute", {})
        if redist and isinstance(redist, dict):
            redist_list = []
            for proto, rdata in sorted(redist.items()):
                r = {"protocol": proto}
                rdata = rdata or {}
                if "metric" in rdata:
                    r["metric"] = int(rdata["metric"])
                if "route-map" in rdata:
                    r["route_map"] = rdata["route-map"]
                redist_list.append(r)
            if redist_list:
                entry["redistribute"] = redist_list

        result.append(entry)
    return result


def _parse_neighbor_af(raw_afs):
    if not raw_afs or not isinstance(raw_afs, dict):
        return []
    result = []
    for af_key, af_data in sorted(raw_afs.items()):
        afi = _AFI_RMAP.get(af_key)
        if not afi:
            continue
        af_data = af_data or {}
        entry = {"afi": afi}

        if "nexthop-self" in af_data:
            entry["nexthop_self"] = True
        if "route-reflector-client" in af_data:
            entry["route_reflector_client"] = True
        if "route-server-client" in af_data:
            entry["route_server_client"] = True
        if "default-originate" in af_data:
            entry["default_originate"] = True
        if "maximum-prefix" in af_data:
            entry["maximum_prefix"] = int(af_data["maximum-prefix"])
        if "weight" in af_data:
            entry["weight"] = int(af_data["weight"])
        if "unsuppress-map" in af_data:
            entry["unsuppress_map"] = af_data["unsuppress-map"]
        if "allowas-in" in af_data:
            ai = af_data["allowas-in"]
            if isinstance(ai, dict) and "number" in ai:
                entry["allowas_in"] = int(ai["number"])
            else:
                entry["allowas_in"] = 1

        sc = af_data.get("soft-reconfiguration", {})
        if sc and "inbound" in sc:
            entry["soft_reconfiguration"] = True

        rm = af_data.get("route-map", {})
        if rm:
            entry["route_map"] = {}
            if "import" in rm:
                entry["route_map"]["import"] = rm["import"]
            if "export" in rm:
                entry["route_map"]["export"] = rm["export"]

        pl = af_data.get("prefix-list", {})
        if pl:
            entry["prefix_list"] = {}
            if "import" in pl:
                entry["prefix_list"]["import"] = pl["import"]
            if "export" in pl:
                entry["prefix_list"]["export"] = pl["export"]

        result.append(entry)
    return result


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}

    if "system-as" in raw:
        result["as_number"] = int(raw["system-as"])

    global_afs = _parse_global_af(raw.get("address-family"))
    if global_afs:
        result["address_family"] = global_afs

    neighbors = []
    for nb_id, nb_data in sorted((raw.get("neighbor") or {}).items()):
        nb_data = nb_data or {}
        nb_afs = _parse_neighbor_af(nb_data.get("address-family"))
        if nb_afs:
            neighbors.append({"neighbor_address": nb_id, "address_family": nb_afs})
    if neighbors:
        result["neighbors"] = neighbors

    return result


def _global_af_cmds(af, have_af):
    cmds = []
    afi = af["afi"]
    af_key = _AFI_MAP[afi]
    abase = _BASE + ["address-family", af_key]
    have_af = have_af or {}

    want_nets = {n["prefix"]: n for n in (af.get("networks") or [])}
    have_nets = {n["prefix"]: n for n in (have_af.get("networks") or [])}
    for prefix in want_nets:
        if prefix not in have_nets:
            cmds.append(("set", abase + ["network", prefix]))

    want_redist = {r["protocol"]: r for r in (af.get("redistribute") or [])}
    have_redist = {r["protocol"]: r for r in (have_af.get("redistribute") or [])}
    for proto, entry in want_redist.items():
        have_entry = have_redist.get(proto, {})
        rbase = abase + ["redistribute", proto]
        if proto not in have_redist:
            cmds.append(("set", rbase))
        if entry.get("metric") and entry["metric"] != have_entry.get("metric"):
            cmds.append(("set", rbase + ["metric", str(entry["metric"])]))
        if entry.get("route_map") and entry["route_map"] != have_entry.get("route_map"):
            cmds.append(("set", rbase + ["route-map", entry["route_map"]]))

    return cmds


def _neighbor_af_cmds(nb_addr, af, have_af):
    cmds = []
    afi = af["afi"]
    af_key = _AFI_MAP[afi]
    nbase = _BASE + ["neighbor", nb_addr, "address-family", af_key]
    have_af = have_af or {}

    if af.get("soft_reconfiguration") and not have_af.get("soft_reconfiguration"):
        cmds.append(("set", nbase + ["soft-reconfiguration", "inbound"]))
    if af.get("nexthop_self") and not have_af.get("nexthop_self"):
        cmds.append(("set", nbase + ["nexthop-self"]))
    if af.get("route_reflector_client") and not have_af.get("route_reflector_client"):
        cmds.append(("set", nbase + ["route-reflector-client"]))
    if af.get("route_server_client") and not have_af.get("route_server_client"):
        cmds.append(("set", nbase + ["route-server-client"]))
    if af.get("default_originate") and not have_af.get("default_originate"):
        cmds.append(("set", nbase + ["default-originate"]))
    if af.get("maximum_prefix") and af["maximum_prefix"] != have_af.get("maximum_prefix"):
        cmds.append(("set", nbase + ["maximum-prefix", str(af["maximum_prefix"])]))
    if af.get("weight") and af["weight"] != have_af.get("weight"):
        cmds.append(("set", nbase + ["weight", str(af["weight"])]))
    if af.get("allowas_in") and af["allowas_in"] != have_af.get("allowas_in"):
        cmds.append(("set", nbase + ["allowas-in", "number", str(af["allowas_in"])]))
    if af.get("unsuppress_map") and af["unsuppress_map"] != have_af.get("unsuppress_map"):
        cmds.append(("set", nbase + ["unsuppress-map", af["unsuppress_map"]]))

    want_rm = af.get("route_map") or {}
    have_rm = have_af.get("route_map") or {}
    if want_rm.get("import") and want_rm["import"] != have_rm.get("import"):
        cmds.append(("set", nbase + ["route-map", "import", want_rm["import"]]))
    if want_rm.get("export") and want_rm["export"] != have_rm.get("export"):
        cmds.append(("set", nbase + ["route-map", "export", want_rm["export"]]))

    want_pl = af.get("prefix_list") or {}
    have_pl = have_af.get("prefix_list") or {}
    if want_pl.get("import") and want_pl["import"] != have_pl.get("import"):
        cmds.append(("set", nbase + ["prefix-list", "import", want_pl["import"]]))
    if want_pl.get("export") and want_pl["export"] != have_pl.get("export"):
        cmds.append(("set", nbase + ["prefix-list", "export", want_pl["export"]]))

    return cmds


def build_commands(config, have, state):
    cmds = []
    config = config or {}

    if state == "deleted":
        if have.get("address_family"):
            cmds.append(("delete", _BASE + ["address-family"]))
        for nb in have.get("neighbors") or []:
            path = _BASE + ["neighbor", nb["neighbor_address"], "address-family"]
            cmds.append(("delete", path))
        return cmds

    if state == "replaced":
        would_set = build_commands(config, {}, "merged")
        have_set = build_commands(have, {}, "merged")
        if would_set == have_set:
            return []
        if have.get("address_family"):
            cmds.append(("delete", _BASE + ["address-family"]))
        for nb in have.get("neighbors") or []:
            path = _BASE + ["neighbor", nb["neighbor_address"], "address-family"]
            cmds.append(("delete", path))
        have = {}

    # global address-family
    have_global_af_map = {af["afi"]: af for af in (have.get("address_family") or [])}
    for af in config.get("address_family") or []:
        cmds += _global_af_cmds(af, have_global_af_map.get(af["afi"]))

    # per-neighbor address-family
    have_nb_map = {
        n["neighbor_address"]: {af["afi"]: af for af in n.get("address_family", [])}
        for n in (have.get("neighbors") or [])
    }

    for nb in config.get("neighbors") or []:
        nb_addr = nb["neighbor_address"]
        have_nb_afs = have_nb_map.get(nb_addr, {})
        for af in nb.get("address_family") or []:
            cmds += _neighbor_af_cmds(nb_addr, af, have_nb_afs.get(af["afi"]))

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            as_number=dict(type="int", required=True),
            address_family=dict(
                type="list",
                elements="dict",
                options=dict(
                    afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
                    networks=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            prefix=dict(type="str", required=True),
                            route_map=dict(type="str"),
                            backdoor=dict(type="bool"),
                        ),
                    ),
                    redistribute=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            protocol=dict(
                                type="str",
                                required=True,
                                choices=[
                                    "connected",
                                    "kernel",
                                    "ospf",
                                    "ospfv3",
                                    "rip",
                                    "ripng",
                                    "static",
                                ],
                            ),
                            metric=dict(type="int"),
                            route_map=dict(type="str"),
                        ),
                    ),
                ),
            ),
            neighbors=dict(
                type="list",
                elements="dict",
                options=dict(
                    neighbor_address=dict(type="str", required=True),
                    address_family=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            afi=dict(type="str", choices=["ipv4", "ipv6"], required=True),
                            allowas_in=dict(type="int"),
                            default_originate=dict(type="bool"),
                            maximum_prefix=dict(type="int"),
                            nexthop_self=dict(type="bool"),
                            route_reflector_client=dict(type="bool"),
                            route_server_client=dict(type="bool"),
                            soft_reconfiguration=dict(type="bool"),
                            unsuppress_map=dict(type="str"),
                            weight=dict(type="int"),
                            attribute_unchanged=dict(
                                type="dict",
                                options=dict(
                                    as_path=dict(type="bool"),
                                    med=dict(type="bool"),
                                    next_hop=dict(type="bool"),
                                ),
                            ),
                            capability=dict(
                                type="dict",
                                options=dict(
                                    orf=dict(type="str", choices=["receive", "send"]),
                                ),
                            ),
                            distribute_list=dict(
                                type="dict",
                                options=dict(
                                    **{
                                        "import": dict(type="int"),
                                        "export": dict(type="int"),
                                    },
                                ),
                            ),
                            prefix_list=dict(
                                type="dict",
                                options=dict(
                                    **{
                                        "import": dict(type="str"),
                                        "export": dict(type="str"),
                                    },
                                ),
                            ),
                            route_map=dict(
                                type="dict",
                                options=dict(
                                    **{
                                        "import": dict(type="str"),
                                        "export": dict(type="str"),
                                    },
                                ),
                            ),
                        ),
                    ),
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
