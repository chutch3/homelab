// Owns the process-level safety net. Errors that escape the awaited run (e.g. a
// background bank-sync promise the Actual API rejects out of band) would crash
// the process before reportFailure runs — the watchdog dying silently. Fatal
// errors are reported then exit nonzero; errors raised inside bestEffort() are
// tolerated so a flaky bank sync degrades to "check on last-synced data".
export function createSupervisor({ proc, onFatal, log = () => {}, exit = (code) => proc.exit(code) }) {
  let suppressed = 0;
  let handled = false;

  const handle = async (error) => {
    if (suppressed > 0) {
      log(`[beholder] ignored async error during best-effort work: ${error.message}`);
      return;
    }
    if (handled) return;
    handled = true;
    try {
      await onFatal(error);
    } catch {
      // reporter failed too — exit anyway
    }
    exit(1);
  };

  proc.on("unhandledRejection", handle);
  proc.on("uncaughtException", handle);

  return {
    async bestEffort(fn) {
      suppressed++;
      try {
        return await fn();
      } finally {
        await new Promise((r) => setImmediate(r)); // let background rejections surface while still suppressed
        suppressed--;
      }
    },
    dispose() {
      proc.removeListener("unhandledRejection", handle);
      proc.removeListener("uncaughtException", handle);
    },
  };
}
