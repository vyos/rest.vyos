#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_user
short_description: Manage local users on VyOS via the REST API.
description:
  - Manages local user accounts on VyOS devices using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_user) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  aggregate:
    description: List of user definitions. Mutually exclusive with I(name).
    type: list
    elements: dict
    aliases: [users, collection]
    suboptions:
      name:
        description: Username.
        type: str
        required: true
      full_name:
        description: Full name.
        type: str
      configured_password:
        description: Plaintext password (will be hashed on device).
        type: str
        no_log: true
      encrypted_password:
        description: Pre-hashed password string.
        type: str
        no_log: true
      update_password:
        description: When to update the password.
        type: str
        choices: [always, on_create]
      level:
        description: User privilege level.
        type: str
        choices: [admin, operator]
      public_keys:
        description: SSH public keys for authentication.
        type: list
        elements: dict
        suboptions:
          name:
            description: Key identifier (e.g. user@host).
            type: str
            required: true
          key:
            description: Base64-encoded public key.
            type: str
            required: true
          type:
            description: Key type.
            type: str
            required: true
            choices: [ssh-dss, ssh-rsa, ecdsa-sha2-nistp256,
                      ecdsa-sha2-nistp384, ssh-ed25519, ecdsa-sha2-nistp521]
      state:
        description: Present or absent.
        type: str
        choices: [present, absent]
  name:
    description: Single username. Mutually exclusive with I(aggregate).
    type: str
  full_name:
    description: Full name for the single user.
    type: str
  configured_password:
    description: Plaintext password.
    type: str
    no_log: true
  encrypted_password:
    description: Pre-hashed password.
    type: str
    no_log: true
  update_password:
    type: str
    choices: [always, on_create]
  level:
    type: str
    choices: [admin, operator]
  public_keys:
    type: list
    elements: dict
    suboptions:
      name:
        type: str
        required: true
      key:
        type: str
        required: true
      type:
        type: str
        required: true
  state:
    description: Whether to create (present) or remove (absent) the user.
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
  description: set/delete commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_KEY_TYPES = [
    "ssh-dss",
    "ssh-rsa",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ssh-ed25519",
    "ecdsa-sha2-nistp521",
]


def _apply_user(client, user_def, commands, update_password="always"):
    name = user_def["name"]
    base = ["system", "login", "user", name]
    client.configure_set(base)
    commands.append("set system login user {n}".format(n=name))

    if user_def.get("full_name"):
        client.configure_set(base + ["full-name"], user_def["full_name"])
    if user_def.get("level"):
        client.configure_set(base + ["level"], user_def["level"])
    if user_def.get("configured_password") and update_password in ("always",):
        client.configure_set(
            base + ["authentication", "plaintext-password"],
            user_def["configured_password"],
        )
        commands.append(
            "set system login user {n} authentication plaintext-password".format(n=name),
        )
    if user_def.get("encrypted_password"):
        client.configure_set(
            base + ["authentication", "encrypted-password"],
            user_def["encrypted_password"],
        )
    for pk in user_def.get("public_keys") or []:
        kb = base + ["authentication", "public-keys", pk["name"]]
        client.configure_set(kb + ["key"], pk["key"])
        client.configure_set(kb + ["type"], pk["type"])
        commands.append(
            "set system login user {n} authentication public-keys {k}".format(
                n=name,
                k=pk["name"],
            ),
        )


def _delete_user(client, name, commands):
    try:
        client.configure_delete(["system", "login", "user", name])
        commands.append("delete system login user {n}".format(n=name))
    except VyOSRestError:
        pass


def main():
    pk_spec = dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            key=dict(type="str", required=True),
            type=dict(type="str", required=True, choices=_KEY_TYPES),
        ),
    )
    user_spec = dict(
        name=dict(type="str", required=True),
        full_name=dict(type="str"),
        configured_password=dict(type="str", no_log=True),
        encrypted_password=dict(type="str", no_log=True),
        update_password=dict(type="str", choices=["always", "on_create"]),
        level=dict(type="str", choices=["admin", "operator"]),
        public_keys=pk_spec,
        state=dict(type="str", choices=["present", "absent"]),
    )
    argument_spec = dict(
        aggregate=dict(
            type="list",
            elements="dict",
            aliases=["users", "collection"],
            options=user_spec,
        ),
        name=dict(type="str"),
        full_name=dict(type="str"),
        configured_password=dict(type="str", no_log=True),
        encrypted_password=dict(type="str", no_log=True),
        update_password=dict(type="str", choices=["always", "on_create"]),
        level=dict(type="str", choices=["admin", "operator"]),
        public_keys=pk_spec,
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["aggregate", "name"]],
        supports_check_mode=True,
    )
    if module.check_mode:
        module.exit_json(changed=True, commands=["(check mode)"])

    client = VyOSRestClient(module)
    commands = []
    changed = False

    # Build unified user list
    users = module.params.get("aggregate") or []
    if module.params.get("name"):
        users = [
            {
                "name": module.params["name"],
                "full_name": module.params.get("full_name"),
                "configured_password": module.params.get("configured_password"),
                "encrypted_password": module.params.get("encrypted_password"),
                "update_password": module.params.get("update_password", "always"),
                "level": module.params.get("level"),
                "public_keys": module.params.get("public_keys"),
                "state": module.params.get("state", "present"),
            },
        ]

    try:
        for u in users:
            u_state = u.get("state") or module.params.get("state", "present")
            if u_state == "absent":
                _delete_user(client, u["name"], commands)
            else:
                _apply_user(
                    client,
                    u,
                    commands,
                    update_password=u.get("update_password") or "always",
                )
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, commands=commands)


if __name__ == "__main__":
    main()
