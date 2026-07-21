import { Agent } from "@mastra/core/agent";
import type { JSONSchema7 } from "json-schema";
import { z } from "zod";

import { createInventoryTools } from "./mastra-tools";
import {
	completedQueryResponseSchema,
	failedQueryResponseSchema,
	type QueryResponse,
} from "./protocol";
import {
	createInventoryToolClient,
	InventoryToolFailedError,
	InventoryToolInvalidResponseError,
	InventoryToolRejectedError,
} from "./tools";

const inventoryToolNames = [
	"balances",
	"documents",
	"ledger",
	"processing_units",
	"receiving_units",
] as const;

const inventorySourceByToolName = {
	balances: "inventory:balances",
	documents: "inventory:documents",
	ledger: "inventory:ledger",
	processing_units: "inventory:processing_units",
	receiving_units: "inventory:receiving_units",
} as const;

type InventoryToolName = keyof typeof inventorySourceByToolName;

const finalAnswerSchema = z
	.object({
		answer: z.string().trim().min(1).max(8_000),
		citations: z
			.array(
				z
					.object({
						tool_name: z.enum(inventoryToolNames),
						source: z.string().regex(/^inventory:[a-z_]+$/),
						summary: z.string().trim().min(1).max(1_000),
					})
					.strict(),
			)
			.min(1)
			.max(5),
	})
	.strict();

type AgentResult = {
	object?: unknown;
	text?: string;
	toolResults?: Array<{ payload?: { toolName?: string } }>;
	response?: { headers?: Record<string, string | undefined> };
	usage?: { inputTokens?: number; outputTokens?: number };
};

type InventoryAgent = {
	generate: (
		input: string,
		options: { experimental_output: JSONSchema7; maxSteps: number },
	) => Promise<AgentResult>;
};

type WorkflowInput = {
	actorGrant: string;
	question: string;
	requestId: string;
	runId: string;
};

type WorkflowConfig = {
	createAgent?: (input: WorkflowInput) => InventoryAgent;
	internalBaseUrl: string;
	internalServiceToken: string;
	providerApiKey: string;
	providerBaseUrl: string;
	providerName: string;
};

type ProviderModelConfigInput = {
	apiKey: string;
	baseUrl: string;
};

function failed(
	category: QueryResponse extends never ? never : string,
): QueryResponse {
	return failedQueryResponseSchema.parse({
		status: "failed",
		error: {
			category,
			retryable:
				category === "timeout" ||
				category === "rate_limited" ||
				category === "provider_unavailable",
		},
	});
}

function getErrorStatus(error: unknown): number | undefined {
	if (typeof error !== "object" || error === null || !("status" in error)) {
		return undefined;
	}

	const { status } = error;
	return typeof status === "number" ? status : undefined;
}

function isTimeoutError(error: unknown): boolean {
	return (
		error instanceof DOMException &&
		(error.name === "AbortError" || error.name === "TimeoutError")
	);
}

