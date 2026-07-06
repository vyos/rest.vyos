#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_logging_global
short_description: Manage syslog configuration on VyOS devices using REST API
description:
  - Manages syslog (logging) configuration on VyOS devices via the REST API.
  - Targets VyOS 1.5+ syslog schema under C(system syslog).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - Sagar Paul (@KB-perByte)

options:
  config:
    description: Logging configuration.
    type: dict
    suboptions:
      console:
        description: Logging to serial console.
        type: dict
        suboptions:
          facilities:
            description: List of syslog facilities to log to the console.
            type: list
            elements: dict
            suboptions:
              facility:
                description: Syslog facility name (e.g. local7, all, kern).
                type: str
              severity:
                description: Minimum severity level to log (e.g. err, debug, all).
                type: str
      global_params:
        description: Global syslog parameters (maps to C(system syslog local) on device).
        type: dict
        suboptions:
          facilities:
            description: List of syslog facilities for local logging.
            type: list
            elements: dict
            suboptions:
              facility:
                description: Syslog facility name.
                type: str
              severity:
                description: Minimum severity level to log.
                type: str
          marker_interval:
            description: Interval in seconds between marker log entries.
            type: int
          preserve_fqdn:
            description: Use the fully qualified domain name in syslog messages.
            type: bool
      hosts:
        description: Logging to remote syslog hosts (maps to C(system syslog remote)).
        type: list
        elements: dict
        suboptions:
          hostname:
            description: IP address or hostname of the remote syslog server.
            type: str
          port:
            description: UDP/TCP port on the remote syslog server (default 514).
            type: int
          protocol:
            description: Transport protocol (udp or tcp).
            type: str
          facilities:
            description: List of syslog facilities to forward to this host.
            type: list
            elements: dict
            suboptions:
              facility:
                description: Syslog facility name.
                type: str
              severity:
                description: Minimum severity level to forward.
                type: str
              protocol:
                description: Per-facility protocol override (udp or tcp).
                type: str
      users:
        description: Logging to local user terminals.
        type: list
        elements: dict
        suboptions:
          username:
            description: Local username whose terminal receives log messages.
            type: str
          facilities:
            description: List of syslog facilities to send to this user.
            type: list
            elements: dict
            suboptions:
              facility:
                description: Syslog facility name.
                type: str
              severity:
                description: Minimum severity level to send.
                type: str


  state:
    description:
      - Desired state of the logging configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
"""

EXAMPLES = r"""
- name: Merge logging configuration
  vyos.rest.vyos_logging_global:
    config:
      console:
        facilities:
          - facility: local7
            severity: err
      hosts:
        - hostname: 172.16.0.1
          port: 514
          facilities:
            - facility: local7
              severity: all
      users:
        - username: vyos
          facilities:
            - facility: local7
              severity: debug
      global_params:
        facilities:
          - facility: cron
            severity: debug
        marker_interval: 111
        preserve_fqdn: true
    state: merged

- name: Delete all logging configuration
  vyos.rest.vyos_logging_global:
    state: deleted

- name: Gather current logging configuration
  vyos.rest.vyos_logging_global:
    state: gathered
"""

RETURN = r"""
before:
  description: Logging configuration before this module ran.
  returned: when state is merged, replaced, overridden or deleted
  type: dict
after:
  description: Logging configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current logging configuration from the device.
  returned: when state is gathered
  type: dict
saved:
  description: Result of save_config after applying changes.
  returned: when changed
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    dict_op,
)


