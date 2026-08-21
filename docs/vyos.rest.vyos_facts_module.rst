.. _vyos.rest.vyos_facts_module:


********************
vyos.rest.vyos_facts
********************

**Get facts about VyOS devices using REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Collects facts from VyOS devices via the REST API.
- Returns structured facts under the ``ansible_facts`` key.
- Uses REST API (``connection=httpapi``) instead of CLI.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>gather_network_resources</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>When supplied, this argument will restrict the facts collected to a given subset. Possible values include the resource module names.</div>
                        <div>This argument is not currently used.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>gather_subset</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">["default"]</div>
                </td>
                <td>
                        <div>When supplied, this argument will restrict the facts collected to a given subset. Possible values for this argument include <code>all</code>, <code>default</code>, <code>config</code>, <code>interfaces</code>, <code>hostname</code>, <code>users</code>, <code>bgp</code>, <code>ospf</code>, <code>ntp</code>, <code>snmp</code> and <code>logging</code>.</div>
                        <div>Specify a list of values to include a larger subset. Use the exclamation mark (<code>!</code>) before a value to exclude it. Values <code>all</code> and <code>default</code> cannot be combined with each other or with negation.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - Requires ``ansible_connection=httpapi`` with the VyOS httpapi plugin.
   - ``ansible_network_os`` must be set to ``vyos.rest.vyos``.
   - Only configuration facts are available via the REST API. Operational state (interface counters, BGP neighbors) is not supported.



Examples
--------

.. code-block:: yaml

    - name: Gather all facts
      vyos.rest.vyos_facts:
        gather_subset: all

    - name: Gather default facts
      vyos.rest.vyos_facts:

    - name: Gather interface and hostname facts only
      vyos.rest.vyos_facts:
        gather_subset:
          - interfaces
          - hostname

    - name: Gather all except config
      vyos.rest.vyos_facts:
        gather_subset:
          - all
          - '!config'


Returned Facts
--------------
Facts returned by this module are added/updated in the ``hostvars`` host facts and can be referenced by name just like any other host fact. They do not need to be registered in order to use them.

.. raw:: html

    <table border=0 cellpadding=0 class="documentation-table">
                                                                                                                                <tr>
            <th colspan="1">Fact</th>
            <th>Returned</th>
            <th width="100%">Description</th>
        </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_bgp</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>BGP configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_config</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>Full device configuration as structured data.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_hostname</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">string</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>Device hostname.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_interfaces</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>Interface configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_logging</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>Logging configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_ntp</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>NTP configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_ospf</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>OSPFv2 configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_ospfv3</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>OSPFv3 configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_snmp</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>SNMP configuration.
                            </div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1" colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>vyos_users</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this fact"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                    </div>
                </td>
                <td></td>
                <td>
                            <div>User accounts (without passwords).
                            </div>
                    <br/>
                </td>
            </tr>
    </table>
    <br/><br/>



Status
------


Authors
~~~~~~~

- VyOS Community (@vyos)
