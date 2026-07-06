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
  returned: when changed
  type: bool
response:
  description: Raw API response.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    normalize_have,
)


_BASE = ["protocols", "bgp"]
_AFI_MAP = {"ipv4": "ipv4-unicast", "ipv6": "ipv6-unicast"}
_AFI_RMAP = {v: k for k, v in _AFI_MAP.items()}

# Tag-node keys whose value dict_op must always see as a dict, never a
# bare string/list -- VyOS's REST API collapses a single-child tag node
# to a plain string (or a list for multiple), exactly like it does for
# ordinary list leaves (see dict_op's own str->list coercion for that
# case). Only genuine tag nodes with no other structure need this.
_AF_TAG_KEYS = {"network", "redistribute"}

# The only neighbor-AF options whose device shape isn't a direct
# structural match for their argspec type. Every other key in this
# level's argspec passes through autoclean()/from_device() untouched.
_NEIGHBOR_AF_IRREGULAR = {"afi", "allowas_in", "capability", "soft_reconfiguration"}


# ---------------------------------------------------------------------------
# want -> device: structural reshaping only (networks/redistribute keyed
# by prefix/protocol, AFI abbreviation, the 3 irregular neighbor-AF
# options). Everything else is autoclean -- no field-name mapping.
# ---------------------------------------------------------------------------


def _global_af_to_device(af_list):
    result = {}
    for af in af_list or []:
        entry = {}
        networks = af.get("networks") or []
        if networks:
            entry["network"] = {
                n["prefix"]: autoclean({k: v for k, v in n.items() if k != "prefix"})
                for n in networks
            }
        redistribute = af.get("redistribute") or []
        if redistribute:
            entry["redistribute"] = {
                r["protocol"]: autoclean({k: v for k, v in r.items() if k != "protocol"})
                for r in redistribute
            }
        result[_AFI_MAP[af["afi"]]] = entry
    return result


def _neighbor_af_to_device(af_list):
    result = {}
    for af in af_list or []:
        entry = autoclean({k: v for k, v in af.items() if k not in _NEIGHBOR_AF_IRREGULAR})

        # allowas-in is a container node ({"number": N}), not a bare scalar.
        if af.get("allowas_in") is not None:
            entry["allowas_in"] = {"number": af["allowas_in"]}

        # capability.orf: the chosen value becomes a dict KEY, not a leaf
        # value (confirmed against vyos-1x: afi-capability-orf.xml.i).
        orf = (af.get("capability") or {}).get("orf")
        if orf:
            entry["capability"] = {"orf": {"prefix-list": {orf: {}}}}

        # soft_reconfiguration is a two-level presence node, not a flat one.
        if af.get("soft_reconfiguration"):
            entry["soft_reconfiguration"] = {"inbound": {}}

        result[_AFI_MAP[af["afi"]]] = entry
    return result


# ---------------------------------------------------------------------------
# device -> argspec (public have/gathered output)
# ---------------------------------------------------------------------------

_GLOBAL_AF_OPTIONS = None  # populated after ARGUMENT_SPEC is defined below
_NEIGHBOR_AF_OPTIONS = None


def _global_af_from_device(raw_afs):
    if not raw_afs or not isinstance(raw_afs, dict):
        return []
    result = []
    for af_key, af_data in sorted(raw_afs.items()):
        afi = _AFI_RMAP.get(af_key)
        if not afi:
            continue
        af_data = dict(af_data or {})
        networks_raw = af_data.pop("network", None) or {}
        redistribute_raw = af_data.pop("redistribute", None) or {}

        entry = {"afi": afi, **from_device(af_data)}
        if networks_raw:
            entry["networks"] = [
                {"prefix": prefix, **from_device(data or {})}
                for prefix, data in sorted(networks_raw.items())
            ]
        if redistribute_raw:
            entry["redistribute"] = [
                {"protocol": proto, **from_device(data or {})}
                for proto, data in sorted(redistribute_raw.items())
            ]

        cast_by_spec(entry, _GLOBAL_AF_OPTIONS)
        result.append(entry)
    return result


