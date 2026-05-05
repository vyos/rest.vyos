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
  state:
    description:
      - C(merged) - Ensure the hostname is set to the value in I(config).
      - C(deleted) - Remove the configured hostname (resets to default).
      - C(gathered) - Read the current hostname from the device and return it
        in I(gathered) without making changes.
    type: str
    choices: [merged, deleted, gathered]
    default: merged
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

- name: Gather current hostname
  vyos.rest.vyos_hostname:
    state: gathered
  register: result

- name: Delete hostname configuration
  vyos.rest.vyos_hostname:
    state: deleted
"""

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


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                hostname=dict(type="str", required=True),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "merged", ["config"])],
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]
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
                commands.append(
                    "set system host-name '{h}'".format(h=desired),
                )
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
