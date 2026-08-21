#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_bgp_global
short_description: Manage BGP global configuration on VyOS devices using REST API
description:
  - Manages BGP global configuration on VyOS devices via the REST API.
  - Covers system AS, parameters, neighbors, and peer-groups.
  - For per-neighbor address-family configuration use M(vyos.rest.vyos_bgp_address_family).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: BGP global configuration.
    type: dict
    suboptions:
      as_number:
        description: BGP autonomous system number.
        type: int
        required: true
      parameters:
        description: BGP global parameters.
        type: dict
        suboptions:
          router_id:
            description: BGP router ID.
            type: str
          confederation:
            description: AS confederation parameters.
            type: dict
            suboptions:
              identifier:
                description: Confederation AS identifier.
                type: int
              peers:
                description: Peer ASs in confederation.
                type: list
                elements: int
          bestpath:
            description: BGP bestpath parameters.
            type: dict
            suboptions:
              as_path:
                description: AS-path attribute comparison.
                type: str
                choices: [confed, ignore, multipath-relax]
          graceful_restart:
            description: Enable graceful restart.
            type: bool
          log_neighbor_changes:
            description: Log neighbor up/down changes.
            type: bool
          no_ipv4_unicast:
            description: Disable IPv4 unicast default.
            type: bool
      neighbors:
        description: BGP neighbors.
        type: list
        elements: dict
        suboptions:
          neighbor_address:
            description: Neighbor IP address.
            type: str
            required: true
          remote_as:
            description: Neighbor AS number.
            type: int
          description:
            description: Neighbor description.
            type: str
          disable_connected_check:
            description: Disable connected route check.
            type: bool
          ebgp_multihop:
            description: EBGP multihop TTL.
            type: int
          local_as:
            description: Local AS number.
            type: int
          password:
            description: MD5 password for neighbor.
            type: str
          peer_group:
            description: Peer group name.
            type: str
          shutdown:
            description: Shutdown neighbor.
            type: bool
          timers:
            description: Neighbor timers.
            type: dict
            suboptions:
              holdtime:
                description: Hold time in seconds.
                type: int
              keepalive:
                description: Keepalive interval in seconds.
                type: int
          update_source:
            description: Source interface/IP for updates.
            type: str
      peer_groups:
        description: BGP peer groups.
        type: list
        elements: dict
        suboptions:
          peer_group:
            description: Peer group name.
            type: str
            required: true
          remote_as:
            description: Peer group AS number.
            type: int
          description:
            description: Peer group description.
            type: str
          ebgp_multihop:
            description: EBGP multihop TTL.
            type: int
          password:
            description: MD5 password.
            type: str
          timers:
            description: Peer group timers.
            type: dict
            suboptions:
              holdtime:
                description: Hold time in seconds.
                type: int
              keepalive:
                description: Keepalive interval in seconds.
                type: int
          update_source:
            description: Source interface/IP for updates.
            type: str
  state:
    description:
      - Desired state of the BGP global configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces the entire BGP configuration.
      - C(deleted) removes BGP configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - BGP system-as must be defined before any other BGP configuration.
"""

EXAMPLES = r"""
- name: Merge BGP global configuration
  vyos.rest.vyos_bgp_global:
    config:
      as_number: 65000
      parameters:
        router_id: 192.0.1.1
      neighbors:
        - neighbor_address: 192.0.2.1
          remote_as: 65001
          description: peer1
          timers:
            holdtime: 30
            keepalive: 10
      peer_groups:
        - peer_group: PG1
          remote_as: 65002
    state: merged

- name: Delete BGP configuration
  vyos.rest.vyos_bgp_global:
    state: deleted

- name: Gather BGP global configuration
  vyos.rest.vyos_bgp_global:
    state: gathered
"""

RETURN = r"""
before:
  description: BGP configuration before this module ran.
  returned: always
  type: dict
after:
  description: BGP configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current BGP configuration as structured data.
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
    scope_to_spec,
)


_BASE = ["protocols", "bgp"]

# "neighbor" and "peer-group" are genuine tag nodes (like network/
# redistribute in vyos_bgp_address_family) that VyOS's REST API can
# collapse to a bare string for a single entry with no other config.
_TAG_KEYS = {"neighbor", "peer-group"}