_BASE = ["system", "syslog"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fac_list_to_device(facilities):
    """Convert [{facility, severity, protocol}] -> {"name": {"level": s, ...}}"""
    result = {}
    for fac in facilities or []:
        name = fac["facility"]
        entry = {}
        if fac.get("severity"):
            entry["level"] = fac["severity"]
        if fac.get("protocol"):
            entry["protocol"] = fac["protocol"]
        result[name] = entry
    return result


def _fac_device_to_list(raw_fac):
    """Convert {"name": {"level": s}} -> [{facility, severity}]"""
    if not raw_fac or not isinstance(raw_fac, dict):
        return []
    result = []
    for name, data in sorted(raw_fac.items()):
        entry = {"facility": name}
        if isinstance(data, dict):
            if data.get("level"):
                entry["severity"] = data["level"]
            if data.get("protocol"):
                entry["protocol"] = data["protocol"]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Shape adapters
# ---------------------------------------------------------------------------


def _want_to_device(config):
    """Convert argspec config to device shape for dict_op.

    VyOS 1.5 syslog schema:
      system syslog console facility <f> level <s>
      system syslog local   facility <f> level <s>   (was: global)
      system syslog remote  <host> facility <f> ...  (was: host)
      system syslog user    <u> facility <f> ...
      system syslog marker  interval <n>             (was: global marker)
      system syslog preserve-fqdn                    (was: global preserve-fqdn)
      NOTE: file and archive are removed in VyOS 1.5
    """
    if not config:
        return {}
    want = {}

    # console
    console = config.get("console") or {}
    if console.get("facilities"):
        want["console"] = {"facility": _fac_list_to_device(console["facilities"])}

    # global_params -> local + top-level marker/preserve-fqdn
    gp = config.get("global_params") or {}
    if gp:
        if gp.get("facilities"):
            want["local"] = {"facility": _fac_list_to_device(gp["facilities"])}
        if gp.get("marker_interval") is not None:
            want["marker"] = {"interval": gp["marker_interval"]}
        if gp.get("preserve_fqdn"):
            want["preserve-fqdn"] = {}

    # hosts -> remote (keyed by hostname)
    for h in config.get("hosts") or []:
        hd = {}
        if h.get("port") is not None:
            hd["port"] = h["port"]
        if h.get("protocol"):
            hd["protocol"] = h["protocol"]
        if h.get("facilities"):
            hd["facility"] = _fac_list_to_device(h["facilities"])
        want.setdefault("remote", {})[h["hostname"]] = hd

    # users -> user (keyed by username)
    for u in config.get("users") or []:
        ud = {}
        if u.get("facilities"):
            ud["facility"] = _fac_list_to_device(u["facilities"])
        want.setdefault("user", {})[u["username"]] = ud

    return want


def _device_to_argspec(raw):
    """Convert raw device response to argspec shape for before/after/gathered."""
    if not raw:
        return {}
    result = {}

    # console
    console = raw.get("console") or {}
    if console:
        facs = _fac_device_to_list(console.get("facility"))
        if facs:
            result["console"] = {"facilities": facs}

    # local -> global_params
    local = raw.get("local") or {}
    marker = raw.get("marker") or {}
    preserve_fqdn = "preserve-fqdn" in raw
    if local or marker or preserve_fqdn:
        gp = {}
        facs = _fac_device_to_list(local.get("facility") if isinstance(local, dict) else {})
        if facs:
            gp["facilities"] = facs
        if isinstance(marker, dict) and "interval" in marker:
            gp["marker_interval"] = marker["interval"]
        if preserve_fqdn:
            gp["preserve_fqdn"] = True
        if gp:
            result["global_params"] = gp

    # remote -> hosts
    remote_raw = raw.get("remote") or {}
    if remote_raw and isinstance(remote_raw, dict):
        hosts = []
        for hostname, data in sorted(remote_raw.items()):
            h = {"hostname": hostname}
            if isinstance(data, dict):
                if data.get("port") is not None:
                    h["port"] = data["port"]
                if data.get("protocol"):
                    h["protocol"] = data["protocol"]
                facs = _fac_device_to_list(data.get("facility"))
                if facs:
                    h["facilities"] = facs
            hosts.append(h)
        if hosts:
            result["hosts"] = hosts

    # user -> users
    user_raw = raw.get("user") or {}
    if user_raw and isinstance(user_raw, dict):
        users = []
        for username, data in sorted(user_raw.items()):
            u = {"username": username}
            if isinstance(data, dict):
                facs = _fac_device_to_list(data.get("facility"))
                if facs:
                    u["facilities"] = facs
            users.append(u)
        if users:
            result["users"] = users

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    argument_spec = dict(
        config=dict(type="dict"),
        state=dict(
            default="merged",
            choices=[
                "merged",
                "replaced",
                "overridden",
                "deleted",
                "gathered",
            ],
        ),
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = vyos.get_config(_BASE)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    want_device = _want_to_device(config)

    if state == "deleted":
        commands = [("delete", _BASE)] if raw_have else []
    elif state == "overridden":
        commands = []
        for section in list(raw_have.keys()):
            if section not in want_device:
                commands.append(("delete", _BASE + [section]))
            else:
                commands += dict_op(
                    want_device[section],
                    raw_have[section],
                    _BASE + [section],
                    op="purge",
                )
        commands += dict_op(want_device, raw_have, _BASE, op="set")
    else:
        commands = []
        if state == "replaced":
            commands += dict_op(want_device, raw_have, _BASE, op="purge")
        commands += dict_op(want_device, raw_have, _BASE, op="set")

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after = {} if state == "deleted" else _device_to_argspec(vyos.get_config(_BASE))
        module.exit_json(
            changed=True,
            before=have,
            after=after,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
