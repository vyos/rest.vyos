#!/usr/bin/python
# -*- coding: utf-8 -*-

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
              - C(pool) replaces C(dynamic) in VyOS 1.3+.
              - C(nts) was added in VyOS 1.4.
              - C(ptp) and C(interleave) were added in VyOS 1.5.
              - C(preempt) is only available in VyOS 1.3 and earlier.
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
      - Provide the output of C(show configuration commands | grep ntp)
        as a string. The module parses it into structured data and returns
        the result in the C(parsed) key.
      - No device connection is required for this state.
    type: str

  state:
    description:
      - The desired state of the NTP configuration.
      - C(merged) adds or updates the provided configuration without removing
        existing entries not mentioned in the task.
      - C(replaced) fully replaces the running NTP configuration with the
        provided config, removing entries not present in the task.
      - C(overridden) deletes all existing allow-client, listen-address, and
        server entries then applies the desired config from scratch.
      - C(deleted) removes all NTP allow-client, listen-address, and server
        entries managed by this module.
      - C(gathered) retrieves and returns the current NTP configuration as
        structured data. No changes are made to the device.
      - C(rendered) returns the CLI commands that would be generated for the
        provided config without connecting to the device.
      - C(parsed) parses the CLI output provided via C(running_config) into
        structured data without connecting to the device.
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

notes:
  - Tested against VyOS 1.4 (sagitta) and 1.5.
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - C(replaced) and C(overridden) differ. C(replaced) performs a surgical diff
    removing only entries not in the task. C(overridden) deletes entire subtrees
    first then re-applies, which is safer when option ordering matters.
  - The C(rendered) and C(parsed) states do not require a device connection.
"""

EXAMPLES = r"""
# Before state:
# -------------
# set service ntp server time1.vyos.net
# set service ntp server time2.vyos.net
# set service ntp server time3.vyos.net

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

# After state:
# ------------
# set service ntp allow-client address '10.6.6.0/24'
# set service ntp listen-address '10.1.3.1'
# set service ntp server 203.0.113.0 prefer
# set service ntp server time1.vyos.net
# set service ntp server time2.vyos.net
# set service ntp server time3.vyos.net

# ------------------------------------------------------------------------

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

# ------------------------------------------------------------------------

- name: Override NTP configuration
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.3.3.0/24
      listen_addresses:
        - 10.7.8.1
      servers:
        - server: server1
          options:
            - dynamic
            - prefer
        - server: server2
          options:
            - noselect
            - preempt
        - server: serv
    state: overridden

# ------------------------------------------------------------------------

- name: Delete all managed NTP configuration
  vyos.rest.vyos_ntp_global:
    state: deleted

# ------------------------------------------------------------------------

- name: Gather current NTP configuration
  vyos.rest.vyos_ntp_global:
    state: gathered

# ------------------------------------------------------------------------

- name: Render NTP configuration commands offline
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.7.7.0/24
        - 10.8.8.0/24
      listen_addresses:
        - 10.7.9.1
      servers:
        - server: server7
        - server: server45
          options:
            - noselect
            - prefer
            - pool
    state: rendered

# ------------------------------------------------------------------------

- name: Parse NTP configuration from CLI output
  vyos.rest.vyos_ntp_global:
    running_config: "{{ lookup('file', './ntp_config.cfg') }}"
    state: parsed
"""

RETURN = r"""
before:
  description: NTP configuration on the device before this module ran.
  returned: when I(state) is C(merged), C(replaced), C(overridden) or C(deleted)
  type: dict

after:
  description: NTP configuration after this module ran.
  returned: when changed
  type: dict

commands:
  description: List of API command tuples or dicts sent to the device.
  returned: always
  type: list

gathered:
  description: Current NTP configuration retrieved from the device as structured data.
  returned: when I(state) is C(gathered)
  type: dict

rendered:
  description: CLI commands generated for the provided configuration (offline, no device needed).
  returned: when I(state) is C(rendered)
  type: list

parsed:
  description: Structured data parsed from the C(running_config) CLI output.
  returned: when I(state) is C(parsed)
  type: dict

saved:
  description: Result of save_config after applying changes.
  returned: when changes are applied
  type: bool

