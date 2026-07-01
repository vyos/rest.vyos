#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_user
short_description: Manage user accounts on VyOS devices using REST API
description:
  - Manages local user accounts on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - Passwords are write-only. Once set, they cannot be read back in plaintext.
  - Use C(update_password=on_create) to avoid resetting passwords on every run.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  users:
    description: List of user definitions.
    type: list
    elements: dict
    suboptions:
      name:
        description: Username.
        type: str
        required: true
      full_name:
        description: Full name of the user.
        type: str
      password:
        description: Plaintext password. Write-only — hashed on device immediately.
        type: str
        no_log: true
      update_password:
        description:
          - Control when password is updated.
          - C(always) updates the password on every run (default).
          - C(on_create) only sets the password when the user is first created.
        type: str
        choices: [always, on_create]
        default: always
      public_keys:
        description: SSH public keys for the user.
        type: list
        elements: dict
        suboptions:
          name:
            description: Key identifier/name.
            type: str
            required: true
          key:
            description: Base64-encoded public key.
            type: str
            required: true
          type:
            description: Key type.
            type: str
            choices: [ssh-dss, ssh-rsa, ecdsa-sha2-nistp256, ecdsa-sha2-nistp384,
                      ecdsa-sha2-nistp521, ssh-ed25519]
            required: true
  state:
    description:
      - C(present) ensures users exist with the specified configuration.
      - C(absent) removes specified users.
      - C(gathered) returns current user configuration as structured data.
    type: str
    choices: [present, absent, gathered]
    default: present
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - The C(vyos) user cannot be deleted as it is required for API access.
  - Passwords are hashed immediately by VyOS and cannot be read back.
"""

EXAMPLES = r"""
- name: Create user
  vyos.rest.vyos_user:
    users:
      - name: alice
        full_name: Alice Smith
        password: securepassword
        update_password: on_create
    state: present

- name: Add SSH public key
  vyos.rest.vyos_user:
    users:
      - name: alice
        public_keys:
          - name: alice-laptop
            type: ssh-rsa
            key: AAAAB3NzaC1yc2EAAAADAQABAAAB...
    state: present

- name: Delete user
  vyos.rest.vyos_user:
    users:
      - name: alice
    state: absent

- name: Gather all users
  vyos.rest.vyos_user:
    state: gathered
"""

RETURN = r"""
before:
  description: User configuration before this module ran.
  returned: always
  type: list
after:
  description: User configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current user configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
response:
  description: Raw API response.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["system", "login", "user"]


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return []
    raw = raw.get("user", raw)
    result = []
    for username, data in sorted(raw.items()):
        user = {"name": username}
        data = data or {}
        if data.get("full-name"):
            user["full_name"] = data["full-name"]
        auth = data.get("authentication", {}) or {}
        if auth.get("encrypted-password"):
            user["encrypted_password"] = auth["encrypted-password"]
        pub_keys = auth.get("public-keys", {}) or {}
        if pub_keys and isinstance(pub_keys, dict):
            keys = []
            for key_name, key_data in sorted(pub_keys.items()):
                key_data = key_data or {}
                k = {"name": key_name}
                if key_data.get("key"):
                    k["key"] = key_data["key"]
                if key_data.get("type"):
                    k["type"] = key_data["type"]
                keys.append(k)
            if keys:
                user["public_keys"] = keys
        result.append(user)
    return result


def build_commands(users, have_list, state):
    cmds = []
    have_map = {u["name"]: u for u in have_list}

    if state == "absent":
        for user in users:
            name = user["name"]
            if name in have_map:
                cmds.append(("delete", _BASE + [name]))
        return cmds

    # state == "present"
    for user in users:
        name = user["name"]
        have = have_map.get(name, {})
        ubase = _BASE + [name]
        is_new = name not in have_map

        # full_name
        if user.get("full_name") and user["full_name"] != have.get("full_name"):
            cmds.append(("set", ubase + ["full-name", user["full_name"]]))

        # password
        if user.get("password"):
            update_pw = user.get("update_password", "always")
            if update_pw == "always" or is_new:
                cmds.append(
                    (
                        "set",
                        ubase
                        + [
                            "authentication",
                            "plaintext-password",
                            user["password"],
                        ],
                    ),
                )

        # public_keys
        want_keys = {k["name"]: k for k in (user.get("public_keys") or [])}
        have_keys = {k["name"]: k for k in (have.get("public_keys") or [])}
        for key_name, key_data in want_keys.items():
            have_key = have_keys.get(key_name, {})
            kbase = ubase + ["authentication", "public-keys", key_name]
            if key_data.get("key") and key_data["key"] != have_key.get("key"):
                cmds.append(("set", kbase + ["key", key_data["key"]]))
            if key_data.get("type") and key_data["type"] != have_key.get("type"):
                cmds.append(("set", kbase + ["type", key_data["type"]]))

    return cmds


ARGUMENT_SPEC = dict(
    users=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            full_name=dict(type="str"),
            password=dict(type="str", no_log=True),
            update_password=dict(
                type="str",
                choices=["always", "on_create"],
                default="always",
            ),
            public_keys=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    key=dict(type="str", required=True),
                    type=dict(
                        type="str",
                        required=True,
                        choices=[
                            "ssh-dss",
                            "ssh-rsa",
                            "ecdsa-sha2-nistp256",
                            "ecdsa-sha2-nistp384",
                            "ecdsa-sha2-nistp521",
                            "ssh-ed25519",
                        ],
                    ),
                ),
            ),
        ),
    ),
    state=dict(
        default="present",
        choices=["present", "absent", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    users = module.params.get("users") or []

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(users, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=get_running_config(vyos),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()
