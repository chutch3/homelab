// Postal HTTP API boundary. One function, no state.
export async function sendMail({ postalUrl, postalApiKey, from, to, subject, body }) {
  const res = await fetch(`${postalUrl}/api/v1/send/message`, {
    method: "POST",
    headers: { "X-Server-API-Key": postalApiKey, "Content-Type": "application/json" },
    body: JSON.stringify({ to, from, subject, plain_body: body }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.status !== "success") {
    throw new Error(`postal send failed: HTTP ${res.status} ${JSON.stringify(json).slice(0, 200)}`);
  }
  return json.data;
}
