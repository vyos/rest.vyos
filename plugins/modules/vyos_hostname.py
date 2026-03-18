#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


def get_running_config(vyos):

    raw = vyos.get_config(["system", "host-name"])

    hostname = None

    if isinstance(raw, dict):
        hostname = raw.get("host-name")

    elif isinstance(raw, str):
        hostname = raw.strip()
    else:
        hostname = None

    return {"hostname": hostname}

def build_commands(want, have, state):

    commands = []

    want_host = want.get("hostname")
    have_host = have.get("hostname")

    if state in ["merged", "replaced", "overridden"]:

        if want_host and want_host != have_host:
            commands.append({
                "op": "set",
                "path": ["system", "host-name", want_host]
            })

    elif state == "deleted":

        if have_host:
            commands.append({
                "op": "delete",
                "path": ["system", "host-name"]
            })

    return commands


def main():

    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                hostname=dict(type="str")
            )
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
    want = module.params.get("config") or {}

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(
            changed=False,
            gathered=have
        )

    commands = build_commands(want, have, state)

    if module.check_mode:
        module.exit_json(
            changed=bool(commands),
            commands=commands
        )

    if commands:

        response = vyos.apply_commands(commands)

        # save config if change applied
        saved = vyos.save_config()

        module.exit_json(
            changed=True,
            before=have,
            after=want,
            commands=commands,
            saved=saved,
            response=response
        )

    module.exit_json(
        changed=False,
        before=have,
        after=have
    )


if __name__ == "__main__":
    main()