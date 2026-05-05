#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_snmp_server
short_description: Manage SNMP server configuration on VyOS devices using REST API
description:
  - Manages SNMP server configuration on VyOS devices via the REST API.
  - Supports communities, listen addresses, contact/location/description,
    trap target, and SNMPv3 (engine ID, groups, users, views).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author: your_name (@yourhandle)
options:
  config:
    description: SNMP server configuration.
    type: dict
    suboptions:
      communities:
        description: SNMP community configuration.
        type: list
        elements: dict
        suboptions:
          name:
            description: Community name.
            type: str
            required: true
          clients:
            description: IP addresses of SNMP clients allowed to contact the system.
            type: list
            elements: str
          networks:
            description: Subnets of SNMP clients allowed to contact the system.
            type: list
            elements: str
          authorization_type:
            description: Authorization type.
            type: str
            choices: ['ro', 'rw']
      contact:
        description: Contact person for the system.
        type: str
      description:
        description: System description.
        type: str
      location:
        description: System location.
        type: str
      smux_peer:
        description: Register a subtree for SMUX-based processing.
        type: str
      trap_source:
        description: SNMP trap source address.
        type: str
      listen_addresses:
        description: IP addresses to listen for incoming SNMP requests.
        type: list
        elements: dict
        suboptions:
          address:
            description: IP address.
            type: str
            required: true
          port:
            description: UDP port (default 161).
            type: int
      trap_target:
        description: SNMP trap target.
        type: dict
        suboptions:
          address:
            type: str
          community:
            type: str
          port:
            type: int
      snmp_v3:
        description: SNMPv3 configuration.
        type: dict
        suboptions:
          engine_id:
            description: EngineID as a hex string.
            type: str
          groups:
            type: list
            elements: dict
            suboptions:
              group:
                type: str
                required: true
              mode:
                type: str
                choices: ['ro', 'rw']
              seclevel:
                type: str
                choices: ['auth', 'priv']
              view:
                type: str
          users:
            type: list
            elements: dict
            suboptions:
              user:
                type: str
                required: true
              authentication:
                type: dict
                suboptions:
                  type:
                    type: str
                    choices: ['md5', 'sha']
                  encrypted_key:
                    description: Encrypted key (stored as encrypted-password on device).
                    type: str
                  plaintext_key:
                    description: Plaintext key (device encrypts it; recommended for 1.5+).
                    type: str
                    no_log: true
              privacy:
                type: dict
                suboptions:
                  type:
                    type: str
                    choices: ['des', 'aes']
                  encrypted_key:
                    type: str
                  plaintext_key:
                    type: str
                    no_log: true
              group:
                type: str
              mode:
                type: str
                choices: ['ro', 'rw']
              tsm_key:
                type: str
          trap_targets:
            type: list
            elements: dict
            suboptions:
              address:
                type: str
              port:
                type: int
              protocol:
                type: str
                choices: ['tcp', 'udp']
              type:
                type: str
                choices: ['inform', 'trap']
              authentication:
                type: dict
                suboptions:
                  type:
                    type: str
                  encrypted_key:
                    type: str
                  plaintext_key:
                    type: str
                    no_log: true
              privacy:
                type: dict
                suboptions:
                  type:
                    type: str
                  encrypted_key:
                    type: str
                  plaintext_key:
                    type: str
                    no_log: true
          views:
            type: list
            elements: dict
            suboptions:
              view:
                type: str
                required: true
              oid:
                type: str
              exclude:
                type: str
              mask:
                type: str
  state:
    description:
      - Desired state of SNMP configuration.
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
- name: Merge SNMP configuration
  vyos.rest.vyos_snmp_server:
    config:
      communities:
        - name: switches
          authorization_type: rw
        - name: bridges
          clients:
            - 1.1.1.1
            - 12.1.1.10
      contact: admin2@ex.com
      listen_addresses:
        - address: 20.1.1.1
        - address: 100.1.2.1
          port: 33
      snmp_v3:
        users:
          - user: admin_user
            authentication:
              plaintext_key: abc1234567
              type: sha
            privacy:
              plaintext_key: abc1234567
              type: aes
    state: merged

- name: Delete all SNMP configuration
  vyos.rest.vyos_snmp_server:
    state: deleted

- name: Gather current SNMP configuration
  vyos.rest.vyos_snmp_server:
    state: gathered
