#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ntp_global
short_description: Manage NTP configuration on VyOS devices using REST API
description:
  - Manages NTP server, allow-client, and listen-address configuration on
    VyOS devices via the REST API.
  - Supports idempotent operation using structured data.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - Targets VyOS 1.4+ where NTP is managed by chronyd under C(service ntp).
version_added: "1.0.0"
author:
  - Varshitha Yataluru (@YVarshitha)

options:
  config:
    description: NTP configuration.
    type: dict
    suboptions:
      allow_clients:
        description:
          - List of client networks or addresses allowed to query this NTP server.
          - Maps to C(service ntp allow-client address) on the device.
        type: list
        elements: str
      listen_addresses:
        description:
          - Local IP addresses the NTP service should listen on.
          - Maps to C(service ntp listen-address) on the device.
        type: list
        elements: str
      servers:
        description:
          - List of upstream NTP servers to synchronise from.
        type: list
        elements: dict
        suboptions:
          server:
            description: Server hostname or IP address.
            type: str
            required: true
          options:
            description:
              - Per-server options.
            type: list
            elements: str
            choices:
              - dynamic
              - noselect
              - pool
              - preempt
              - prefer
              - nts
              - ptp
              - interleave

  running_config:
    description:
      - Used only with state C(parsed).
      - Provide the output of C(show configuration commands | grep ntp).
    type: str

  state:
    description:
      - The desired state of the NTP configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
      - rendered
      - parsed
"""

EXAMPLES = r"""
- name: Gather current NTP configuration
  vyos.rest.vyos_ntp_global:
    state: gathered

- name: Merge NTP configuration
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.6.6.0/24
      listen_addresses:
        - 10.1.3.1
      servers:
        - server: 203.0.113.0
          options:
            - prefer
    state: merged

- name: Replace NTP configuration
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.6.6.0/24
      listen_addresses:
        - 10.1.3.1
      servers:
        - server: 203.0.113.0
          options:
            - prefer
    state: replaced

- name: Delete all managed NTP configuration
  vyos.rest.vyos_ntp_global:
    state: deleted
"""

RETURN = r"""
before:
  description: NTP configuration before this module ran.
  returned: when state is merged, replaced, overridden or deleted
  type: dict
after:
  description: NTP configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API commands sent to the device.
  returned: always
  type: list
gathered:
  description: Current NTP configuration as structured data.
  returned: when state is gathered
  type: dict
rendered:
  description: CLI commands generated for the provided config (offline).
  returned: when state is rendered
  type: list
parsed:
  description: Structured data parsed from running_config.
  returned: when state is parsed
  type: dict
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.utils import normalize_to_list
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


def normalize_config(config):
    result = {
        "allow_clients": sorted(config.get("allow_clients") or []),
        "listen_addresses": sorted(config.get("listen_addresses") or []),
        "servers": {},
    }
    for s in config.get("servers") or []:
        name = s["server"]
        result["servers"][name] = sorted(s.get("options") or [])
    return result


def normalize_servers(value):
    result = {}
    if isinstance(value, dict):
        for server, data in value.items():
            if isinstance(data, dict):
                result[server] = sorted(list(data.keys()))
            elif isinstance(data, list):
                result[server] = sorted(data)
            elif isinstance(data, str):
                result[server] = [data]
            else:
                result[server] = []
    elif isinstance(value, list):
        for server in value:
            result[server] = []
    elif isinstance(value, str):
        result[value] = []
    return result


def get_running_config(vyos):
    raw = vyos.get_config(["service", "ntp"])
    result = {
        "allow_clients": [],
        "listen_addresses": [],
        "servers": {},
    }
    if not raw:
        return result

    # allow-client: handle both VyOS schemas
    #   1.4:  {"allow-client": {"address": {"10.x.x.x/y": {}}}}
    #   1.5+: {"allow-client": {"10.x.x.x/y": {}}}  (no address subnode)
    allow_raw_outer = raw.get("allow-client", {})
    if "address" in allow_raw_outer:
        allow_raw = allow_raw_outer.get("address", [])
    else:
        allow_raw = allow_raw_outer
    result["allow_clients"] = sorted(normalize_to_list(allow_raw))

    result["listen_addresses"] = sorted(
        normalize_to_list(raw.get("listen-address", [])),
    )
    result["servers"] = normalize_servers(raw.get("server", {}))
    return result


