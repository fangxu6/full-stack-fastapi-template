import { spawn } from "node:child_process"
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"
import type { FullConfig } from "@playwright/test"

const root = path.dirname(fileURLToPath(import.meta.url))
const statePath = path.join(root, "../playwright/.mailbox-state.json")

export default async function globalSetup(_config: FullConfig) {
  if (
    process.env.E2E_MAILBOX_EXTERNAL === "true" &&
    process.env.MAILCATCHER_HOST
  ) {
    return
  }
  const bun = process.env.BUN_BINARY ?? "bun"
  const serverPath = path.join(root, "utils/mailbox.ts")
  const child = spawn(bun, [serverPath], {
    stdio: ["ignore", "pipe", "inherit"],
  })
  const line = await new Promise<string>((resolve, reject) => {
    let output = ""
    const timer = setTimeout(
      () => reject(new Error("Timed out starting E2E mailbox")),
      5000,
    )
    child.stdout?.on("data", (chunk: Buffer) => {
      output += chunk.toString()
      const newline = output.indexOf("\n")
      if (newline >= 0) {
        clearTimeout(timer)
        resolve(output.slice(0, newline))
      }
    })
    child.once("error", (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.once("exit", (code) => {
      if (code !== null && code !== 0) {
        clearTimeout(timer)
        reject(new Error(`E2E mailbox exited during startup (${code})`))
      }
    })
  }).catch(async (error) => {
    child.kill()
    throw error
  })
  const ports = JSON.parse(line) as { httpPort: number; smtpPort: number }
  process.env.MAILCATCHER_HOST = `http://127.0.0.1:${ports.httpPort}`
  process.env.E2E_SMTP_PORT = String(ports.smtpPort)
  await mkdir(path.dirname(statePath), { recursive: true })
  await writeFile(
    statePath,
    JSON.stringify({ pid: child.pid, ...ports }),
    "utf8",
  )
}

export async function stopMailbox() {
  let state: { pid?: number } | undefined
  try {
    state = JSON.parse(await readFile(statePath, "utf8"))
  } catch {
    return
  }
  if (!state) return
  if (state.pid) {
    try {
      process.kill(state.pid)
    } catch {
      // The process may already have exited after a startup failure.
    }
  }
  await unlink(statePath).catch(() => undefined)
}
