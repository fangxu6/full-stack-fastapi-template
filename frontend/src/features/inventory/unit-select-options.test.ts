import { describe, expect, test } from "bun:test"

import { buildUnitOptionsRequest } from "./unit-select-options"

describe("buildUnitOptionsRequest", () => {
  test("loads the first 20 units when a document filter has no search term", () => {
    expect(
      buildUnitOptionsRequest({ isActive: undefined, searchTerm: "   " }),
    ).toEqual({ limit: 20, skip: 0 })
  })

  test("uses the trimmed search term and active-only scope for document editing", () => {
    expect(
      buildUnitOptionsRequest({ isActive: true, searchTerm: "  星纺  " }),
    ).toEqual({ isActive: true, limit: 20, name: "星纺", skip: 0 })
  })
})
