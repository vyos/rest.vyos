#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
module: vyos_ha
short_description: Manage VRRP and load balancer configuration on VyOS via REST API
description:
- Manages VRRP groups, global VRRP parameters, sync-groups, virtual servers, and LVS
  real servers on VyOS devices via the REST API.
- Uses REST API (C(connection=httpapi)) instead of CLI.
- Targets VyOS 1.4+.
version_added: 1.0.0
author:
- Evgeny Molotkov (@omnom62)
options:
  config:
    description: High-availability configuration.
    type: dict
    suboptions:
      disable:
        description: Disable all high-availability configuration.
        type: bool
        default: false
      virtual_servers:
        description: List of load balancer virtual server definitions.
        type: list
        elements: dict
        suboptions:
          name:
            type: str
            required: true
            description: Name.
          address:
            type: str
            description: Address.
          algorithm:
            type: str
            description: Algorithm.
          delay_loop:
            type: int
            description: Delay loop.
          forward_method:
            type: str
            choices:
            - direct
            - nat
            description: Forward method.
          fwmark:
            type: int
            description: Fwmark.
          persistence_timeout:
            type: int
            description: Persistence timeout.
          port:
            type: int
            description: Port.
          protocol:
            type: str
            choices:
            - tcp
            - udp
            description: Protocol.
          real_server:
            type: list
            elements: dict
            suboptions:
              address:
                type: str
                required: true
                description: Address.
              port:
                type: int
                description: Port.
              connection_timeout:
                type: int
                description: Connection timeout.
              health_check_script:
                type: str
                description: Health check script.
            description: Real server.
      vrrp:
        description: VRRP configuration.
        type: dict
        suboptions:
          global_parameters:
            type: dict
            suboptions:
              garp:
                type: dict
                suboptions:
                  interval:
                    type: int
                    description: Interval.
                  master_delay:
                    type: int
                    description: Master delay.
                  master_refresh:
                    type: int
                    description: Master refresh.
                  master_refresh_repeat:
                    type: int
                    description: Master refresh repeat.
                  master_repeat:
                    type: int
                    description: Master repeat.
                description: Garp.
              startup_delay:
                type: int
                description: Startup delay.
              version:
                type: str
                description: Version.
            description: Global parameters.
          groups:
            type: list
            elements: dict
            suboptions:
              name:
                type: str
                required: true
                description: Name.
              address:
                type: list
                elements: str
                description: Address.
              advertise_interval:
                type: int
                description: Advertise interval.
              authentication:
                type: dict
                suboptions:
                  password:
                    type: str
                    description: Password.
                  type:
                    type: str
                    description: Type.
                description: Authentication.
              description:
                type: str
                description: Description.
              disable:
                type: bool
                default: false
                description: Disable.
              excluded_address:
                type: list
                elements: str
                description: Excluded address.
              garp:
                type: dict
                suboptions:
                  interval:
                    type: int
                    description: Interval.
                  master_delay:
                    type: int
                    description: Master delay.
                  master_refresh:
                    type: int
                    description: Master refresh.
                  master_refresh_repeat:
                    type: int
                    description: Master refresh repeat.
                  master_repeat:
                    type: int
                    description: Master repeat.
                description: Garp.
              health_check:
                type: dict
                suboptions:
                  failure_count:
                    type: int
                    description: Failure count.
                  interval:
                    type: int
                    description: Interval.
                  ping:
                    type: str
                    description: Ping.
                  script:
                    type: str
                    description: Script.
                description: Health check.
              hello_source_address:
                type: str
                description: Hello source address.
              interface:
                type: str
                description: Interface.
              no_preempt:
                type: bool
                default: false
                description: No preempt.
              peer_address:
                type: str
                description: Peer address.
              preempt_delay:
                type: int
                description: Preempt delay.
              priority:
                type: int
                description: Priority.
              rfc3768_compatibility:
                type: bool
                default: false
                description: Rfc3768 compatibility.
              track:
                type: dict
                suboptions:
                  exclude_vrrp_interface:
                    type: bool
                    description: Exclude vrrp interface.
                  interface:
                    type: list
                    elements: str
                    description: Interface.
                description: Track.
              transition_script:
                type: dict
                suboptions:
                  backup:
                    type: str
                    description: Backup.
                  fault:
                    type: str
                    description: Fault.
                  master:
                    type: str
                    description: Master.
                  stop:
                    type: str
                    description: Stop.
                description: Transition script.
              vrid:
                type: int
                description: Vrid.
            description: Groups.
          snmp:
            type: str
            choices:
            - enabled
            - disabled
            description: Snmp.
          sync_groups:
            type: list
            elements: dict
            suboptions:
              name:
                type: str
                required: true
                description: Name.
              health_check:
                type: dict
                suboptions:
                  failure_count:
                    type: int
                    description: Failure count.
                  interval:
                    type: int
                    description: Interval.
                  ping:
                    type: str
                    description: Ping.
                  script:
                    type: str
                    description: Script.
                description: Health check.
              member:
                type: list
                elements: str
                description: Member.
              transition_script:
                type: dict
                suboptions:
                  backup:
                    type: str
                    description: Backup.
                  fault:
                    type: str
                    description: Fault.
                  master:
                    type: str
                    description: Master.
                  stop:
                    type: str
                    description: Stop.
                description: Transition script.
            description: Sync groups.
  state:
    description: Desired end state of the configuration.
    type: str
    choices:
    - merged
    - replaced
    - overridden
    - deleted
    - gathered
    default: merged

