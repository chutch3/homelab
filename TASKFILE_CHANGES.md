# Taskfile Changes Summary

**Date:** 2026-03-11
**File:** `ansible/Taskfile-UPDATED.yml`

---

## Overview

The Taskfile has been updated to support **both legacy and refactored playbooks**. This allows for gradual migration while maintaining backward compatibility.

---

## 🔄 Changed Commands

### 1. Cluster Initialization

#### **New (Recommended):**
```bash
task ansible:cluster:init
```
- **File:** `ansible/playbooks/cluster/init-refactored.yml`
- **Features:** Full verification, proper modules, comprehensive reporting
- **Output:** Detailed verification at each step

#### **Legacy:**
```bash
task ansible:cluster:init:legacy
```
- **File:** `ansible/playbooks/cluster/init.yml` (original)
- **Features:** Basic init, shell commands, minimal verification

---

### 2. Worker Join

#### **New (Recommended):**
```bash
task ansible:cluster:join -- -e "manager_ip=192.168.86.227" -e "manager_token=SWMTKN-..."
```
- **File:** `ansible/playbooks/cluster/join-refactored.yml`
- **Features:** Pre-flight checks, full verification, manager connectivity test
- **Output:** Verifies node is Ready and reachable from manager

#### **Legacy:**
```bash
task ansible:cluster:join:legacy -- -e "manager_ip=..." -e "manager_token=..."
```
- **File:** `ansible/playbooks/cluster/join.yml` (original)
- **Features:** Basic join, minimal verification

---

### 3. Teardown Operations

#### **New (Recommended):**
```bash
task ansible:teardown -- -e "confirm_teardown=true"
```
- **File:** `ansible/playbooks/cluster/teardown.yml` (NEW LOCATION!)
- **Features:**
  - 9-phase teardown with verification
  - Network removal with VIP release
  - iSCSI/OCFS2 unmount
  - Fstab cleanup
  - Comprehensive reporting
- **Safety:** Requires explicit confirmation

#### **Legacy:**
```bash
task ansible:teardown:legacy
```
- **File:** `ansible/playbooks/ops/teardown.yml` (original)
- **Features:** Basic stack removal only, no verification

#### **Additional Teardown Commands:**

**Full teardown (everything):**
```bash
task ansible:teardown:full
```
Equivalent to:
```bash
task ansible:teardown -- -e "confirm_teardown=true remove_volumes=true leave_swarm=true"
```

**Stacks only (preserve swarm):**
```bash
task ansible:teardown:stacks-only
```
Removes stacks and networks, preserves volumes and swarm membership.

**Dry run (check mode):**
```bash
task ansible:teardown:check
```
Shows what WOULD be removed without actually doing it.

---

## 📝 Updated Descriptions

### DNS Commands
- **Updated:** `dns:add-services` description now mentions "with verification"
- **Behavior:** Now uses refactored task with dig verification (when you replace the task file)

### Uptime Kuma Commands
- **Updated:** `uptime:add-services` description now mentions "with verification"
- **Behavior:** Now uses refactored task with status verification (when you replace the task file)

---

## 🆕 New Commands

### Teardown Variants

| Command | Purpose |
|---------|---------|
| `task ansible:teardown` | New complete teardown (requires confirmation) |
| `task ansible:teardown:legacy` | Old teardown (stacks only) |
| `task ansible:teardown:full` | Scorched-earth (everything) |
| `task ansible:teardown:stacks-only` | Stacks + networks only |
| `task ansible:teardown:check` | Dry run mode |

### Cluster Variants

| Command | Purpose |
|---------|---------|
| `task ansible:cluster:init` | New verified init |
| `task ansible:cluster:init:legacy` | Old basic init |
| `task ansible:cluster:join` | New verified join |
| `task ansible:cluster:join:legacy` | Old basic join |

---

## 🔧 How to Apply Changes

### Option 1: Replace Taskfile (Recommended)
```bash
cd /home/cody/workspace/homelab/ansible
cp Taskfile.yml Taskfile-BACKUP.yml
cp Taskfile-UPDATED.yml Taskfile.yml
```

### Option 2: Manual Merge
If you have custom tasks, manually merge the changes:
1. Keep your custom tasks
2. Update the `cluster:*` commands
3. Add the new `teardown:*` commands
4. Update descriptions for `dns:add-services` and `uptime:add-services`

---

## 📋 Command Comparison Matrix

