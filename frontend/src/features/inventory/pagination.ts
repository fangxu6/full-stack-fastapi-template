export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

export function toOffset(page: number, pageSize: number) {
  return (page - 1) * pageSize
}
