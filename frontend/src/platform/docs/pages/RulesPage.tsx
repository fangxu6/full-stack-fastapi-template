import { useQuery } from "@tanstack/react-query"
import { useNavigate, useSearch } from "@tanstack/react-router"
import { Alert, Button, Card, Empty, List, Skeleton, Typography } from "antd"
import { startTransition, useEffect } from "react"

import { ApiError, DocsService, type RuleDocumentSummary } from "@/client"

const { Paragraph, Text, Title } = Typography

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

function RulesLoadingState() {
  return (
    <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} title />
      </Card>
      <Card className="min-h-[32rem]">
        <Skeleton active paragraph={{ rows: 14 }} title />
      </Card>
    </div>
  )
}

function RulesErrorState({
  description,
  onRetry,
}: {
  description: string
  onRetry?: () => void
}) {
  return (
    <Alert
      action={
        onRetry ? (
          <Button type="primary" onClick={onRetry}>
            Retry
          </Button>
        ) : null
      }
      description={description}
      message="Unable to load rules"
      showIcon
      type="error"
    />
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
    <Card
      className="h-full"
      title="Rules"
      extra={<Text type="secondary">{documents.length} repository rules</Text>}
    >
      <List
        className="max-h-[70vh] overflow-y-auto"
        dataSource={documents}
        renderItem={(document) => {
          const isActive = document.slug === selectedSlug

          return (
            <List.Item className="!border-0 !px-0 !py-1">
              <button
                type="button"
                onClick={() => onSelect(document.slug)}
                className={[
                  "w-full rounded-lg border px-4 py-3 text-left transition-colors",
                  "hover:border-foreground/20 hover:bg-accent/50",
                  isActive
                    ? "border-primary bg-accent text-accent-foreground"
                    : "border-border bg-background",
                ].join(" ")}
              >
                <div className="font-medium">{document.title}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {document.path}
                </div>
              </button>
            </List.Item>
          )
        }}
      />
    </Card>
  )
}

export function RulesPage() {
  const { slug } = useSearch({ from: "/_layout/rules" })
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
        <Title level={2} className="!mb-0">
          Rules
        </Title>
        <Paragraph type="secondary" className="!mb-0">
          Browse the repository rules from <Text code>docs/rules/*.md</Text>.
        </Paragraph>
      </div>

      {ruleDocumentsQuery.isLoading ? <RulesLoadingState /> : null}

      {ruleDocumentsQuery.isError ? (
        <RulesErrorState
          description={getRuleErrorMessage(ruleDocumentsQuery.error)}
          onRetry={() => void ruleDocumentsQuery.refetch()}
        />
      ) : null}

      {!ruleDocumentsQuery.isLoading &&
      !ruleDocumentsQuery.isError &&
      documents.length === 0 ? (
        <Card className="min-h-[20rem]">
          <Empty
            description="The docs/rules directory is currently empty."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
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

          {ruleDocumentQuery.isLoading ? (
            <Card className="min-h-[32rem]">
              <Skeleton active paragraph={{ rows: 14 }} title />
            </Card>
          ) : null}

          {ruleDocumentQuery.isError ? (
            <RulesErrorState
              description={getRuleErrorMessage(ruleDocumentQuery.error)}
              onRetry={() => void ruleDocumentQuery.refetch()}
            />
          ) : null}

          {ruleDocumentQuery.data ? (
            <Card
              className="min-h-[32rem]"
              title={ruleDocumentQuery.data.title}
            >
              <Paragraph type="secondary">
                {ruleDocumentQuery.data.path}
              </Paragraph>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-muted/40 p-4 text-sm leading-6">
                {ruleDocumentQuery.data.content}
              </pre>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
