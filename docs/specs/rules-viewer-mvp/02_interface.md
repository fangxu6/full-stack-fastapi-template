# Interface Spec

## Overview
- Auth method: 复用现有 Bearer token 登录态，所有已登录用户可访问。
- Idempotency rules: 两个接口均为只读 `GET`，重复调用应返回稳定结果。
- Error response format: 沿用 FastAPI 默认错误格式，主要通过 `detail` 描述失败原因。

## Endpoint
- `GET /api/v1/docs/rules`
- 读取当前仓库 `docs/rules/*.md` 的规则列表。

- `GET /api/v1/docs/rules/{slug}`
- 根据规则 slug 读取单篇规则正文。

## Request
- `GET /api/v1/docs/rules`
  - 无请求体。
- `GET /api/v1/docs/rules/{slug}`
  - `slug: string`
  - 必填。
  - 必须命中后端白名单映射，不接受任意文件路径。

## Response
- `GET /api/v1/docs/rules`
  - `data: RuleDocumentSummary[]`
  - `count: number`
- `RuleDocumentSummary`
  - `slug: string`
  - `title: string`
  - `path: string`

- `GET /api/v1/docs/rules/{slug}`
  - `slug: string`
  - `title: string`
  - `path: string`
  - `content: string`

## Error Codes
- `401`: 未登录或 token 无效。
- `404`: slug 不存在，或对应规则文件不可用。
- `500`: 白名单目录不可读等非预期服务端错误。

## Examples
- Success example: `GET /api/v1/docs/rules`
```json
{
  "data": [
    {
      "slug": "前端开发规范",
      "title": "前端开发规范",
      "path": "docs/rules/前端开发规范.md"
    }
  ],
  "count": 1
}
```

- Success example: `GET /api/v1/docs/rules/前端开发规范`
```json
{
  "slug": "前端开发规范",
  "title": "前端开发规范",
  "path": "docs/rules/前端开发规范.md",
  "content": "# 前端开发规范\n..."
}
```

- Failure example:
```json
{
  "detail": "Rule document not found"
}
```

## Notes
- slug 由后端从白名单文件名稳定生成，前端只消费接口返回的 slug，不自行推导磁盘路径。
- 当前只暴露 `docs/rules/*.md`，后续扩展到其他 `docs/**` 时应新增独立白名单与接口，而不是放宽本接口范围。
