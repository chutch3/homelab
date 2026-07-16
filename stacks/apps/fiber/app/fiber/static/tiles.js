/* tiles.js — Throne Room tile-update logic. Loaded as a module that also exposes
   updateTile globally for the classic wall.js script, and unit-tested in isolation
   with vitest + jsdom. */

// Apply a fresh tile render. A straining tile is re-pushed every ~2s; replacing the
// whole node restarts its CSS animations (the tile's rise-in flash and the strainbar's
// sweep), which reads as flashing + a resetting progress bar. So when the status class
// is unchanged, sync only the live text in place and leave the node — and its running
// animations — intact. Replace the node only on an actual status transition. Returns
// true when the node was replaced (the caller should re-run layout).
export function updateTile(el, html) {
  const tmp = document.createElement("template");
  tmp.innerHTML = html.trim();
  const fresh = tmp.content.firstElementChild;
  if (!fresh) return false;
  if (el.className === fresh.className) {
    const oldLabel = el.querySelector("[data-strain]");
    const newLabel = fresh.querySelector("[data-strain]");
    if (oldLabel && newLabel) oldLabel.textContent = newLabel.textContent;
    const oldFoot = el.querySelectorAll(".foot span");
    const newFoot = fresh.querySelectorAll(".foot span");
    newFoot.forEach((n, i) => {
      if (oldFoot[i]) oldFoot[i].textContent = n.textContent;
    });
    return false;
  }
  el.replaceWith(fresh);
  return true;
}

// Expose as a global so the classic wall.js script (which can't import a module) can
// call it; harmless in the vitest/jsdom environment.
if (typeof window !== "undefined") window.updateTile = updateTile;
