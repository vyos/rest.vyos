.. _vyos.rest.vyos_httpapi:


**************
vyos.rest.vyos
**************

**VyOS REST API**



.. contents::
   :local:
   :depth: 1


Synopsis
--------
- HTTPAPI plugin for interacting with VyOS REST API.




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
                            <div> ini entries:
                                    <p>[httpapi]<br>api_key = VALUE</p>
                            </div>
                                <div>env:ANSIBLE_HTTPAPI_API_KEY</div>
                                <div>var: ansible_httpapi_api_key</div>
                    </td>
                <td>
                        <div>VyOS API key</div>
                </td>
            </tr>
    </table>
    <br/>








Status
------


Authors
~~~~~~~

- Evgeny Molotkov (@eomnom62)


.. hint::
    Configuration entries for each entry type have a low to high priority order. For example, a variable that is lower in the list will override a variable that is higher up.