def build_commands(desired, existing, state):
    cmds = []

    if state == "overridden":
        state = "replaced"

    if state == "deleted":
        if existing["servers"] or existing["allow_clients"] or existing["listen_addresses"]:
            cmds.append(("delete", ["service", "ntp"]))
        return cmds

    cmds += diff_list(
        "allow-client",
        "address",
        desired["allow_clients"],
        existing["allow_clients"],
        state,
    )
    cmds += diff_list(
        "listen-address",
        None,
        desired["listen_addresses"],
        existing["listen_addresses"],
        state,
    )
    cmds += diff_servers(desired["servers"], existing["servers"], state)
    return cmds


def diff_list(node, subnode, desired, existing, state):
    cmds = []
    desired = set(desired)
    existing = set(existing)

    if state in ("merged", "replaced"):
        for v in desired - existing:
            path = ["service", "ntp", node]
            if subnode:
                path += [subnode, v]
            else:
                path += [v]
            cmds.append(("set", path))

    if state in ("replaced", "deleted"):
        for v in existing - desired:
            path = ["service", "ntp", node]
            if subnode:
                path += [subnode, v]
            else:
                path += [v]
            cmds.append(("delete", path))

    return cmds


def diff_servers(desired, existing, state):
    cmds = []
    desired_set = set(desired.keys())
    existing_set = set(existing.keys())

    if state in ("merged", "replaced"):
        for server in desired_set:
            desired_opts = set(desired[server])
            existing_opts = set(existing.get(server, []))
            if server not in existing_set:
                cmds.append(("set", ["service", "ntp", "server", server]))
            for opt in desired_opts - existing_opts:
                cmds.append(("set", ["service", "ntp", "server", server, opt]))
            if state == "replaced":
                for opt in existing_opts - desired_opts:
                    cmds.append(("delete", ["service", "ntp", "server", server, opt]))

    if state in ("replaced", "deleted"):
        for server in existing_set - desired_set:
            cmds.append(("delete", ["service", "ntp", "server", server]))

    return cmds


def parse_running_config(text):
    result = {"allow_clients": [], "listen_addresses": [], "servers": {}}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 4:
            continue
        if parts[3] == "allow-clients":
            result["allow_clients"].append(parts[-1])
        elif parts[3] == "listen-address":
            result["listen_addresses"].append(parts[-1])
        elif parts[3] == "server":
            server = parts[4]
            if server not in result["servers"]:
                result["servers"][server] = []
            if len(parts) > 5:
                result["servers"][server].append(parts[5])
    return result


def render_commands(config):
    cmds = []
    for c in config["allow_clients"]:
        cmds.append("set service ntp allow-client address {c}".format(c=c))
    for la in config["listen_addresses"]:
        cmds.append("set service ntp listen-address {la}".format(la=la))
    for server, opts in config["servers"].items():
        if not opts:
            cmds.append("set service ntp server {s}".format(s=server))
        for opt in opts:
            cmds.append("set service ntp server {s} {o}".format(s=server, o=opt))
    return cmds


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                allow_clients=dict(type="list", elements="str"),
                listen_addresses=dict(type="list", elements="str"),
                servers=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        server=dict(type="str", required=True),
                        options=dict(
                            type="list",
                            elements="str",
                            choices=[
                                "dynamic",
                                "noselect",
                                "pool",
                                "preempt",
                                "prefer",
                                "nts",
                                "ptp",
                                "interleave",
                            ],
                        ),
                    ),
                ),
            ),
        ),
        running_config=dict(type="str"),
        state=dict(
            default="merged",
            choices=[
                "merged",
                "replaced",
                "overridden",
                "deleted",
                "gathered",
                "rendered",
                "parsed",
            ],
        ),
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    if state == "parsed":
        module.exit_json(parsed=parse_running_config(module.params["running_config"]))

    desired = normalize_config(config)

    if state == "rendered":
        module.exit_json(rendered=render_commands(desired))

    existing = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(gathered=existing)

    if state == "deleted":
        desired = {"allow_clients": [], "listen_addresses": [], "servers": {}}

    commands = build_commands(desired, existing, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=existing)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=existing,
            after=desired,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=existing, after=existing, commands=[])


if __name__ == "__main__":
    main()
