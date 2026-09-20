// Daily scheduling with the clock, timer, execution, and error reporting supplied by the caller.
export function msUntilNextRun(runAt, now) {
  const [h, m] = runAt.split(":").map(Number);
  const next = new Date(now);
  next.setHours(h, m, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next - now;
}

export function scheduleDaily({ runAt, now, schedule, execute, onError }) {
  const loop = () => {
    schedule(
      async () => {
        try {
          await execute();
        } catch (error) {
          await onError(error);
        }
        loop();
      },
      msUntilNextRun(runAt, now()),
    );
  };
  loop();
}
