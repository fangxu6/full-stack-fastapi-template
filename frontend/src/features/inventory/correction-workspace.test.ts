import { describe, expect, test } from "bun:test"

import {
  correctionQueryKeys,
  getCorrectionAccess,
  getCorrectionTabs,
  resolveCorrectionTab,
} from "./correction-workspace"

describe("inventory correction workspace policy", () => {
  test("derives available tabs from permissions", () => {
    const access = getCorrectionAccess([
      "inventory.corrections.request",
      "inventory.corrections.recover",
    ])

    expect(getCorrectionTabs(access)).toEqual([
      { key: "mine", label: "我的申请" },
      { key: "recovery", label: "失败恢复" },
    ])
    expect(resolveCorrectionTab("review", access)).toBe("mine")
  })

  test("keeps a requested tab when its permission remains available", () => {
    const access = getCorrectionAccess([
      "inventory.corrections.review",
      "inventory.corrections.recover",
    ])

    expect(resolveCorrectionTab("recovery", access)).toBe("recovery")
  })

  test("shares stable list and detail query-key roots", () => {
    expect(correctionQueryKeys.list("mine", { limit: 20, skip: 0 })).toEqual([
      "inventory",
      "corrections",
      "mine",
      { limit: 20, skip: 0 },
    ])
    expect(correctionQueryKeys.detailRoot()).toEqual([
      "inventory",
      "corrections",
      "detail",
    ])
  })
})
