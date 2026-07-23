import { describe, expect, test } from "bun:test"
import { readFile } from "node:fs/promises"

import { checkThinRouteSource } from "./check-thin-routes.mjs"

describe("checkThinRouteSource", () => {
  test("accepts a route that imports its page component", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/_layout/forbidden.tsx",
      [
        'import { createFileRoute } from "@tanstack/react-router"',
        'import { ForbiddenPage } from "@/app/router/ForbiddenPage"',
        "",
        'export const Route = createFileRoute("/_layout/forbidden")({',
        "  component: ForbiddenPage,",
        "})",
      ].join("\n"),
    )

    expect(violations).toEqual([])
  })

  test("rejects a local PascalCase component declaration", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/_layout/index.tsx",
      [
        'import { createFileRoute } from "@tanstack/react-router"',
        "",
        'export const Route = createFileRoute("/_layout/")({',
        "  component: Dashboard,",
        "})",
        "",
        "function Dashboard() {",
        "  return <div />",
        "}",
      ].join("\n"),
    )

    expect(violations).toEqual([
      "local component declaration Dashboard is not allowed in a route entry",
    ])
  })

  test("rejects an inline component callback", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/_layout/example.tsx",
      [
        'import { createFileRoute } from "@tanstack/react-router"',
        "",
        'export const Route = createFileRoute("/_layout/example")({',
        "  component: () => <div />",
        "})",
      ].join("\n"),
    )

    expect(violations).toEqual([
      "inline component callback is not allowed in a route entry",
    ])
  })

  test("rejects a PascalCase component wrapped by memo", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/_layout/example.tsx",
      [
        'import { memo } from "react"',
        "",
        "const ExamplePage = memo(() => <div />)",
      ].join("\n"),
    )

    expect(violations).toEqual([
      "local component declaration ExamplePage is not allowed in a route entry",
    ])
  })

  test("rejects a nested PascalCase component declaration", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/_layout/example.tsx",
      [
        "function createRoute() {",
        "  const ExamplePage = () => <div />",
        "  return ExamplePage",
        "}",
      ].join("\n"),
    )

    expect(violations).toEqual([
      "local component declaration ExamplePage is not allowed in a route entry",
    ])
  })

  test("allows the root Router shell callbacks", () => {
    const violations = checkThinRouteSource(
      "frontend/src/routes/__root.tsx",
      [
        'import { createRootRoute, Outlet } from "@tanstack/react-router"',
        "",
        "export const Route = createRootRoute({",
        "  component: () => <Outlet />",
        "})",
      ].join("\n"),
    )

    expect(violations).toEqual([])
  })

  test("accepts the dashboard route as a thin entry", async () => {
    const source = await readFile(
      "frontend/src/routes/_layout/index.tsx",
      "utf8",
    )

    expect(
      checkThinRouteSource("frontend/src/routes/_layout/index.tsx", source),
    ).toEqual([])
  })
})