"""

RETURN = r"""
before:
  description: SNMP configuration before this module ran.
  returned: when state is merged, replaced, overridden or deleted
  type: dict
after:
  description: SNMP configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command dicts sent to the device.
  returned: always
  type: list
gathered:
  description: Current SNMP configuration as structured data.
  returned: when state is gathered
  type: dict
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


SNMP_BASE = ["service", "snmp"]

SCALAR_FIELDS = {
    "contact": "contact",
    "description": "description",
    "location": "location",
    "smux_peer": "smux-peer",
    "trap_source": "trap-source",
}


def to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return list(value.keys())
    return [str(value)]


def _cmd(op, path):
    return {"op": op, "path": path}


def _set(path):
    return _cmd("set", path)


def _delete(path):
    return _cmd("delete", path)


def _parse_communities(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for name, data in sorted(raw.items()):
        entry = {"name": name}
        if not isinstance(data, dict):
            result.append(entry)
            continue
        if "authorization" in data:
            entry["authorization_type"] = data["authorization"]
        if "client" in data:
            entry["clients"] = sorted(to_list(data["client"]))
        if "network" in data:
            entry["networks"] = sorted(to_list(data["network"]))
        result.append(entry)
    return result


def _parse_listen_addresses(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for addr, data in sorted(raw.items()):
        entry = {"address": addr}
        if isinstance(data, dict) and "port" in data:
            entry["port"] = int(data["port"])
        result.append(entry)
    return result


def _parse_trap_target(raw):
    if not raw:
        return None
    if isinstance(raw, str):
        return {"address": raw}
    entry = {}
    if "address" in raw:
        entry["address"] = raw["address"]
    if "community" in raw:
        entry["community"] = raw["community"]
    if "port" in raw:
        entry["port"] = int(raw["port"])
    return entry if entry else None


def _parse_v3_auth_privacy(raw, key):
    block = raw.get(key) if isinstance(raw, dict) else None
    if not block:
        return None
    result = {}
    if "type" in block:
        result["type"] = block["type"]
    if "encrypted-password" in block:
        result["encrypted_key"] = block["encrypted-password"]
    if "plaintext-key" in block:
        result["plaintext_key"] = block["plaintext-key"]
    return result if result else None


def _parse_v3_users(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for username, data in sorted(raw.items()):
        entry = {"user": username}
        auth = _parse_v3_auth_privacy(data, "auth")
        if auth:
            entry["authentication"] = auth
        priv = _parse_v3_auth_privacy(data, "privacy")
        if priv:
            entry["privacy"] = priv
        if isinstance(data, dict):
            if "group" in data:
                entry["group"] = data["group"]
            if "mode" in data:
                entry["mode"] = data["mode"]
            if "tsm-key" in data:
                entry["tsm_key"] = data["tsm-key"]
        result.append(entry)
    return result


def _parse_v3_groups(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for name, data in sorted(raw.items()):
        entry = {"group": name}
        if isinstance(data, dict):
            for key in ("mode", "seclevel", "view"):
                if key in data:
                    entry[key] = data[key]
        result.append(entry)
    return result


def _parse_v3_views(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for name, data in sorted(raw.items()):
        entry = {"view": name}
        if isinstance(data, dict) and "oid" in data:
            oid_data = data["oid"]
            if isinstance(oid_data, dict) and oid_data:
                entry["oid"] = str(list(oid_data.keys())[0])
            elif isinstance(oid_data, str):
                entry["oid"] = oid_data
        if isinstance(data, dict):
            if "exclude" in data:
                entry["exclude"] = data["exclude"]
            if "mask" in data:
                entry["mask"] = data["mask"]
        result.append(entry)
    return result


def _parse_v3_trap_targets(raw):
    if not raw or not isinstance(raw, dict):
        return []
    result = []
    for addr, data in sorted(raw.items()):
        entry = {"address": addr}
        if isinstance(data, dict):
            if "port" in data:
                entry["port"] = int(data["port"])
            if "protocol" in data:
                entry["protocol"] = data["protocol"]
            if "type" in data:
                entry["type"] = data["type"]
            auth = _parse_v3_auth_privacy(data, "auth")
            if auth:
                entry["authentication"] = auth
            priv = _parse_v3_auth_privacy(data, "privacy")
            if priv:
                entry["privacy"] = priv
        result.append(entry)
    return result


def parse_snmp_config(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    for argspec_key, api_key in SCALAR_FIELDS.items():
        if api_key in raw:
            result[argspec_key] = raw[api_key]
    communities = _parse_communities(raw.get("community"))
    if communities:
        result["communities"] = communities
    listen = _parse_listen_addresses(raw.get("listen-address"))
    if listen:
        result["listen_addresses"] = listen
    trap = _parse_trap_target(raw.get("trap-target"))
    if trap:
        result["trap_target"] = trap
    v3_raw = raw.get("v3")
    if v3_raw and isinstance(v3_raw, dict):
        v3 = {}
        if "engineid" in v3_raw:
            v3["engine_id"] = v3_raw["engineid"]
        groups = _parse_v3_groups(v3_raw.get("group"))
        if groups:
            v3["groups"] = groups
        users = _parse_v3_users(v3_raw.get("user"))
        if users:
            v3["users"] = users
        views = _parse_v3_views(v3_raw.get("view"))
        if views:
            v3["views"] = views
        trap_targets = _parse_v3_trap_targets(v3_raw.get("trap-target"))
        if trap_targets:
            v3["trap_targets"] = trap_targets
        if v3:
            result["snmp_v3"] = v3
    return result


def get_running_config(vyos):
    try:
        raw = vyos.get_config(SNMP_BASE)
    except Exception as e:
        if "Configuration under specified path is empty" in str(e):
            return {}
        raise
    return parse_snmp_config(raw)


def _build_scalar_commands(want, have, state):
    cmds = []
    for argspec_key, api_key in SCALAR_FIELDS.items():
        want_val = want.get(argspec_key)
        have_val = have.get(argspec_key)
        path = SNMP_BASE + [api_key]
        if state in ("merged", "replaced", "overridden"):
            if want_val and want_val != have_val:
                cmds.append(_set(path + [want_val]))
        if state in ("replaced", "overridden"):
            if have_val and want_val != have_val:
                cmds.append(_delete(path))
    return cmds


def _build_community_commands(want_list, have_list, state):
    cmds = []
    want_map = {c["name"]: c for c in (want_list or [])}
    have_map = {c["name"]: c for c in (have_list or [])}
    if state in ("replaced", "overridden"):
        for name in have_map:
            if name not in want_map:
                cmds.append(_delete(SNMP_BASE + ["community", name]))
    for name, want_comm in want_map.items():
        have_comm = have_map.get(name, {})
        base = SNMP_BASE + ["community", name]
        want_auth = want_comm.get("authorization_type")
        have_auth = have_comm.get("authorization_type")
        if want_auth and want_auth != have_auth:
            cmds.append(_set(base + ["authorization", want_auth]))
        if state in ("replaced", "overridden") and have_auth and want_auth != have_auth:
            cmds.append(_delete(base + ["authorization"]))
        want_clients = set(want_comm.get("clients") or [])
        have_clients = set(have_comm.get("clients") or [])
        for c in want_clients - have_clients:
            cmds.append(_set(base + ["client", c]))
        if state in ("replaced", "overridden"):
            for c in have_clients - want_clients:
                cmds.append(_delete(base + ["client", c]))
        want_nets = set(want_comm.get("networks") or [])
        have_nets = set(have_comm.get("networks") or [])
        for n in want_nets - have_nets:
            cmds.append(_set(base + ["network", n]))
        if state in ("replaced", "overridden"):
            for n in have_nets - want_nets:
                cmds.append(_delete(base + ["network", n]))
    return cmds


def _build_listen_address_commands(want_list, have_list, state):
    cmds = []
    want_map = {e["address"]: e for e in (want_list or [])}
    have_map = {e["address"]: e for e in (have_list or [])}
    base = SNMP_BASE + ["listen-address"]
    if state in ("replaced", "overridden"):
        for addr in have_map:
            if addr not in want_map:
                cmds.append(_delete(base + [addr]))
    for addr, want_entry in want_map.items():
        have_entry = have_map.get(addr, {})
        want_port = want_entry.get("port")
        have_port = have_entry.get("port")
        if addr not in have_map:
            if want_port:
                cmds.append(_set(base + [addr, "port", str(want_port)]))
            else:
                cmds.append(_set(base + [addr]))
        elif want_port != have_port:
            cmds.append(_delete(base + [addr]))
            if want_port:
                cmds.append(_set(base + [addr, "port", str(want_port)]))
            else:
                cmds.append(_set(base + [addr]))
    return cmds


def _build_trap_target_commands(want, have, state):
    cmds = []
    base = SNMP_BASE + ["trap-target"]
    if state in ("merged", "replaced", "overridden"):
        if want:
            want_addr = want.get("address")
            have_addr = have.get("address") if have else None
            if want_addr and want_addr != have_addr:
                cmds.append(_set(base + [want_addr]))
            if want.get("community"):
                cmds.append(_set(base + [want_addr, "community", want["community"]]))
            if want.get("port"):
                cmds.append(_set(base + [want_addr, "port", str(want["port"])]))
    if state in ("replaced", "overridden"):
        if have and (not want or have.get("address") != (want or {}).get("address")):
            cmds.append(_delete(base))
    return cmds


def _build_v3_auth_privacy_commands(base, want_block, have_block, api_key):
    cmds = []
    if not want_block:
        return cmds
    block_base = base + [api_key]
    have_block = have_block or {}
    if want_block.get("type") and want_block["type"] != have_block.get("type"):
        cmds.append(_set(block_base + ["type", want_block["type"]]))
    if want_block.get("encrypted_key") and want_block["encrypted_key"] != have_block.get(
        "encrypted_key",
    ):
        cmds.append(_set(block_base + ["encrypted-password", want_block["encrypted_key"]]))
    if want_block.get("plaintext_key"):
        cmds.append(_set(block_base + ["plaintext-key", want_block["plaintext_key"]]))
    return cmds


def _build_v3_user_commands(want_list, have_list, state):
    cmds = []
    want_map = {u["user"]: u for u in (want_list or [])}
    have_map = {u["user"]: u for u in (have_list or [])}
    base = SNMP_BASE + ["v3", "user"]
    if state in ("replaced", "overridden"):
        for username in have_map:
            if username not in want_map:
                cmds.append(_delete(base + [username]))
    for username, want_user in want_map.items():
        have_user = have_map.get(username, {})
        user_base = base + [username]
        cmds += _build_v3_auth_privacy_commands(
            user_base,
            want_user.get("authentication"),
            have_user.get("authentication"),
            "auth",
        )
        cmds += _build_v3_auth_privacy_commands(
            user_base,
            want_user.get("privacy"),
            have_user.get("privacy"),
            "privacy",
        )
        if want_user.get("group") and want_user["group"] != have_user.get("group"):
            cmds.append(_set(user_base + ["group", want_user["group"]]))
        if want_user.get("mode") and want_user["mode"] != have_user.get("mode"):
            cmds.append(_set(user_base + ["mode", want_user["mode"]]))
        if want_user.get("tsm_key") and want_user["tsm_key"] != have_user.get("tsm_key"):
            cmds.append(_set(user_base + ["tsm-key", want_user["tsm_key"]]))
    return cmds


def _build_v3_group_commands(want_list, have_list, state):
    cmds = []
    want_map = {g["group"]: g for g in (want_list or [])}
    have_map = {g["group"]: g for g in (have_list or [])}
    base = SNMP_BASE + ["v3", "group"]
    if state in ("replaced", "overridden"):
        for name in have_map:
            if name not in want_map:
                cmds.append(_delete(base + [name]))
    for name, want_group in want_map.items():
        have_group = have_map.get(name, {})
        group_base = base + [name]
        for key, api_key in [("mode", "mode"), ("seclevel", "seclevel"), ("view", "view")]:
            want_val = want_group.get(key)
            have_val = have_group.get(key)
            if want_val and want_val != have_val:
                cmds.append(_set(group_base + [api_key, want_val]))
            if state in ("replaced", "overridden") and have_val and want_val != have_val:
                cmds.append(_delete(group_base + [api_key]))
    return cmds


def _build_v3_view_commands(want_list, have_list, state):
    cmds = []
    want_map = {v["view"]: v for v in (want_list or [])}
    have_map = {v["view"]: v for v in (have_list or [])}
    base = SNMP_BASE + ["v3", "view"]
    if state in ("replaced", "overridden"):
        for name in have_map:
            if name not in want_map:
                cmds.append(_delete(base + [name]))
    for name, want_view in want_map.items():
        have_view = have_map.get(name, {})
        view_base = base + [name]
        want_oid = str(want_view["oid"]) if want_view.get("oid") else None
        have_oid = str(have_view.get("oid")) if have_view.get("oid") else None
        if want_oid and want_oid != have_oid:
            cmds.append(_set(view_base + ["oid", want_oid]))
        if state in ("replaced", "overridden") and have_oid and want_oid != have_oid:
            cmds.append(_delete(view_base + ["oid", have_oid]))
        for key in ("exclude", "mask"):
            want_val = want_view.get(key)
            have_val = have_view.get(key)
            if want_val and want_val != have_val:
                cmds.append(_set(view_base + [key, want_val]))
    return cmds


def _build_v3_commands(want_v3, have_v3, state):
    cmds = []
    want_v3 = want_v3 or {}
    have_v3 = have_v3 or {}
    want_eid = want_v3.get("engine_id")
    have_eid = have_v3.get("engine_id")
    if want_eid and want_eid != have_eid:
        cmds.append(_set(SNMP_BASE + ["v3", "engineid", want_eid]))
    if state in ("replaced", "overridden") and have_eid and want_eid != have_eid:
        cmds.append(_delete(SNMP_BASE + ["v3", "engineid"]))
    cmds += _build_v3_group_commands(want_v3.get("groups"), have_v3.get("groups"), state)
    cmds += _build_v3_user_commands(want_v3.get("users"), have_v3.get("users"), state)
    cmds += _build_v3_view_commands(want_v3.get("views"), have_v3.get("views"), state)
    return cmds


def build_commands(want, have, state):
    if state == "deleted":
        if have:
            return [_delete(SNMP_BASE)]
        return []
    cmds = []
    cmds += _build_scalar_commands(want, have, state)
    cmds += _build_community_commands(want.get("communities"), have.get("communities"), state)
    cmds += _build_listen_address_commands(
        want.get("listen_addresses"),
        have.get("listen_addresses"),
        state,
    )
    cmds += _build_trap_target_commands(want.get("trap_target"), have.get("trap_target"), state)
    cmds += _build_v3_commands(want.get("snmp_v3"), have.get("snmp_v3"), state)
    return cmds


def _auth_privacy_spec():
    return dict(
        type=dict(type="str"),
        encrypted_key=dict(type="str", no_log=False),
        plaintext_key=dict(type="str", no_log=True),
    )


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            communities=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    clients=dict(type="list", elements="str"),
                    networks=dict(type="list", elements="str"),
                    authorization_type=dict(type="str", choices=["ro", "rw"]),
                ),
            ),
            contact=dict(type="str"),
            description=dict(type="str"),
            location=dict(type="str"),
            smux_peer=dict(type="str"),
            trap_source=dict(type="str"),
            listen_addresses=dict(
                type="list",
                elements="dict",
                options=dict(
                    address=dict(type="str", required=True),
                    port=dict(type="int"),
                ),
            ),
            trap_target=dict(
                type="dict",
                options=dict(
                    address=dict(type="str"),
                    community=dict(type="str"),
                    port=dict(type="int"),
                ),
            ),
            snmp_v3=dict(
                type="dict",
                options=dict(
                    engine_id=dict(type="str"),
                    groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            group=dict(type="str", required=True),
                            mode=dict(type="str", choices=["ro", "rw"]),
                            seclevel=dict(type="str", choices=["auth", "priv"]),
                            view=dict(type="str"),
                        ),
                    ),
                    users=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            user=dict(type="str", required=True),
                            authentication=dict(type="dict", options=_auth_privacy_spec()),
                            privacy=dict(type="dict", options=_auth_privacy_spec()),
                            group=dict(type="str"),
                            mode=dict(type="str", choices=["ro", "rw"]),
                            tsm_key=dict(type="str"),
                        ),
                    ),
                    trap_targets=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str"),
                            port=dict(type="int"),
                            protocol=dict(type="str", choices=["tcp", "udp"]),
                            type=dict(type="str", choices=["inform", "trap"]),
                            authentication=dict(type="dict", options=_auth_privacy_spec()),
                            privacy=dict(type="dict", options=_auth_privacy_spec()),
                        ),
                    ),
                    views=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            view=dict(type="str", required=True),
                            oid=dict(type="str"),
                            exclude=dict(type="str"),
                            mask=dict(type="str"),
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


def main():
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)
    state = module.params["state"]
    config = module.params.get("config") or {}

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    want = config
    commands = build_commands(want, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=want,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
