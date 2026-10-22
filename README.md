# vyos.rest

Ansible collection for managing VyOS network devices via the HTTPS REST API,
as an alternative to the SSH/CLI-based `vyos.vyos` collection.

## Requirements

- ansible-core >=2.16.0, see [Ansible version compatibility](#ansible-version-compatibility).
- Python >=3.10 on the Ansible controller, as required by ansible-core 2.16.
- [ansible.netcommon](https://galaxy.ansible.com/ui/repo/published/ansible/netcommon/) >=2.5.1, installed automatically as a dependency of this collection.
- `ansible.utils`, installed automatically as a dependency of `ansible.netcommon`.
- VyOS 1.3 or later with the REST API enabled and reachable over HTTPS with the `ansible.netcommon.httpapi` connection.
- No additional Python packages are required by the collection's code.

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

You can install the collection with the Ansible Galaxy CLI:

    ansible-galaxy collection install vyos.rest

Red Hat customers should install this collection from
[Red Hat Ansible Automation Hub](https://console.redhat.com/ansible/automation-hub/repo/published/vyos/rest/).
Configure Automation Hub as a Galaxy server in `ansible.cfg` as described in
[Configuring Ansible Automation Hub](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/),
then use the same commands as below. Red Hat does not support installing collections from GitHub.

To install a specific version, for example 1.0.0:

    ansible-galaxy collection install vyos.rest:==1.0.0

To upgrade to the latest version:

    ansible-galaxy collection install vyos.rest --upgrade

You can also include it in a `requirements.yml` file and install it with `ansible-galaxy collection install -r requirements.yml`, using the format:

```yaml
---
collections:
  - name: vyos.rest
```

<!--start collection content-->
### Httpapi plugins
Name | Description
--- | ---
[vyos.rest.vyos](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_httpapi.rst)|HttpApi plugin for VyOS REST API

### Modules
Name | Description
--- | ---
[vyos.rest.vyos_banner](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_banner_module.rst)|Manage multiline banners on VyOS devices via REST API.
[vyos.rest.vyos_bgp_address_family](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_bgp_address_family_module.rst)|Manage BGP address-family configuration on VyOS devices using REST API
[vyos.rest.vyos_bgp_global](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_bgp_global_module.rst)|Manage BGP global configuration on VyOS devices using REST API
[vyos.rest.vyos_command](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_command_module.rst)|Run show commands on VyOS devices using REST API
[vyos.rest.vyos_config](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_config_module.rst)|Manage VyOS configuration using REST API
[vyos.rest.vyos_configure](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_configure_module.rst)|Send raw set/delete commands to a VyOS device via REST API.
[vyos.rest.vyos_facts](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_facts_module.rst)|Get facts about VyOS devices using REST API
[vyos.rest.vyos_firewall_global](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_firewall_global_module.rst)|Manage global firewall configuration on VyOS devices using REST API
[vyos.rest.vyos_firewall_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_firewall_interfaces_module.rst)|Manage firewall hook filters on VyOS devices using REST API
[vyos.rest.vyos_firewall_rules](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_firewall_rules_module.rst)|Manage firewall rule sets on VyOS devices using REST API
[vyos.rest.vyos_ha](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_ha_module.rst)|Manage VRRP and load balancer configuration on VyOS via REST API
[vyos.rest.vyos_hostname](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_hostname_module.rst)|Manage the system hostname on a VyOS device via the REST API.
[vyos.rest.vyos_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_interfaces_module.rst)|Manage interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_l3_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_l3_interfaces_module.rst)|Manage L3 interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_lag_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_lag_interfaces_module.rst)|Manage LAG interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_lldp_global](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_lldp_global_module.rst)|Manage LLDP global configuration on VyOS via REST API.
[vyos.rest.vyos_lldp_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_lldp_interfaces_module.rst)|Manage LLDP interface configuration on VyOS devices via REST API.
[vyos.rest.vyos_logging_global](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_logging_global_module.rst)|Manage syslog configuration on VyOS devices using REST API
[vyos.rest.vyos_nat](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_nat_module.rst)|Manage NAT configuration on VyOS devices using REST API
[vyos.rest.vyos_ntp_global](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_ntp_global_module.rst)|Manage NTP configuration on VyOS devices using REST API
[vyos.rest.vyos_ospf_interfaces](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_ospf_interfaces_module.rst)|Manage OSPF interface configuration on VyOS devices using REST API
[vyos.rest.vyos_ospfv2](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_ospfv2_module.rst)|Manage OSPFv2 configuration on VyOS devices using REST API
[vyos.rest.vyos_ospfv3](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_ospfv3_module.rst)|Manage OSPFv3 configuration on VyOS devices using REST API
[vyos.rest.vyos_prefix_lists](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_prefix_lists_module.rst)|Manage prefix-list configuration on VyOS devices using REST API
[vyos.rest.vyos_route_maps](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_route_maps_module.rst)|Manage route-map configuration on VyOS devices using REST API
[vyos.rest.vyos_snmp_server](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_snmp_server_module.rst)|Manage SNMP server configuration on VyOS devices using REST API
[vyos.rest.vyos_static_routes](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_static_routes_module.rst)|Manage static routes on VyOS devices via REST API.
[vyos.rest.vyos_system](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_system_module.rst)|Manage system settings on VyOS devices using REST API
[vyos.rest.vyos_user](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_user_module.rst)|Manage user accounts on VyOS devices using REST API
[vyos.rest.vyos_vlan](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_vlan_module.rst)|Manage VLAN (vif) configuration on VyOS devices using REST API
[vyos.rest.vyos_vrf](https://github.com/vyos/rest.vyos/blob/main/docs/vyos.rest.vyos_vrf_module.rst)|Manage VRF configuration on VyOS devices using REST API

<!--end collection content-->

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.16.0**.

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

## Support

As Red Hat Ansible Certified Content, this collection is entitled to support through Ansible Automation Platform (AAP) using the **Create issue** button in the top right corner
of the collection page on Automation Hub.

The collection is maintained by the VyOS team. <!-- TODO: VyOS commercial support statement/link -->
If the collection was obtained from Galaxy or GitHub, community help is available through [GitHub issues](https://github.com/vyos/rest.vyos/issues), the [VyOS forum](https://forum.vyos.io/)
and the [Ansible Forum](https://forum.ansible.com/).