"""

EXAMPLES = r"""
- name: Merge VRRP configuration
  vyos.rest.vyos_ha:
    config:
      vrrp:
        global_parameters:
          startup_delay: 30
        groups:
          - name: g1
            interface: eth0
            vrid: 20
            priority: 100
            address:
              - 192.168.1.100/24
        sync_groups:
          - name: sg1
            member: [g1]
        snmp: enabled
    state: merged

- name: Delete all HA configuration
  vyos.rest.vyos_ha:
    state: deleted

- name: Gather current HA configuration
  vyos.rest.vyos_ha:
    state: gathered
"""

RETURN = r"""
before:
  description: HA configuration before this module ran.
  returned: always
  type: dict
after:
  description: HA configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API commands sent to the device.
  returned: always
  type: list
gathered:
  description: Current HA configuration as structured data.
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
    normalize_have,
    to_tag_dict,
)


_BASE = ["high-availability"]

ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            disable=dict(type="bool", default=False),
            virtual_servers=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    address=dict(type="str"),
                    algorithm=dict(type="str"),
                    delay_loop=dict(type="int"),
                    forward_method=dict(type="str", choices=["direct", "nat"]),
                    fwmark=dict(type="int"),
                    persistence_timeout=dict(type="int"),
                    port=dict(type="int"),
                    protocol=dict(type="str", choices=["tcp", "udp"]),
                    real_server=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str", required=True),
                            port=dict(type="int"),
                            connection_timeout=dict(type="int"),
                            health_check_script=dict(type="str"),
                        ),
                    ),
                ),
            ),
            vrrp=dict(
                type="dict",
                options=dict(
                    global_parameters=dict(
                        type="dict",
                        options=dict(
                            garp=dict(
                                type="dict",
                                options=dict(
                                    interval=dict(type="int"),
                                    master_delay=dict(type="int"),
                                    master_refresh=dict(type="int"),
                                    master_refresh_repeat=dict(type="int"),
                                    master_repeat=dict(type="int"),
                                ),
                            ),
                            startup_delay=dict(type="int"),
                            version=dict(type="str"),
                        ),
                    ),
                    groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            address=dict(type="list", elements="str"),
                            advertise_interval=dict(type="int"),
                            authentication=dict(
                                type="dict",
                                options=dict(
                                    password=dict(type="str", no_log=True),
                                    type=dict(type="str"),
                                ),
                            ),
                            description=dict(type="str"),
                            disable=dict(type="bool", default=False),
                            excluded_address=dict(type="list", elements="str"),
                            garp=dict(
                                type="dict",
                                options=dict(
                                    interval=dict(type="int"),
                                    master_delay=dict(type="int"),
                                    master_refresh=dict(type="int"),
                                    master_refresh_repeat=dict(type="int"),
                                    master_repeat=dict(type="int"),
                                ),
                            ),
                            health_check=dict(
                                type="dict",
                                options=dict(
                                    failure_count=dict(type="int"),
                                    interval=dict(type="int"),
                                    ping=dict(type="str"),
                                    script=dict(type="str"),
                                ),
                            ),
                            hello_source_address=dict(type="str"),
                            interface=dict(type="str"),
                            no_preempt=dict(type="bool", default=False),
                            peer_address=dict(type="str"),
                            preempt_delay=dict(type="int"),
                            priority=dict(type="int"),
                            rfc3768_compatibility=dict(type="bool", default=False),
                            track=dict(
                                type="dict",
                                options=dict(
                                    exclude_vrrp_interface=dict(type="bool"),
                                    interface=dict(type="list", elements="str"),
                                ),
                            ),
                            transition_script=dict(
                                type="dict",
                                options=dict(
                                    backup=dict(type="str"),
                                    fault=dict(type="str"),
                                    master=dict(type="str"),
                                    stop=dict(type="str"),
                                ),
                            ),
                            vrid=dict(type="int"),
                        ),
                    ),
                    snmp=dict(type="str", choices=["enabled", "disabled"]),
                    sync_groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(type="str", required=True),
                            health_check=dict(
                                type="dict",
                                options=dict(
                                    failure_count=dict(type="int"),
                                    interval=dict(type="int"),
                                    ping=dict(type="str"),
                                    script=dict(type="str"),
                                ),
                            ),
                            member=dict(type="list", elements="str"),
                            transition_script=dict(
                                type="dict",
                                options=dict(
                                    backup=dict(type="str"),
                                    fault=dict(type="str"),
                                    master=dict(type="str"),
                                    stop=dict(type="str"),
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
        choices=["merged", "replaced", "overridden", "deleted", "gathered"],
    ),
)

