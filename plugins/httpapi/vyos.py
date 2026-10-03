import json
import os
import time

from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.connection import ConnectionError
from ansible.plugins.httpapi import HttpApiBase


DOCUMENTATION = r"""
---
httpapi: vyos
short_description: VyOS REST API
description:
  - HTTPAPI plugin for interacting with VyOS REST API.
  - >-
    Supports multiple authentication methods against the VyOS REST API --
    C(key) (API key in the request body), C(header) (API key as an
    C(X-API-Key) header), C(bearer) (a VyOS-issued bearer token, fetched
    and cached), C(mtls) (mutual TLS, no application-level credential),
    and C(oidc) (a bearer token obtained from an external OpenID Connect
    provider via the client_credentials grant, fetched and cached).
author: Evgeny Molotkov (@eomnom62)
options:
  api_key:
    description: VyOS API key. Required for auth_method C(key), C(header), and C(bearer).
    type: str
    vars:
      - name: ansible_httpapi_api_key
    env:
      - name: ANSIBLE_HTTPAPI_API_KEY
      - name: VYOS_API_KEY
    ini:
      - section: httpapi
        key: api_key
  auth_method:
    description: Authentication method to use against the VyOS REST API.
    type: str
    choices: [key, header, bearer, mtls, oidc]
    default: key
    vars:
      - name: ansible_httpapi_auth_method
    ini:
      - section: httpapi
        key: auth_method
  oidc_token_url:
    description: Token endpoint URL of the OIDC provider. Required for auth_method C(oidc).
    type: str
    vars:
      - name: ansible_httpapi_oidc_token_url
    ini:
      - section: httpapi
        key: oidc_token_url
  oidc_client_id:
    description: OIDC client ID for the client_credentials grant.
    type: str
    vars:
      - name: ansible_httpapi_oidc_client_id
    ini:
      - section: httpapi
        key: oidc_client_id
  oidc_client_secret:
    description: OIDC client secret for the client_credentials grant.
    type: str
    vars:
      - name: ansible_httpapi_oidc_client_secret
    ini:
      - section: httpapi
        key: oidc_client_secret
"""


class HttpApi(HttpApiBase):

    def __init__(self, connection):
        super().__init__(connection)
        self._bearer_token = None
        self._bearer_token_expiry = 0
        self._oidc_token = None
        self._oidc_token_expiry = 0

    def logout(self):
        self._bearer_token = None
        self._bearer_token_expiry = 0
        self._oidc_token = None
        self._oidc_token_expiry = 0

    def handle_httperror(self, exception):
        if getattr(exception, "code", None) == 401:
            raise AnsibleConnectionFailure(
                "Authentication to the VyOS REST API failed: {0}".format(exception),
            )
        return exception

    # -----------------------------------------------------------------
    # API key resolution -- shared by the key, header, and bearer
    # (token-fetch) auth methods.
    # -----------------------------------------------------------------

    def _get_api_key(self):
        api_key = self.get_option("api_key")
        if not api_key:
            api_key = os.environ.get("VYOS_API_KEY")
        if not api_key:
            raise ConnectionError(
                "No VyOS API key available: set api_key (or ANSIBLE_HTTPAPI_API_KEY / "
                "VYOS_API_KEY) to authenticate.",
            )
        return api_key

    @staticmethod
    def _parse_response(response):
        if hasattr(response, "read"):
            response = response.read()
        if isinstance(response, bytes):
            response = response.decode("utf-8")
        if isinstance(response, str):
            response = json.loads(response)
        return response

    # -----------------------------------------------------------------
    # Bearer token: fetched from the VyOS device itself (/token),
    # authenticated the same way the "key" method authenticates an
    # ordinary request, then cached until it expires.
    # -----------------------------------------------------------------

    def _fetch_bearer_token(self):
        api_key = self._get_api_key()
        body = urlencode({"key": api_key})
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        _status, raw_response = self.connection.send(
            "/token",
            data=body,
            method="POST",
            headers=headers,
        )
        response = self._parse_response(raw_response)
        if not response.get("success"):
            raise ConnectionError(response.get("error") or "VyOS token request failed")
        data = response.get("data") or {}
        token = data.get("token")
        expires_in = data.get("expires_in", 3600)
        self._bearer_token = token
        self._bearer_token_expiry = time.time() + expires_in
        return token

    def _get_bearer_token(self):
        if self._bearer_token and self._bearer_token_expiry > time.time():
            return self._bearer_token
        return self._fetch_bearer_token()

    # -----------------------------------------------------------------
    # OIDC token: fetched from an external IdP via the
    # client_credentials grant, cached the same way as the bearer
    # token.
    # -----------------------------------------------------------------

    def _fetch_oidc_token(self):
        token_url = self.get_option("oidc_token_url")
        if not token_url:
            raise ConnectionError(
                "oidc_token_url is required when auth_method=oidc.",
            )
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.get_option("oidc_client_id"),
                "client_secret": self.get_option("oidc_client_secret"),
            },
        ).encode("utf-8")
        request = Request(
            token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request) as resp:
                payload = json.loads(resp.read())
        except Exception as exc:
            raise ConnectionError("OIDC token fetch failed: {0}".format(exc))

        access_token = payload.get("access_token")
        if not access_token:
            raise ConnectionError(
                "OIDC token response did not contain an access_token.",
            )
        expires_in = payload.get("expires_in", 3600)
        self._oidc_token = access_token
        self._oidc_token_expiry = time.time() + expires_in
        return access_token

    def _get_oidc_token(self):
        if self._oidc_token and self._oidc_token_expiry > time.time():
            return self._oidc_token
        return self._fetch_oidc_token()

    # -----------------------------------------------------------------
    # send_request: shared by every auth method. Only the auth
    # material attached to the request (body field vs. header, and
    # which header) differs by method; the request/response envelope
    # itself is identical.
    # -----------------------------------------------------------------

    def send_request(self, url_path, **data):
        auth_method = self.get_option("auth_method") or "key"

        form_data = {}
        if data:
            form_data["data"] = json.dumps(data)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if auth_method == "key":
            form_data["key"] = self._get_api_key()
        elif auth_method == "header":
            headers["X-API-Key"] = self._get_api_key()
        elif auth_method == "bearer":
            headers["Authorization"] = "Bearer {0}".format(self._get_bearer_token())
        elif auth_method == "oidc":
            headers["Authorization"] = "Bearer {0}".format(self._get_oidc_token())
        elif auth_method == "mtls":
            pass
        else:
            raise ConnectionError("Unsupported auth_method: {0}".format(auth_method))

        body = urlencode(form_data)

        _status, raw_response = self.connection.send(
            url_path,
            data=body,
            method="POST",
            headers=headers,
        )
        response = self._parse_response(raw_response)

        if not response.get("success"):
            raise ConnectionError(response.get("error") or "VyOS API request failed")

        return response
