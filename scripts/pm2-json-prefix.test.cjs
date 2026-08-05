const assert = require("node:assert/strict")
const { spawnSync } = require("node:child_process")
const test = require("node:test")
const path = require("node:path")

const wrapperPath = path.join(__dirname, "pm2-json-prefix.cjs")

test("formats a compact display line without repeating metadata", () => {
  const line = JSON.stringify({
    timestamp: "2026-08-05T00:00:00.123456Z",
    severity: "WARNING",
    source: "app.jobs.Report.run",
    line: 123,
    event_name: "task.failed",
    environment: "local",
    schema_version: 1,
    request_id: "request-id",
  })

  assert.equal(
    require("./pm2-json-prefix.cjs").formatJsonLine(line),
    '2026-08-05 00:00:00 | WARN | app.jobs.Report.run:123 | task.failed | {"request_id":"request-id"}',
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