_TOP_OPTIONS = ARGUMENT_SPEC["config"]["options"]
_VS_OPTIONS = _TOP_OPTIONS["virtual_servers"]["options"]
_RS_OPTIONS = _VS_OPTIONS["real_server"]["options"]
_VRRP_OPTIONS = _TOP_OPTIONS["vrrp"]["options"]
_GROUP_OPTIONS = _VRRP_OPTIONS["groups"]["options"]
_SYNC_GROUP_OPTIONS = _VRRP_OPTIONS["sync_groups"]["options"]

# Tag nodes VyOS's REST API can collapse to a bare string/list for a
# single entry with no other config. Split by section because "address"
# means two different things depending on where it appears -- confirmed
# against vyos-1x: vrrp.group.<name>.address is a genuine tagNode (VRRP
# virtual IPs, each with real child structure), but virtual-server.
# <name>.address is a flat scalar string (the load-balancer's own bind
# address). A single blanket key-name-based coercion across the whole
# raw tree would wrongly reshape the latter into a tag-node dict --
# exactly the class of bug this split avoids.
_VS_TAG_KEYS = {"virtual-server", "real-server"}
_VRRP_TAG_KEYS = {"group", "sync-group", "address", "excluded-address"}

# track.interface and sync-group.member are NOT included above --
# confirmed <leafNode><multi/>, i.e. plain multi-value leaves, not tag
# nodes; dict_op's own native list handling (which already corrects for
# the same single-value-collapse quirk) applies to them directly, no
# reshaping needed.


# ---------------------------------------------------------------------------
# Structural adapters — the only genuine exceptions, confirmed against
# vyos-1x schema, not assumed:
# 1. Named-object lists (virtual_servers, real_server, groups,
#    sync_groups): argspec uses [{name: "x", ...}], device uses
#    {"x": {...}}.
# 2. address / excluded_address (VRRP group virtual IPs): genuine
#    tagNodes (each has real child structure) -> {"a": {}, "b": {}}.
# 3. snmp: argspec "enabled"/"disabled" string <-> device presence node
#    (present) / absent. "disabled" has no device-side representation at
#    all -- see the explicit delete in build_commands().
# 4. health_check_script: argspec flat field <-> device nested under
#    health-check.script.
#
# Everything else -- including track.interface and sync_group.member,
# both plain multi-value leaves despite superficially looking like the
# same shape as address/excluded_address -- flows through autoclean/
# from_device untouched.
# ---------------------------------------------------------------------------


def _real_server_to_device(rs):
    entry = autoclean(
        {k: v for k, v in rs.items() if k not in ("address", "health_check_script")},
    )
    if rs.get("health_check_script"):
        entry["health-check"] = {"script": rs["health_check_script"]}
    return entry


def _real_server_from_device(addr, data):
    data = dict(data or {})
    hc = data.pop("health-check", None) or {}
    entry = {"address": addr, **from_device(data)}
    if hc.get("script"):
        entry["health_check_script"] = hc["script"]
    cast_by_spec(entry, _RS_OPTIONS)
    return entry


def _virtual_server_to_device(vs):
    entry = autoclean({k: v for k, v in vs.items() if k not in ("name", "real_server")})
    if vs.get("real_server"):
        entry["real-server"] = {
            rs["address"]: _real_server_to_device(rs) for rs in vs["real_server"]
        }
    return entry


def _virtual_server_from_device(name, data):
    data = dict(data or {})
    rs_raw = data.pop("real-server", None) or {}
    entry = {"name": name, **from_device(data)}
    cast_by_spec(entry, _VS_OPTIONS)
    if rs_raw:
        entry["real_server"] = [
            _real_server_from_device(addr, rdata) for addr, rdata in sorted(rs_raw.items())
        ]
    return entry


