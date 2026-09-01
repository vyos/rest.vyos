#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv2
short_description: Manage OSPFv2 configuration on VyOS devices using REST API
description:
  - Manages OSPFv2 configuration on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - >-
    Scope matches the current vyos.vyos.vyos_ospfv2 (CLI collection) module:
    areas (including virtual_link), auto_cost, default_information,
    default_metric, distance, log_adjacency_changes, max_metric, mpls_te,
    neighbor, parameters, passive_interface, passive_interface_exclude,
    redistribute, timers. VyOS's OSPF schema is considerably larger than
    even this -- access-list, aggregation, capability, graceful-restart,
    ldp-sync, maximum-paths, per-interface tuning (bandwidth/hello-
    multiplier/network-type/authentication/intervals beyond passive),
    segment-routing, and summary-address are not modeled here, matching
    real gaps in the CLI module's own scope, not oversights.
  - >-
    A standalone top-level C(route_map) field exists in the CLI module's
    argspec but does not correspond to any real device path -- confirmed
    against a live VyOS 1.5.0 device's C(set protocols ospf) completions,
    which list no C(route-map) entry at that level (only nested under
    C(default-information originate) and per-protocol under
    C(redistribute), both of which are modeled here). Deliberately
    omitted rather than built against a confirmed non-functional field.
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
          virtual_link:
            description: Virtual link.
            type: list
            elements: dict
            suboptions:
              address:
                description: Virtual link address (router ID of the remote ABR).
                type: str
                required: true
              authentication:
                description: Virtual link authentication.
                type: dict
                suboptions:
                  md5:
                    description: MD5 key id based authentication.
                    type: list
                    elements: dict
                    suboptions:
                      key_id:
                        description: MD5 key id (1-255).
                        type: int
                      md5_key:
                        description: MD5 key (16 characters or less).
                        type: str
                  plaintext_password:
                    description: Plain text password (8 characters or less).
                    type: str
              dead_interval:
                description: Interval after which a neighbor is declared dead.
                type: int
              hello_interval:
                description: Interval between hello packets.
                type: int
              retransmit_interval:
                description: Interval between retransmitting lost link state advertisements.
                type: int
              transmit_delay:
                description: Link state transmit delay.
                type: int
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
      max_metric:
        description: OSPFv2 maximum/infinite-distance metric.
        type: dict
        suboptions:
          router_lsa:
            description: Advertise own Router-LSA with infinite distance (stub router).
            type: dict
            suboptions:
              administrative:
                description: Administratively apply, for an indefinite period.
                type: bool
              on_shutdown:
                description: Time (seconds) to advertise self as stub-router before shutdown.
                type: int
              on_startup:
                description: Time (seconds) to advertise self as stub-router on startup.
                type: int
      mpls_te:
        description: MPLS Traffic Engineering parameters.
        type: dict
        suboptions:
          enabled:
            description: Enable MPLS-TE functionality.
            type: bool
          router_address:
            description: Stable IP address of the advertising router.
            type: str
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
        description: >-
          Interfaces to suppress routing updates on, via per-interface
          configuration (C(protocols ospf interface <name> passive)).
        type: list
        elements: str
      passive_interface_exclude:
        description: >-
          Interfaces to explicitly exclude from passive mode (via
          C(protocols ospf interface <name> passive disable)) -- e.g.
          when passive is otherwise applied broadly.
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
      timers:
        description: Routing timers.
        type: dict
        suboptions:
          refresh:
            description: Refresh parameters.
            type: dict
            suboptions:
              timers:
                description: Refresh timer (seconds).
                type: int
          throttle:
            description: Throttling adaptive timers.
            type: dict
            suboptions:
              spf:
                description: SPF timers.
                type: dict
                suboptions:
                  delay:
                    description: Delay (ms) from first change received to SPF calculation.
                    type: int
                  initial_holdtime:
                    description: Initial hold time (ms) between consecutive SPF calculations.
                    type: int
                  max_holdtime:
                    description: Maximum hold time (ms).
                    type: int
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
seealso:
  - module: vyos.vyos.vyos_ospfv2
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
      max_metric:
        router_lsa:
          administrative: true
      mpls_te:
        enabled: true
        router_address: 192.0.11.11
      timers:
        throttle:
          spf:
            delay: 200
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    cast_by_spec,
    dict_op,
    from_device,
    to_tag_dict,
)


_BASE = ["protocols", "ospf"]


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


