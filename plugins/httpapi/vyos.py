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
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  api_key:
    type: str
    description:
      - The API key configured on the VyOS device.
    env:
      - name: VYOS_API_KEY
    vars:
      - name: ansible_httpapi_api_key
      - name: ansible_vyos_api_key
  auth_method:
    type: str
    default: key
    choices:
      - key
      - header
      - bearer
      - mtls
      - oidc
    vars:
      - name: ansible_httpapi_vyos_auth_method
      - name: ansible_vyos_auth_method
  oidc_token_url:
    type: str
    description:
      - Full URL of the OAuth2/OIDC token endpoint.
      - Required when C(auth_method=oidc).
      - Must use C(https://) -- the client secret is sent in the request
        body, so an C(http://) URL is rejected to avoid transmitting it
        in plaintext.
    vars:
      - name: ansible_vyos_oidc_token_url
  oidc_client_id:
    type: str
    vars:
      - name: ansible_vyos_oidc_client_id
  oidc_client_secret:
    type: str
    vars:
      - name: ansible_vyos_oidc_client_secret
"""

EXAMPLES = r""""""

import json
import time
import traceback


try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils._text import to_text
from ansible.module_utils.connection import ConnectionError
from ansible.module_utils.urls import open_url
from ansible.plugins.httpapi import HttpApiBase


class HttpApi(HttpApiBase):
    """HttpApi plugin for the VyOS HTTPS REST API."""

    def __init__(self, *args, **kwargs):
        super(HttpApi, self).__init__(*args, **kwargs)
        self._bearer_token = None
        self._bearer_token_expiry = 0
        self._oidc_token = None
        self._oidc_token_expiry = 0

    def login(self, username, password):
        """VyOS uses a static API key or external auth — no login endpoint needed."""
        pass

    def logout(self):
        self._bearer_token = None
        self._bearer_token_expiry = 0
        self._oidc_token = None
        self._oidc_token_expiry = 0

    def update_auth(self, response, response_text):
        return None

    def handle_httperror(self, exc):
        if exc.code == 401:
            raise AnsibleConnectionFailure(
                "VyOS API returned HTTP 401 Unauthorized. "
                "Check your authentication configuration and that "
                "'set service https api rest' is enabled on the device.",
            )
        return exc

    def _get_api_key(self):
        """Read the API key - option, env var, or fail clearly."""
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

    def _get_auth_method(self):
        try:
            return self.get_option("auth_method") or "key"
        except Exception:
            return "key"

    def _get_bearer_token(self):
        """Return a cached VyOS JWT, refreshing if expired."""
        if self._bearer_token and time.time() < self._bearer_token_expiry - 30:
            return self._bearer_token

        api_key = self._get_api_key()
        form_data = urlencode({"key": api_key})
        response, response_data = self.connection.send(
            "/token",
            data=form_data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        raw = to_text(response_data.getvalue())
        try:
            result = json.loads(raw)
        except ValueError:
            raise ConnectionError(
                "VyOS /token returned non-JSON: {0}".format(raw[:300]),
            )
        if not result.get("success"):
            raise ConnectionError(
                "VyOS /token error: {0}".format(
                    result.get("error") or "success=false",
                ),
            )
        token_data = result.get("data", {})
        token = token_data.get("token")
        if not token:
            raise ConnectionError(
                "VyOS /token response missing a valid token value.",
            )
        self._bearer_token = token
        expires_in = token_data.get("expires_in", 3600)
        self._bearer_token_expiry = time.time() + expires_in
        return self._bearer_token

    def _get_oidc_token(self):
        """Fetch an OIDC token from the IdP using client credentials, cache it."""
        if self._oidc_token and time.time() < self._oidc_token_expiry - 30:
            return self._oidc_token

        try:
            token_url = self.get_option("oidc_token_url")
            client_id = self.get_option("oidc_client_id")
            client_secret = self.get_option("oidc_client_secret")
        except Exception:
            token_url = client_id = client_secret = None

        if not token_url:
            raise ConnectionError(
                "ansible_vyos_oidc_token_url is required for auth_method=oidc.",
            )
        if not token_url.lower().startswith("https://"):
            raise ConnectionError(
                "ansible_vyos_oidc_token_url must use https:// -- refusing to "
                "send the OIDC client secret over an insecure connection.",
            )
        if not client_id:
            raise ConnectionError(
                "ansible_vyos_oidc_client_id is required for auth_method=oidc.",
            )
        if not client_secret:
            raise ConnectionError(
                "ansible_vyos_oidc_client_secret is required for auth_method=oidc.",
            )

        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        ).encode("utf-8")

        try:
            resp = open_url(
                token_url,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
                timeout=10,
            )
            raw = resp.read().decode("utf-8")
        except Exception as exc:
            raise ConnectionError(
                "OIDC token fetch failed from {0}: {1}".format(token_url, exc),
            )

        try:
            token_response = json.loads(raw)
        except ValueError:
            raise ConnectionError(
                "OIDC token endpoint returned non-JSON: {0}".format(raw[:300]),
            )

        access_token = token_response.get("access_token")
        if not access_token:
            raise ConnectionError(
                "OIDC token response missing a valid access_token: {0}".format(raw[:300]),
            )

        self._oidc_token = access_token
        expires_in = token_response.get("expires_in", 3600)
        self._oidc_token_expiry = time.time() + expires_in
        return self._oidc_token

    def send_request(self, data, **payload):  # pylint: disable=arguments-renamed
        """POST to a VyOS REST endpoint."""
        endpoint = data
        auth_method = self._get_auth_method()

        try:
            if "_raw_list" in payload:
                body = json.dumps(payload["_raw_list"])
            else:
                body = json.dumps(payload)

            if auth_method == "header":
                api_key = self._get_api_key()
                form_data = urlencode({"data": body})
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-API-Key": api_key,
                }
                response, response_data = self.connection.send(
                    endpoint,
                    data=form_data,
                    method="POST",
                    headers=headers,
                )

            elif auth_method == "bearer":
                token = self._get_bearer_token()
                form_data = urlencode({"data": body})
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": "Bearer {0}".format(token),
                }
                response, response_data = self.connection.send(
                    endpoint,
                    data=form_data,
                    method="POST",
                    headers=headers,
                )

            elif auth_method == "mtls":
                form_data = urlencode({"data": body})
                response, response_data = self.connection.send(
                    endpoint,
                    data=form_data,
                    method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            elif auth_method == "oidc":
                token = self._get_oidc_token()
                form_data = urlencode({"data": body})
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": "Bearer {0}".format(token),
                }
                response, response_data = self.connection.send(
                    endpoint,
                    data=form_data,
                    method="POST",
                    headers=headers,
                )

            else:
                api_key = self._get_api_key()
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
        """GET /info - the one unauthenticated endpoint."""
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
