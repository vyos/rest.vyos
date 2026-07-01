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


def _parse_parameters(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    if "router-id" in raw:
        result["router_id"] = raw["router-id"]
    if "log-neighbor-changes" in raw:
        result["log_neighbor_changes"] = True
    if "no-ipv4-unicast" in raw:
        result["no_ipv4_unicast"] = True
    if "graceful-restart" in raw:
        result["graceful_restart"] = True
    bp = raw.get("bestpath", {}) or {}
    if bp:
        bestpath = {}
        if "as-path" in bp:
            bestpath["as_path"] = bp["as-path"]
        if bestpath:
            result["bestpath"] = bestpath
    conf = raw.get("confederation", {}) or {}
    if conf:
        confederation = {}
        if "identifier" in conf:
            confederation["identifier"] = int(conf["identifier"])
        if "peers" in conf:
            peers = conf["peers"]
            if isinstance(peers, list):
                confederation["peers"] = [int(p) for p in peers]
            else:
                confederation["peers"] = [int(peers)]
        if confederation:
            result["confederation"] = confederation
    return result


def _parse_neighbor(nb_id, data):
    nb = {"neighbor_address": nb_id}
    data = data or {}
    if "remote-as" in data:
        nb["remote_as"] = int(data["remote-as"])
    if "description" in data:
        nb["description"] = data["description"]
    if "ebgp-multihop" in data:
        nb["ebgp_multihop"] = int(data["ebgp-multihop"])
    if "local-as" in data:
        nb["local_as"] = int(data["local-as"])
    if "password" in data:
        nb["password"] = data["password"]
    if "peer-group" in data:
        nb["peer_group"] = data["peer-group"]
    if "shutdown" in data:
        nb["shutdown"] = True
    if "update-source" in data:
        nb["update_source"] = data["update-source"]
    if "disable-connected-check" in data:
        nb["disable_connected_check"] = True
    timers = data.get("timers", {}) or {}
    if timers:
        t = {}
        if "holdtime" in timers:
            t["holdtime"] = int(timers["holdtime"])
        if "keepalive" in timers:
            t["keepalive"] = int(timers["keepalive"])
        if t:
            nb["timers"] = t
    return nb


def _parse_peer_group(pg_name, data):
    pg = {"peer_group": pg_name}
    data = data or {}
    if "remote-as" in data:
        pg["remote_as"] = int(data["remote-as"])
    if "description" in data:
        pg["description"] = data["description"]
    if "ebgp-multihop" in data:
        pg["ebgp_multihop"] = int(data["ebgp-multihop"])
    if "password" in data:
        pg["password"] = data["password"]
    if "update-source" in data:
        pg["update_source"] = data["update-source"]
    timers = data.get("timers", {}) or {}
    if timers:
        t = {}
        if "holdtime" in timers:
            t["holdtime"] = int(timers["holdtime"])
        if "keepalive" in timers:
            t["keepalive"] = int(timers["keepalive"])
        if t:
            pg["timers"] = t
    return pg


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}

    if "system-as" in raw:
        result["as_number"] = int(raw["system-as"])

    params = _parse_parameters(raw.get("parameters"))
    if params:
        result["parameters"] = params

    neighbors = []
    for nb_id, data in sorted((raw.get("neighbor") or {}).items()):
        neighbors.append(_parse_neighbor(nb_id, data))
    if neighbors:
        result["neighbors"] = neighbors

    peer_groups = []
    for pg_name, data in sorted((raw.get("peer-group") or {}).items()):
        peer_groups.append(_parse_peer_group(pg_name, data))
    if peer_groups:
        result["peer_groups"] = peer_groups

    return result


