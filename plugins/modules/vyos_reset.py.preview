#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_reset
short_description: Execute reset commands on a VyOS device via REST API.
description:
  - Sends a C(reset) operational command to a VyOS device via the HTTPS REST
    API (C(/reset) endpoint).
  - Useful for resetting BGP sessions, VPN tunnels, ARP caches, etc.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  path:
    description:
      - Reset command path tokens.
      - E.g. C(["ip", "bgp", "192.0.2.1"]) to reset a BGP peer.
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
requirements:
  - VyOS 1.3+
examples: |
  - name: Reset a BGP peer
    vyos.rest.vyos_reset:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["ip", "bgp", "192.0.2.11"]

  - name: Reset an IPsec VPN peer
    vyos.rest.vyos_reset:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["vpn", "ipsec-peer", "203.0.113.5"]

  - name: Clear ARP cache
    vyos.rest.vyos_reset:
      hostname: 192.168.1.1
      api_key: MY-KEY
      path: ["arp", "cache"]
"""

RETURN = r"""
output:
  description: Text output from the reset command (usually empty on success).
  returned: success
  type: str
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
        supports_check_mode=False,
    )

    client = VyOSRestClient(module)
    try:
        result = client.reset(module.params["path"])
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=True, output=result.get("data", ""))


if __name__ == "__main__":
    main()
