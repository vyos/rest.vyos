# vyos.rest

Ansible collection for managing VyOS network devices via the HTTPS REST API,
as an alternative to the SSH/CLI-based `vyos.vyos` collection.

## Requirements

- VyOS 1.3 or later
- Ansible >= 2.15.0
- `ansible.netcommon` >= 2.5.1
- `ansible.utils`

## Configuring VyOS for REST API access

Before using this collection, enable the REST API on each VyOS device:

```
set service https api keys id ansible key YOUR_SECRET_KEY
set service https api rest
commit
save
```

> **Note:** Choose a strong random key. The key is sent with every API
> request and acts as the authentication credential.

## Inventory configuration

Add the following variables to your inventory for each VyOS host:

```ini
[vyos]
vyos-router-01 ansible_host=192.168.1.1

[vyos:vars]
ansible_connection=ansible.netcommon.httpapi
ansible_network_os=vyos.rest.vyos
ansible_httpapi_use_ssl=true
ansible_httpapi_validate_certs=false
ansible_httpapi_api_key=YOUR_SECRET_KEY
```

Or in YAML format:

```yaml
all:
  hosts:
    vyos-router-01:
      ansible_host: 192.168.1.1
      ansible_connection: ansible.netcommon.httpapi
      ansible_network_os: vyos.rest.vyos
      ansible_httpapi_use_ssl: true
      ansible_httpapi_validate_certs: false
      ansible_httpapi_api_key: YOUR_SECRET_KEY
```

## Installation

```bash
ansible-galaxy collection install vyos.rest
```

Or from source:

```bash
git clone https://github.com/vyos/vyos.rest.git
ansible-galaxy collection install vyos.rest/ --force
```

<!--start collection content-->
### Httpapi plugins
Name | Description
--- | ---
[vyos.rest.vyos](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_httpapi.rst)|HttpApi plugin for VyOS REST API

### Modules
Name | Description
--- | ---
[vyos.rest.vyos_banner](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_banner_module.rst)|Manage multiline banners on VyOS devices via REST API.
[vyos.rest.vyos_bgp_address_family](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_bgp_address_family_module.rst)|Manage BGP address-family configuration on VyOS devices using REST API
[vyos.rest.vyos_bgp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_bgp_global_module.rst)|Manage BGP global configuration on VyOS devices using REST API
[vyos.rest.vyos_command](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_command_module.rst)|Run show commands on VyOS devices using REST API
[vyos.rest.vyos_config](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_config_module.rst)|Manage VyOS configuration using REST API
[vyos.rest.vyos_configure](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_configure_module.rst)|Send raw set/delete commands to a VyOS device via REST API.
[vyos.rest.vyos_facts](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_facts_module.rst)|Get facts about VyOS devices using REST API
[vyos.rest.vyos_firewall_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_global_module.rst)|Manage global firewall configuration on VyOS devices using REST API
[vyos.rest.vyos_firewall_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_interfaces_module.rst)|Manage firewall hook filters on VyOS devices using REST API
[vyos.rest.vyos_firewall_rules](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_rules_module.rst)|Manage firewall rule sets on VyOS devices using REST API
[vyos.rest.vyos_ha](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ha_module.rst)|Manage VRRP and load balancer configuration on VyOS via REST API
[vyos.rest.vyos_hostname](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_hostname_module.rst)|Manage the system hostname on a VyOS device via the REST API.
[vyos.rest.vyos_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_interfaces_module.rst)|Manage interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_l3_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_l3_interfaces_module.rst)|Manage L3 interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_lag_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lag_interfaces_module.rst)|Manage LAG interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_lldp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_global_module.rst)|Manage LLDP global configuration on VyOS via REST API.
[vyos.rest.vyos_lldp_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_int
erfaces_module.rst)|Manage LLDP interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_logging_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_logging_global_module.rst)|Manage syslog configuration on VyOS devices using REST API
[vyos.rest.vyos_nat](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_nat_module.rst)|Manage NAT configuration on VyOS devices using REST API
[vyos.rest.vyos_ntp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ntp_global_module.rst)|Manage NTP configuration on VyOS devices using REST API
[vyos.rest.vyos_ospf_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospf_interfaces_module.rst)|Manage OSPF interface configuration on VyOS devices using REST API
[vyos.rest.vyos_ospfv2](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospfv2_module.rst)|Manage OSPFv2 configuration on VyOS devices using REST API
[vyos.rest.vyos_ospfv3](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospfv3_module.rst)|Manage OSPFv3 configuration on VyOS devices using REST API
[vyos.rest.vyos_prefix_lists](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_prefix_lists_module.rst)|Manage prefix-list configuration on VyOS devices using REST API
[vyos.rest.vyos_route_maps](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_route_maps_module.rst)|Manage route-map configuration on VyOS devices using REST API
[vyos.rest.vyos_snmp_server](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_snmp_server_module.rst)|Manage SNMP server configuration on VyOS devices using REST API
[vyos.rest.vyos_static_routes](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_static_routes_module.rst)|Manage static routes on VyOS devices via REST API.
[vyos.rest.vyos_system](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_system_module.rst)|Manage system settings on VyOS devices using REST API
[vyos.rest.vyos_user](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_user_module.rst)|Manage user accounts on VyOS devices using REST API
[vyos.rest.vyos_vlan](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_vlan_module.rst)|Manage VLAN (vif) configuration on VyOS devices using REST API

<!--end collection content-->

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.15.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

## Relation to vyos.vyos

This collection mirrors the module interface of the
[vyos.vyos](https://github.com/vyos/vyos.vyos) collection but communicates
over HTTPS REST instead of SSH/network_cli. It is suitable for environments
where SSH access is restricted or where the REST API is preferred for
automation.

| Feature | vyos.vyos | vyos.rest |
|---------|-----------|-----------|
| Transport | SSH / network_cli | HTTPS REST |
| Connection plugin | `ansible.netcommon.network_cli` | `ansible.netcommon.httpapi` |
| VyOS requirement | Any | VyOS 1.3+ with REST API enabled |
| Atomic commits | Per-command | Batch (single commit) |


