from ansible.module_utils.connection import Connection


class VyOSModule:

    def __init__(self, module):
        self.module = module

        if not module._socket_path:
            module.fail_json(msg="Connection must be httpapi")

        self.connection = Connection(module._socket_path)
        self.existing = {}

    # ----------------------------------------------------------
    # Low-level transport
    # ----------------------------------------------------------

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
            data=payload,
        )

        if not response:
            self.module.fail_json(msg="Empty response from device")

        if not response.get("success"):
            error = response.get("error", "")
            # VyOS returns an error when path has no config — treat as empty
            if "empty" in error.lower() or "path is empty" in error.lower():
                return {}
            self.module.fail_json(
                msg="VyOS API error: {0}".format(error),
                response=response,
            )

        return response.get("data") or {}

    # ----------------------------------------------------------
    # Config retrieval
    # ----------------------------------------------------------

    def get_config(self, path_list):
        """
        Fetch config at path_list via showConfig.
        Returns empty dict when path has no configuration.
        """
        result = self._send(
            path="/retrieve",
            op="showConfig",
            path_list=path_list,
        )
        self.existing = result
        return result

    # ----------------------------------------------------------
    # Config application
    # ----------------------------------------------------------

    def apply_commands(self, commands):
        """
        Send a list of commands to /configure.
        Accepts tuples (op, path) or dicts {"op": ..., "path": ...}.
        Returns the raw API response dict.
        Raises via fail_json on API error.
        Does NOT call exit_json — the caller controls module exit.
        """
        if not commands:
            return {}

        payload_commands = []
        for cmd in commands:
            if isinstance(cmd, tuple):
                op, path = cmd
                payload_commands.append({"op": op, "path": path})
            elif isinstance(cmd, dict):
                payload_commands.append(cmd)
            else:
                self.module.fail_json(
                    msg="Invalid command format: {0}".format(cmd),
                )

        return self._send(
            path="/configure",
            commands=payload_commands,
        )

    def save_config(self):
        """
        Persist running config to disk.
        Returns True on success, fails via fail_json on error.
        """
        self._send(path="/config-file", op="save")
        return True