| Operation | Legacy Command | New Command | Key Differences |
|-----------|---------------|-------------|-----------------|
| **Swarm Init** | `cluster:init` → init.yml | `cluster:init` → init-refactored.yml | +Verification, +Proper modules |
| **Worker Join** | `cluster:join` → join.yml | `cluster:join` → join-refactored.yml | +Pre-flight, +Manager check |
| **Teardown** | `teardown` → ops/teardown.yml | `teardown` → cluster/teardown.yml | +9 phases, +Storage cleanup, +Verification |
| **DNS Add** | `dns:add-services` | Same command | +dig verification (after task replacement) |
| **Uptime Add** | `uptime:add-services` | Same command | +Status verification (after task replacement) |

---

## 🎯 Recommended Migration Path

### Phase 1: Update Taskfile
```bash
cd /home/cody/workspace/homelab/ansible
cp Taskfile-UPDATED.yml Taskfile.yml
```

### Phase 2: Test New Commands (Don't Break Existing)
```bash
# Test new init (dry run)
task ansible:cluster:init -- --check

# Test new teardown (dry run)
task ansible:teardown:check
```

### Phase 3: Use New Commands
```bash
# From now on, use:
task ansible:cluster:init          # Instead of cluster:init:legacy
task ansible:cluster:join          # Instead of cluster:join:legacy
task ansible:teardown              # Instead of teardown:legacy
```

### Phase 4: Update Role Tasks (Optional)
Once comfortable, replace the DNS and Uptime Kuma task files:
```bash
cd /home/cody/workspace/homelab/ansible

# DNS
mv roles/dns/tasks/add-service-cnames.yml roles/dns/tasks/add-service-cnames-OLD.yml
mv roles/dns/tasks/add-service-cnames-refactored.yml roles/dns/tasks/add-service-cnames.yml

# Uptime Kuma
mv roles/uptime_kuma/tasks/add-service-monitors.yml roles/uptime_kuma/tasks/add-service-monitors-OLD.yml
mv roles/uptime_kuma/tasks/add-service-monitors-refactored.yml roles/uptime_kuma/tasks/add-service-monitors.yml
```

---

## 🔍 Verification

After updating the Taskfile:

```bash
# List all available tasks
task --list

# Should show new commands:
# - ansible:cluster:init (points to refactored)
# - ansible:cluster:init:legacy
# - ansible:teardown (points to new cluster/teardown.yml)
# - ansible:teardown:legacy
# - ansible:teardown:full
# - ansible:teardown:stacks-only
# - ansible:teardown:check
```

---

## 🚨 Important Notes

### Safety Features

1. **New teardown requires confirmation:**
   ```bash
   # This will fail with error message
   task ansible:teardown

   # Must use:
   task ansible:teardown -- -e "confirm_teardown=true"
   ```

2. **Legacy commands still work:**
   - No breaking changes
   - Can roll back at any time
   - Use `:legacy` suffix for old behavior

3. **Dry run available:**
   ```bash
   task ansible:teardown:check
   ```
   Shows what would be removed without actually doing it.

### Backward Compatibility

- All legacy commands preserved with `:legacy` suffix
- Default commands (`cluster:init`, `cluster:join`, `teardown`) now point to refactored versions
- Can switch between versions at any time

---

## 📊 What Gets Verified Now

### With New Commands:

| Command | Verifications Added |
|---------|-------------------|
| `cluster:init` | ✅ Swarm active<br>✅ Manager role<br>✅ Node Ready<br>✅ Network created<br>✅ Labels applied |
| `cluster:join` | ✅ Manager reachable<br>✅ Node joined<br>✅ Node Ready<br>✅ Visible from manager<br>✅ Labels applied |
| `teardown` | ✅ Stacks removed<br>✅ Containers removed<br>✅ Networks removed<br>✅ Storage unmounted<br>✅ iSCSI logged out<br>✅ Fstab cleaned<br>✅ Swarm left |

---

## 🎉 Benefits

1. **Safer operations:** Verification catches failures early
2. **Better debugging:** Detailed output shows exactly what failed
3. **Complete cleanup:** No more manual cleanup after teardown
4. **Backward compatible:** Legacy commands still available
5. **Gradual migration:** Can test new commands without breaking existing workflows

---

## 🔗 Related Files

- **Audit Report:** `AUDIT_REPORT.md` - Why these changes were made
- **Implementation Guide:** `IMPLEMENTATION_GUIDE.md` - How to migrate
- **Summary:** `REFACTOR_SUMMARY.md` - What was delivered

---

**Ready to use!** Just copy `Taskfile-UPDATED.yml` to `Taskfile.yml` and start using the new commands.
