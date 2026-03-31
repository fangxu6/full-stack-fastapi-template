import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { AlertCircle, FileText, RefreshCw } from "lucide-react"
import { startTransition, useEffect } from "react"
import { z } from "zod"

import { ApiError, DocsService, type RuleDocumentSummary } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const searchSchema = z.object({
  slug: z.string().optional(),
})

function getRuleDocumentsQueryOptions() {
  return {
    queryFn: () => DocsService.readRuleDocuments(),
    queryKey: ["rule-documents"],
    staleTime: 60_000,
  }
}

function getRuleDocumentQueryOptions(slug: string) {
  return {
    queryFn: () => DocsService.readRuleDocument({ slug }),
    queryKey: ["rule-document", slug],
    staleTime: 60_000,
  }
}

export const Route = createFileRoute("/_layout/rules")({
  component: Rules,
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      {
        title: "Rules - FastAPI Template",
      },
    ],
  }),
})

function getRuleErrorMessage(error: unknown) {
  if (
    error instanceof ApiError &&
    typeof error.body === "object" &&
    error.body &&
    "detail" in error.body &&
    typeof error.body.detail === "string"
  ) {
    return error.body.detail
  }

  return "Unable to load this rule document."
}

function RulesListSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={`rule-skeleton-${index}`} className="h-16 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

function RuleDocumentSkeleton() {
  return (
    <Card className="min-h-[32rem]">
      <CardHeader>
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: 14 }).map((_, index) => (
          <Skeleton key={`rule-line-${index}`} className="h-4 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

function EmptyRulesState() {
  return (
    <Card className="border-dashed">
      <CardContent className="flex min-h-[20rem] flex-col items-center justify-center gap-4 text-center">
        <div className="rounded-full bg-muted p-4">
          <FileText className="h-8 w-8 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">No rules available</h2>
          <p className="text-sm text-muted-foreground">
            The `docs/rules` directory is currently empty.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

function InlineErrorState({
  description,
  onRetry,
}: {
  description: string
  onRetry?: () => void
}) {
  return (
    <Card className="border-destructive/40">
      <CardContent className="flex min-h-[20rem] flex-col items-center justify-center gap-4 text-center">
        <div className="rounded-full bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-8 w-8" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Unable to load rules</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        {onRetry ? (
          <Button type="button" variant="outline" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}

function RulesSidebar({
  documents,
  selectedSlug,
  onSelect,
}: {
  documents: RuleDocumentSummary[]
  selectedSlug?: string
  onSelect: (slug: string) => void
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Rules</CardTitle>
        <CardDescription>{documents.length} repository rules</CardDescription>
      </CardHeader>
      <CardContent className="max-h-[70vh] space-y-2 overflow-y-auto">
        {documents.map((document) => {
          const isActive = document.slug === selectedSlug

          return (
            <button
              type="button"
              key={document.slug}
              onClick={() => onSelect(document.slug)}
              className={cn(
                "w-full rounded-lg border px-4 py-3 text-left transition-colors",
                "hover:border-foreground/20 hover:bg-accent/50",
                isActive
                  ? "border-primary bg-accent text-accent-foreground"
                  : "border-border bg-background",
              )}
            >
              <div className="font-medium">{document.title}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {document.path}
              </div>
            </button>
          )
        })}
      </CardContent>
    </Card>
  )
}

function Rules() {
  const { slug } = Route.useSearch()
  const navigate = useNavigate()

  const ruleDocumentsQuery = useQuery(getRuleDocumentsQueryOptions())
  const documents = ruleDocumentsQuery.data?.data ?? []
  const selectedSlug = slug || documents[0]?.slug

  useEffect(() => {
    if (slug || !documents[0]?.slug) {
      return
    }

    startTransition(() => {
      navigate({
        to: "/rules",
        replace: true,
        search: { slug: documents[0].slug },
      })
    })
  }, [documents, navigate, slug])

  const ruleDocumentQuery = useQuery({
    ...getRuleDocumentQueryOptions(selectedSlug ?? ""),
    enabled: Boolean(selectedSlug),
  })

  const handleSelect = (nextSlug: string) => {
    startTransition(() => {
      navigate({
        to: "/rules",
        search: { slug: nextSlug },
      })
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Rules</h1>
        <p className="text-muted-foreground">
          Browse the repository rules from `docs/rules/*.md`.
        </p>
      </div>

      {ruleDocumentsQuery.isLoading ? (
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <RulesListSkeleton />
          <RuleDocumentSkeleton />
        </div>
      ) : null}

      {ruleDocumentsQuery.isError ? (
        <InlineErrorState
          description={getRuleErrorMessage(ruleDocumentsQuery.error)}
          onRetry={() => void ruleDocumentsQuery.refetch()}
        />
      ) : null}

      {!ruleDocumentsQuery.isLoading &&
      !ruleDocumentsQuery.isError &&
      documents.length === 0 ? (
        <EmptyRulesState />
      ) : null}

      {!ruleDocumentsQuery.isLoading &&
      !ruleDocumentsQuery.isError &&
      documents.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <RulesSidebar
            documents={documents}
            selectedSlug={selectedSlug}
            onSelect={handleSelect}
          />

          {ruleDocumentQuery.isLoading ? <RuleDocumentSkeleton /> : null}

          {ruleDocumentQuery.isError ? (
            <InlineErrorState
              description={getRuleErrorMessage(ruleDocumentQuery.error)}
              onRetry={() => void ruleDocumentQuery.refetch()}
            />
          ) : null}

          {ruleDocumentQuery.data ? (
            <Card className="min-h-[32rem]">
              <CardHeader>
                <CardTitle>{ruleDocumentQuery.data.title}</CardTitle>
                <CardDescription>{ruleDocumentQuery.data.path}</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-muted/40 p-4 text-sm leading-6">
                  {ruleDocumentQuery.data.content}
                </pre>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
