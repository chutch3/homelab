# Actual migration regression fixture

`actual-26.7.0.zip` is a synthetic budget exported with `@actual-app/api@26.7.0`.
It contains no household data or server credentials. Checking starts at $5,000,
Discover at -$1,000, and the Spending group contains Wealthfront and Groceries.
There are no purchases or budget allocations.

The archive includes migrations through `1780606215001`, matching the migration
boundary that the 26.5.2 client could not read. Keep this fixture independent of
the installed API: regenerating it on each test run would hide this regression.
The integration test uploads it to the real 26.5.2 test server using sync format 2,
then runs Beholder's normal preview entry point against that server.

To reproduce the fixture with API 26.7.0 in a separate temporary directory:
initialize a local data directory with `api.init({ dataDir })`, create the budget
with `api.runImport` and the accounts/categories described above, then call
`api.internal.send("export-budget")` and write its `data` buffer to this ZIP.
Always call `api.shutdown()` afterward. No server is needed for this export.

The account-group sync regression reuses this older snapshot and posts an
`accounts.account_group_id = null` message through the server's sync endpoint.
That reproduces the case where a newer Actual client has written sync updates
without replacing the uploaded snapshot. API 26.7.0 fails to apply that message;
API 26.9.0 migrates the local schema before applying it. No household data is used.
