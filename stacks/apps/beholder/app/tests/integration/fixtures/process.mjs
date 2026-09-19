import { spawn } from "node:child_process";

// Starts the application and its external fixture server. A timeout must terminate the
// process before rejecting, otherwise failed tests leave servers behind.
export function startProcess(command, args, { timeoutMs = 20000, ...options } = {}) {
  const proc = spawn(command, args, { ...options, stdio: ["ignore", "pipe", "pipe"] });
  let stdout = "";
  let stderr = "";
  let failure;
  proc.stdout?.on("data", (chunk) => {
    stdout = (stdout + chunk).slice(-65536);
  });
  proc.stderr?.on("data", (chunk) => {
    stderr = (stderr + chunk).slice(-65536);
  });
  const finished = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      failure = new Error(`subprocess timed out after ${timeoutMs}ms`);
      proc.kill("SIGKILL");
    }, timeoutMs);
    proc.once("error", (error) => {
      failure = error;
    });
    proc.once("close", (code, signal) => {
      clearTimeout(timer);
      if (failure) reject(new Error(`${failure.message}\nstdout: ${stdout}\nstderr: ${stderr}`));
      else resolve({ code, signal, stdout, stderr });
    });
  });
  // Long-lived servers may fail before a test starts awaiting their completion.
  finished.catch(() => {});
  return {
    proc,
    finished,
    output: () => ({ stdout, stderr }),
    async stop() {
      if (proc.exitCode === null && proc.signalCode === null) proc.kill("SIGTERM");
      await finished.catch(() => {});
    },
  };
}
