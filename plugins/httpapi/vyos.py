import json

from urllib.parse import urlencode

from ansible.plugins.httpapi import HttpApiBase


DOCUMENTATION = r"""
---
httpapi: vyos
short_description: VyOS REST API
description:
  - HTTPAPI plugin for interacting with VyOS REST API.
author: Evgeny Molotkov (@eomnom62)
options:
  api_key:
    description: VyOS API key
    type: str
    vars:
      - name: ansible_httpapi_api_key
    env:
      - name: ANSIBLE_HTTPAPI_API_KEY
    ini:
      - section: httpapi
        key: api_key
"""


class HttpApi(HttpApiBase):

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super().set_options(
            task_keys=task_keys,
            var_options=var_options,
            direct=direct,
        )

    def send_request(self, path, data=None, method="POST", headers=None):

        api_key = self.get_option("api_key")

        if not api_key:
            # fallback to inventory vars
            api_key = self._play_context.vars.get("ansible_httpapi_api_key")

        if not api_key:
            raise ValueError("api_key is required")

        form_data = {}

        if data is not None:
            if not isinstance(data, str):
                data = json.dumps(data)
            form_data["data"] = data

        form_data["key"] = api_key

        body = urlencode(form_data).encode("utf-8")

        if headers is None:
            headers = {}

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        status, response = self.connection.send(
            path,
            body,
            method=method,
            headers=headers,
        )

        if hasattr(response, "read"):
            response = response.read()

        if isinstance(response, bytes):
            response = response.decode("utf-8")

        if isinstance(response, str):
            response = json.loads(response)

        return response
