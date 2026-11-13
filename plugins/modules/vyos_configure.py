#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_configure
short_description: Send raw set/delete commands to a VyOS device via REST API.
description:
  - Sends one or more set/delete configuration commands to a VyOS device
    via the HTTPS REST API as a single atomic batch commit.
  - Useful for configuration not covered by dedicated resource modules,
    or for test setup and teardown tasks.
  - Commands are parsed from CLI-style strings (C(set ...) / C(delete ...)).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  commands:
    description:
      - List of CLI-style configuration commands.
      - Each command must start with C(set) or C(delete).
      - Quote a value that contains spaces, as in the CLI, for example
        C(set interfaces ethernet eth0 description "WAN link").
    type: list
    elements: str
    required: true
  save:
    description:
      - Whether to save the configuration after applying commands.
      - The task fails if the configuration cannot be saved, even though the commands were applied.
    type: bool
    default: false
seealso:
  - module: vyos.vyos.vyos_config
"""

EXAMPLES = r"""
- name: Add loopback address for testing
  vyos.rest.vyos_configure:
    commands:
      - set interfaces loopback lo address 20.1.1.1/32
    save: false

- name: Remove loopback address after testing
  vyos.rest.vyos_configure:
    commands:
      - delete interfaces loopback lo address 20.1.1.1/32
    save: false

- name: Multiple commands in one atomic commit
  vyos.rest.vyos_configure:
    commands:
      - set system host-name vyos-test
      - set system domain-name example.com
    save: true
"""

RETURN = r"""
commands:
  description: Parsed command payloads sent to the device.
  returned: always
  type: list
response:
  description: Raw API response.
  returned: when commands are applied
  type: dict
"""

import shlex

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


def _parse_command(line):
    """Parse a CLI-style command string into (op, path) tuple.

    Examples:
        "set interfaces loopback lo address 20.1.1.1/32"
            -> ("set", ["interfaces", "loopback", "lo", "address", "20.1.1.1/32"])
        'set interfaces ethernet eth0 description "WAN link"'
            -> ("set", ["interfaces", "ethernet", "eth0", "description", "WAN link"])
        "delete service snmp"
            -> ("delete", ["service", "snmp"])

    Returns None when the line is not a set or delete command with a path.
    Raises ValueError when a quote is not closed.
    """
    tokens = shlex.split(line)
    if len(tokens) < 2 or tokens[0] not in ("set", "delete"):
        return None
    return (tokens[0], tokens[1:])


def main():
    module = AnsibleModule(
        argument_spec=dict(
            commands=dict(type="list", elements="str", required=True),
            save=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)
    commands_raw = module.params["commands"]
    do_save = module.params["save"]

    commands = []
    for line in commands_raw:
        parsed = None
        try:
            parsed = _parse_command(line)
        except ValueError as exc:
            module.fail_json(msg="Invalid command '{c}': {e}".format(c=line, e=exc))

        if parsed is None:
            module.fail_json(
                msg="Invalid command '{c}' — must start with 'set' or 'delete'".format(c=line),
            )
        commands.append(parsed)

    if not commands:
        module.exit_json(changed=False, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, commands=commands)

    response = vyos.apply_commands(commands)

    if do_save and not vyos.save_config():
        module.fail_json(
            msg="The commands were applied but saving the configuration failed",
            changed=True,
            commands=commands,
            response=response,
        )

    module.exit_json(
        changed=True,
        commands=commands,
        response=response,
    )


if __name__ == "__main__":
    main()
