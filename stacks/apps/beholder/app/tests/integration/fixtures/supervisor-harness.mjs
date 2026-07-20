// Exercises the real supervisor + reporter in a real Node process. MODE=fatal
// raises an out-of-band rejection outside best-effort work (must email + exit 1);
// MODE=suppressed raises one inside best-effort work (must be tolerated, run continues).
import { createReporter } from "../../../src/reporter.js";
import { createSupervisor } from "../../../src/supervisor.js";

const config = {
  postalUrl: process.env.POSTAL_URL,
  postalApiKey: "harness-key",
  alertFrom: "budget@harness.test",
  alertTo: ["to@harness.test"],
};

const sendMail = async (msg) => {
  await fetch(`${config.postalUrl}/api/v1/send/message`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-server-api-key": config.postalApiKey },
    body: JSON.stringify(msg),
  });
};

const reportFailure = createReporter({ metrics: { recordFailure() {} }, sendMail, config, log() {} });
const supervisor = createSupervisor({ proc: process, onFatal: reportFailure, log() {} });

if (process.env.MODE === "fatal") {
  Promise.reject(new Error("out-of-band fatal"));
} else {
  await supervisor.bestEffort(async () => {
    Promise.reject(new Error("bank sync noise"));
  });
  console.log("run continued");
  process.exit(0);
}
