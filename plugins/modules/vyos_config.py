#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_config
short_description: Manage VyOS configuration using REST API
description:
  - Manages VyOS device configuration via the REST API.
  - Accepts configuration commands in CLI C(set)/C(delete) string format
    and applies them via the REST C(/configure) endpoint.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  lines:
    description:
      - Ordered list of C(set) or C(delete) commands to apply.
      - Commands should be in standard VyOS CLI format, e.g.
        C(set system host-name router1) or C(delete protocols bgp).
    type: list
    elements: str
  src:
    description:
      - Path to a file containing C(set)/C(delete) commands, one per line.
      - Blank lines and lines starting with C(#) are ignored.
      - Mutually exclusive with C(lines).
    type: path
  match:
    description:
      - Controls how commands are matched against the running configuration.
      - C(line) checks each command against the running config and only
        applies commands that would change the configuration.
      - C(none) applies all commands without checking the running config.
    type: str
    default: line
    choices: [line, none]
  save:
    description:
      - Save the configuration to disk after applying changes.
    type: bool
    default: false
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - Unlike the CLI collection's C(vyos_config), this module does not support
    C(backup), C(confirm), or C(comment) options as these are CLI-specific.
  - Commands are parsed from CLI string format into REST API path arrays.
"""

EXAMPLES = r"""
- name: Apply configuration lines
  vyos.rest.vyos_config:
    lines:
      - set system host-name router1
      - set system domain-name example.com
      - set interfaces ethernet eth0 description "WAN"
    save: true

- name: Delete configuration
  vyos.rest.vyos_config:
    lines:
      - delete protocols bgp
    save: true

- name: Apply config from file
  vyos.rest.vyos_config:
    src: /tmp/vyos_config.txt
    match: none
    save: true

- name: Always apply without matching
  vyos.rest.vyos_config:
    lines:
      - set system host-name router1
    match: none
"""

RETURN = r"""
commands:
  description: List of commands applied to the device.
  returned: always
  type: list
saved:
  description: Whether the configuration was saved to disk.
  returned: when save is true and changes were made
  type: bool
response:
  description: Raw API response from the device.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


def parse_line(line):
    """Parse a CLI set/delete line into (op, path) tuple.

    Args:
        line (str): CLI command, e.g. "set system host-name router1"

    Returns:
        tuple: (op, path) where op is "set" or "delete" and path is a list,
               or None if the line is not a valid command.
    """
    import shlex

    line = line.strip()
    if not line or line.startswith("#"):
        return None
    try:
        tokens = shlex.split(line)
    except ValueError:
        tokens = line.split()
    if len(tokens) < 2:
        return None
    op = tokens[0].lower()
    if op not in ("set", "delete"):
        return None
    path = tokens[1:]
    return (op, path)


def load_lines(module):
    """Load lines from either lines param or src file."""
    if module.params["lines"]:
        return module.params["lines"]
    src = module.params["src"]
    if src:
        try:
            with open(src) as f:
                return f.readlines()
        except IOError as e:
            module.fail_json(msg="Unable to read src file: %s" % str(e))
    return []


def parse_commands(lines):
    """Parse a list of CLI lines into (op, path) tuples."""
    commands = []
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            commands.append(parsed)
    return commands


def filter_commands(commands, vyos):
    """Filter commands that would not change the running config.

    For set commands, check if the path already has the desired value.
    For delete commands, check if the path exists.
    """
    filtered = []
    for op, path in commands:
        if op == "set":
            if len(path) >= 2:
                # For leaf: path[-1] is the value, path[:-1] is the config path
                # e.g. ["system","host-name","vyos150"] -> get ["system","host-name"]
                # returns {"host-name": "vyos150"} -> unwrap -> "vyos150"
                parent_path = path[:-1]
                value = path[-1]
                parent = vyos.get_config(parent_path)
                if isinstance(parent, dict):
                    # unwrap single-key dict (API wraps leaf values)
                    if len(parent) == 1:
                        actual = list(parent.values())[0]
                    else:
                        actual = parent.get(parent_path[-1])
                    if actual == value:
                        continue
                    # value may be a key in the dict (tag node)
                    if value in parent:
                        continue
                elif isinstance(parent, str) and parent == value:
                    continue
            filtered.append((op, path))
        elif op == "delete":
            current = vyos.get_config(path)
            if current is not None and current != {}:
                filtered.append((op, path))
    return filtered


def main():
    module = AnsibleModule(
        argument_spec=dict(
            lines=dict(type="list", elements="str"),
            src=dict(type="path"),
            match=dict(type="str", default="line", choices=["line", "none"]),
            save=dict(type="bool", default=False),
        ),
        mutually_exclusive=[["lines", "src"]],
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)

    lines = load_lines(module)
    commands = parse_commands(lines)

    if not commands:
        module.exit_json(changed=False, commands=[])

    match = module.params["match"]
    if match == "line":
        commands = filter_commands(commands, vyos)

    if not commands:
        module.exit_json(changed=False, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, commands=commands)

    response = vyos.apply_commands(commands)

    saved = False
    if module.params["save"]:
        saved = vyos.save_config()

    module.exit_json(
        changed=True,
        commands=commands,
        saved=saved,
        response=response,
    )


if __name__ == "__main__":
    main()