def _keyed_list_from_device(raw, key_field, entry_transform=None, key_cast=None):
    entry_transform = entry_transform or from_device
    key_cast = key_cast or (lambda k: k)
    return [
        {key_field: key_cast(key), **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


# ---------------------------------------------------------------------------
# area_type -- confirmed against vyos-1x: normal (presence), nssa (a node
# with default-cost/no-summary/translate -- presence of the node itself
# is the "set" flag, matching the argspec's own "set" boolean rather
# than a separate device leaf), stub (default-cost/no-summary,
# same presence pattern). Genuine structural exception: the argspec's
# nssa/stub "set" key doesn't exist as a device leaf at all -- the
# *node's presence* IS the set flag, so "set" must be stripped out
# before the walk and re-derived on the way back.
# ---------------------------------------------------------------------------


def _area_type_to_device(area_type):
    if not area_type:
        return {}
    device = {}
    if area_type.get("normal"):
        device["normal"] = {}
    nssa = area_type.get("nssa")
    if nssa:
        nssa_device = _kebab_fields({k: v for k, v in nssa.items() if k != "set"})
        device["nssa"] = nssa_device
    stub = area_type.get("stub")
    if stub:
        stub_device = _kebab_fields({k: v for k, v in stub.items() if k != "set"})
        device["stub"] = stub_device
    return device


def _area_type_from_device(data):
    if not data:
        return None
    entry = {}
    if "normal" in data:
        entry["normal"] = True
    if "nssa" in data:
        nssa = from_device(data["nssa"] or {})
        nssa["set"] = True
        entry["nssa"] = nssa
    if "stub" in data:
        stub = from_device(data["stub"] or {})
        stub["set"] = True
        entry["stub"] = stub
    return entry or None


# ---------------------------------------------------------------------------
# virtual_link -- confirmed against vyos-1x: keyed by address, with an
# "authentication" node (md5 tag-node keyed by key-id, or a bare
# plaintext-password leaf), plus dead-interval/hello-interval/
# retransmit-interval/transmit-delay as plain leaves.
# ---------------------------------------------------------------------------


def _vlink_auth_to_device(auth):
    if not auth:
        return {}
    device = {}
    md5_list = auth.get("md5") or []
    if md5_list:
        device["md5"] = {
            str(entry["key_id"]): {"md5-key": entry["md5_key"]}
            for entry in md5_list
            if entry.get("key_id") is not None
        }
    if auth.get("plaintext_password"):
        device["plaintext-password"] = auth["plaintext_password"]
    return device


def _vlink_auth_from_device(data):
    if not data:
        return None
    entry = {}
    md5_raw = data.get("md5")
    if md5_raw:
        entry["md5"] = [
            {"key_id": int(key_id), "md5_key": (kdata or {}).get("md5-key")}
            for key_id, kdata in sorted(to_tag_dict(md5_raw).items())
        ]
    if data.get("plaintext-password"):
        entry["plaintext_password"] = data["plaintext-password"]
    return entry or None


def _vlink_entry_to_device(rest):
    exclude = {"authentication"}
    device = _kebab_fields({k: v for k, v in rest.items() if k not in exclude})
    if rest.get("authentication"):
        auth_device = _vlink_auth_to_device(rest["authentication"])
        if auth_device:
            device["authentication"] = auth_device
    return device


def _vlink_entry_from_device(data):
    exclude = {"authentication"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})
    auth = _vlink_auth_from_device(data.get("authentication"))
    if auth:
        entry["authentication"] = auth
    return entry


# ---------------------------------------------------------------------------
# area -- orchestrates area_type, network, range, virtual_link, and the
# plain leaves (authentication, shortcut).
# ---------------------------------------------------------------------------

_NETWORK_KEY = "address"
_RANGE_KEY = "address"
_VLINK_KEY = "address"


def _area_entry_to_device(rest):
    exclude = {"area_type", "network", "range", "virtual_link"}
    device = autoclean({k: v for k, v in rest.items() if k not in exclude})

    at = _area_type_to_device(rest.get("area_type"))
    if at:
        device["area-type"] = at

    networks = rest.get("network") or []
    if networks:
        device["network"] = {n["address"]: {} for n in networks if n.get("address")}

    ranges = rest.get("range") or []
    if ranges:
        device["range"] = _keyed_list_to_device(ranges, _RANGE_KEY)

    vlinks = rest.get("virtual_link") or []
    if vlinks:
        device["virtual-link"] = _keyed_list_to_device(vlinks, _VLINK_KEY, _vlink_entry_to_device)

    return device


def _area_entry_from_device(data):
    exclude = {"area-type", "network", "range", "virtual-link"}
    entry = from_device({k: v for k, v in data.items() if k not in exclude})

    at = _area_type_from_device(data.get("area-type"))
    if at:
        entry["area_type"] = at

    net_raw = data.get("network")
    if net_raw:
        entry["network"] = [{"address": addr} for addr in sorted(to_tag_dict(net_raw))]

    range_raw = data.get("range")
    if range_raw:
        entry["range"] = _keyed_list_from_device(range_raw, _RANGE_KEY)

    vlink_raw = data.get("virtual-link")
    if vlink_raw:
        entry["virtual_link"] = _keyed_list_from_device(
            vlink_raw,
            _VLINK_KEY,
            _vlink_entry_from_device,
        )

    return entry


# ---------------------------------------------------------------------------
# distance -- confirmed genuine structural exception: argspec's "global"
# is a reserved-adjacent-but-legal dict key (fine as a string key, no
# Python keyword issue since it's inside dict(**{...}), unlike "as"
# elsewhere in this collection), device path is distance.global (a
# leaf) and distance.ospf.{external,inter-area,intra-area}.
# ---------------------------------------------------------------------------


def _distance_to_device(dist):
    if not dist:
        return {}
    device = {}
    if dist.get("global") is not None:
        device["global"] = dist["global"]
    ospf = dist.get("ospf")
    if ospf:
        ospf_device = _kebab_fields(ospf)
        if ospf_device:
            device["ospf"] = ospf_device
    return device


def _distance_from_device(data):
    if not data:
        return None
    entry = {}
    if "global" in data:
        entry["global"] = int(data["global"])
    if data.get("ospf"):
        entry["ospf"] = from_device(data["ospf"])
    return entry or None


# ---------------------------------------------------------------------------
# timers -- confirmed genuine structural exception: argspec groups
# "refresh" and "throttle" both under one "timers" parent, but the
# device has them as two SEPARATE top-level nodes ("refresh" and
# "timers.throttle") -- not a nested nesting-insertion like most
# exceptions in this collection, but a nesting *removal*/regrouping.
# Handled at the top level in build_commands/get_running_config rather
# than as a single self-contained entry-transform, since it spans two
# different top-level device keys.
# ---------------------------------------------------------------------------


def _timers_to_device_refresh(timers):
    """Returns the device's top-level "refresh" node contents."""
    refresh = (timers or {}).get("refresh") or {}
    if refresh.get("timers") is not None:
        return {"timers": refresh["timers"]}
    return {}


def _timers_to_device_throttle(timers):
    """Returns the device's top-level "timers" node contents (just the
    throttle.spf subtree, matching confirmed scope)."""
    throttle = (timers or {}).get("throttle") or {}
    spf = throttle.get("spf") or {}
    spf_device = _kebab_fields(spf)
    if spf_device:
        return {"throttle": {"spf": spf_device}}
    return {}


def _timers_from_device(refresh_raw, timers_raw):
    entry = {}
    if refresh_raw and refresh_raw.get("timers") is not None:
        entry["refresh"] = {"timers": int(refresh_raw["timers"])}
    throttle_raw = (timers_raw or {}).get("throttle") or {}
    spf_raw = throttle_raw.get("spf")
    if spf_raw:
        entry["throttle"] = {"spf": from_device(spf_raw)}
    return entry or None


# ---------------------------------------------------------------------------
# passive_interface / passive_interface_exclude -- confirmed against
# vyos-1x: both map onto the SAME per-interface "interface <name>
# passive" node -- presence alone means passive-enabled,
# "passive.disable" (a generic-disable-node) means explicitly
# excluded. These share one device subtree, so both are handled
# together rather than as two independent list diffs.
# ---------------------------------------------------------------------------


def _passive_to_device(passive_list, exclude_list):
    device = {}
    for iface in passive_list or []:
        device[iface] = {"passive": {}}
    for iface in exclude_list or []:
        device[iface] = {"passive": {"disable": {}}}
    return device


def _passive_from_device(iface_raw):
    passive = []
    excluded = []
    for name, data in sorted((iface_raw or {}).items()):
        data = data or {}
        passive_node = data.get("passive")
        if passive_node is None:
            continue
        if isinstance(passive_node, dict) and "disable" in passive_node:
            excluded.append(name)
        else:
            passive.append(name)
    return passive, excluded


# ---------------------------------------------------------------------------
# redistribute -- fully generic once keyed by route_type; metric/
# metric-type/route-map are all plain leaves.
# ---------------------------------------------------------------------------

_REDISTRIBUTE_KEY = "route_type"
_NEIGHBOR_KEY = "neighbor_id"


def _want_to_device(config):
    config = config or {}
    device = {}

    areas = config.get("areas") or []
    if areas:
        device["area"] = _keyed_list_to_device(areas, "area_id", _area_entry_to_device)

    ac = config.get("auto_cost") or {}
    if ac.get("reference_bandwidth") is not None:
        device["auto-cost"] = {"reference-bandwidth": ac["reference_bandwidth"]}

    di = (config.get("default_information") or {}).get("originate") or {}
    di_device = _kebab_fields(di)
    if di_device:
        device["default-information"] = {"originate": di_device}

    if config.get("default_metric") is not None:
        device["default-metric"] = config["default_metric"]

    dist_device = _distance_to_device(config.get("distance"))
    if dist_device:
        device["distance"] = dist_device

    if config.get("log_adjacency_changes"):
        device["log-adjacency-changes"] = {config["log_adjacency_changes"]: {}}

    mm = (config.get("max_metric") or {}).get("router_lsa") or {}
    mm_device = _kebab_fields(mm)
    if mm_device:
        device["max-metric"] = {"router-lsa": mm_device}

    mpls = config.get("mpls_te") or {}
    mpls_device = {}
    if mpls.get("enabled"):
        mpls_device["enable"] = {}
    if mpls.get("router_address"):
        mpls_device["router-address"] = mpls["router_address"]
    if mpls_device:
        device["mpls-te"] = mpls_device

    neighbors = config.get("neighbor") or []
    if neighbors:
        device["neighbor"] = _keyed_list_to_device(neighbors, _NEIGHBOR_KEY)

    params_device = _kebab_fields(config.get("parameters") or {})
    if params_device:
        device["parameters"] = params_device

    iface_device = _passive_to_device(
        config.get("passive_interface"),
        config.get("passive_interface_exclude"),
    )
    if iface_device:
        device["interface"] = iface_device

    redist = config.get("redistribute") or []
    if redist:
        device["redistribute"] = _keyed_list_to_device(redist, _REDISTRIBUTE_KEY)

    refresh_device = _timers_to_device_refresh(config.get("timers"))
    if refresh_device:
        device["refresh"] = refresh_device
    throttle_device = _timers_to_device_throttle(config.get("timers"))
    if throttle_device:
        device.setdefault("timers", {}).update(throttle_device)

    return device


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    if not raw:
        return {}
    entry = {}

    area_raw = raw.get("area")
    if area_raw:
        entry["areas"] = _keyed_list_from_device(area_raw, "area_id", _area_entry_from_device)

    ac = raw.get("auto-cost") or {}
    if ac.get("reference-bandwidth") is not None:
        entry["auto_cost"] = {"reference_bandwidth": int(ac["reference-bandwidth"])}

    di_raw = (raw.get("default-information") or {}).get("originate")
    if di_raw:
        entry["default_information"] = {"originate": from_device(di_raw)}

    if "default-metric" in raw:
        entry["default_metric"] = int(raw["default-metric"])

    dist = _distance_from_device(raw.get("distance"))
    if dist:
        entry["distance"] = dist

    lac = raw.get("log-adjacency-changes")
    if lac:
        lac_dict = to_tag_dict(lac)
        if "detail" in lac_dict:
            entry["log_adjacency_changes"] = "detail"

    mm_raw = (raw.get("max-metric") or {}).get("router-lsa")
    if mm_raw:
        entry["max_metric"] = {"router_lsa": from_device(mm_raw)}

    mpls_raw = raw.get("mpls-te") or {}
    mpls_entry = {}
    if "enable" in mpls_raw:
        mpls_entry["enabled"] = True
    if mpls_raw.get("router-address"):
        mpls_entry["router_address"] = mpls_raw["router-address"]
    if mpls_entry:
        entry["mpls_te"] = mpls_entry

    neighbor_raw = raw.get("neighbor")
    if neighbor_raw:
        entry["neighbor"] = _keyed_list_from_device(neighbor_raw, _NEIGHBOR_KEY)

    params_raw = raw.get("parameters")
    if params_raw:
        entry["parameters"] = from_device(params_raw)

    passive, excluded = _passive_from_device(raw.get("interface"))
    if passive:
        entry["passive_interface"] = passive
    if excluded:
        entry["passive_interface_exclude"] = excluded

    redist_raw = raw.get("redistribute")
    if redist_raw:
        entry["redistribute"] = _keyed_list_from_device(redist_raw, _REDISTRIBUTE_KEY)

    timers = _timers_from_device(raw.get("refresh"), raw.get("timers"))
    if timers:
        entry["timers"] = timers

    return entry


def _kebab_fields(d):
    """autoclean, then kebab-convert the resulting keys.

    Safe specifically because every call site below is a leaf-level
    dict of schema field names (nssa/stub attributes, distance.ospf,
    default_information.originate, max_metric.router_lsa, parameters,
    timers.throttle.spf, virtual_link's plain fields, and range/
    neighbor/redistribute entry fields) with no further nested
    tag-node-keyed structure underneath -- never an opaque value like
    an area ID or interface name used as a dict key, which must stay
    verbatim (confirmed real corruption risk: a blanket recursive
    conversion turns "my_area" into "my-area").

    Needed because dict_op requires have's keys to already be genuine
    device kebab-case -- it only normalizes underscores to dashes for
    its own lookup index, but uses have's key verbatim for the output
    path. autoclean deliberately leaves keys exactly as given (dict_op
    is meant to convert during its own want-vs-have comparison), which
    only works when have comes straight from the device. Here, have is
    instead reconstructed by round-tripping through this module's own
    entry-transforms (needed for confirmed structural exceptions like
    area-type's "set" flag or the shared interface/passive subtree),
    so any field passed through unconverted stays snake_case and
    dict_op has no way to recover the real device key. Confirmed as a
    real bug: "default_cost" appeared in a generated delete command
    instead of "default-cost".
    """
    cleaned = autoclean(d)
    return {k.replace("_", "-"): v for k, v in cleaned.items()}


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


_VLINK_AUTH_OPTIONS = dict(
    md5=dict(
        type="list",
        elements="dict",
        options=dict(
            key_id=dict(type="int"),
            md5_key=dict(type="str", no_log=True),
        ),
    ),
    plaintext_password=dict(type="str", no_log=True),
)

_VLINK_OPTIONS = dict(
    address=dict(type="str", required=True),
    authentication=dict(type="dict", options=_VLINK_AUTH_OPTIONS),
    dead_interval=dict(type="int"),
    hello_interval=dict(type="int"),
    retransmit_interval=dict(type="int"),
    transmit_delay=dict(type="int"),
)

_AREA_OPTIONS = dict(
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
                    translate=dict(type="str", choices=["always", "candidate", "never"]),
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
    authentication=dict(type="str", choices=["plaintext-password", "md5"]),
    network=dict(
        type="list",
        elements="dict",
        options=dict(address=dict(type="str", required=True)),
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
    virtual_link=dict(type="list", elements="dict", options=_VLINK_OPTIONS),
)

_CONFIG_OPTIONS = dict(
    areas=dict(type="list", elements="dict", options=_AREA_OPTIONS),
    auto_cost=dict(
        type="dict",
        options=dict(reference_bandwidth=dict(type="int")),
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
    max_metric=dict(
        type="dict",
        options=dict(
            router_lsa=dict(
                type="dict",
                options=dict(
                    administrative=dict(type="bool"),
                    on_shutdown=dict(type="int"),
                    on_startup=dict(type="int"),
                ),
            ),
        ),
    ),
    mpls_te=dict(
        type="dict",
        options=dict(
            enabled=dict(type="bool"),
            router_address=dict(type="str"),
        ),
    ),
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
            abr_type=dict(type="str", choices=["cisco", "ibm", "shortcut", "standard"]),
            opaque_lsa=dict(type="bool"),
            rfc1583_compatibility=dict(type="bool"),
            router_id=dict(type="str"),
        ),
    ),
    passive_interface=dict(type="list", elements="str"),
    passive_interface_exclude=dict(type="list", elements="str"),
    redistribute=dict(
        type="list",
        elements="dict",
        options=dict(
            route_type=dict(type="str", choices=["bgp", "connected", "kernel", "rip", "static"]),
            metric=dict(type="int"),
            metric_type=dict(type="int"),
            route_map=dict(type="str"),
        ),
    ),
    timers=dict(
        type="dict",
        options=dict(
            refresh=dict(
                type="dict",
                options=dict(timers=dict(type="int")),
            ),
            throttle=dict(
                type="dict",
                options=dict(
                    spf=dict(
                        type="dict",
                        options=dict(
                            delay=dict(type="int"),
                            initial_holdtime=dict(type="int"),
                            max_holdtime=dict(type="int"),
                        ),
                    ),
                ),
            ),
        ),
    ),
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
