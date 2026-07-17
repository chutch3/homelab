// Boundary: snapshot persistence. One JSON file on the state volume.
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export async function loadState(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    return { snapshots: [] };
  }
}

export async function saveState(path, state) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(state, null, 2));
}
