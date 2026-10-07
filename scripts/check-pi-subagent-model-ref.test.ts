import { describe, expect, test } from "bun:test"

import { buildPiArgs, resolveRunCfg } from "../.pi/extensions/trellis/index"

// The pi extension hands the sub-agent model to a child CLI as
// `--model <ref>:<thinking>`. A bare ref (no provider prefix) there makes pi's
// auth-blind fuzzy matcher pick an arbitrary provider — the reported failure was
// "gpt-5:high" resolving to amazon-bedrock/us.openai.gpt-5.6-terra, which has no
// credentials. See .trellis/tasks/10-07-pi-subagent-model-ref/prd.md.

const SESSION = "cctq-codex/gpt-6-luna"
const TOOLS = { tools: ["read"] }

const modelArg = (
  input: Record<string, unknown>,
  agentCfg: Record<string, unknown> = TOOLS,
  sessionModel: string | undefined = SESSION,
) => {
  const args = buildPiArgs(
    resolveRunCfg(input as never, agentCfg as never, "high", sessionModel),
  )
  const at = args.indexOf("--model")
  return at < 0 ? undefined : args[at + 1]
}

const call = (model?: string) => ({ agent: "trellis-implement", prompt: "x", ...(model ? { model } : {}) })

describe("subagent model refs", () => {
  test("qualifies a bare tool-call model with the session provider", () => {
    expect(modelArg(call("gpt-5"))).toBe("cctq-codex/gpt-5:high")
  })

  test("keeps an explicitly provider-qualified model untouched", () => {
    expect(modelArg(call("rightapi-codex/gpt-6-sol"))).toBe("rightapi-codex/gpt-6-sol:high")
  })

  test("uses the agent frontmatter pin when the tool call passes no model", () => {
    expect(modelArg(call(), { ...TOOLS, model: "openai/gpt-5.6-terra" })).toBe(
      "openai/gpt-5.6-terra:high",
    )
  })

  test("tool-call model overrides the frontmatter pin, still qualified", () => {
    expect(modelArg(call("gpt-5.6-terra"), { ...TOOLS, model: "openai/gpt-6-sol" })).toBe(
      "cctq-codex/gpt-5.6-terra:high",
    )
  })

  test("moves a thinking suffix out of the model string", () => {
    expect(modelArg(call("gpt-5:max"))).toBe("cctq-codex/gpt-5:max")
  })

  test("refuses a bare model when the session model is unknown", () => {
    expect(() => resolveRunCfg(call("gpt-5") as never, TOOLS as never, undefined, undefined)).toThrow(
      /no provider prefix/,
    )
  })
})
