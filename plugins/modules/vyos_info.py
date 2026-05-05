#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_info
short_description: Retrieve system information from a VyOS device via the REST API.
description:
  - Queries the public C(/info) endpoint (HTTP GET) which requires no
    authentication and returns the VyOS version, hostname, and a welcome banner.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  hostname:
    description: IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description: HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description: >
      API key. Not required for this module (the /info endpoint is public)
      but kept in the spec for consistency with other modules in this collection.
    type: str
    no_log: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 10
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
requirements:
  - VyOS 1.3+
examples: |
  - name: Get VyOS system info
    vyos.rest.vyos_info:
      hostname: 192.168.1.1
    register: sys_info

  - name: Print VyOS version
    ansible.builtin.debug:
      msg: "Running VyOS {{ sys_info.version }}"
"""

RETURN = r"""
version:
  description: VyOS version string.
  returned: success
  type: str
  sample: "1.4-rolling-202401010000"
hostname:
  description: System hostname.
  returned: success
  type: str
  sample: vyos-router
banner:
  description: Welcome banner text.
  returned: success
  type: str
  sample: "Welcome to VyOS"
info:
  description: Full info dict as returned by the device.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def main():
    argument_spec = dict()
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    # api_key not strictly required for /info
    argument_spec["api_key"]["required"] = False
    argument_spec["api_key"]["default"] = ""

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    try:
        result = client.info()
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    data = result.get("data", {})
    module.exit_json(
        changed=False,
        version=data.get("version", ""),
        hostname=data.get("hostname", ""),
        banner=data.get("banner", ""),
        info=data,
    )


if __name__ == "__main__":
    main()
