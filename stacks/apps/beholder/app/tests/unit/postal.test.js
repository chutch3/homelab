import { describe, expect, it } from "vitest";
import { sendMail } from "../../src/postal.js";

describe("sendMail", () => {
  const message = {
    postalUrl: "invalid:",
    postalApiKey: "key",
    from: "from@test",
    to: ["to@test"],
    subject: "Budget",
    body: "Plain",
    html: "<p>HTML</p>",
  };
  it("passes the exact message to the owned Postal transport and returns delivery metadata", async () => {
    const requests = [];
    const request = async (value) => {
      requests.push(value);
      return { status: 200, ok: true, body: '{"status":"success","data":{"message_id":"123"}}' };
    };
    expect(await sendMail(message, request)).toEqual({ message_id: "123" });
    expect(requests).toEqual([
      {
        url: "invalid:/api/v1/send/message",
        apiKey: "key",
        payload: {
          to: ["to@test"],
          from: "from@test",
          subject: "Budget",
          plain_body: "Plain",
          html_body: "<p>HTML</p>",
        },
      },
    ]);
  });
  it("omits HTML for a plain-text failure report", async () => {
    const requests = [];
    const { html, ...plain } = message;
    await sendMail(plain, async (value) => {
      requests.push(value);
      return { ok: true, status: 200, body: '{"status":"success","data":{}}' };
    });
    expect(requests[0].payload).toEqual({
      to: ["to@test"],
      from: "from@test",
      subject: "Budget",
      plain_body: "Plain",
    });
  });
  it.each([
    [
      { ok: true, status: 200, body: '{"status":"error","message":"rejected"}' },
      'postal send failed: HTTP 200 {"status":"error","message":"rejected"}',
    ],
    [{ ok: true, status: 200, body: "not JSON" }, "postal send failed: HTTP 200 {}"],
    [
      { ok: false, status: 503, body: '{"status":"error"}' },
      'postal send failed: HTTP 503 {"status":"error"}',
    ],
  ])("rejects an unsuccessful Postal response %#", async (response, error) => {
    await expect(sendMail(message, async () => response)).rejects.toThrow(error);
  });
  it("propagates a transport failure", async () => {
    const error = new Error("connection lost");
    await expect(
      sendMail(message, async () => {
        throw error;
      }),
    ).rejects.toBe(error);
  });
});
