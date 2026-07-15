# Pagination Contract

> Executable contract for paginated frontend lists. Use it when a page loads
> one slice of a larger server-side result set or introduces Ant Design
> `Table` / `Pagination` pagination.

## Scenario: Ant Design Server-Side Pagination

### 1. Scope / Trigger

Use this contract for data-dense management lists under `features/*` or
`platform/*` when the backend returns a page slice and a total count. New
server-backed management lists default to Ant Design 6 `Table` pagination;
do not fetch an arbitrary large result set and paginate it in the browser.

The current `items` API is the repository reference for offset pagination:

- `ItemsService.readItems({ skip, limit })` sends `skip` and `limit`.
- `ItemsPublic` returns `{ data, count }`.
- Ant Design pages are one-based; the existing API offset is zero-based.
- The `items` route validates `skip >= 0` and `1 <= limit <= 100` before
  database access, and its page query uses `created_at DESC, id DESC` so equal
  timestamps cannot make adjacent pages nondeterministic.

The existing `shared/components/table/DataTable.tsx` is client-side pagination
over an already-loaded array. It remains suitable only for small, bounded data
that is intentionally loaded in full. Do not compose its TanStack table
pagination with a server-paginated API response.

Official reference: [Ant Design Pagination](https://ant.design/components/pagination-cn).

### 2. Signatures

Keep page state one-based in the UI and derive the API offset at the request
boundary:

```ts
type PageState = {
  page: number // Ant Design current; always >= 1
  pageSize: number
}

type OffsetPage<T> = {
  data: T[]
  count: number // total matching records, not data.length
}

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

function toOffset({ page, pageSize }: PageState) {
  return (page - 1) * pageSize
}
```

For the current generated Items client, the request mapping is:

```ts
ItemsService.readItems({
  skip: toOffset({ page, pageSize }),
  limit: pageSize,
})
```

For a new endpoint, preserve the same externally observable contract or make a
deliberate cross-layer decision. A server-paginated response must carry both
the current page slice and the total matching count; a list array alone cannot
drive an accurate numbered pager.

### 3. Frontend and Query Contracts

- Use controlled `current`, `pageSize`, and `total` values. Do not mix
  `defaultCurrent` / `defaultPageSize` with component state.
- Pass `total: response.count`, never `response.data.length`.
- Set `showSizeChanger` explicitly. Ant Design 6 can make it visible when the
  total crosses `totalBoundaryShowSizeChanger` (default `50`); product behavior
  must not change just because the record count changes.
- `Pagination.onChange(page, pageSize)` is called for both page and size
  changes. Use it as the single fetch-state update path; do not trigger a
  second fetch from both `onChange` and `onShowSizeChange`.
- When the page size changes, set the UI page to `1` before requesting data.
  Ant Design preserves (or clamps) the current page by default, so this reset
  must be explicit for predictable list navigation.
- Reset the page to `1` when committed search filters, filter values, or sort
  order change. Include each committed server input in the React Query key.
- Use the generated OpenAPI service and generated response type. Do not
  hand-write a parallel pagination DTO in the page.
- Keep local view state in the page or a focused page-local hook. Only extract
  a shared pagination helper after multiple domains need the same
  domain-neutral composition.

```tsx
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { Table, type TableProps } from "antd"

import { ItemsService, type ItemPublic } from "@/client"

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

function getItemsQueryOptions(page: number, pageSize: number) {
  return {
    queryKey: ["items", { page, pageSize }],
    queryFn: () =>
      ItemsService.readItems({
        skip: (page - 1) * pageSize,
        limit: pageSize,
      }),
    placeholderData: keepPreviousData,
  }
}

function ItemsListPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const itemsQuery = useQuery(getItemsQueryOptions(page, pageSize))
  const items = itemsQuery.data

  const handleTableChange: TableProps<ItemPublic>["onChange"] = (pagination) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }

  return (
    <Table<ItemPublic>
      columns={columns}
      dataSource={items?.data ?? []}
      loading={itemsQuery.isFetching}
      onChange={handleTableChange}
      pagination={{
        current: page,
        pageSize,
        total: items?.count ?? 0,
        pageSizeOptions: PAGE_SIZE_OPTIONS,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
        responsive: true,
      }}
      rowKey="id"
    />
  )
}
```

`columns` in the example belongs to the owning page or feature. The table only
renders the server page in `dataSource`; it must not apply a second client-side
slice to those rows.

### 4. Validation and Error Matrix

| Condition | Required behavior |
| --- | --- |
| `page < 1`, non-integer page, or unsupported `pageSize` | Normalize before the request; UI state must remain a valid one-based page and an approved size. |
| Server response has `data` but no reliable total | Do not display a numbered/total pager from `data.length`; extend the backend response and regenerate the client. |
| Filter, search, or sort is committed | Set `page` to `1`, include its values in the query key, then load the new result set. |
| Page-size change | Set `pageSize`, reset `page` to `1`, and make one request through the normal query path. |
| Mutation leaves the selected page empty while `count > 0` | Decrement to the last valid page and refetch; do not leave the user on a false empty state. |
| Request fails | Preserve the last valid page controls and show the page-level error state; do not replace it with an empty state. |
| `count === 0` | Render the page's empty state and omit the pager or use `hideOnSinglePage` when that matches the page design. |

### 5. Good / Base / Bad Cases

- **Good:** A list requests `skip = (page - 1) * pageSize`, supplies
  `response.count` to Ant Design, and keys React Query by page, page size,
  committed filters, and committed sort.
- **Base:** A known-small, fully loaded list uses the existing `DataTable` and
  clearly has no server total or server navigation requirement.
- **Bad:** A page calls `readItems({ skip: 0, limit: 100 })`, sends all rows to
  a client pager, and later treats `data.length` as the total for a dataset that
  may exceed that first 100 rows.

### 6. Tests Required

- Request mapping: changing from page `1` to `3` at size `20` calls the
  generated service with `skip: 40` and `limit: 20`.
- Pagination state: changing page size from `20` to `50` resets the requested
  page to `1` and causes one new query.
- Query isolation: distinct page, page-size, committed-filter, or sort values
  produce distinct query keys and do not reuse the wrong page result.
- UI total: the pager displays `response.count`, not the number of rows in the
  current response.
- Empty/error separation: a successful `{ data: [], count: 0 }` shows the
  empty state; a failed request shows the error state.
- Mutation recovery: deleting the last row on a later page navigates to the
  last valid page and reloads it.

### 7. Wrong vs Correct

#### Wrong

```tsx
const { data } = useQuery({
  queryKey: ["items"],
  queryFn: () => ItemsService.readItems({ skip: 0, limit: 100 }),
})

<Table
  dataSource={data?.data}
  pagination={{ total: data?.data.length }}
/>
```

This silently caps the visible dataset at 100 rows, reports a false total, and
does not refetch when a user changes page.

#### Correct

```tsx
const { data } = useQuery({
  queryKey: ["items", { page, pageSize, filters, sort }],
  queryFn: () =>
    ItemsService.readItems({
      skip: (page - 1) * pageSize,
      limit: pageSize,
    }),
})

<Table
  dataSource={data?.data ?? []}
  pagination={{ current: page, pageSize, total: data?.count ?? 0 }}
/>
```

This keeps the server result, Ant Design controls, and React Query cache aligned.

## Code Anchors

- Current offset request and count response: [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py), [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py), [`frontend/src/client/sdk.gen.ts`](../../../frontend/src/client/sdk.gen.ts), [`frontend/src/client/types.gen.ts`](../../../frontend/src/client/types.gen.ts)
- Current small-list client-side pagination: [`frontend/src/shared/components/table/DataTable.tsx`](../../../frontend/src/shared/components/table/DataTable.tsx)
- Current item list, which intentionally requests the first 100 records and is not yet a server-paginated page: [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Ant Design provider and complex-UI boundary: [`frontend/src/app/providers/AntdProvider.tsx`](../../../frontend/src/app/providers/AntdProvider.tsx), [Component Guidelines](./component-guidelines.md)
