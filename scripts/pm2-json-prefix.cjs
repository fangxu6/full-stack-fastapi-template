const { spawn } = require("node:child_process")
const readline = require("node:readline")

const DISPLAY_FIELDS = new Set([
  "timestamp",
  "severity",
  "source",
  "line",
  "event_name",
])
const LEVEL_ALIASES = { WARNING: "WARN", CRITICAL: "FATAL" }

function formatSeverity(value) {
  return LEVEL_ALIASES[value] ?? value
}

function formatTimestamp(value) {
  if (typeof value !== "string") return value
  const match = value.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/)
  return match ? `${match[1]} ${match[2]}` : value
}

function formatJsonLine(line) {
  const trimmedLine = line.trim()
  if (!trimmedLine) return line

  try {
    const payload = JSON.parse(trimmedLine)
    if (
      payload === null ||
      typeof payload !== "object" ||
      Array.isArray(payload)
    ) {
      return line
    }

    const requiredFields = [
      payload.timestamp,
      payload.severity,
      payload.source,
      payload.line,
      payload.event_name,
    ]
    if (requiredFields.some((value) => value === undefined)) return line

    const source = `${payload.source}:${payload.line}`
    const details = Object.fromEntries(
      Object.entries(payload).filter(
        ([key]) =>
          !DISPLAY_FIELDS.has(key) &&
          key !== "environment" &&
          key !== "schema_version",
      ),
    )
    const fields = [
      formatTimestamp(payload.timestamp),
      formatSeverity(payload.severity),
      source,
      payload.event_name,
    ]
    if (Object.keys(details).length > 0) fields.push(JSON.stringify(details))

    return fields.join(" | ")
  } catch {
    return line
  }
}

function main(args = process.argv.slice(2)) {
  const separator = args.indexOf("--")
  const childArgs = separator === -1 ? args : args.slice(separator + 1)
  if (childArgs.length === 0) {
    console.error("Usage: pm2-json-prefix.cjs -- <command> [args...]")
    return 2
  }

  const [command, ...commandArgs] = childArgs
  const child = spawn(command, commandArgs, {
    cwd: process.cwd(),
    env: process.env,
    stdio: ["inherit", "pipe", "pipe"],
    windowsHide: true,
  })
  let childError = false

  const stdout = readline.createInterface({ input: child.stdout })
  stdout.on("line", (line) => {
    process.stdout.write(`${formatJsonLine(line)}\n`)
  })
  child.stderr.on("data", (chunk) => process.stderr.write(chunk))

  const forwardSignal = (signal) => {
    if (!child.killed) child.kill(signal)
  }
  process.on("SIGINT", () => forwardSignal("SIGINT"))
  process.on("SIGTERM", () => forwardSignal("SIGTERM"))

  child.on("error", (error) => {
    childError = true
    process.stderr.write(`pm2-json-prefix: ${error.message}\n`)
  })
  child.on("close", (code) => {
    process.exitCode = childError ? 1 : code ?? 1
  })
}

if (require.main === module) {
  const exitCode = main()
  if (typeof exitCode === "number") process.exitCode = exitCode
}

module.exports = { formatJsonLine, main }
