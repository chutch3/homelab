# DNS Playbooks

Ansible playbooks for managing DNS records in the homelab.

## Usage

```bash
# Add DNS records for all services
task ansible:dns:add-records

# Remove DNS records for all services
task ansible:dns:remove-records
```

See `ansible/roles/dns/` for the underlying role implementation.
