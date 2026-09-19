import { cardCoverage, cardGrowth, fmt } from "./money.js";

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
}

function dateLabel(date) {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function cardBalance(balance) {
  return balance === 0 ? fmt(0) : `${fmt(Math.abs(balance))} ${balance > 0 ? "credit" : "owed"}`;
}

const colors = {
  surface: "#243b53",
  text: "#d9e2ec",
  raised: "#334e68",
  border: "#486581",
  muted: "#9fb3c8",
  danger: "#ff9b9b",
  accent: "#9446ed",
  frame: "#102a43",
};

// Colors follow Actual's default dark theme (style/themes/dark.ts and style/palette.ts).
// Pure presentation: the same values and wording feed both email formats.
export function renderEmail({
  date,
  categories,
  checking,
  cards,
  baseline,
  findings,
  uncategorized,
  budgetUrl,
  driftThresholdCents,
}) {
  const month = new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "long" });
  const subject = `${month} budget · ${dateLabel(date)}`;
  const categoryRows = [...categories]
    .sort((a, b) => a.name.localeCompare(b.name, "en"))
    .map(({ name, balance, spent }) => {
      const row = {
        name,
        amount: `${fmt(Math.abs(balance))} ${balance < 0 ? "over" : "left"}`,
        over: balance < 0,
        progress: null,
      };
      if (!Number.isFinite(spent)) return row;
      const available = balance - spent;
      const used = Math.max(0, -spent);
      const percentage = available > 0 ? Math.round((used / available) * 100) : null;
      row.progress = {
        percent: percentage === null ? (used > 0 ? 100 : 0) : Math.min(100, percentage),
        percentageLabel: percentage === null ? "No funds available" : `${percentage}% spent`,
        label:
          spent > 0
            ? `${fmt(spent)} net inflow · ${fmt(available)} available before activity`
            : available > 0
              ? `${fmt(used)} spent of ${fmt(available)} available`
              : `${fmt(used)} spent · No funds available`,
      };
      return row;
    });
  const spending = -uncategorized.reduce((sum, t) => sum + Math.min(t.amount, 0), 0);
  const inflows = uncategorized.reduce((sum, t) => sum + Math.max(t.amount, 0), 0);
  const notice = uncategorized.length
    ? `${uncategorized.length} ${uncategorized.length === 1 ? "transaction needs a category" : "transactions need categories"} (past 14 days): ${fmt(spending)} spending${inflows ? ` and ${fmt(inflows)} inflows` : ""}. Category balances may change.`
    : "";
  const { owed, headroom, percent: coverage } = cardCoverage(checking, cards);
  const cashRows = [
    ["Checking", fmt(checking)],
    ...cards.map((card) => [card.name, cardBalance(card.balance)]),
  ];
  const coverageLabel =
    coverage === null
      ? "No card debt to cover."
      : coverage === 100 && headroom < 0
        ? "Less than 100% covered"
        : `${coverage}% covered`;
  const cashNote =
    "Uses current balances; excludes upcoming income and other cash. Not a payment-due calculation.";
  const accountSections = [
    {
      title: "Account balances",
      purpose: "Current checking and credit-card balances.",
      headers: ["Account", "Balance"],
      rows: cashRows,
    },
    {
      title: "Can checking cover the cards?",
      purpose: "Compare checking with the total owed on cards.",
      headers: ["Comparison", "Amount"],
      rows: [
        ["Checking", fmt(checking)],
        ["Total card debt", fmt(owed)],
        [headroom < 0 ? "Shortfall" : "Remaining after covering cards", fmt(Math.abs(headroom))],
      ],
      total: true,
      coverage: true,
      note: cashNote,
    },
  ];
  const changes =
    baseline && findings.some((finding) => finding.check === "drift")
      ? cardGrowth(cards, baseline.cards, driftThresholdCents).map(
          (card) =>
            `${card.name}'s balance increased by ${fmt(card.growth)} since ${dateLabel(baseline.date)} (earlier balance: ${cardBalance(card.then)}; current balance: ${cardBalance(card.now)}).`,
        )
      : [];
  const changeNote = changes.length ? "Purchases and payment timing can both affect this change." : "";
  const alertSections = findings.flatMap((finding) => {
    if (finding.check === "duplicates")
      return finding.pairs.map(({ pending, posted }) => ({
        title: "Possible duplicate charges",
        purpose: `${pending.account} · Check whether the posted charge replaced the pending entry.`,
        headers: ["Status", "Date", "Merchant", "Amount"],
        rows: [
          ["Pending", dateLabel(pending.date), pending.merchant, fmt(Math.abs(pending.amount))],
          ["Posted", dateLabel(posted.date), posted.merchant, fmt(Math.abs(posted.amount))],
        ],
      }));
    if (finding.check === "raid")
      return [
        {
          title: "Savings transactions to review",
          purpose: "Confirm these transactions belong in the savings category.",
          headers: ["Date", "Transaction", "Inflow"],
          rows: [
            ...finding.transactions.map((t) => [dateLabel(t.date), t.payee, fmt(t.amount)]),
            ["", "Total", fmt(finding.total)],
          ],
          total: true,
        },
      ];
    if (finding.check === "schedule")
      return finding.comparisons.map((comparison) => ({
        title: "Payment differs from schedule",
        purpose: `${comparison.label} · ${dateLabel(comparison.date)}`,
        headers: ["Comparison", "Amount"],
        rows: [
          ["Scheduled", fmt(comparison.expected)],
          ["Recorded", fmt(comparison.recorded)],
          [
            "Difference",
            `${fmt(Math.abs(comparison.difference))} ${comparison.difference > 0 ? "more" : "less"}`,
          ],
        ],
        total: true,
        note: "Check whether the transaction or scheduled amount needs correcting.",
      }));
    return [];
  });
  const sectionText = (section) =>
    [
      section.title,
      section.purpose,
      section.coverage ? coverageLabel : "",
      ...section.rows.map((row) => row.filter((value) => value !== "").join(": ")),
      section.note || "",
    ]
      .filter(Boolean)
      .join("\n");
  const transactionRows = uncategorized.map((t) => [
    dateLabel(t.date),
    t.payee,
    t.account,
    `${fmt(Math.abs(t.amount))} ${t.amount > 0 ? "received" : "spent"}`,
  ]);
  const transactionTitle = `Transactions needing categories · ${transactionRows.length}`;
  const transactionInstruction = "Assign a category to these transactions in Actual.";
  const footer = "Based on the latest available bank data.";
  const text = [
    subject,
    notice ? `Transactions to categorize\n${notice}` : "",
    `Open budget: ${budgetUrl}`,
    `Left to spend\n${categoryRows.length ? categoryRows.map(({ name, amount, progress }) => `${name}: ${amount}${progress ? `\n${progress.label}` : ""}`).join("\n") : "No visible spending categories."}`,
    ...accountSections.map(sectionText),
    ...changes,
    changeNote,
    ...alertSections.map(sectionText),
    transactionRows.length
      ? `${transactionTitle}\n${transactionInstruction}\n${transactionRows.map((row) => row.join(" · ")).join("\n")}`
      : "",
    footer,
  ]
    .filter(Boolean)
    .join("\n\n");
  const table = (
    headers,
    bodyRows,
    label = "",
    total = false,
  ) => `<table ${label ? `aria-label="${escapeHtml(label)}"` : ""} style="width:100%;border-collapse:collapse;font-size:14px;background:${colors.surface};color:${colors.text};">
    <thead><tr style="background:${colors.raised};">${headers.map((header) => `<th scope="col" style="padding:9px 6px;text-align:left;">${escapeHtml(header)}</th>`).join("")}</tr></thead>
    <tbody>${bodyRows.map((row, rowIndex) => `<tr style="${total && rowIndex === bodyRows.length - 1 ? `font-weight:bold;background:${colors.raised};` : ""}">${row.map((cell, i) => `<td style="padding:10px 6px;border-bottom:1px solid ${colors.border};overflow-wrap:anywhere;${i === row.length - 1 ? "text-align:right;overflow-wrap:normal;" : ""}">${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  const paragraph = (value) => `<p style="margin:8px 0;font-size:14px;">${escapeHtml(value)}</p>`;
  const heading = (value) => `<h2 style="font-size:19px;margin:20px 0 10px;">${escapeHtml(value)}</h2>`;
  const bar = (percent, label, color) =>
    `<table role="presentation" aria-label="${escapeHtml(label)}" width="100%" cellpadding="0" cellspacing="0" style="width:100%;table-layout:fixed;border-collapse:collapse;margin:8px 0;"><tr>${percent > 0 ? `<td width="${percent}%" height="6" bgcolor="${color}" style="height:6px;font-size:0;line-height:0;background:${color};">&nbsp;</td>` : ""}${percent < 100 ? `<td width="${100 - percent}%" height="6" bgcolor=colors.raised style="height:6px;font-size:0;line-height:0;background:${colors.raised};">&nbsp;</td>` : ""}</tr></table>`;
  const categoryTable = `<table aria-label="Category balances" style="width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>${categoryRows
    .map(({ name, amount, over, progress: detail }) => {
      const color = over ? colors.danger : colors.text;
      return `<tr><td style="padding:12px 0;border-bottom:1px solid ${colors.border};overflow-wrap:anywhere;"><table role="presentation" style="width:100%;table-layout:fixed;border-collapse:collapse;"><tr><td style="font-size:15px;font-weight:bold;width:53%;vertical-align:top;">${escapeHtml(name)}</td><td style="font-size:17px;font-weight:bold;text-align:right;color:${color};vertical-align:top;">${escapeHtml(amount)}</td></tr></table>${detail ? `${bar(detail.percent, `${name}: ${detail.percentageLabel}`, over ? colors.danger : colors.accent)}<div style="font-size:12px;color:${colors.muted};">${escapeHtml(detail.label)}</div>` : ""}</td></tr>`;
    })
    .join("")}</tbody></table>`;
  const action = `<p style="margin:16px 0;"><a href="${escapeHtml(budgetUrl)}" style="display:inline-block;padding:10px 18px;background:${colors.accent};color:#fff;text-decoration:none;font-size:14px;font-weight:bold;border-radius:4px;">Open budget</a></p>`;
  const sectionHtml = (section) => `${heading(section.title)}${paragraph(section.purpose)}
    ${section.coverage ? `${coverage === null ? "" : bar(coverage, coverageLabel, "#65d6ad")}${paragraph(coverageLabel)}` : ""}
    ${table(section.headers, section.rows, section.title, section.total)}
    ${section.note ? `<p style="margin:8px 0;font-size:12px;color:${colors.muted};">${escapeHtml(section.note)}</p>` : ""}`;
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${escapeHtml(subject)}</title></head>
<body style="margin:0;padding:16px 10px;background:#080811;color:${colors.text};font-family:Arial,Helvetica,sans-serif;line-height:1.5;">
<table role="presentation" style="width:100%;max-width:620px;margin:0 auto;border-spacing:0;">
<tr><td style="background:${colors.frame};padding:20px;border-radius:12px 12px 0 0;color:#fff;"><div style="font-size:11px;letter-spacing:2px;">BEHOLDER</div><h1 style="font-size:25px;line-height:1.3;margin:6px 0 0;">${escapeHtml(subject)}</h1></td></tr>
<tr><td style="background:${colors.surface};padding:20px;color:${colors.text};">
${notice ? `<div style="padding:12px 14px;background:#87540d;border-left:3px solid #e6bb20;border-radius:4px;color:#f5e35d;"><strong>Transactions to categorize</strong>${paragraph(notice)}</div>` : ""}
${action}
${heading("Left to spend")}${categoryRows.length ? categoryTable : paragraph("No visible spending categories.")}
${accountSections.map(sectionHtml).join("")}
${changes.map(paragraph).join("")}${changeNote ? paragraph(changeNote) : ""}
${alertSections.map(sectionHtml).join("")}
${transactionRows.length ? `${heading(transactionTitle)}${paragraph(transactionInstruction)}${table(["Date", "Transaction", "Account", "Amount"], transactionRows)}` : ""}
</td></tr><tr><td style="background:${colors.frame};padding:16px 20px;border-radius:0 0 12px 12px;font-size:12px;color:${colors.muted};">${escapeHtml(footer)}</td></tr></table></body></html>`;
  return { subject, text, html };
}

// Owned transport seam: request data in, HTTP status and raw body out.
async function postalRequest({ url, apiKey, payload }) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "X-Server-API-Key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { ok: response.ok, status: response.status, body: await response.text() };
}

// Failure reports may supply plain text only.
export async function sendMail(
  { postalUrl, postalApiKey, from, to, subject, body, html },
  request = postalRequest,
) {
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
