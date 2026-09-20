// Owned transport seam: request data in, HTTP status and raw body out.
export async function postalRequest({ url, apiKey, payload }) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "X-Server-API-Key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { ok: response.ok, status: response.status, body: await response.text() };
}

// Failure reports may supply plain text only.
export async function sendMail({ postalUrl, postalApiKey, from, to, subject, body, html }, request) {
  const response = await request({
    url: `${postalUrl}/api/v1/send/message`,
    apiKey: postalApiKey,
    payload: { to, from, subject, plain_body: body, ...(html === undefined ? {} : { html_body: html }) },
  });
  let json;
  try {
    json = JSON.parse(response.body);
  } catch {
    json = {};
  }
  if (!response.ok || json.status !== "success") {
    throw new Error(`postal send failed: HTTP ${response.status} ${JSON.stringify(json).slice(0, 200)}`);
  }
  return json.data;
}
