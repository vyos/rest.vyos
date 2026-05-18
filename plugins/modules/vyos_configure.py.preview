#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_configure
short_description: Manage VyOS device configuration via the REST API.
description:
  - Sends one or more C(set) or C(delete) configuration commands to a VyOS
    device via its HTTPS REST API (C(/configure) endpoint).
  - Each command in I(commands) is executed and committed atomically.
  - Supports Ansible check-mode (C(check_mode=yes)) - no changes are applied.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  commands:
    description:
      - List of VyOS configuration commands.
      - Each item may be either a plain string in VyOS CLI syntax
        (e.g. C(set interfaces ethernet eth0 description 'WAN'))
        or a dict with keys C(op), C(path), and optionally C(value).
    type: list
    elements: raw
    required: true
  save:
    description:
      - Whether to save the configuration to disk after a successful commit.
    type: bool
    default: false
  hostname:
    description:
    - IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description:
    - HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description:
    - API key configured on the device.
    type: str
    required: true
    no_log: true
  timeout:
    description:
    - Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description:
    - Validate the device's TLS certificate.
    type: bool
    default: false
notes:
  - The VyOS HTTP API must be enabled on the device before using this module.
  - Enable with C(set service https api keys id <ID> key <KEY>) and
    C(set service https api rest), then C(commit && save).
  - Tested against VyOS 1.3 and 1.4.
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.rest.vyos_retrieve
  - module: vyos.rest.vyos_show"""

RETURN = r"""
commands_sent:
  description: The list of commands dispatched to the API.
  returned: always
  type: list
  elements: dict
  sample:
    - op: set
      path: ["system", "host-name"]
      value: vyos-router
changed:
  description: Whether the device configuration was modified.
  returned: always
  type: bool
saved:
  description: Whether the configuration was saved to disk.
  returned: always
  type: bool
"""

import re


EXAMPLES = r"""
- name: Set hostname via REST API
  vyos.rest.vyos_configure:
    hostname: 192.168.1.1
    api_key: MY-KEY
    commands:
      - "set system host-name vyos-router"

- name: Configure an interface description and address
  vyos.rest.vyos_configure:
    hostname: 192.168.1.1
    api_key: MY-KEY
    commands:
      - "set interfaces ethernet eth1 description 'UPLINK'"
      - "set interfaces ethernet eth1 address 10.0.0.1/30"
    save: true

- name: Delete a static route using dict syntax
  vyos.rest.vyos_configure:
    hostname: 192.168.1.1
    api_key: MY-KEY
    commands:
      - op: delete
        path: ["protocols", "static", "route", "192.0.2.0/24"]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def _parse_cli_command(cmd_str):
    """Parse a VyOS CLI-syntax string into an API payload dict.

    Supports:
        set <path> [<value>]
        delete <path>
        comment <path> <comment>

    Args:
        cmd_str (str): e.g. "set interfaces ethernet eth0 description 'WAN'"

    Returns:
        dict: e.g. {"op": "set", "path": [...], "value": "WAN"}
    """
    cmd_str = cmd_str.strip()
    op_match = re.match(r"^(set|delete|comment)\s+(.+)$", cmd_str, re.IGNORECASE)
    if not op_match:
        raise ValueError(
            "Cannot parse command '{cmd}'. Must start with set/delete/comment.".format(
                cmd=cmd_str,
            ),
        )
    op = op_match.group(1).lower()
    rest = op_match.group(2).strip()

    # Extract a quoted or bare trailing value for 'set'
    value = None
    if op == "set":
        # Look for a trailing quoted value: '...' or "..."
        quoted = re.search(r"""(['"])(.*?)\1\s*$""", rest)
        if quoted:
            value = quoted.group(2)
            rest = rest[: quoted.start()].strip()
        else:
            # Bare final token may be the value if the second-to-last token
            # is a known leaf keyword – use a simple heuristic: if the
            # last segment has no sub-tokens we treat it as value.
            tokens = rest.split()
            # We cannot know the schema here, so we pass the full path and
            # no value; the device will decide.
            path = tokens
            return {"op": op, "path": path}

    path = rest.split()
    payload = {"op": op, "path": path}
    if value is not None:
        payload["value"] = value
    return payload


def _normalise_commands(raw_commands):
    """Normalise the mixed list of str/dict commands into API dicts."""
    result = []
    for item in raw_commands:
        if isinstance(item, dict):
            if "op" not in item or "path" not in item:
                raise ValueError(
                    "Command dict must have 'op' and 'path' keys: {item}".format(
                        item=item,
                    ),
                )
            result.append(item)
        elif isinstance(item, str):
            result.append(_parse_cli_command(item))
        else:
            raise ValueError(
                "Command must be a string or dict, got: {t}".format(t=type(item)),
            )
    return result


def main():
    argument_spec = dict(
        commands=dict(type="list", elements="raw", required=True),
        save=dict(type="bool", default=False),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        commands = _normalise_commands(module.params["commands"])
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    if module.check_mode:
        module.exit_json(
            changed=True,
            commands_sent=commands,
            saved=False,
            msg="Check mode: no changes applied.",
        )

    client = VyOSRestClient(module)
    changed = False
    saved = False

    try:
        for cmd in commands:
            op = cmd["op"].lower()
            path = cmd["path"]
            value = cmd.get("value")
            if op == "set":
                client.configure_set(path, value)
            elif op == "delete":
                client.configure_delete(path)
            elif op == "comment":
                client.configure_comment(path, value or "")
            else:
                module.fail_json(
                    msg="Unsupported op '{op}'".format(op=op),
                )
        changed = True

        if module.params["save"]:
            client.config_file_save()
            saved = True

    except VyOSRestError as exc:
        module.fail_json(msg=str(exc), commands_sent=commands)

    module.exit_json(changed=changed, commands_sent=commands, saved=saved)


if __name__ == "__main__":
    main()