def _neighbor_cmds(nb, have_nb):
    cmds = []
    nb_addr = nb["neighbor_address"]
    nbase = _BASE + ["neighbor", nb_addr]
    have_nb = have_nb or {}

    if nb.get("remote_as") and nb["remote_as"] != have_nb.get("remote_as"):
        cmds.append(("set", nbase + ["remote-as", str(nb["remote_as"])]))
    if nb.get("description") and nb["description"] != have_nb.get("description"):
        cmds.append(("set", nbase + ["description", nb["description"]]))
    if nb.get("ebgp_multihop") and nb["ebgp_multihop"] != have_nb.get("ebgp_multihop"):
        cmds.append(("set", nbase + ["ebgp-multihop", str(nb["ebgp_multihop"])]))
    if nb.get("local_as") and nb["local_as"] != have_nb.get("local_as"):
        cmds.append(("set", nbase + ["local-as", str(nb["local_as"])]))
    if nb.get("password") and nb["password"] != have_nb.get("password"):
        cmds.append(("set", nbase + ["password", nb["password"]]))
    if nb.get("peer_group") and nb["peer_group"] != have_nb.get("peer_group"):
        cmds.append(("set", nbase + ["peer-group", nb["peer_group"]]))
    if nb.get("update_source") and nb["update_source"] != have_nb.get("update_source"):
        cmds.append(("set", nbase + ["update-source", nb["update_source"]]))
    if nb.get("shutdown") and not have_nb.get("shutdown"):
        cmds.append(("set", nbase + ["shutdown"]))
    if nb.get("disable_connected_check") and not have_nb.get("disable_connected_check"):
        cmds.append(("set", nbase + ["disable-connected-check"]))

    want_t = nb.get("timers") or {}
    have_t = have_nb.get("timers") or {}
    if want_t.get("holdtime") and want_t["holdtime"] != have_t.get("holdtime"):
        cmds.append(("set", nbase + ["timers", "holdtime", str(want_t["holdtime"])]))
    if want_t.get("keepalive") and want_t["keepalive"] != have_t.get("keepalive"):
        cmds.append(("set", nbase + ["timers", "keepalive", str(want_t["keepalive"])]))

    return cmds


def _peer_group_cmds(pg, have_pg):
    cmds = []
    pg_name = pg["peer_group"]
    pbase = _BASE + ["peer-group", pg_name]
    have_pg = have_pg or {}

    if pg.get("remote_as") and pg["remote_as"] != have_pg.get("remote_as"):
        cmds.append(("set", pbase + ["remote-as", str(pg["remote_as"])]))
    if pg.get("description") and pg["description"] != have_pg.get("description"):
        cmds.append(("set", pbase + ["description", pg["description"]]))
    if pg.get("ebgp_multihop") and pg["ebgp_multihop"] != have_pg.get("ebgp_multihop"):
        cmds.append(("set", pbase + ["ebgp-multihop", str(pg["ebgp_multihop"])]))
    if pg.get("password") and pg["password"] != have_pg.get("password"):
        cmds.append(("set", pbase + ["password", pg["password"]]))
    if pg.get("update_source") and pg["update_source"] != have_pg.get("update_source"):
        cmds.append(("set", pbase + ["update-source", pg["update_source"]]))

    want_t = pg.get("timers") or {}
    have_t = have_pg.get("timers") or {}
    if want_t.get("holdtime") and want_t["holdtime"] != have_t.get("holdtime"):
        cmds.append(("set", pbase + ["timers", "holdtime", str(want_t["holdtime"])]))
    if want_t.get("keepalive") and want_t["keepalive"] != have_t.get("keepalive"):
        cmds.append(("set", pbase + ["timers", "keepalive", str(want_t["keepalive"])]))

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

    # system-as — must be first
    if config.get("as_number") and config["as_number"] != have.get("as_number"):
        cmds.append(("set", _BASE + ["system-as", str(config["as_number"])]))

    # parameters
    params = config.get("parameters") or {}
    have_params = have.get("parameters") or {}
    if params.get("router_id") and params["router_id"] != have_params.get("router_id"):
        cmds.append(("set", _BASE + ["parameters", "router-id", params["router_id"]]))
    if params.get("log_neighbor_changes") and not have_params.get("log_neighbor_changes"):
        cmds.append(("set", _BASE + ["parameters", "log-neighbor-changes"]))
    if params.get("no_ipv4_unicast") and not have_params.get("no_ipv4_unicast"):
        cmds.append(("set", _BASE + ["parameters", "no-ipv4-unicast"]))
    if params.get("graceful_restart") and not have_params.get("graceful_restart"):
        cmds.append(("set", _BASE + ["parameters", "graceful-restart"]))
    bp = params.get("bestpath") or {}
    have_bp = have_params.get("bestpath") or {}
    if bp.get("as_path") and bp["as_path"] != have_bp.get("as_path"):
        cmds.append(("set", _BASE + ["parameters", "bestpath", "as-path", bp["as_path"]]))

    # neighbors
    have_nb_map = {n["neighbor_address"]: n for n in (have.get("neighbors") or [])}
    for nb in config.get("neighbors") or []:
        cmds += _neighbor_cmds(nb, have_nb_map.get(nb["neighbor_address"]))

    # peer_groups
    have_pg_map = {p["peer_group"]: p for p in (have.get("peer_groups") or [])}
    for pg in config.get("peer_groups") or []:
        cmds += _peer_group_cmds(pg, have_pg_map.get(pg["peer_group"]))

    return cmds


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
