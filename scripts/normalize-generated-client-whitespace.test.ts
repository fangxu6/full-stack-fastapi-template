import { expect, test } from "bun:test"

import { stripTrailingWhitespace } from "./normalize-generated-client-whitespace.mjs"

test("strips trailing spaces and tabs while preserving line endings", () => {
  expect(
    stripTrailingWhitespace("first  \r\nsecond\t\nthird  "),
  ).toBe("first\r\nsecond\nthird")
})
