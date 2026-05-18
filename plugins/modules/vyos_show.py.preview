#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_show
short_description: Execute op-mode show commands on a VyOS device via REST API.
description:
  - Sends a C(show) operational-mode command to a VyOS device via the
    HTTPS REST API (C(/show) endpoint) and returns the text output.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  path:
    description:
      - Operational-mode command tokens following C(show).
      - E.g. C(["interfaces"]) maps to C(show interfaces).
    type: list
    elements: str
    required: true
  hostname:
    description: IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description: HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description: API key configured on the device.
    type: str
    required: true
    no_log: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
notes:
  - This module never modifies device state.
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.rest.vyos_configure
  - module: vyos.rest.vyos_retrieve
examples: |
  - name: Show interfaces
    vyos.rest.vyos_show:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["interfaces"]
    register: iface_output

  - name: Show version
    vyos.rest.vyos_show:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["version"]
    register: ver_output

  - name: Show installed images
    vyos.rest.vyos_show:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["system", "image"]
    register: images
"""

RETURN = r"""
output:
  description: Raw text output from the show command.
  returned: success
  type: str
  sample: |
    Codes: S - State, L - Link, u - Up, D - Down, A - Admin Down
    Interface   IP Address   S/L  Description
    eth0        10.0.0.1/24  u/u  WAN
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def main():
    argument_spec = dict(
        path=dict(type="list", elements="str", required=True),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    try:
        result = client.show(module.params["path"])
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=False, output=result.get("data", ""))


if __name__ == "__main__":
    main()
