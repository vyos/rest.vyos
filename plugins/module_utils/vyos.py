from ansible.module_utils.connection import Connection
import json


class VyOSModule:

    def __init__(self, module):

        self.module = module

        if not module._socket_path:
            module.fail_json(msg="Connection must be httpapi")

        self.connection = Connection(module._socket_path)

        self.existing = {}
        self.commands = []

    #
    # LOW LEVEL transport
    #
    def _send(self, path, op=None, path_list=None, commands=None):

        payload = {}

        if op:
            payload["op"] = op

        if path_list:
            payload["path"] = path_list

        if commands:
            payload["commands"] = commands

        response = self.connection.send_request(
            path=path,
            method="POST",
            data=payload
        )

        if not response:
            self.module.fail_json(msg="Empty response from device")

        if not response.get("success"):
            self.module.fail_json(msg="VyOS error", response=response)

        return response.get("data", {})

    #
    # Fetch config
    #
    def get_config(self, path_list):

        self.existing = self._send(
            path="/retrieve",
            op="showConfig",
            path_list=path_list
        )

        return self.existing

    #
    # Add command
    #
    def add_command(self, cmd):

        self.commands.append(cmd)

    #
    # Diff
    #
    def get_diff(self):

        diff = []

        existing_servers = []

        #
        # Extract existing servers safely
        #
        if isinstance(self.existing, dict):
            server_block = self.existing.get("server", {})
            if isinstance(server_block, dict):
                existing_servers = list(server_block.keys())

        #
        # Compare commands vs existing state
        #
        for cmd in self.commands:

            op = cmd.get("op")
            path = cmd.get("path", [])

            if not path:
                continue

            server = path[-1]

            if op == "set":
                if server not in existing_servers:
                    diff.append(cmd)

            elif op == "delete":
                if server in existing_servers:
                    diff.append(cmd)

        return diff
    #
    # Apply config
    #
    def apply_config(self, diff):

        if not diff:
            self.module.exit_json(
                changed=False,
                msg="Already configured"
            )

        response = self._send(
            path="/configure",
            commands=diff
        )

        self.module.exit_json(
            changed=True,
            commands=diff,
            response=response
        )

    #
    # Apply commands
    #
    def apply_commands(self, commands):

        if not commands:
            self.module.exit_json(
                changed=False,
                commands=[],
                msg="Already configured"
            )

        # convert tuples to dicts for API
        payload_commands = []
        for cmd in commands:
            if isinstance(cmd, tuple):
                op, path = cmd
                payload_commands.append({"op": op, "path": path})
            elif isinstance(cmd, dict):
                payload_commands.append(cmd)
            else:
                self.module.fail_json(msg=f"Invalid command type: {cmd}")

        response = self._send(
            path="/configure",
            commands=payload_commands
        )

        self.save_config()

        self.module.exit_json(
            changed=True,
            commands=commands,
            response=response,
        )
    #
    # Delete config
    #
    def delete_config(self, cmds):

        response = self._send(
            path="/configure",
            commands=cmds
        )

        self.module.exit_json(
            changed=True,
            commands=cmds,
            response=response
        )
    
    def save_config(self):

        response = self._send(
            path="/config-file",
            op="save"
        )

        return True