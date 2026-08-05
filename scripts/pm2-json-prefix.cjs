const { spawn } = require("node:child_process")
const readline = require("node:readline")

const PREFIX_FIELD_COUNT = 7

function formatValue(value) {
  if (typeof value === "string") return value
  if (value === null) return ""
  return JSON.stringify(value)
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

    const values = Object.values(payload).slice(0, PREFIX_FIELD_COUNT)
    if (values.length < PREFIX_FIELD_COUNT) return line

    return `${values.map(formatValue).join(" | ")} | ${line}`
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
