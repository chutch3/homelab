// fetch hides the real reason (DNS, refused, TLS) in error.cause; surface the chain.
function causes(error) {
  let text = "";
  for (let cause = error.cause, depth = 0; cause !== undefined && depth < 5; cause = cause?.cause, depth++) {
    text += ` (caused by: ${cause?.message ?? String(cause)})`;
  }
  return text;
}

// A watchdog must not fail silently: a broken run is itself a finding.
export function createReporter({ metrics, sendMail, config, now, log }) {
  return async function reportFailure(error) {
    metrics.recordFailure({ now: now() });
    const [headline, ...frames] = (error.stack || error.message).split("\n");
    log([`[beholder] run failed: ${headline}${causes(error)}`, ...frames].join("\n"));
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
      log(`[beholder] failure email also failed: ${mailError.message}${causes(mailError)}`);
    }
  };
}
