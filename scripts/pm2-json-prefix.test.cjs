const assert = require("node:assert/strict")
const { spawnSync } = require("node:child_process")
const test = require("node:test")
const path = require("node:path")

const wrapperPath = path.join(__dirname, "pm2-json-prefix.cjs")

test("formats the first seven JSON values before the original line", () => {
  const line = JSON.stringify({
    timestamp: "2026-08-05T00:00:00Z",
    severity: "ERROR",
    source: "app.jobs.Report.run",
    line: 123,
    event_name: "task.failed",
    environment: "local",
    schema_version: 1,
    request_id: "request-id",
  })

  assert.equal(
    require("./pm2-json-prefix.cjs").formatJsonLine(line),
    `2026-08-05T00:00:00Z | ERROR | app.jobs.Report.run | 123 | task.failed | local | 1 | ${line}`,
  )
})

test("passes non-JSON and short JSON lines through unchanged", () => {
  const { formatJsonLine } = require("./pm2-json-prefix.cjs")

  assert.equal(formatJsonLine("warning: worker unavailable"), "warning: worker unavailable")
  assert.equal(formatJsonLine('{"severity":"ERROR"}'), '{"severity":"ERROR"}')
})

test("forwards stderr and the child exit code", () => {
  const result = spawnSync(
    process.execPath,
    [
      wrapperPath,
      "--",
      process.execPath,
      "-e",
      'process.stderr.write("child error\\n"); process.exit(7)',
    ],
    { encoding: "utf8" },
  )

  assert.equal(result.status, 7)
  assert.equal(result.stderr, "child error\n")
})
