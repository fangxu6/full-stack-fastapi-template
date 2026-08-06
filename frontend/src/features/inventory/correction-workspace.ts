import {
  type InventoryCorrectionDocumentProposal,
  type InventoryCorrectionOperation,
  InventoryCorrectionsService,
  type InventoryDocumentPublic,
} from "@/client"

export type CorrectionTab = "mine" | "recovery" | "review"

export type CorrectionAccess = {
  canRecover: boolean
  canRequest: boolean
  canReview: boolean
}

export type CorrectionTabItem = {
  key: CorrectionTab
  label: string
}

type CorrectionPageParams = {
  limit: number
  skip: number
}

export const correctionQueryKeys = {
  all: ["inventory", "corrections"] as const,
  detail: (requestId: number | undefined) =>
    ["inventory", "corrections", "detail", requestId] as const,
  detailRoot: () => ["inventory", "corrections", "detail"] as const,
  list: (tab: CorrectionTab, params: CorrectionPageParams) =>
    ["inventory", "corrections", tab, params] as const,
  target: (documentId: string | undefined) =>
    ["inventory", "document", documentId] as const,
}

export function getCorrectionAccess(
  permissions: readonly string[] | undefined,
): CorrectionAccess {
  return {
    canRecover: permissions?.includes("inventory.corrections.recover") ?? false,
    canRequest: permissions?.includes("inventory.corrections.request") ?? false,
    canReview: permissions?.includes("inventory.corrections.review") ?? false,
  }
}

export function getCorrectionTabs(
  access: CorrectionAccess,
): CorrectionTabItem[] {
  return [
    access.canRequest ? { key: "mine", label: "我的申请" } : null,
    access.canReview ? { key: "review", label: "待审核" } : null,
    access.canRecover ? { key: "recovery", label: "失败恢复" } : null,
  ].filter((item): item is CorrectionTabItem => item !== null)
}

export function resolveCorrectionTab(
  requestedTab: CorrectionTab,
  access: CorrectionAccess,
): CorrectionTab {
  const tabs = getCorrectionTabs(access)
  return (
    tabs.find((tab) => tab.key === requestedTab)?.key ??
    tabs[0]?.key ??
    requestedTab
  )
}

export function createCorrectionRequest({
  operation,
  proposal,
  reason,
  target,
}: {
  operation: InventoryCorrectionOperation
  proposal: InventoryCorrectionDocumentProposal | null
  reason: string
  target: InventoryDocumentPublic | undefined
}) {
  if (!target) {
    return Promise.reject(new Error("请选择需要纠错的单据"))
  }
  return InventoryCorrectionsService.createCorrectionRequest({
    requestBody: {
      document_id: target.id,
      expected_updated_at: target.updated_at,
      operation,
      proposal,
      reason: reason.trim(),
    },
  })
}

export function runCorrectionRequestAction(
  action: "approve" | "reject" | "withdraw",
  requestId: number,
) {
  if (action === "approve") {
    return InventoryCorrectionsService.approveCorrectionRequest({
      correctionRequestId: requestId,
    })
  }
  if (action === "reject") {
    return InventoryCorrectionsService.rejectCorrectionRequest({
      correctionRequestId: requestId,
    })
  }
  return InventoryCorrectionsService.withdrawCorrectionRequest({
    correctionRequestId: requestId,
  })
}

export function recoverCorrectionWorkItem(workItemId: number) {
  return InventoryCorrectionsService.recoverCorrectionWorkItem({ workItemId })
}