response:
  description: Raw API response from the VyOS REST API.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.utils import normalize_to_list
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def normalize_config(config):

    result = {
        "allow_clients": sorted(config.get("allow_clients", [])),
        "listen_addresses": sorted(config.get("listen_addresses", [])),
        "servers": {},
    }

    for s in config.get("servers", []):

        name = s["server"]

        result["servers"][name] = sorted(s.get("options", []))

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

    allow_raw = raw.get("allow-client", {}).get("address", [])
    result["allow_clients"] = sorted(normalize_to_list(allow_raw))

    listen_raw = raw.get("listen-address", [])
    result["listen_addresses"] = sorted(normalize_to_list(listen_raw))

    servers_raw = raw.get("server", {})
    result["servers"] = normalize_servers(servers_raw)

    return result


def build_commands(desired, existing, state):

    cmds = []

    # overridden = delete all then merged
    if state == "overridden":

        if existing["allow_clients"]:
            cmds.append(("delete", ["service", "ntp", "allow-clients"]))

        if existing["listen_addresses"]:
            cmds.append(("delete", ["service", "ntp", "listen-address"]))

        if existing["servers"]:
            cmds.append(("delete", ["service", "ntp", "server"]))

        state = "merged"

    cmds += diff_list(
        "allow-client",
        "address",  # singular
        desired["allow_clients"],
        existing["allow_clients"],
        state,
    )

    # listen_addresses
    cmds += diff_list(
        "listen-address",
        None,
        desired["listen_addresses"],
        existing["listen_addresses"],
        state,
    )

    # servers
    cmds += diff_servers(
        desired["servers"],
        existing["servers"],
        state,
    )

    return cmds


def diff_list(node, subnode, desired, existing, state):

    cmds = []

    desired = set(desired)
    existing = set(existing)

    if state in ["merged", "replaced"]:

        for v in desired - existing:

            path = ["service", "ntp", node]

            if subnode:
                path += [subnode, v]
            else:
                path += [v]

            cmds.append(("set", path))

    if state in ["replaced", "deleted"]:

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

    # add/update
    if state in ["merged", "replaced"]:

        for server in desired_set:

            desired_opts = set(desired[server])
            existing_opts = set(existing.get(server, []))

            # add server
            if server not in existing_set:
                cmds.append(("set", ["service", "ntp", "server", server]))

            # add options
            for opt in desired_opts - existing_opts:

                cmds.append(
                    ("set", ["service", "ntp", "server", server, opt]),
                )

            # remove options (replaced only)
            if state == "replaced":

                for opt in existing_opts - desired_opts:

                    cmds.append(
                        ("delete", ["service", "ntp", "server", server, opt]),
                    )

    # delete
    if state in ["replaced", "deleted"]:

        for server in existing_set - desired_set:

            cmds.append(("delete", ["service", "ntp", "server", server]))

    return cmds


def parse_running_config(text):

    result = {
        "allow_clients": [],
        "listen_addresses": [],
        "servers": {},
    }

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
        cmds.append(f"set service ntp allow-clients address {c}")

    for la in config["listen_addresses"]:
        cmds.append(f"set service ntp listen-address {la}")

    for server, opts in config["servers"].items():

        if not opts:
            cmds.append(f"set service ntp server {server}")

        for opt in opts:
            cmds.append(f"set service ntp server {server} {opt}")

    return cmds


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


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
                        options=dict(type="list", elements="str"),
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

    result = {
        "changed": False,
    }

    # --------------------------------------------------------
    # parsed
    # --------------------------------------------------------

    if state == "parsed":

        parsed = parse_running_config(module.params["running_config"])

        module.exit_json(parsed=parsed)

    # --------------------------------------------------------
    # rendered
    # --------------------------------------------------------

    desired = normalize_config(config)

    if state == "rendered":

        module.exit_json(rendered=render_commands(desired))

    # --------------------------------------------------------
    # gathered
    # --------------------------------------------------------

    existing = get_running_config(vyos)

    if state == "gathered":

        module.exit_json(gathered=existing)

    # --------------------------------------------------------
    # deleted
    # --------------------------------------------------------

    if state == "deleted":

        desired = {
            "allow_clients": [],
            "listen_addresses": [],
            "servers": {},
        }

    # --------------------------------------------------------
    # diff engine
    # --------------------------------------------------------

    # commands = build_commands(desired, existing, state)

    # result["before"] = existing

    # result["commands"] = commands

    # if commands:

    #     result["changed"] = True

    #     if not module.check_mode:

    #         vyos.apply_commands(commands)

    #     result["after"] = desired

    # module.exit_json(**result)

    commands = build_commands(desired, existing, state)

    if module.check_mode:
        module.exit_json(
            changed=bool(commands),
            commands=commands,
            before=existing,
        )

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

    module.exit_json(
        changed=False,
        before=existing,
        after=existing,
        commands=[],
    )


if __name__ == "__main__":
    main()
