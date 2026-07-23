import { readdir, readFile, writeFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

export function stripTrailingWhitespace(content) {
  return content.replace(/[ \t]+(?=\r?\n|$)/g, "")
}

async function findTypeScriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const paths = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name)
      if (entry.isDirectory()) return findTypeScriptFiles(entryPath)
      return /\.(?:cts|mts|ts|tsx)$/.test(entry.name) ? [entryPath] : []
    }),
  )
  return paths.flat()
}

export async function normalizeGeneratedClientWhitespace(directory) {
  const files = await findTypeScriptFiles(directory)
  let normalizedFiles = 0

  for (const file of files) {
    const content = await readFile(file, "utf8")
    const normalized = stripTrailingWhitespace(content)
    if (normalized !== content) {
      await writeFile(file, normalized, "utf8")
      normalizedFiles += 1
    }
  }

  return normalizedFiles
}

async function main() {
  const targetDirectory = process.argv[2]
  if (!targetDirectory) {
    throw new Error("Expected the generated client directory as the first argument")
  }

  const normalizedFiles = await normalizeGeneratedClientWhitespace(targetDirectory)
  console.log(`Normalized trailing whitespace in ${normalizedFiles} generated files.`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}
