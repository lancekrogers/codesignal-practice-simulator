import { randomUUID } from "node:crypto";
import { rm, rename, writeFile } from "node:fs/promises";

export async function writeClock(path, value, options = {}) {
  const nextId = options.randomUUID || randomUUID;
  const write = options.writeFile || writeFile;
  const move = options.rename || rename;
  const remove = options.rm || rm;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const temporary = `${path}.${nextId()}.tmp`;
    let ownsTemporary = false;
    try {
      await write(temporary, value, { encoding: "utf8", flag: "wx" });
      ownsTemporary = true;
      await move(temporary, path);
      return;
    } catch (error) {
      if (ownsTemporary) {
        try {
          await remove(temporary, { force: true });
        } catch {
          // Preserve the operation error if cleanup itself fails.
        }
      }
      if (error?.code !== "EEXIST") throw error;
    }
  }
  throw new Error("could not allocate a unique clock temp file");
}
