import { readFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"
import ts from "typescript"

const COMPONENT_PROPERTIES = new Set([
  "component",
  "errorComponent",
  "notFoundComponent",
])
const ROOT_ROUTE_SUFFIX = "frontend/src/routes/__root.tsx"

function isRootRoute(filePath) {
  return filePath.replaceAll("\\", "/").endsWith(ROOT_ROUTE_SUFFIX)
}

function isPascalCaseIdentifier(node) {
  return ts.isIdentifier(node) && /^[A-Z]/.test(node.text)
}

function isInlineFunction(node) {
  return ts.isArrowFunction(node) || ts.isFunctionExpression(node)
}

function containsInlineFunction(node) {
  if (isInlineFunction(node)) return true
  if (ts.isCallExpression(node)) {
    return node.arguments.some(containsInlineFunction)
  }
  return false
}

function propertyName(node) {
  if (ts.isIdentifier(node.name) || ts.isStringLiteral(node.name)) {
    return node.name.text
  }
  return undefined
}

export function checkThinRouteSource(filePath, sourceText) {
  if (isRootRoute(filePath)) return []

  const sourceFile = ts.createSourceFile(
    filePath,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  )
  const violations = []

  function visit(node) {
    if (ts.isFunctionDeclaration(node) && isPascalCaseIdentifier(node.name)) {
      violations.push(
        `local component declaration ${node.name.text} is not allowed in a route entry`,
      )
    }
    if (ts.isVariableDeclaration(node)) {
      const declaration = node
      if (
        isPascalCaseIdentifier(declaration.name) &&
        declaration.name.text !== "Route" &&
        declaration.initializer &&
        containsInlineFunction(declaration.initializer)
      ) {
        violations.push(
          `local component declaration ${declaration.name.text} is not allowed in a route entry`,
        )
      }
    }
    if (
      ts.isPropertyAssignment(node) &&
      COMPONENT_PROPERTIES.has(propertyName(node)) &&
      containsInlineFunction(node.initializer)
    ) {
      violations.push("inline component callback is not allowed in a route entry")
    }
    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return violations
}

export async function checkThinRouteFiles(filePaths) {
  return Promise.all(
    filePaths.map(async (filePath) => ({
      filePath,
      violations: checkThinRouteSource(filePath, await readFile(filePath, "utf8")),
    })),
  )
}

async function main() {
  const filePaths = process.argv.slice(2)
  if (filePaths.length === 0) {
    throw new Error("Expected one or more route files")
  }

  const results = await checkThinRouteFiles(filePaths.map((filePath) => path.resolve(filePath)))
  console.log(JSON.stringify(results))
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}
