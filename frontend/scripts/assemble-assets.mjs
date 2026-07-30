import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

async function assemble(partsDirectory, destination) {
  const directory = join(root, partsDirectory);
  const names = (await readdir(directory))
    .filter((name) => name.endsWith(".txt"))
    .sort();
  if (!names.length) throw new Error(`No source parts found in ${partsDirectory}`);
  const content = (
    await Promise.all(names.map((name) => readFile(join(directory, name), "utf8")))
  ).join("");
  const output = join(root, destination);
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, content, "utf8");
  console.log(`assembled ${destination} from ${names.length} parts`);
}

await assemble("src/generated/dashboard-v2", "src/dashboard-v2.tsx");
await assemble("src/generated/app-v2", "src/app-v2.css");