def _group_to_device(grp):
    entry = autoclean(
        {k: v for k, v in grp.items() if k not in ("name", "address", "excluded_address")},
    )
    if grp.get("address"):
        entry["address"] = {a: {} for a in grp["address"]}
    if grp.get("excluded_address"):
        entry["excluded-address"] = {a: {} for a in grp["excluded_address"]}
    return entry


def _group_from_device(name, data):
    data = dict(data or {})
    addr_raw = data.pop("address", None)
    excl_raw = data.pop("excluded-address", None)
    entry = {"name": name, **from_device(data)}
    cast_by_spec(entry, _GROUP_OPTIONS)
    if addr_raw:
        entry["address"] = sorted(to_tag_dict(addr_raw).keys())
    if excl_raw:
        entry["excluded_address"] = sorted(to_tag_dict(excl_raw).keys())
    return entry


def _sync_group_from_device(name, data):
    entry = {"name": name, **from_device(data or {})}
    cast_by_spec(entry, _SYNC_GROUP_OPTIONS)
    return entry


def _want_to_device(config):
    if not config:
        return {}
    want = autoclean({k: v for k, v in config.items() if k not in ("virtual_servers", "vrrp")})

    if config.get("virtual_servers"):
        want["virtual-server"] = {
            vs["name"]: _virtual_server_to_device(vs) for vs in config["virtual_servers"]
        }

    vrrp = config.get("vrrp") or {}
    if vrrp:
        vrrp_dev = autoclean(
            {k: v for k, v in vrrp.items() if k not in ("groups", "sync_groups", "snmp")},
        )
        # snmp: "enabled" -> presence node; "disabled" has no device-side
        # form at all (handled via an explicit delete in build_commands).
        if vrrp.get("snmp") == "enabled":
            vrrp_dev["snmp"] = {}
        if vrrp.get("groups"):
            vrrp_dev["group"] = {g["name"]: _group_to_device(g) for g in vrrp["groups"]}
        if vrrp.get("sync_groups"):
            vrrp_dev["sync-group"] = {
                sg["name"]: autoclean({k: v for k, v in sg.items() if k != "name"})
                for sg in vrrp["sync_groups"]
            }
        if vrrp_dev:
            want["vrrp"] = vrrp_dev

    return want


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    if not raw:
        return {}
    result = from_device({k: v for k, v in raw.items() if k not in ("virtual-server", "vrrp")})
    cast_by_spec(result, _TOP_OPTIONS)

    vs_raw = raw.get("virtual-server") or {}
    if vs_raw:
        result["virtual_servers"] = [
            _virtual_server_from_device(name, data) for name, data in sorted(vs_raw.items())
        ]

    vrrp_raw = raw.get("vrrp") or {}
    if vrrp_raw:
        vrrp_arg = from_device(
            {k: v for k, v in vrrp_raw.items() if k not in ("group", "sync-group", "snmp")},
        )
        cast_by_spec(vrrp_arg, _VRRP_OPTIONS)
        if "snmp" in vrrp_raw:
            vrrp_arg["snmp"] = "enabled"

        grp_raw = vrrp_raw.get("group") or {}
        if grp_raw:
            vrrp_arg["groups"] = [
                _group_from_device(name, data) for name, data in sorted(grp_raw.items())
            ]

        sg_raw = vrrp_raw.get("sync-group") or {}
        if sg_raw:
            vrrp_arg["sync_groups"] = [
                _sync_group_from_device(name, data) for name, data in sorted(sg_raw.items())
            ]

        if vrrp_arg:
            result["vrrp"] = vrrp_arg

    return result


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or {}

    if state == "deleted":
        return [("delete", _BASE)] if raw_have else []

    want = _want_to_device(config)
    norm_have = {k: v for k, v in raw_have.items() if k not in ("virtual-server", "vrrp")}
    if raw_have.get("virtual-server"):
        norm_have["virtual-server"] = normalize_have(raw_have, _VS_TAG_KEYS)["virtual-server"]
    if raw_have.get("vrrp"):
        norm_have["vrrp"] = normalize_have(raw_have, _VRRP_TAG_KEYS)["vrrp"]

    commands = []
    if state == "overridden":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        for section, section_want in want.items():
            section_have = norm_have.get(section, {})
            commands += dict_op(section_want, section_have, _BASE + [section], op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")

    # snmp "disabled" has no device-side value to compare against --
    # it's the absence of the presence node, which dict_op's set/purge
    # logic can't express as a "delete" on its own. Handled explicitly.
    if (config.get("vrrp") or {}).get("snmp") == "disabled":
        if "snmp" in (raw_have.get("vrrp") or {}):
            commands.append(("delete", _BASE + ["vrrp", "snmp"]))

    return commands


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after = _device_to_argspec(get_running_config(vyos))
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
