#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


DOCUMENTATION = r"""
---
module: vyos_banner
short_description: Manage login banners on VyOS devices using REST API
description:
  - Configure pre-login and post-login banners on VyOS devices via REST API.
  - Supports idempotent configuration using structured data.
  - Multiline banner text is supported.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - Your Name (@yourhandle)

options:
  config:
    description:
      - Banner configuration.
    type: dict
    required: true
    suboptions:
      banner:
        description:
          - Banner type to configure.
        type: str
        required: true
        choices:
          - pre-login
          - post-login
      text:
        description:
          - Banner text (supports multiline string).
        type: str

  state:
    description:
      - Desired state of the configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered

notes:
  - This module requires C(ansible_connection=httpapi).
  - Banner text comparison is whitespace-normalized for idempotency.
"""

EXAMPLES = r"""
- name: Configure pre-login banner
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
      text: |
        Unauthorized access is prohibited
        Disconnect immediately
    state: merged

- name: Replace post-login banner
  vyos.rest.vyos_banner:
    config:
      banner: post-login
      text: |
        Welcome to VyOS
    state: replaced

- name: Remove pre-login banner
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: deleted

- name: Gather banner configuration
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: gathered
"""

RETURN = r"""
before:
  description: Configuration before changes.
  returned: always
  type: dict

after:
  description: Configuration after changes.
  returned: when changed
  type: dict

commands:
  description: List of commands sent to the device.
  returned: when changes are required
  type: list

gathered:
  description: Current device configuration.
  returned: when state is gathered
  type: dict

response:
  description: Raw response from VyOS REST API.
  returned: when changes are applied
  type: dict
"""


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def normalize_text(text):
    if text is None:
        return None
    return text.strip()


def get_running_config(vyos, banner):
    try:
        raw = vyos.get_config(["system", "login", "banner"])
    except Exception as e:
        if "Configuration under specified path is empty" in str(e):
            return {"banner": banner, "text": None}
        raise

    if not raw or not isinstance(raw, dict):
        return {"banner": banner, "text": None}

    val = raw.get(banner)

    if not val:
        return {"banner": banner, "text": None}

    if isinstance(val, str):
        return {
            "banner": banner,
            "text": val.strip(),
        }

    if isinstance(val, list):
        lines = [line.strip() for line in val if line.strip()]
        return {
            "banner": banner,
            "text": "\n".join(lines) if lines else None,
        }

    return {"banner": banner, "text": None}


def build_commands(want, have, state):
    """
    Build list of VyOS REST API commands to apply `want` configuration
    based on current `have` configuration and desired `state`.
    Handles:
      - missing paths
      - idempotency
      - multiline banners
      - merged, replaced, overridden, deleted
    """
    commands = []

    banner = want["banner"]
    want_text = want.get("text")
    have_text = have.get("text")

    base_path = ["system", "login", "banner", banner]

    want_lines = want_text.splitlines() if want_text else []
    have_lines = have_text.splitlines() if have_text else []

    banner_exists = have_text is not None
    # --------------------------------------------------------
    # deleted
    # --------------------------------------------------------
    if state == "deleted":
        if banner_exists or have_text is not None:
            commands.append(
                {
                    "op": "delete",
                    "path": base_path,
                },
            )
        return commands

    # --------------------------------------------------------
    # merged
    # --------------------------------------------------------

    if state == "merged":

        # normalize both
        want_lines = want_text.splitlines() if want_text else []
        have_lines = have_text.splitlines() if have_text else []

        # if identical → idempotent
        if want_lines == have_lines:
            return []

        # if device empty → just push all
        if not have_lines:
            return [{"op": "set", "path": base_path + [line]} for line in want_lines]

        # append missing lines only
        commands = []
        for line in want_lines:
            if line not in have_lines:
                commands.append(
                    {
                        "op": "set",
                        "path": base_path + [line],
                    },
                )

        return commands

    # if state == "merged":
    #     # create parent path if missing

    #     for line in want_lines:
    #         if line not in have_lines:
    #             commands.append({
    #                 "op": "set",
    #                 "path": base_path + [line]
    #             })

    #     return commands

    # --------------------------------------------------------
    # replaced / overridden
    # --------------------------------------------------------
    if state in ["replaced", "overridden"]:
        # if existing lines differ from desired lines, delete first
        if banner_exists and want_lines != have_lines:
            commands.append(
                {
                    "op": "delete",
                    "path": base_path,
                },
            )
            # create parent path again before setting lines
            if want_lines:
                commands.append(
                    {
                        "op": "set",
                        "path": base_path,
                        "value": "",
                    },
                )

        # set all desired lines
        for line in want_lines:
            commands.append(
                {
                    "op": "set",
                    "path": base_path + [line],
                },
            )

        return commands

    return commands


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main():

    argument_spec = dict(
        config=dict(
            type="dict",
            required=True,
            options=dict(
                banner=dict(
                    type="str",
                    required=True,
                    choices=["pre-login", "post-login"],
                ),
                text=dict(type="str"),
            ),
        ),
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

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    banner = config.get("banner")

    if not banner:
        module.fail_json(msg="banner is required in config")

    have = get_running_config(vyos, banner)

    # --------------------------------------------------------
    # gathered
    # --------------------------------------------------------

    if state == "gathered":
        module.exit_json(
            changed=False,
            gathered=have,
        )

    want = {
        "banner": banner,
        "text": config.get("text"),
    }

    commands = build_commands(want, have, state)

    if module.check_mode:
        module.exit_json(
            changed=bool(commands),
            commands=commands,
        )
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

    module.exit_json(
        changed=False,
        before=have,
        after=have,
    )


if __name__ == "__main__":
    main()
