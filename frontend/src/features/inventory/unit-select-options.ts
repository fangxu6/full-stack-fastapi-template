import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import type { MasterUnitPublic } from "@/client"
import {
  readProcessingUnitsPage,
  readReceivingUnitsPage,
} from "@/features/inventory/api"

export const UNIT_SELECT_LIMIT = 20

type UnitKind = "processing" | "receiving"

type UnitOptionsRequest = {
  isActive?: boolean
  limit: number
  name?: string
  skip: number
}

type UnitSelectOption = {
  label: string
  value: string
}

type UseUnitSelectOptionsParams = {
  enabled?: boolean
  isActive?: boolean
  kind: UnitKind
  selectedValue?: string
}

export function buildUnitOptionsRequest({
  isActive,
  searchTerm,
}: {
  isActive?: boolean
  searchTerm: string
}): UnitOptionsRequest {
  const name = searchTerm.trim()
  return {
    ...(isActive === undefined ? {} : { isActive }),
    limit: UNIT_SELECT_LIMIT,
    ...(name ? { name } : {}),
    skip: 0,
  }
}

function useDebouncedValue(value: string, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs)
    return () => window.clearTimeout(timeout)
  }, [delayMs, value])

  return debouncedValue
}

function toOption(unit: MasterUnitPublic): UnitSelectOption {
  return { label: unit.name, value: unit.id }
}

export function useUnitSelectOptions({
  enabled = true,
  isActive,
  kind,
  selectedValue,
}: UseUnitSelectOptionsParams) {
  const [searchTerm, setSearchTerm] = useState("")
  const [knownUnits, setKnownUnits] = useState<Map<string, MasterUnitPublic>>(
    () => new Map(),
  )
  const debouncedSearchTerm = useDebouncedValue(searchTerm, 300)
  const request = buildUnitOptionsRequest({
    isActive,
    searchTerm: debouncedSearchTerm,
  })
  const isDebouncing = searchTerm.trim() !== debouncedSearchTerm.trim()
  const unitsQuery = useQuery({
    enabled,
    queryFn: () =>
      kind === "processing"
        ? readProcessingUnitsPage(request)
        : readReceivingUnitsPage(request),
    queryKey: [
      "inventory",
      "unit-options",
      kind,
      isActive ?? "all",
      request.name ?? "",
    ],
  })

  useEffect(() => {
    const units = unitsQuery.data?.data
    if (!units?.length) return

    setKnownUnits((current) => {
      const next = new Map(current)
      for (const unit of units) next.set(unit.id, unit)
      return next
    })
  }, [unitsQuery.data])

  const options = useMemo(() => {
    const visibleUnits =
      isDebouncing || !enabled ? [] : (unitsQuery.data?.data ?? [])
    const selectedUnit = selectedValue
      ? knownUnits.get(selectedValue)
      : undefined
    const units = selectedUnit
      ? [
          selectedUnit,
          ...visibleUnits.filter((unit) => unit.id !== selectedUnit.id),
        ]
      : visibleUnits
    return units.map(toOption)
  }, [enabled, isDebouncing, knownUnits, selectedValue, unitsQuery.data])

  return {
    isError: unitsQuery.isError,
    isLoading: enabled && (isDebouncing || unitsQuery.isFetching),
    onSearch: setSearchTerm,
    options,
  }
}
