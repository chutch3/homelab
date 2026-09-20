import { readFile } from "node:fs/promises";
import Handlebars from "handlebars";
import * as helpers from "./helpers.js";

// Packaged files and Handlebars stay behind the application's loadTemplates seam.
export async function loadEmailTemplates() {
  const partialNames = [
    "layout",
    "table",
    "progress",
    "subject",
    "notice",
    "card-balance",
    "budget-summary",
    "spending-label",
    "spending-percent",
    "drift",
  ];
  const names = ["report.html", "report.text", ...partialNames.map((name) => `partials/${name}`)];
  const [html, text, ...partials] = await Promise.all(
    names.map((name) => readFile(new URL(`./templates/${name}.hbs`, import.meta.url), "utf8")),
  );
  // Separate compiled partials preserve HTML escaping regardless of render order.
  const htmlEngine = Handlebars.create();
  const textEngine = Handlebars.create();
  for (const [engine, noEscape] of [
    [htmlEngine, false],
    [textEngine, true],
  ]) {
    engine.registerHelper({ ...helpers });
    partialNames.forEach((name, index) => {
      engine.registerPartial(name, engine.compile(partials[index].trim(), { strict: true, noEscape }));
    });
  }
  return {
    renderSubject: textEngine.partials.subject,
    renderText: textEngine.compile(text, { strict: true, noEscape: true }),
    renderHtml: htmlEngine.compile(html, { strict: true }),
  };
}
