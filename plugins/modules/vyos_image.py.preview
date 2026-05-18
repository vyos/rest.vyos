#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_image
short_description: Manage VyOS system images via the REST API.
description:
  - Adds or removes VyOS system images using the HTTPS REST API
    (C(/image) endpoint).
  - Use I(state=present) to download and install an image from a URL.
  - Use I(state=absent) to delete an installed image by name.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  state:
    description:
      - C(present): Download and install the image from I(url).
      - C(absent): Delete the image specified by I(name).
    type: str
    choices: [present, absent]
    required: true
  url:
    description:
      - HTTP(S) URL of the VyOS C(.iso) file to install.
      - Required when I(state=present).
    type: str
  name:
    description:
      - Version name of the image to remove (e.g. C(1.4-rolling-202401010000)).
      - Required when I(state=absent).
    type: str
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
    description: >
      Request timeout in seconds. Image downloads can take several minutes;
      increase this value accordingly.
    type: int
    default: 300
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
requirements:
  - VyOS 1.3+
examples: |
  - name: Install the latest rolling release
    vyos.rest.vyos_image:
      hostname: 192.168.1.1
      api_key: MY-KEY
      state: present
      url: "https://downloads.vyos.io/rolling/current/amd64/vyos-rolling-latest.iso"
      timeout: 600

  - name: Remove an old image
    vyos.rest.vyos_image:
      hostname: 192.168.1.1
      api_key: MY-KEY
      state: absent
      name: "1.4-rolling-202312010000"
"""

RETURN = r"""
output:
  description: Text output from the image add/delete operation.
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
        state=dict(type="str", required=True, choices=["present", "absent"]),
        url=dict(type="str"),
        name=dict(type="str"),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    # Override default timeout to 300s for image downloads
    argument_spec["timeout"]["default"] = 300

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ["url"]),
            ("state", "absent", ["name"]),
        ],
        supports_check_mode=False,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]

    try:
        if state == "present":
            result = client.image_add(module.params["url"])
        else:
            result = client.image_delete(module.params["name"])
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=True, output=result.get("data", ""))


if __name__ == "__main__":
    main()
