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
- Use with ``ansible_connection=ansible.netcommon.httpapi`` and ``ansible_network_os=vyos.rest.vyos``.
- The VyOS REST API must be enabled with ``set service https api keys id ansible key YOUR_KEY``, ``set service https api rest``, then ``commit && save``.




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
                        <div>Set <code>ansible_httpapi_api_key</code> in inventory or the <code>VYOS_API_KEY</code> environment variable.</div>
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
