.. _vyos.rest.vyos_ntp_global_module:


*************************
vyos.rest.vyos_ntp_global
*************************

**Manage NTP configuration on VyOS devices using REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Manages NTP server, allow-client, and listen-address configuration on VyOS devices via the REST API.
- Supports idempotent operation using structured data.
- Uses REST API (``connection=httpapi``) instead of CLI.
- Targets VyOS 1.4+ where NTP is managed by chronyd under ``service ntp``.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="3">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="3">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>config</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>NTP configuration.</div>
                </td>
            </tr>
                                <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>allow_clients</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>List of client networks or addresses allowed to query this NTP server.</div>
                        <div>Maps to <code>service ntp allow-client address</code> on the device.</div>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>listen_addresses</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Local IP addresses the NTP service should listen on.</div>
                        <div>Maps to <code>service ntp listen-address</code> on the device.</div>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>servers</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=dictionary</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>List of upstream NTP servers to synchronise from.</div>
                </td>
            </tr>
                                <tr>
                    <td class="elbow-placeholder"></td>
                    <td class="elbow-placeholder"></td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>options</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>dynamic</li>
                                    <li>noselect</li>
                                    <li>pool</li>
                                    <li>preempt</li>
                                    <li>prefer</li>
                                    <li>nts</li>
                                    <li>ptp</li>
                                    <li>interleave</li>
                        </ul>
                </td>
                <td>
                        <div>Per-server options.</div>
                        <div><code>pool</code> replaces <code>dynamic</code> in VyOS 1.3+.</div>
                        <div><code>nts</code> was added in VyOS 1.4.</div>
                        <div><code>ptp</code> and <code>interleave</code> were added in VyOS 1.5.</div>
                        <div><code>preempt</code> is only available in VyOS 1.3 and earlier.</div>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder"></td>
                    <td class="elbow-placeholder"></td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>server</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Server hostname or IP address.</div>
                </td>
            </tr>


            <tr>
                <td colspan="3">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>running_config</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Used only with state <code>parsed</code>.</div>
                        <div>Provide the output of <code>show configuration commands | grep ntp</code> as a string. The module parses it into structured data and returns the result in the <code>parsed</code> key.</div>
                        <div>No device connection is required for this state.</div>
                </td>
            </tr>
            <tr>
                <td colspan="3">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>state</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>merged</b>&nbsp;&larr;</div></li>
                                    <li>replaced</li>
                                    <li>overridden</li>
                                    <li>deleted</li>
                                    <li>gathered</li>
                                    <li>rendered</li>
                                    <li>parsed</li>
                        </ul>
                </td>
                <td>
                        <div>The desired state of the NTP configuration.</div>
                        <div><code>merged</code> adds or updates the provided configuration without removing existing entries not mentioned in the task.</div>
                        <div><code>replaced</code> fully replaces the running NTP configuration with the provided config, removing entries not present in the task.</div>
                        <div><code>overridden</code> deletes all existing allow-client, listen-address, and server entries then applies the desired config from scratch.</div>
                        <div><code>deleted</code> removes all NTP allow-client, listen-address, and server entries managed by this module.</div>
                        <div><code>gathered</code> retrieves and returns the current NTP configuration as structured data. No changes are made to the device.</div>
                        <div><code>rendered</code> returns the CLI commands that would be generated for the provided config without connecting to the device.</div>
                        <div><code>parsed</code> parses the CLI output provided via <code>running_config</code> into structured data without connecting to the device.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - Tested against VyOS 1.4 (sagitta) and 1.5.
   - Requires ``ansible_connection=httpapi`` with the VyOS httpapi plugin.
   - ``ansible_network_os`` must be set to ``vyos.rest.vyos``.
   - ``replaced`` and ``overridden`` differ. ``replaced`` performs a surgical diff removing only entries not in the task. ``overridden`` deletes entire subtrees first then re-applies, which is safer when option ordering matters.
   - The ``rendered`` and ``parsed`` states do not require a device connection.