function parseTextOutput(text: string | undefined): unknown {
	if (!text) return undefined;

	const trimmedText = text.trim();
	const codeBlock = trimmedText.match(/^```(?:json)?\s*\n?([\s\S]*?)\s*```$/i);
	const jsonText = codeBlock?.[1] ?? trimmedText;
	try {
		return JSON.parse(jsonText);
	} catch {
		return undefined;
	}
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isInventoryToolName(value: unknown): value is InventoryToolName {
	return (
		typeof value === "string" && Object.hasOwn(inventorySourceByToolName, value)
	);
}

function getExecutedToolNames(result: AgentResult): InventoryToolName[] {
	return [
		...new Set(
			result.toolResults
				?.map((toolResult) => toolResult.payload?.toolName)
				.filter(isInventoryToolName),
		),
	];
}

function normalizeTextOutput(value: unknown, result: AgentResult): unknown {
	if (!isRecord(value) || ("answer" in value && "citations" in value)) {
		return value;
	}

	const answer = value.答案 ?? value.说明;
	const citations = value.citation ? [value.citation] : value.citations;
	if (answer === undefined || !Array.isArray(citations)) return value;

	const executedToolNames = new Set(getExecutedToolNames(result));
	return {
		answer,
		citations: citations.map((citation) => {
			if (!isRecord(citation) || !isInventoryToolName(citation.tool_name)) {
				return citation;
			}
			if (!executedToolNames.has(citation.tool_name)) return citation;
			return {
				...citation,
				source: inventorySourceByToolName[citation.tool_name],
				summary:
					citation.summary ?? `已调用 ${citation.tool_name} 工具查询库存数据。`,
			};
		}),
	};
}

function naturalLanguageTextOutput(
	text: string | undefined,
	result: AgentResult,
): unknown {
	const answer = text?.trim();
	const toolNames = getExecutedToolNames(result);
	if (!answer || toolNames.length === 0) return undefined;

	return {
		answer,
		citations: toolNames.map((toolName) => ({
			tool_name: toolName,
			source: inventorySourceByToolName[toolName],
			summary: `已调用 ${toolName} 工具查询库存数据。`,
		})),
	};
}

function parseFinalAnswer(result: AgentResult) {
	const parsedText = parseTextOutput(result.text);
	const output = result.object ?? parsedText;
	const normalizedOutput = normalizeTextOutput(output, result);
	const parsedOutput = finalAnswerSchema.safeParse(normalizedOutput);
	if (parsedOutput.success) return parsedOutput.data;
	if (result.object !== undefined || parsedText !== undefined) {
		throw parsedOutput.error;
	}
	return finalAnswerSchema.parse(
		naturalLanguageTextOutput(result.text, result),
	);
}

export function createProviderModelConfig({
	apiKey,
	baseUrl,
}: ProviderModelConfigInput) {
	return {
		apiKey,
		id: "openai/gpt-5.6-luna" as const,
		url: baseUrl,
	};
}

export function createInventoryWorkflow({
	createAgent,
	internalBaseUrl,
	internalServiceToken,
	providerApiKey,
	providerBaseUrl,
	providerName,
}: WorkflowConfig) {
	return async function runInventoryWorkflow(
		input: WorkflowInput,
	): Promise<QueryResponse> {
		const startedAt = performance.now();
		try {
			const agent =
				createAgent?.(input) ??
				new Agent({
					id: "inventory-orchestrator",
					name: "Inventory Orchestrator",
					instructions: {
						role: "system",
						content:
							"你只能使用已注册的库存只读工具。必须基于工具结果回答中文问题，并为每个结论提供 citation。",
						providerOptions: { openai: { reasoningEffort: "medium" } },
					},
					model: createProviderModelConfig({
						apiKey: providerApiKey,
						baseUrl: providerBaseUrl,
					}),
					tools: createInventoryTools({
						client: createInventoryToolClient({
							baseUrl: internalBaseUrl,
							fetch,
							serviceToken: internalServiceToken,
						}),
						context: input,
					}),
				});
			const result = await agent.generate(input.question, {
				experimental_output: z.toJSONSchema(finalAnswerSchema) as JSONSchema7,
				maxSteps: 5,
			});
			const output = parseFinalAnswer(result);
			return completedQueryResponseSchema.parse({
				...output,
				status: "completed",
				provider_metadata: {
					provider: providerName,
					model: "gpt-5.6-luna",
					provider_request_id:
						result.response?.headers?.["x-request-id"] ??
						result.response?.headers?.["request-id"] ??
						null,
					latency_ms: Math.round(performance.now() - startedAt),
					input_tokens: result.usage?.inputTokens ?? null,
					output_tokens: result.usage?.outputTokens ?? null,
				},
			});
		} catch (error) {
			if (error instanceof InventoryToolRejectedError)
				return failed("tool_rejected");
			if (error instanceof InventoryToolFailedError)
				return failed("tool_failed");
			if (error instanceof InventoryToolInvalidResponseError)
				return failed("invalid_response");
			if (error instanceof z.ZodError) return failed("invalid_response");
			if (getErrorStatus(error) === 429) return failed("rate_limited");
			if (isTimeoutError(error)) return failed("timeout");
			return failed("provider_unavailable");
		}
	};
}