# ---------------------------------------------------------------------------
# want -> device / device -> argspec
#
# Every leaf here is a direct structural match between argspec and device
# shape (unlike vyos_bgp_address_family, this module has zero device-shape
# exceptions) -- only the two tag-node reshapes (neighbors keyed by
# address, peer_groups keyed by name) are unavoidable structural work.
# ---------------------------------------------------------------------------


def _neighbors_to_device(neighbors):
    return {
        nb["neighbor_address"]: autoclean(
            {k: v for k, v in nb.items() if k != "neighbor_address"},
        )
        for nb in neighbors or []
    }


def _neighbors_from_device(raw):
    result = []
    for addr, data in sorted((raw or {}).items()):
        scoped = scope_to_spec(data or {}, _NEIGHBOR_OPTIONS, exclude={"neighbor_address"})
        entry = {"neighbor_address": addr, **from_device(scoped)}
        cast_by_spec(entry, _NEIGHBOR_OPTIONS)
        result.append(entry)
    return result


def _peer_groups_to_device(peer_groups):
    return {
        pg["peer_group"]: autoclean({k: v for k, v in pg.items() if k != "peer_group"})
        for pg in peer_groups or []
    }


def _peer_groups_from_device(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        scoped = scope_to_spec(data or {}, _PEER_GROUP_OPTIONS, exclude={"peer_group"})
        entry = {"peer_group": name, **from_device(scoped)}
        cast_by_spec(entry, _PEER_GROUP_OPTIONS)
        result.append(entry)
    return result


def _want_to_device(config):
    config = config or {}
    result = {}
    if config.get("as_number") is not None:
        result["system_as"] = config["as_number"]
    if config.get("parameters"):
        result["parameters"] = autoclean(config["parameters"])
    if config.get("neighbors"):
        result["neighbor"] = _neighbors_to_device(config["neighbors"])
    if config.get("peer_groups"):
        result["peer_group"] = _peer_groups_to_device(config["peer_groups"])
    return result


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "system-as" in raw:
        result["as_number"] = int(raw["system-as"])
    if raw.get("parameters"):
        params = from_device(raw["parameters"])
        cast_by_spec(params, _PARAMETERS_OPTIONS)
        result["parameters"] = params
    neighbors = _neighbors_from_device(raw.get("neighbor"))
    if neighbors:
        result["neighbors"] = neighbors
    peer_groups = _peer_groups_from_device(raw.get("peer-group"))
    if peer_groups:
        result["peer_groups"] = peer_groups
    return result


# ---------------------------------------------------------------------------
# Command building — dict_op scoped per owned subtree, with one exception.
#
# "protocols bgp" is a shared root with vyos_bgp_address_family, and each
# neighbor entry mixes fields owned by *both* modules (this module owns
# remote-as/timers/etc.; the sibling module owns the nested address-family
# subtree). Every dict_op call for a neighbor or peer-group here first
# goes through scope_to_spec() against this module's own ARGUMENT_SPEC, so
# a foreign subtree like address-family is never visible to purge/set —
# without hardcoding its name, since this module's argspec simply never
# declared it.
#
# The one exception: removing system-as. VyOS rejects any commit that
# leaves "protocols bgp" non-empty without an AS number defined, so that
# specific transition can't be done with scoped/incremental commands --
# see the short-circuit at the top of build_commands().
# ---------------------------------------------------------------------------


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    # "deleted" is "replaced" with an empty desired state -- same scoped
    # purge mechanics, no separate blanket-delete-the-whole-root logic
    # (which would have wiped the sibling module's config too)...
    want = _want_to_device({} if state == "deleted" else config)
    effective_state = "replaced" if state == "deleted" else state

    # ...EXCEPT for one case: VyOS requires system-as to be defined
    # whenever "protocols bgp" has any content at all, and rejects the
    # commit otherwise. So if system-as is being removed (present in
    # have, absent from want) under replaced/deleted -- the only states
    # that purge at all -- the only valid action is to delete the entire
    # tree in one atomic commit, including address-family, which cannot
    # validly exist without an AS number anyway. This is a real
    # device-model cascade, not cross-module scope creep. It must never
    # fire for "merged": an omitted config/as_number there is a no-op by
    # definition, and merged's set-only dict_op flow below already
    # leaves system-as untouched correctly on its own.
    if effective_state == "replaced" and "system-as" in raw_have and "system_as" not in want:
        return [("delete", _BASE)]

    commands = []

    norm_have = normalize_have(raw_have, _TAG_KEYS)

    top_have = {k: v for k, v in raw_have.items() if k in ("system-as", "parameters")}
    top_want = {k: v for k, v in want.items() if k in ("system_as", "parameters")}
    if effective_state == "replaced":
        commands += dict_op(top_want, top_have, _BASE, op="purge")
    commands += dict_op(top_want, top_have, _BASE, op="set")

    raw_neighbors = norm_have.get("neighbor") or {}
    want_neighbors = want.get("neighbor", {})
    for addr in sorted(set(want_neighbors) | set(raw_neighbors)):
        nbase = _BASE + ["neighbor", addr]
        have_scoped = scope_to_spec(
            raw_neighbors.get(addr) or {},
            _NEIGHBOR_OPTIONS,
            exclude={"neighbor_address"},
        )
        want_entry = want_neighbors.get(addr, {})
        if effective_state == "replaced":
            commands += dict_op(want_entry, have_scoped, nbase, op="purge")
        commands += dict_op(want_entry, have_scoped, nbase, op="set")

    raw_peer_groups = norm_have.get("peer-group") or {}
    want_peer_groups = want.get("peer_group", {})
    for name in sorted(set(want_peer_groups) | set(raw_peer_groups)):
        pbase = _BASE + ["peer-group", name]
        have_scoped = scope_to_spec(
            raw_peer_groups.get(name) or {},
            _PEER_GROUP_OPTIONS,
            exclude={"peer_group"},
        )
        want_entry = want_peer_groups.get(name, {})
        if effective_state == "replaced":
            commands += dict_op(want_entry, have_scoped, pbase, op="purge")
        commands += dict_op(want_entry, have_scoped, pbase, op="set")

    return commands


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            as_number=dict(type="int", required=True),
            parameters=dict(
                type="dict",
                options=dict(
                    router_id=dict(type="str"),
                    log_neighbor_changes=dict(type="bool"),
                    no_ipv4_unicast=dict(type="bool"),
                    graceful_restart=dict(type="bool"),
                    bestpath=dict(
                        type="dict",
                        options=dict(
                            as_path=dict(
                                type="str",
                                choices=["confed", "ignore", "multipath-relax"],
                            ),
                        ),
                    ),
                    confederation=dict(
                        type="dict",
                        options=dict(
                            identifier=dict(type="int"),
                            peers=dict(type="list", elements="int"),
                        ),
                    ),
                ),
            ),
            neighbors=dict(
                type="list",
                elements="dict",
                options=dict(
                    neighbor_address=dict(type="str", required=True),
                    remote_as=dict(type="int"),
                    description=dict(type="str"),
                    disable_connected_check=dict(type="bool"),
                    ebgp_multihop=dict(type="int"),
                    local_as=dict(type="int"),
                    password=dict(type="str", no_log=True),
                    peer_group=dict(type="str"),
                    shutdown=dict(type="bool"),
                    timers=dict(
                        type="dict",
                        options=dict(
                            holdtime=dict(type="int"),
                            keepalive=dict(type="int"),
                        ),
                    ),
                    update_source=dict(type="str"),
                ),
            ),
            peer_groups=dict(
                type="list",
                elements="dict",
                options=dict(
                    peer_group=dict(type="str", required=True),
                    remote_as=dict(type="int"),
                    description=dict(type="str"),
                    ebgp_multihop=dict(type="int"),
                    password=dict(type="str", no_log=True),
                    timers=dict(
                        type="dict",
                        options=dict(
                            holdtime=dict(type="int"),
                            keepalive=dict(type="int"),
                        ),
                    ),
                    update_source=dict(type="str"),
                ),
            ),
        ),
    ),
    state=dict(
        default="merged",
        choices=["merged", "replaced", "deleted", "gathered"],
    ),
)

# Populated post-definition (avoids forward-reference ordering); backs
# cast_by_spec/scope_to_spec so have-side casting and cross-module
# protection are both derived from the spec itself.
_PARAMETERS_OPTIONS = ARGUMENT_SPEC["config"]["options"]["parameters"]["options"]
_NEIGHBOR_OPTIONS = ARGUMENT_SPEC["config"]["options"]["neighbors"]["options"]
_PEER_GROUP_OPTIONS = ARGUMENT_SPEC["config"]["options"]["peer_groups"]["options"]


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
