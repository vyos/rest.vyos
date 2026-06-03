#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_logging_global
short_description: Manage syslog configuration on VyOS devices using REST API
description:
  - Manages syslog (logging) configuration on VyOS devices via the REST API.
  - Supports console, file, host, user, and global logging targets with
    per-target facility and severity configuration.
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
      files:
        description: Logging to local files.
        type: list
        elements: dict
        suboptions:
          path:
            description: Path to the log file on the device.
            type: str
          archive:
            description: Log file archive/rotation settings.
            type: dict
            suboptions:
              file_num:
                description: Number of archived log files to keep.
                type: int
              size:
                description: Maximum size of log file in kilobytes before rotation.
                type: int
          facilities:
            description: List of syslog facilities to log to this file.
            type: list
            elements: dict
            suboptions:
              facility:
                description: Syslog facility name.
                type: str
              severity:
                description: Minimum severity level to log.
                type: str
      global_params:
        description: Global syslog parameters (maps to C(system syslog global)).
        type: dict
        suboptions:
          archive:
            description: Global log archive/rotation settings.
            type: dict
            suboptions:
              file_num:
                description: Number of archived log files to keep.
                type: int
              size:
                description: Maximum size of log file in kilobytes before rotation.
                type: int
          facilities:
            description: List of syslog facilities for global logging.
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
        description: Logging to remote syslog hosts.
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

  running_config:
    description: Used only with state C(parsed).
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
      - rendered
      - parsed
"""

EXAMPLES = r"""
- name: Merge logging configuration
  vyos.rest.vyos_logging_global:
    config:
      console:
        facilities:
          - facility: local7
            severity: err
      files:
        - path: logFile
          archive:
            file_num: 2
          facilities:
            - facility: local6
              severity: emerg
      hosts:
        - hostname: 172.16.0.1
          port: 223
          facilities:
            - facility: local7
              severity: all
            - facility: all
              protocol: udp
      users:
        - username: vyos
          facilities:
            - facility: local7
              severity: debug
      global_params:
        archive:
          file_num: 2
          size: 111
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
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


# ------------------------------------------------------------
# Normalization
# ------------------------------------------------------------


def normalize_config(cfg):
    result = {
        "console": {"facilities": {}},
        "global": {"facilities": {}},
        "hosts": {},
        "files": {},
        "users": {},
    }

    for f in cfg.get("console", {}).get("facilities", []):
        result["console"]["facilities"][f["facility"]] = f.get("severity")

    gp = cfg.get("global_params", {})
    for f in gp.get("facilities", []):
        result["global"]["facilities"][f["facility"]] = f.get("severity")
    if gp.get("archive"):
        result["global"]["archive"] = gp["archive"]
    if gp.get("marker_interval"):
        result["global"]["marker_interval"] = gp["marker_interval"]
    if gp.get("preserve_fqdn"):
        result["global"]["preserve_fqdn"] = True

    for h in cfg.get("hosts", []):
        host = {"port": h.get("port"), "facilities": {}}
        for f in h.get("facilities", []):
            host["facilities"][f["facility"]] = {k: v for k, v in f.items() if k != "facility"}
        result["hosts"][h["hostname"]] = host

    for f in cfg.get("files", []):
        facilities = {x["facility"]: x.get("severity") for x in f.get("facilities", [])}
        result["files"][f["path"]] = {
            "archive": f.get("archive"),
            "facilities": facilities,
        }

    for u in cfg.get("users", []):
        result["users"][u["username"]] = {
            "facilities": {f["facility"]: f.get("severity") for f in u.get("facilities", [])},
        }

    return result


def normalize_running(raw):
    result = {
        "console": {"facilities": {}},
        "global": {"facilities": {}},
        "hosts": {},
        "files": {},
        "users": {},
    }

    if not raw:
        return result

    for f, data in raw.get("console", {}).get("facility", {}).items():
        result["console"]["facilities"][f] = data.get("level")

    g = raw.get("global", {})
    for f, data in g.get("facility", {}).items():
        result["global"]["facilities"][f] = data.get("level")
    if "archive" in g:
        result["global"]["archive"] = g["archive"]
    if "marker" in g and "interval" in g["marker"]:
        result["global"]["marker_interval"] = g["marker"]["interval"]
    if "preserve-fqdn" in g:
        result["global"]["preserve_fqdn"] = True

    for host, data in raw.get("host", {}).items():
        h = {"port": data.get("port"), "facilities": {}}
        for f, fd in data.get("facility", {}).items():
            h["facilities"][f] = {
                "severity": fd.get("level"),
                "protocol": fd.get("protocol"),
            }
        result["hosts"][host] = h

    for path, data in raw.get("file", {}).items():
        facilities = {}
        for f, fd in data.get("facility", {}).items():
            facilities[f] = fd.get("level")
        result["files"][path] = {
            "archive": data.get("archive"),
            "facilities": facilities,
        }

    for user, data in raw.get("user", {}).items():
        facilities = {}
        for f, fd in data.get("facility", {}).items():
            facilities[f] = fd.get("level")
        result["users"][user] = {"facilities": facilities}

    return result


# ------------------------------------------------------------
# Diff helpers
# ------------------------------------------------------------


def diff_facilities(base, want, have, state):
    cmds = []
    want_keys = set(want)
    have_keys = set(have)

    for f in want_keys:
        if f not in have_keys or want[f] != have[f]:
            path = base + ["facility", f]
            if want[f]:
                path += ["level", want[f]]
            cmds.append(("set", path))

    if state in ["replaced", "deleted"]:
        for f in have_keys - want_keys:
            cmds.append(("delete", base + ["facility", f]))

    return cmds


def diff_map(base, want, have, state):
    cmds = []
    w = set(want)
    h = set(have)

    if state in ["merged", "replaced"]:
        for k in w - h:
            cmds.append(("set", base + [k]))

    if state in ["replaced", "deleted"]:
        for k in h - w:
            cmds.append(("delete", base + [k]))

    return cmds


# ------------------------------------------------------------
# Build commands
# ------------------------------------------------------------


def build_commands(want, have, state):
    cmds = []

    if state == "overridden":
        cmds.append(("delete", ["system", "syslog"]))
        state = "merged"

    cmds += diff_facilities(
        ["system", "syslog", "console"],
        want["console"]["facilities"],
        have["console"]["facilities"],
        state,
    )

    cmds += diff_facilities(
        ["system", "syslog", "global"],
        want["global"]["facilities"],
        have["global"]["facilities"],
        state,
    )

    cmds += diff_map(
        ["system", "syslog", "file"],
        want["files"],
        have["files"],
        state,
    )

    cmds += diff_map(
        ["system", "syslog", "host"],
        want["hosts"],
        have["hosts"],
        state,
    )

    cmds += diff_map(
        ["system", "syslog", "user"],
        want["users"],
        have["users"],
        state,
    )

    return cmds


# ------------------------------------------------------------
# Running config
# ------------------------------------------------------------


def get_running_config(vyos):
    raw = vyos.get_config(["system", "syslog"])
    return normalize_running(raw)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main():
    argument_spec = dict(
        config=dict(type="dict"),
        running_config=dict(type="str"),
        state=dict(
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

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    if state == "gathered":
        module.exit_json(gathered=get_running_config(vyos))

    want = normalize_config(config)
    have = get_running_config(vyos)

    if state == "deleted":
        want = {
            "console": {"facilities": {}},
            "global": {"facilities": {}},
            "hosts": {},
            "files": {},
            "users": {},
        }

    commands = build_commands(want, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=want,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