def _neighbor_af_from_device(raw_afs):
    if not raw_afs or not isinstance(raw_afs, dict):
        return []
    result = []
    for af_key, af_data in sorted(raw_afs.items()):
        afi = _AFI_RMAP.get(af_key)
        if not afi:
            continue
        af_data = dict(af_data or {})
        allowas = af_data.pop("allowas-in", None)
        orf = ((af_data.pop("capability", None) or {}).get("orf") or {}).get("prefix-list") or {}
        soft = af_data.pop("soft-reconfiguration", None)

        entry = {"afi": afi, **from_device(af_data)}
        cast_by_spec(entry, _NEIGHBOR_AF_OPTIONS)

        if isinstance(allowas, dict) and "number" in allowas:
            entry["allowas_in"] = int(allowas["number"])
        elif allowas is not None:
            entry["allowas_in"] = 1

        if "receive" in orf:
            entry["capability"] = {"orf": "receive"}
        elif "send" in orf:
            entry["capability"] = {"orf": "send"}

        if isinstance(soft, dict) and "inbound" in soft:
            entry["soft_reconfiguration"] = True

        result.append(entry)
    return result


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "system-as" in raw:
        result["as_number"] = int(raw["system-as"])

    global_afs = _global_af_from_device(raw.get("address-family"))
    if global_afs:
        result["address_family"] = global_afs

    neighbors = []
    for nb_id, nb_data in sorted((raw.get("neighbor") or {}).items()):
        nb_afs = _neighbor_af_from_device((nb_data or {}).get("address-family"))
        if nb_afs:
            neighbors.append({"neighbor_address": nb_id, "address_family": nb_afs})
    if neighbors:
        result["neighbors"] = neighbors

    return result


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


# ---------------------------------------------------------------------------
# Command building — dict_op scoped per owned subtree.
#
# "protocols bgp" is a shared root owned jointly with vyos_bgp_global, so
# every dict_op call here is scoped to a subtree this module fully owns
# (global address-family, or one neighbor's address-family) — never the
# shared root, and never a whole "neighbor.<addr>" entry (which also
# holds remote-as/timers/password etc. that belong to other modules).
# ---------------------------------------------------------------------------


def build_commands(config, raw_have, state):
    config = config or {}
    raw_have = raw_have or {}
    commands = []

    global_af_base = _BASE + ["address-family"]
    raw_global_af = raw_have.get("address-family") or {}
    raw_neighbors = raw_have.get("neighbor") or {}

    want_global_af = _global_af_to_device(config.get("address_family") or [])
    want_neighbors = {
        nb["neighbor_address"]: _neighbor_af_to_device(nb.get("address_family") or [])
        for nb in (config.get("neighbors") or [])
    }

    if state == "deleted":
        if raw_global_af:
            commands.append(("delete", global_af_base))
        for nb_addr, nb_data in sorted(raw_neighbors.items()):
            if (nb_data or {}).get("address-family"):
                commands.append(("delete", _BASE + ["neighbor", nb_addr, "address-family"]))
        return commands

    norm_global_af = normalize_have(raw_global_af, _AF_TAG_KEYS)
    if state == "replaced":
        commands += dict_op(want_global_af, norm_global_af, global_af_base, op="purge")
    commands += dict_op(want_global_af, norm_global_af, global_af_base, op="set")

    for nb_addr in sorted(set(want_neighbors) | set(raw_neighbors)):
        nb_base = _BASE + ["neighbor", nb_addr, "address-family"]
        raw_nb_af = (raw_neighbors.get(nb_addr) or {}).get("address-family") or {}
        norm_nb_af = normalize_have(raw_nb_af, _AF_TAG_KEYS)
        want_nb_af = want_neighbors.get(nb_addr, {})

        if state == "replaced":
            commands += dict_op(want_nb_af, norm_nb_af, nb_base, op="purge")
        commands += dict_op(want_nb_af, norm_nb_af, nb_base, op="set")

    return commands


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

# Populated post-definition to avoid forward-reference ordering issues;
# these back cast_by_spec so have-side int leaves are derived from the
# spec itself rather than a hand-maintained field list.
_GLOBAL_AF_OPTIONS = ARGUMENT_SPEC["config"]["options"]["address_family"]["options"]
_NEIGHBOR_AF_OPTIONS = ARGUMENT_SPEC["config"]["options"]["neighbors"]["options"]["address_family"][
    "options"
]


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have, commands=[])

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=_device_to_argspec(get_running_config(vyos)),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
