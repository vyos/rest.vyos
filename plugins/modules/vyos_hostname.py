#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_hostname
short_description: Manage the system hostname on a VyOS device via the REST API.
description:
  - Manages the C(set system host-name) configuration on a VyOS device
    using the HTTPS REST API.
  - Mirrors the behaviour of C(vyos.vyos.vyos_hostname) but uses the HTTP
    API instead of SSH/network_cli.
  - The states C(replaced), C(overridden) behave identically to C(merged)
    for this single-value resource.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description:
      - Hostname configuration.
    type: dict
    suboptions:
      hostname:
        description:
          - System hostname (max 63 characters, no underscores).
        type: str
        required: true
  running_config:
    description:
      - Used only with state C(parsed).
      - The value should be the output of
        B(show configuration commands | grep host-name) from the device.
    type: str
  state:
    description:
      - C(merged) - Ensure the hostname is set to the value in I(config).
      - C(replaced) - Identical to C(merged) for this single-value resource.
      - C(overridden) - Identical to C(merged) for this single-value resource.
      - C(deleted) - Remove the configured hostname (resets to default).
      - C(gathered) - Read the current hostname from the device and return it
        in I(gathered) without making changes.
      - C(rendered) - Return the CLI commands for the given config without
        connecting to the device.
      - C(parsed) - Parse the C(running_config) string and return structured
        data without connecting to the device.
    type: str
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
      - rendered
      - parsed
    default: merged
  hostname:
    description:
      - IP address or FQDN of the VyOS device (not needed with httpapi inventory).
    type: str
  port:
    description:
      - HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description:
      - API key configured on the device.
    type: str
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
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.vyos.vyos_hostname
"""

RETURN = r"""
before:
  description: Configuration on the device before the module ran.
  returned: always
  type: dict
after:
  description: Configuration on the device after the module ran.
  returned: when changed
  type: dict
gathered:
  description: Hostname read from the device (state=gathered only).
  returned: when state is gathered
  type: dict
rendered:
  description: CLI commands for the provided config (state=rendered only).
  returned: when state is rendered
  type: list
parsed:
  description: Structured data parsed from running_config (state=parsed only).
  returned: when state is parsed
  type: dict
commands:
  description: REST API commands dispatched.
  returned: always
  type: list
"""

EXAMPLES = r"""
- name: Set hostname
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos-core-01
    state: merged

- name: Replace hostname
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos-core-02
    state: replaced

- name: Gather current hostname
  vyos.rest.vyos_hostname:
    state: gathered
  register: result

- name: Delete hostname configuration
  vyos.rest.vyos_hostname:
    state: deleted

- name: Render commands without connecting
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos-core-01
    state: rendered

- name: Parse running config
  vyos.rest.vyos_hostname:
    running_config: "set system host-name 'vyos'"
    state: parsed
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_PATH = ["system", "host-name"]


def _get_hostname(client):
    try:
        result = client.retrieve_return_value(_PATH)
        return result.get("data", "")
    except VyOSRestError:
        return ""


def _parse_hostname(running_config):
    """Parse hostname from 'show configuration commands | grep host-name' output."""
    match = re.search(r"host-name\s+['\"]?(\S+?)['\"]?\s*$", running_config, re.M)
    return match.group(1) if match else ""


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                hostname=dict(type="str", required=True),
            ),
        ),
        running_config=dict(type="str"),
        state=dict(
            type="str",
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
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["config", "running_config"]],
        required_if=[
            ("state", "merged", ["config"]),
            ("state", "replaced", ["config"]),
            ("state", "overridden", ["config"]),
            ("state", "rendered", ["config"]),
            ("state", "parsed", ["running_config"]),
        ],
        supports_check_mode=True,
    )

    state = module.params["state"]

    # rendered — offline, no device connection needed
    if state == "rendered":
        hostname = module.params["config"]["hostname"]
        module.exit_json(
            rendered=["set system host-name '{h}'".format(h=hostname)],
            commands=[],
        )

    # parsed — offline, no device connection needed
    if state == "parsed":
        hostname = _parse_hostname(module.params["running_config"] or "")
        module.exit_json(
            parsed={"hostname": hostname},
            commands=[],
        )

    # collapsed states — replaced and overridden are identical to merged
    if state in ("replaced", "overridden"):
        state = "merged"

    client = VyOSRestClient(module)
    commands = []
    changed = False

    current = _get_hostname(client)
    before = {"hostname": current}

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state == "merged":
            desired = module.params["config"]["hostname"]
            if current != desired:
                client.configure_set(_PATH, desired)
                commands.append("set system host-name '{h}'".format(h=desired))
                changed = True

        elif state == "deleted":
            if current:
                client.configure_delete(_PATH)
                commands.append("delete system host-name")
                changed = True

    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = {"hostname": _get_hostname(client)} if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()
