import { beforeEach, describe, expect, it } from "vitest";

import { updateTile } from "../../fiber/static/tiles.js";

// Minimal markup mirroring _tile.html — only the parts updateTile reads/writes:
// the status class, the [data-strain] live-progress label, and the .foot spans.
function strainingTile(progress, footRight = "running…") {
  const el = document.createElement("div");
  el.className = "tile s-straining";
  el.innerHTML = `
    <div class="mid"><div class="strainbar"><div class="f"></div>
      <div class="l" data-strain>${progress}</div></div></div>
    <div class="foot"><span>Straining</span><span>${footRight}</span></div>`;
  return el;
}

function cleanTileHtml() {
  return `<div class="tile s-clean">
    <div class="mid"><div class="k">last dump</div><b>1.2 MB</b></div>
    <div class="foot"><span>Clean</span><span>2m ago</span></div></div>`;
}

describe("updateTile", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("morphs live text in place, keeping the same node, when the status is unchanged", () => {
    const el = strainingTile("10 MB · 3s");
    document.body.append(el);

    const replaced = updateTile(el, strainingTile("20 MB · 6s").outerHTML);

    // The node is preserved (so its CSS animations keep running)...
    expect(document.body.firstElementChild).toBe(el);
    // ...and only the live progress text is updated.
    expect(el.querySelector("[data-strain]").textContent).toBe("20 MB · 6s");
    expect(replaced).toBe(false);
  });

  it("syncs the footer text in place as well", () => {
    const el = strainingTile("10 MB", "running…");
    document.body.append(el);

    updateTile(el, strainingTile("10 MB", "still running…").outerHTML);

    expect(el.querySelectorAll(".foot span")[1].textContent).toBe("still running…");
  });

  it("replaces the node on a status transition", () => {
    const el = strainingTile("10 MB");
    document.body.append(el);

    const replaced = updateTile(el, cleanTileHtml());

    expect(document.body.contains(el)).toBe(false);
    expect(document.body.firstElementChild.className).toBe("tile s-clean");
    expect(replaced).toBe(true);
  });

  it("is a no-op for blank html", () => {
    const el = strainingTile("10 MB");
    document.body.append(el);

    const replaced = updateTile(el, "   ");

    expect(document.body.firstElementChild).toBe(el);
    expect(replaced).toBe(false);
  });
});
