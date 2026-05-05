#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ping
short_description: Test reachability using ping via VyOS REST API.
description:
  - Sends an ICMP ping via the VyOS HTTPS REST API (/show endpoint) and
    checks reachability. Mirrors C(vyos.vyos.vyos_ping).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  dest:
    description: Destination IP address or hostname.
    type: str
    required: true
  count:
    description: Number of packets to send.
    type: int
    default: 5
  source:
    description: Source interface or IP address.
    type: str
  ttl:
    description: Time-to-live value.
    type: int
  size:
    description: Packet size in bytes.
    type: int
  interval:
    description: Interval between pings in seconds.
    type: int
  state:
    description: C(present) = expect success; C(absent) = expect failure.
    type: str
    choices: [present, absent]
    default: present
  hostname:
    type: str
    required: true
  port:
    type: int
    default: 443
  api_key:
    type: str
    required: true
    no_log: true
  timeout:
    type: int
    default: 30
  verify_ssl:
    type: bool
    default: false
"""

RETURN = r"""
commands:
  description: Ping command tokens sent to the API.
  returned: always
  type: list
packet_loss:
  description: Packet loss percentage string.
  returned: always
  type: str
packets_rx:
  description: Packets received.
  returned: always
  type: int
packets_tx:
  description: Packets transmitted.
  returned: always
  type: int
rtt:
  description: RTT statistics dict (min/avg/max/mdev).
  returned: when available
  type: dict
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def _build_ping_path(params):
    path = ["ping", params["dest"]]
    if params.get("count"):
        path += ["count", str(params["count"])]
    if params.get("source"):
        path += ["interface", params["source"]]
    if params.get("ttl"):
        path += ["ttl", str(params["ttl"])]
    if params.get("size"):
        path += ["size", str(params["size"])]
    return path


def _parse_ping_output(output):
    stats = {"packet_loss": "100%", "packets_rx": 0, "packets_tx": 0}
    tx_match = re.search(r"(\d+) packets transmitted", output)
    rx_match = re.search(r"(\d+) received", output)
    loss_match = re.search(r"(\d+(?:\.\d+)?%)\s+packet loss", output)
    if tx_match:
        stats["packets_tx"] = int(tx_match.group(1))
    if rx_match:
        stats["packets_rx"] = int(rx_match.group(1))
    if loss_match:
        stats["packet_loss"] = loss_match.group(1)
    rtt_match = re.search(
        r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
        output,
    )
    if rtt_match:
        stats["rtt"] = {
            "min": rtt_match.group(1),
            "avg": rtt_match.group(2),
            "max": rtt_match.group(3),
            "mdev": rtt_match.group(4),
        }
    return stats


def main():
    argument_spec = dict(
        dest=dict(type="str", required=True),
        count=dict(type="int", default=5),
        source=dict(type="str"),
        ttl=dict(type="int"),
        size=dict(type="int"),
        interval=dict(type="int"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(changed=False, commands=[], packet_loss="0%", packets_rx=0, packets_tx=0)

    client = VyOSRestClient(module)
    path = _build_ping_path(module.params)

    try:
        result = client.show(path)
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    output = result.get("data", "")
    stats = _parse_ping_output(output)
    reachable = stats["packets_rx"] > 0

    if module.params["state"] == "present" and not reachable:
        module.fail_json(
            msg="Ping to {dest} failed — no packets received.".format(dest=module.params["dest"]),
            **stats,
        )
    elif module.params["state"] == "absent" and reachable:
        module.fail_json(
            msg="Expected {dest} to be unreachable but ping succeeded.".format(
                dest=module.params["dest"],
            ),
            **stats,
        )

    module.exit_json(changed=False, commands=path, **stats)


if __name__ == "__main__":
    main()
