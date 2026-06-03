# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
name: vyos
short_description: HttpApi plugin for VyOS REST API
description:
  - This HttpApi plugin provides methods to connect to VyOS devices via their
    HTTPS REST API.
  - Use with C(ansible_connection=ansible.netcommon.httpapi) and
    C(ansible_network_os=vyos.rest.vyos).
  - The VyOS REST API must be enabled with
    C(set service https api keys id ansible key YOUR_KEY),
    C(set service https api rest), then C(commit && save).
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  api_key:
    type: str
    description:
      - The API key configured on the VyOS device.
      - Set C(ansible_httpapi_api_key) in inventory or the C(VYOS_API_KEY)
        environment variable.
    env:
      - name: VYOS_API_KEY
    vars:
      - name: ansible_httpapi_api_key
      - name: ansible_vyos_api_key
"""

import json
import traceback


try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils._text import to_text
from ansible.module_utils.connection import ConnectionError
from ansible.plugins.httpapi import HttpApiBase


class HttpApi(HttpApiBase):
    """HttpApi plugin for the VyOS HTTPS REST API."""

    def login(self, username, password):
        """VyOS uses a static API key — no login endpoint needed."""
        pass

    def logout(self):
        pass

    def update_auth(self, response, response_text):
        return None

    def handle_httperror(self, exc):
        if exc.code == 401:
            raise AnsibleConnectionFailure(
                "VyOS API returned HTTP 401 Unauthorized. "
                "Check ansible_httpapi_api_key is correct and that "
                "'set service https api rest' is configured on the device.",
            )
        return exc

    def _get_api_key(self):
        """Read the API key — option, env var, or fail clearly."""
        try:
            key = self.get_option("api_key")
        except Exception:
            key = None
        if not key:
            import os

            key = os.environ.get("VYOS_API_KEY", "")
        if not key:
            raise ConnectionError(
                "No VyOS API key found. Set ansible_httpapi_api_key in "
                "inventory or export VYOS_API_KEY=<key>.",
            )
        return key

    def send_request(self, data, **payload):  # pylint: disable=arguments-renamed
        """POST to a VyOS REST endpoint.

        Args:
            data (str): API path, e.g. '/configure' or '/retrieve'.
                        Named 'data' to match the HttpApiBase signature.
                        Internally referred to as endpoint to avoid collision
                        with the VyOS payload field also called 'data'.
            **payload: VyOS API fields: op, path, value, url, file, etc.

        Returns:
            dict: Parsed JSON response from VyOS.

        Raises:
            ConnectionError: on HTTP error or VyOS success=false response.
        """
        endpoint = data

        try:
            api_key = self._get_api_key()
            if "_raw_list" in payload:
                body = json.dumps(payload["_raw_list"])
            else:
                body = json.dumps(payload)

            form_data = urlencode({"data": body, "key": api_key})
            response, response_data = self.connection.send(
                endpoint,
                data=form_data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            raw = to_text(response_data.getvalue())

            try:
                result = json.loads(raw)
            except ValueError:
                raise ConnectionError(
                    "VyOS API at {ep} returned non-JSON ({code}): {raw}".format(
                        ep=endpoint,
                        code=getattr(response, "status", "?"),
                        raw=raw[:300],
                    ),
                )

            if not result.get("success"):
                raise ConnectionError(
                    "VyOS API error [{ep}]: {err}".format(
                        ep=endpoint,
                        err=result.get("error") or "success=false",
                    ),
                )

            return result

        except (ConnectionError, AnsibleConnectionFailure):
            raise
        except Exception as exc:
            raise ConnectionError(
                "{exc_type} in send_request({ep}): {exc}\n{tb}".format(
                    exc_type=type(exc).__name__,
                    ep=endpoint,
                    exc=to_text(exc),
                    tb=traceback.format_exc(),
                ),
            )

    def get_info(self):
        """GET /info — the one unauthenticated endpoint."""
        try:
            response, response_data = self.connection.send(
                "/info",
                data=None,
                method="GET",
            )
            return json.loads(to_text(response_data.getvalue()))
        except (ConnectionError, AnsibleConnectionFailure):
            raise
        except Exception as exc:
            raise ConnectionError(
                "{exc_type} in get_info(): {exc}\n{tb}".format(
                    exc_type=type(exc).__name__,
                    exc=to_text(exc),
                    tb=traceback.format_exc(),
                ),
            )