Examples
--------

.. code-block:: yaml

    # Before state:
    # -------------
    # set service ntp server time1.vyos.net
    # set service ntp server time2.vyos.net
    # set service ntp server time3.vyos.net

    - name: Merge NTP configuration
      vyos.rest.vyos_ntp_global:
        config:
          allow_clients:
            - 10.6.6.0/24
          listen_addresses:
            - 10.1.3.1
          servers:
            - server: 203.0.113.0
              options:
                - prefer
        state: merged

    # After state:
    # ------------
    # set service ntp allow-client address '10.6.6.0/24'
    # set service ntp listen-address '10.1.3.1'
    # set service ntp server 203.0.113.0 prefer
    # set service ntp server time1.vyos.net
    # set service ntp server time2.vyos.net
    # set service ntp server time3.vyos.net

    # ------------------------------------------------------------------------

    - name: Replace NTP configuration
      vyos.rest.vyos_ntp_global:
        config:
          allow_clients:
            - 10.6.6.0/24
          listen_addresses:
            - 10.1.3.1
          servers:
            - server: 203.0.113.0
              options:
                - prefer
        state: replaced

    # ------------------------------------------------------------------------

    - name: Override NTP configuration
      vyos.rest.vyos_ntp_global:
        config:
          allow_clients:
            - 10.3.3.0/24
          listen_addresses:
            - 10.7.8.1
          servers:
            - server: server1
              options:
                - dynamic
                - prefer
            - server: server2
              options:
                - noselect
                - preempt
            - server: serv
        state: overridden

    # ------------------------------------------------------------------------

    - name: Delete all managed NTP configuration
      vyos.rest.vyos_ntp_global:
        state: deleted

    # ------------------------------------------------------------------------

    - name: Gather current NTP configuration
      vyos.rest.vyos_ntp_global:
        state: gathered

    # ------------------------------------------------------------------------

    - name: Render NTP configuration commands offline
      vyos.rest.vyos_ntp_global:
        config:
          allow_clients:
            - 10.7.7.0/24
            - 10.8.8.0/24
          listen_addresses:
            - 10.7.9.1
          servers:
            - server: server7
            - server: server45
              options:
                - noselect
                - prefer
                - pool
        state: rendered

    # ------------------------------------------------------------------------

    - name: Parse NTP configuration from CLI output
      vyos.rest.vyos_ntp_global:
        running_config: "{{ lookup('file', './ntp_config.cfg') }}"
        state: parsed



Return Values
-------------
Common return values are documented `here <https://docs.ansible.com/ansible/latest/reference_appendices/common_return_values.html#common-return-values>`_, the following are the fields unique to this module:

.. raw:: html

    <table border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Key</th>
            <th>Returned</th>
            <th width="100%">Description</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>after</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when changed</td>
                <td>
                            <div>NTP configuration after this module ran.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>before</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>merged</code>, <code>replaced</code>, <code>overridden</code> or <code>deleted</code></td>
                <td>
                            <div>NTP configuration on the device before this module ran.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>commands</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>List of API command tuples or dicts sent to the device.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>gathered</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>gathered</code></td>
                <td>
                            <div>Current NTP configuration retrieved from the device as structured data.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>parsed</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>parsed</code></td>
                <td>
                            <div>Structured data parsed from the <code>running_config</code> CLI output.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>rendered</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>rendered</code></td>
                <td>
                            <div>CLI commands generated for the provided configuration (offline, no device needed).</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>response</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when changes are applied</td>
                <td>
                            <div>Raw API response from the VyOS REST API.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>saved</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>when changes are applied</td>
                <td>
                            <div>Result of save_config after applying changes.</div>
                    <br/>
                </td>
            </tr>
    </table>
    <br/><br/>


Status
------


Authors
~~~~~~~

- Varshitha Yataluru (@YVarshitha)
