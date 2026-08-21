#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_command
short_description: Run show commands on VyOS devices using REST API
description:
  - Sends show commands to VyOS devices via the REST API C(/show) endpoint
    and returns the output.
  - Equivalent to C(vyos_command) in the CLI collection but uses the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  commands:
    description:
      - List of show commands to run on the device.
      - Each command is a list of path elements passed to the C(/show) endpoint.
      - Commands may be specified as a string (space-separated) or a list.
    type: list
    elements: raw
    required: true
  wait_for:
    description:
      - Specifies what to evaluate from the output of the command and what
        conditionals to apply. This argument will cause the task to wait for
        a particular conditional to be true before moving forward.
    type: list
    elements: str
    aliases: [waitfor]
  match:
    description:
      - The C(match) argument is used in conjunction with the C(wait_for)
        argument to specify the match policy.
    type: str
    choices: [any, all]
    default: all
  retries:
    description:
      - Specifies the number of retries a command should be run before it
        is considered failed.
    type: int
    default: 10
  interval:
    description:
      - Configures the interval in seconds to wait between retries of the
        command.
    type: int
    default: 1
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - Only C(show) commands are supported via the REST API.
  - Commands are passed as path lists to the C(/show) endpoint.
"""

EXAMPLES = r"""
- name: Run show version
  vyos.rest.vyos_command:
    commands:
      - - version
  register: result

- name: Run multiple show commands
  vyos.rest.vyos_command:
    commands:
      - - interfaces
      - - ip
        - route
      - - system
        - uptime
  register: result

- name: Run show commands as strings
  vyos.rest.vyos_command:
    commands:
      - "interfaces"
      - "ip route"
      - "version"
  register: result

- name: Wait for BGP to establish
  vyos.rest.vyos_command:
    commands:
      - - ip
        - bgp
        - summary
    wait_for:
      - result[0] contains Established
    retries: 10
    interval: 5
"""

RETURN = r"""
stdout:
  description: List of output from each command.
  returned: always
  type: list
  sample: ["VyOS 1.5.0\n...", "Interface    IP Address\n..."]
stdout_lines:
  description: List of output split into lines for each command.
  returned: always
  type: list
failed_conditions:
  description: List of conditions that failed.
  returned: failed
  type: list
"""

import time

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


def parse_command(cmd):
    """Convert a command to a path list."""
    if isinstance(cmd, list):
        return cmd
    elif isinstance(cmd, str):
        return cmd.split()
    return list(cmd)


def run_commands(vyos, commands):
    """Run show commands and return stdout list."""
    stdout = []
    for cmd in commands:
        path = parse_command(cmd)
        try:
            result = vyos.show(path)
            stdout.append(result if result else "")
        except Exception as e:
            stdout.append("ERROR: %s" % str(e))
    return stdout


def evaluate_conditions(stdout, wait_for, match):
    """Evaluate wait_for conditions against stdout."""
    failed = []
    results = []

    for condition in wait_for:
        # Parse simple conditions: "result[N] contains STRING"
        if " contains " in condition:
            parts = condition.split(" contains ", 1)
            ref = parts[0].strip()
            value = parts[1].strip()
            # Extract index from result[N]
            if ref.startswith("result[") and ref.endswith("]"):
                try:
                    idx = int(ref[7:-1])
                    matched = value in stdout[idx]
                    results.append(matched)
                    if not matched:
                        failed.append(condition)
                except (ValueError, IndexError):
                    failed.append(condition)
            else:
                failed.append(condition)
        else:
            # Unsupported condition format
            failed.append(condition)

    if match == "any":
        return not any(results), failed
    return bool(failed), failed


def main():
    module = AnsibleModule(
        argument_spec=dict(
            commands=dict(type="list", elements="raw", required=True),
            wait_for=dict(type="list", elements="str", aliases=["waitfor"]),
            match=dict(type="str", default="all", choices=["any", "all"]),
            retries=dict(type="int", default=10),
            interval=dict(type="int", default=1),
        ),
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)
    commands = module.params["commands"]
    wait_for = module.params["wait_for"] or []
    match = module.params["match"]
    retries = module.params["retries"]
    interval = module.params["interval"]

    stdout = []
    failed_conditions = []

    for attempt in range(retries):
        stdout = run_commands(vyos, commands)

        if not wait_for:
            break

        failed_check, failed_conditions = evaluate_conditions(stdout, wait_for, match)
        if not failed_check:
            break

        if attempt < retries - 1:
            time.sleep(interval)
    else:
        if failed_conditions:
            module.fail_json(
                msg="One or more conditional statements have not been satisfied",
                failed_conditions=failed_conditions,
            )

    stdout_lines = [out.splitlines() for out in stdout]

    module.exit_json(
        changed=False,
        stdout=stdout,
        stdout_lines=stdout_lines,
    )


if __name__ == "__main__":
    main()
