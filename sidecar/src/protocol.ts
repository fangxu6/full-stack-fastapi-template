import { z } from "zod";

export const inventoryToolNameSchema = z.enum([
	"balances",
	"documents",
	"ledger",
	"processing_units",
	"receiving_units",
]);

export const queryRequestSchema = z
	.object({
		run_id: z.uuid(),
		question: z.string().trim().min(1).max(2_000),
	})
	.strict();

export const citationSchema = z
	.object({
		tool_name: inventoryToolNameSchema,
		source: z.string().regex(/^inventory:[a-z_]+$/),
		summary: z.string().trim().min(1).max(1_000),
	})
	.strict();

export const providerMetadataSchema = z
	.object({
		model: z.literal("gpt-5.6-luna"),
		openai_request_id: z.string().min(1).nullable(),
		latency_ms: z.number().int().nonnegative(),
		input_tokens: z.number().int().nonnegative().nullable(),
		output_tokens: z.number().int().nonnegative().nullable(),
	})
	.strict();

export const completedQueryResponseSchema = z
	.object({
		status: z.literal("completed"),
		answer: z.string().trim().min(1).max(8_000),
		citations: z.array(citationSchema).min(1).max(5),
		provider_metadata: providerMetadataSchema,
	})
	.strict();

export const failureCategorySchema = z.enum([
	"timeout",
	"rate_limited",
	"provider_unavailable",
	"tool_rejected",
	"tool_failed",
	"invalid_response",
]);

const retryableFailureCategories = new Set([
	"timeout",
	"rate_limited",
	"provider_unavailable",
]);

export const failedQueryResponseSchema = z
	.object({
		status: z.literal("failed"),
		error: z
			.object({
				category: failureCategorySchema,
				retryable: z.boolean(),
			})
			.strict()
			.refine(
				({ category, retryable }) =>
					!retryable || retryableFailureCategories.has(category),
				"Only transient failure categories may be retryable",
			),
	})
	.strict();

export const queryResponseSchema = z.discriminatedUnion("status", [
	completedQueryResponseSchema,
	failedQueryResponseSchema,
]);

export type QueryRequest = z.infer<typeof queryRequestSchema>;
export type Citation = z.infer<typeof citationSchema>;
export type ProviderMetadata = z.infer<typeof providerMetadataSchema>;
export type QueryResponse = z.infer<typeof queryResponseSchema>;
