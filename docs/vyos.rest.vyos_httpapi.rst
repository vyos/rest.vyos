.. _vyos.rest.vyos_httpapi:


**************
vyos.rest.vyos
**************

**HttpApi plugin for VyOS REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- This HttpApi plugin provides methods to connect to VyOS devices via their HTTPS REST API.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
                <th>Configuration</th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>api_key</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>env:VYOS_API_KEY</div>
                                <div>var: ansible_httpapi_api_key</div>
                                <div>var: ansible_vyos_api_key</div>
                    </td>
                <td>
                        <div>The API key configured on the VyOS device.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>auth_method</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>key</b>&nbsp;&larr;</div></li>
                                    <li>header</li>
                                    <li>bearer</li>
                                    <li>mtls</li>
                                    <li>oidc</li>
                        </ul>
                </td>
                    <td>
                                <div>var: ansible_httpapi_vyos_auth_method</div>
                                <div>var: ansible_vyos_auth_method</div>
                    </td>
                <td>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_client_id</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_client_id</div>
                    </td>
                <td>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_client_secret</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_client_secret</div>
                    </td>
                <td>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_token_url</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_token_url</div>
                    </td>
                <td>
                        <div>Full URL of the OAuth2/OIDC token endpoint.</div>
                        <div>Required when <code>auth_method=oidc</code>.</div>
                        <div>Must use <code>https://</code> -- the client secret is sent in the request body, so an <code>http://</code> URL is rejected to avoid transmitting it in plaintext.</div>
                </td>
            </tr>
    </table>
    <br/>








Status
------


Authors
~~~~~~~

- VyOS Community (@vyos)


.. hint::
    Configuration entries for each entry type have a low to high priority order. For example, a variable that is lower in the list will override a variable that is higher up.
