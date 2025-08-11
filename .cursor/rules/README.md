# Cursor Rules Overview

This directory defines **enforceable coding and workflow rules** for agents and humans working in this repository.
The rules are modular, following [Cursor Context Rules](https://docs.cursor.com/en/context/rules) best practices.

---

## 📜 Rule Files

### 1. `tdd_enforcement.mdc`
**Purpose:** Enforces **Strict TDD (Red → Green → Refactor)** for all code changes.

Key points:
- **RED:** Write failing tests first.
- **GREEN:** Implement minimum code to pass tests.
- **REFACTOR:** Clean up while all tests pass.
- No marking GREEN complete with failing relevant tests.
- Must resolve root causes, no shortcuts.
- TDD is **iterative** — multiple cycles may occur in the same branch.
- Logs phase, cycle number, and violations in the **State Log**.

---

### 2. `branch_commit_pr.mdc`
**Purpose:** Enforces branching, commit, and PR hygiene.

Key points:
- Create a new branch **before starting on a new issue**.
- One branch and one PR per issue.
- PR must list TDD cycles performed and link to the **State Log**.
- Commit frequently, use **Conventional Commits** format.
- Keep commits single-line and changes simple.

---

### 3. `state_tracking.mdc`
**Purpose:** Defines a **unified logging format** for all workflow tracking.

Key points:
- **State Log** includes:
  - Cycle number
  - Current phase (RED, GREEN, or REFACTOR)
  - Timestamps
  - Commit history
  - Relevant test results
  - Violations + corrective actions
- Update log at **end of every phase** and on **violations**.
- Log must be accessible to reviewers (e.g., linked in PR).

---

## 🛠 How They Work Together
1. **`tdd_enforcement.mdc`** ensures the *process* is followed.
2. **`branch_commit_pr.mdc`** enforces *version control hygiene*.
3. **`state_tracking.mdc`** standardizes *logging and visibility*.

Together, they guarantee:
- Every change is **test-driven**.
- Every workflow step is **documented**.
- Every PR is **traceable and reviewable**.

---

## ✅ Compliance Checklist
- [ ] New branch created before starting work.
- [ ] Failing test written before implementation.
- [ ] GREEN phase only marked complete with all relevant tests passing.
- [ ] REFACTOR phase keeps all tests passing.
- [ ] Commits are small, frequent, and follow Conventional Commits.
- [ ] State Log updated at every phase and linked in PR.

---

*These rules are enforced automatically by Cursor agents but are also expected to be followed by human contributors.*
