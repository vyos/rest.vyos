#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_config_file
short_description: Save or load VyOS configuration files via the REST API.
description:
  - Manages VyOS configuration persistence via the HTTPS REST API
    (C(/config-file) endpoint).
  - Use I(op=save) to write the running configuration to a file.
  - Use I(op=load) to load a configuration from a file and apply it.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  op:
    description:
      - C(save) - Save the running configuration to I(file) or the default C(/config/config.boot).
      - C(load) - Load and commit the configuration from I(file).
    type: str
    choices: [save, load]
    default: save
  file:
    description:
      - Path on the VyOS device for save/load target.
      - If omitted for C(save), the device uses its default boot config path.
    type: str
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
  - VyOS 1.3+"""

RETURN = r"""
output:
  description: Text output from the config-file operation.
  returned: success
  type: str
"""

EXAMPLES = r"""
- name: Save running config (default location)
  vyos.rest.vyos_config_file:
    hostname: 192.168.1.1
    api_key: MY-KEY
    op: save

- name: Save running config to a custom file
  vyos.rest.vyos_config_file:
    hostname: 192.168.1.1
    api_key: MY-KEY
    op: save
    file: /config/backups/config.boot.bak

- name: Load a configuration from file
  vyos.rest.vyos_config_file:
    hostname: 192.168.1.1
    api_key: MY-KEY
    op: load
    file: /config/backups/config.boot.bak
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def main():
    argument_spec = dict(
        op=dict(type="str", default="save", choices=["save", "load"]),
        file=dict(type="str"),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("op", "load", ["file"])],
        supports_check_mode=False,
    )

    client = VyOSRestClient(module)
    op = module.params["op"]
    file_path = module.params.get("file")

    try:
        if op == "save":
            result = client.config_file_save(file_path)
        else:
            result = client.config_file_load(file_path)
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=True, output=result.get("data", ""))


if __name__ == "__main__":
    main()
