import { describe, expect, it } from "vitest";
import { renderEmail, sendMail } from "../../src/mailer.js";

function report(overrides = {}) {
  return {
    date: "2026-09-10",
    categories: [],
    checking: 269486,
    cards: [{ name: "Discover", balance: -541459 }],
    baseline: null,
    findings: [],
    uncategorized: [],
    budgetUrl: "https://budget.test/",
    ...overrides,
  };
}

describe("renderEmail", () => {
  it("renders both entries with their status, merchant, date and amount", () => {
    const pending = { account: "Discover", merchant: "Cafe <Pending>", date: "2026-09-10", amount: -100 };
    const posted = { account: "Discover", merchant: "Cafe Posted", date: "2026-09-11", amount: -4000 };
    const { html, text } = renderEmail(
      report({ findings: [{ check: "duplicates", pairs: [{ pending, posted }] }] }),
    );
    expect(text).toContain("Pending: September 10, 2026: Cafe <Pending>: $1.00");
    expect(text).toContain("Posted: September 11, 2026: Cafe Posted: $40.00");
    expect(html).toContain("Cafe &lt;Pending&gt;");
    expect(html).toContain('aria-label="Possible duplicate charges"');
    expect(html).not.toContain("Cafe <Pending>");
  });

  it("uses Actual dark-theme accents for warning, overspending and progress", () => {
    const { html } = renderEmail(
      report({
        categories: [{ name: "Food", balance: -100, spent: -200 }],
        uncategorized: [{ date: "2026-09-09", amount: -100, payee: "Shop", account: "Card" }],
      }),
    );
    for (const color of ["#ff9b9b", "#87540d", "#f5e35d", "#65d6ad"]) expect(html).toContain(color);
    for (const oldColor of ["#f2f4f1", "#f5f7f4", "#e8ede7", "#fff5e7", "#a33228"])
      expect(html).not.toContain(oldColor);
    expect(html).toContain('name="supported-color-schemes" content="dark"');
  });

  it.each([0, 1, 2])("labels uncategorized details and their action for %s transactions", (count) => {
    const uncategorized = Array.from({ length: count }, (_, i) => ({
      date: "2026-09-09",
      amount: -100,
      payee: `Shop ${i}`,
      account: "Card",
    }));
    const { html, text } = renderEmail(report({ uncategorized }));
    for (const body of [html, text]) {
      expect(body.includes(`Transactions needing categories · ${count}`)).toBe(count > 0);
      expect(body.includes("Assign a category to these transactions in Actual.")).toBe(count > 0);
      expect(body).not.toContain("Transaction details");
    }
  });

  it("renders cash comparison rows and zero card balances without owed labels", () => {
    const { html, text } = renderEmail(
      report({
        checking: 59440,
        cards: [
          { name: "Discover", balance: -612554 },
          { name: "Unused", balance: 0 },
        ],
      }),
    );
    for (const body of [html, text]) {
      for (const value of [
        "Account balances",
        "Can checking cover the cards?",
        "Total card debt",
        "$6,125.54",
        "Shortfall",
        "$5,531.14",
        "10% covered",
      ])
        expect(body).toContain(value);
      expect(body).not.toContain("$0.00 owed");
      expect(body).not.toContain("Items to review");
    }
    expect(html).toContain('aria-label="Can checking cover the cards?"');
  });

  it("keeps a single-transaction notice short and omits zero inflows", () => {
    const { html, text } = renderEmail(
      report({ uncategorized: [{ date: "2026-09-09", amount: -5261, payee: "Shop", account: "Card" }] }),
    );
    for (const body of [html, text]) {
      expect(body).toContain("1 transaction needs a category (past 14 days): $52.61 spending.");
      expect(body).not.toContain("$0.00 inflows");
    }
  });

  it.each([
    { balance: 7500, spent: -2500, label: "$25.00 spent of $100.00 available", percent: 25 },
    { balance: 0, spent: -10000, label: "$100.00 spent of $100.00 available", percent: 100 },
    { balance: -2000, spent: -12000, label: "$120.00 spent of $100.00 available", percent: 120 },
    { balance: 0, spent: 0, label: "$0.00 spent · No funds available", percent: 0 },
    { balance: -1000, spent: -1000, label: "$10.00 spent · No funds available", percent: 100 },
    {
      balance: 12000,
      spent: 2000,
      label: "$20.00 net inflow · $100.00 available before activity",
      percent: 0,
    },
  ])("renders bounded spending bars for $label", ({ balance, spent, label, percent }) => {
    const { html, text } = renderEmail(report({ categories: [{ name: "Food", balance, spent }] }));
    expect(html).toContain(label);
    expect(text).toContain(label);
    expect(html).toContain(
      `aria-label="Food: ${balance - spent > 0 ? `${percent}% spent` : "No funds available"}"`,
    );
    expect(html).not.toMatch(/NaN|Infinity/);
  });

  it.each([9999, 10000, 10001])("does not round a shortfall into full coverage (%s)", (checking) => {
    const { html, text } = renderEmail(report({ checking, cards: [{ name: "Card", balance: -10000 }] }));
    const label = checking < 10000 ? "Less than 100% covered" : "100% covered";
    expect(text).toContain(`\n${label}\n`);
    expect(html).toContain(`aria-label="${label}"`);
  });

  it("caps an overspending bar without capping its label", () => {
    const { html } = renderEmail(report({ categories: [{ name: "Food", balance: -2500, spent: -12500 }] }));
    expect(html).toMatch(/aria-label="Food: 125% spent"[^>]*><tr><td width="100%"/);
  });

  it("keeps accounts before review findings and details last", () => {
    const { html, text } = renderEmail(
      report({
        findings: [
          {
            check: "raid",
            total: 2609,
            transactions: [{ date: "2026-09-01", amount: 2609, payee: "Interest" }],
          },
        ],
        uncategorized: [{ date: "2026-09-09", amount: -100, payee: "Shop", account: "Card" }],
      }),
    );
    for (const body of [html, text]) {
      const labels = [
        "Open budget",
        "Left to spend",
        "Account balances",
        "Can checking cover the cards?",
        "Savings transactions to review",
        "Transactions needing categories",
      ];
      for (const label of labels) expect(body).toContain(label);
      for (let i = 1; i < labels.length; i++)
        expect(body.indexOf(labels[i - 1])).toBeLessThan(body.indexOf(labels[i]));
      expect(body).not.toContain("Next step");
    }
  });

  it("preserves a floor shortfall when checking is negative and cards have no debt", () => {
    const { text, html } = renderEmail(report({ checking: -1000, cards: [] }));
    for (const body of [text, html]) {
      expect(body).toContain("$10.00");
      expect(body).toContain("Shortfall");
    }
  });

  it("labels historical debt as owed instead of displaying negative money", () => {
    const { text, html } = renderEmail(
      report({
        baseline: { date: "2026-08-11", cards: { Discover: -252056 } },
        findings: [{ check: "drift" }],
      }),
    );
    for (const body of [text, html]) {
      expect(body).toContain("earlier balance: $2,520.56 owed");
      expect(body).toContain("current balance: $5,414.59 owed");
      expect(body).not.toContain("-$");
    }
  });

  it("renders one dated report in HTML and plain text with empty categories", () => {
    const result = renderEmail(report());
    expect(Object.keys(result).sort()).toEqual(["html", "subject", "text"]);
    expect(result.subject).toBe("September budget · September 10, 2026");
    for (const body of [result.text, result.html]) {
      expect(typeof body).toBe("string");
      expect(body).toContain("No visible spending categories");
      expect(body).toContain("$2,719.73");
      expect(body).toContain("Shortfall");
      expect(body).toContain("50% covered");
      expect(body).toContain("payment-due calculation");
      expect(body).not.toContain("card floor");
      expect(body).not.toContain("no email means");
      expect(body).not.toContain("Next step");
    }
    expect(result.html).toContain('href="https://budget.test/"');
    expect(result.text).toContain("Open budget: https://budget.test/");
  });

  it("alphabetizes every category without mutating categories", () => {
    const categories = [
      { name: "Zero", balance: 0 },
      { name: "Available", balance: 12000 },
      { name: "Over", balance: -4500 },
    ];
    const { text, html } = renderEmail(report({ categories }));
    expect(text).toContain("Available: $120.00 left\nOver: $45.00 over\nZero: $0.00 left");
    expect(html).toContain(">Over<");
    expect(html).toContain(">Available<");
    expect(html.indexOf(">Available<")).toBeLessThan(html.indexOf(">Over<"));
    expect(categories.map((c) => c.name)).toEqual(["Zero", "Available", "Over"]);
  });

  it("shows spending and inflows separately above categories and details after the action", () => {
    const uncategorized = [
      { id: "a", date: "2026-09-09", amount: -1000, payee: "Shop", account: "Card" },
      { id: "b", date: "2026-09-08", amount: 500, payee: "Refund", account: "Card" },
    ];
    const { text, html } = renderEmail(report({ uncategorized }));
    for (const body of [text, html]) {
      expect(body).toContain("$10.00 spending");
      expect(body).toContain("$5.00 inflows");
      expect(body).toContain("2 transactions");
      expect(body).toContain("past 14 days");
      for (const heading of [
        "Transactions to categorize",
        "Left to spend",
        "Can checking cover the cards?",
        "Transactions needing categories",
      ])
        expect(body).toContain(heading);
      expect(body.indexOf("Transactions to categorize")).toBeLessThan(body.indexOf("Left to spend"));
      expect(body.indexOf("Can checking cover the cards?")).toBeLessThan(
        body.indexOf("Transactions needing categories"),
      );
      expect(body).not.toContain("Categorize these transactions in Actual.");
      expect(body).toContain("Shop");
      expect(body).toContain("Refund");
    }
    expect(text).toContain("$10.00 spent");
    expect(text).toContain("$5.00 received");
  });

  it("escapes category, merchant, account and URL text in HTML", () => {
    const { html, text } = renderEmail(
      report({
        categories: [{ name: '<img src=x onerror="bad()"> & food', balance: 1 }],
        cards: [{ name: "<Card>", balance: -1 }],
        budgetUrl: 'https://budget.test/?a=1&b="two"',
        uncategorized: [
          { date: "2026-09-09", amount: -1, payee: "<script>bad()</script>", account: "<Account>" },
        ],
      }),
    );
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;Card&gt;");
    expect(html).toContain("&lt;Account&gt;");
    expect(html).toContain("&amp;b=&quot;two&quot;");
    expect(text).toContain('<img src=x onerror="bad()"> & food: $0.01 left');
  });

  it.each([
    0, 1000,
  ])("handles zero debt or a card credit without a misleading coverage bar (%s)", (balance) => {
    const { html, text } = renderEmail(report({ cards: [{ name: "Card", balance }] }));
    for (const body of [text, html]) {
      expect(body).toContain("No card debt to cover");
      expect(body).not.toContain("NaN");
      expect(body).not.toContain("Infinity");
      expect(body).not.toContain("% of the full card balance");
    }
    if (balance > 0) expect(text).toContain("Card: $10.00 credit");
  });

  it("shows each card and does not offset debt with another card's credit", () => {
    const { text } = renderEmail(
      report({
        checking: 5000,
        cards: [
          { name: "Owed", balance: -10000 },
          { name: "Credit", balance: 2500 },
        ],
      }),
    );
    expect(text).toContain("Owed: $100.00 owed");
    expect(text).toContain("Credit: $25.00 credit");
    expect(text).toContain("$50.00");
    expect(text).toContain("Shortfall");
  });

  it("shows drift with its actual baseline date without claiming overspending caused it", () => {
    const { text, html } = renderEmail(
      report({
        baseline: { date: "2026-09-09", cards: { Discover: -252056 } },
        findings: [{ check: "drift", summary: "old wording", detail: "old detail" }],
      }),
    );
    for (const body of [text, html]) {
      expect(body).toContain("Discover");
      expect(body).toContain("$2,894.03");
      expect(body).toContain("September 9, 2026");
      expect(body).toContain("$2,520.56");
      expect(body).not.toContain("last month");
      expect(body).not.toContain("outrunning");
    }
  });

  it("keeps savings and scheduled-payment findings in both formats", () => {
    const findings = [
      {
        check: "raid",
        total: 7500,
        transactions: [{ date: "2026-09-01", amount: 7500, payee: "Savings transfer" }],
      },
      {
        check: "schedule",
        comparisons: [
          { label: "Furniture", date: "2026-09-01", expected: 20000, recorded: 11900, difference: -8100 },
        ],
      },
    ];
    const { text, html } = renderEmail(report({ findings }));
    for (const body of [text, html]) {
      expect(body).toContain("Savings transactions to review");
      expect(body).toContain("Payment differs from schedule");
      for (const value of [
        "Savings transfer",
        "$75.00",
        "Furniture",
        "$119.00",
        "$200.00",
        "$81.00 less",
        "September 1, 2026",
      ])
        expect(body).toContain(value);
    }
  });
});

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
