// A watchdog must not fail silently: a broken run is itself a finding.
export function createReporter({ metrics, sendMail, config, log = console.error }) {
  return async function reportFailure(error) {
    metrics.recordFailure({ now: Date.now() / 1000 });
    log(`[beholder] run failed: ${error.stack || error.message}`);
    try {
      await sendMail({
        postalUrl: config.postalUrl,
        postalApiKey: config.postalApiKey,
        from: config.alertFrom,
        to: config.alertTo,
        subject: "beholder: run failed - the watchdog itself needs attention",
        body: `beholder could not complete its checks:\n\n${error.message}\n\nUntil this is fixed, nothing is being watched.`,
      });
    } catch (mailError) {
      log(`[beholder] failure email also failed: ${mailError.message}`);
    }
  };
}
