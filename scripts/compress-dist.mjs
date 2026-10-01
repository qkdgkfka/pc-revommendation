import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { gzipSync, constants } from "node:zlib";
async function compress(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await compress(path);
    else if (/\.(?:html|css|js|json|svg|txt|xml|webmanifest)$/.test(entry.name))
      await writeFile(
        path + ".gz",
        gzipSync(await readFile(path), { level: constants.Z_BEST_COMPRESSION }),
      );
  }
}
await compress(new URL("../dist/", import.meta.url).pathname);
