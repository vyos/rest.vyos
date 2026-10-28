=============================
Vyos Collection Release Notes
=============================

.. contents:: Topics

v1.0.0
======

Release Summary
---------------

Initial release of the ``vyos.rest`` collection. It manages VyOS devices through the HTTPS REST API using ``ansible.netcommon.httpapi``, as the REST-based counterpart of the SSH/CLI-based ``vyos.vyos`` collection.

Minor Changes
-------------

- Added / Modified the items to meet AAP requirements.
- module_utils/vyos.py - Fix cast_by_spec to handle int-typed leaves returned as collapsed lists (including empty list -> None).
- plugins/module_utils/vyos.py - Add VyOSModule.get_value() wrapper for the "returnValue" retrieve operation.
- vyos httpapi plugin - add support for four additional authentication methods against the VyOS REST API - ``header`` (API key sent as an ``X-API-Key`` header), ``bearer`` (a VyOS-issued bearer token, fetched once and cached until it expires), ``mtls`` (mutual TLS, with no application-level credential sent at all), and ``oidc`` (a bearer token obtained from an external OpenID Connect provider via the client_credentials grant, likewise fetched and cached) - selectable via the new ``auth_method`` option. The existing API-key-in-the-request-body behaviour remains the default, so no change is required for existing inventories.
- vyos httpapi plugin - the OIDC token endpoint must use ``https``, because the request carries the client secret and the response carries a bearer token. A plain ``http`` endpoint (for example a lab identity provider) is accepted only with the new ``oidc_allow_insecure_http`` option, which logs a warning, and other URL schemes are never accepted. Certificate validation of the token endpoint can be turned off for a self-signed lab provider with ``oidc_validate_certs``, and the request is bounded by ``oidc_timeout``.
- vyos_banner - Add new module and tests.
- vyos_banner - Fix SIT overridden, merged and rtt.
- vyos_bgp_address_family - Add new module and tests.
- vyos_bgp_global - Add new module and tests.
- vyos_command - Add new module and tests.
- vyos_config - Add new module and tests.
- vyos_facts - Add new module and tests.
- vyos_firewall_global - Add new module and tests.
- vyos_firewall_interfaces - Add new module and tests.
- vyos_firewall_rules - Add new module and tests.
- vyos_ha - Add new module and tests.
- vyos_hostname - Add new module and tests.
- vyos_interfaces - Add support for L2 interface configuration
- vyos_interfaces - Refactor the module to comply with the dict_op paradigm.
- vyos_l3_interfaces - Add support for L3 interfaces configuration
- vyos_l3_interfaces - Refactor the module to comply with dict_op paradigm.
- vyos_lag_interfaces - Refactor the module to comply with dict_op paradigm.
- vyos_lldp_global - Add new module and tests.
- vyos_lldp_interfaces - Refactor lldp_interface module to comply with dict_op paradigm.
- vyos_logging_global - Add new module and tests.
- vyos_logging_global - Fix RTT integration test.
- vyos_nat - Add new module and tests.
- vyos_ntp_global - Add new module and tests.
- vyos_ospf_interfaces - Refactor module to dict_op arch, add more tests.
- vyos_ospfv2 - add support for ``areas[].virtual_link``, ``max_metric``, ``mpls_te``, ``timers``, and ``passive_interface_exclude``.
- vyos_ospfv2 - refactor command generation onto ``dict_op``.
- vyos_ospfv3 - Refactor module to dict_op style.
- vyos_prefix_lists - Add new module and tests.
- vyos_route_maps - Add new module and tests.
- vyos_snmp_server - Add new module and tests.
- vyos_statc_routes - Added static_routes module, documenatation and tests..
- vyos_static_routes - Add new module and tests.
- vyos_static_routes - Refactor to convert to dict_op.
- vyos_system - Add new module and tests.
- vyos_user - Add new module and tests.
- vyos_vlan - Add new module and tests.
- vyos_vrf - Add new module and tests.

Bugfixes
--------

- vyos_hostname - Added method to VyOS helper; fixed bugs in the module and in UAT/SIT tests.

New Modules
-----------

- vyos_banner - Manage multiline banners on VyOS devices via REST API.
- vyos_bgp_address_family - Manage BGP address\-family configuration on VyOS devices using REST API
- vyos_bgp_global - Manage BGP global configuration on VyOS devices using REST API
- vyos_command - Run show commands on VyOS devices using REST API
- vyos_config - Manage VyOS configuration using REST API
- vyos_configure - Send raw set/delete commands to a VyOS device via REST API.
- vyos_facts - Get facts about VyOS devices using REST API
- vyos_firewall_global - Manage global firewall configuration on VyOS devices using REST API
- vyos_firewall_interfaces - Manage firewall hook filters on VyOS devices using REST API
- vyos_firewall_rules - Manage firewall rule sets on VyOS devices using REST API
- vyos_ha - Manage VRRP and load balancer configuration on VyOS via REST API
- vyos_hostname - Manage the system hostname on a VyOS device via the REST API.
- vyos_interfaces - Manage interface configuration on VyOS devices via REST API.
- vyos_l3_interfaces - Manage L3 interface configuration on VyOS devices via REST API.
- vyos_lag_interfaces - Manage LAG interface configuration on VyOS devices via REST API.
- vyos_lldp_global - Manage LLDP global configuration on VyOS via REST API.
- vyos_lldp_interfaces - Manage LLDP interface configuration on VyOS devices via REST API.
- vyos_logging_global - Manage syslog configuration on VyOS devices using REST API
- vyos_nat - Manage NAT configuration on VyOS devices using REST API
- vyos_ntp_global - Manage NTP configuration on VyOS devices using REST API
- vyos_ospf_interfaces - Manage OSPF interface configuration on VyOS devices using REST API
- vyos_ospfv2 - Manage OSPFv2 configuration on VyOS devices using REST API
- vyos_ospfv3 - Manage OSPFv3 configuration on VyOS devices using REST API
- vyos_prefix_lists - Manage prefix\-list configuration on VyOS devices using REST API
- vyos_route_maps - Manage route\-map configuration on VyOS devices using REST API
- vyos_snmp_server - Manage SNMP server configuration on VyOS devices using REST API
- vyos_static_routes - Manage static routes on VyOS devices via REST API.
- vyos_system - Manage system settings on VyOS devices using REST API
- vyos_user - Manage user accounts on VyOS devices using REST API
- vyos_vlan - Manage VLAN (vif) configuration on VyOS devices using REST API
- vyos_vrf - Manage VRF configuration on VyOS devices using REST API
