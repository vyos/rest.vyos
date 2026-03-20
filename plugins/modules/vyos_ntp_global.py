#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function


__metaclass__ = type

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

    commands = build_commands(desired, existing, state)

    result["before"] = existing

    result["commands"] = commands

    if commands:

        result["changed"] = True

        if not module.check_mode:

            vyos.apply_commands(commands)

        result["after"] = desired

    module.exit_json(**result)


if __name__ == "__main__":
    main()
