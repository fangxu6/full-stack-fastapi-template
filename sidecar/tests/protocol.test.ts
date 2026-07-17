import { expect, test } from "bun:test";

import {
	completedQueryResponseSchema,
	failedQueryResponseSchema,
} from "../src/protocol";

test("accepts a completed response with a stable citation", () => {
	const response = completedQueryResponseSchema.parse({
		status: "completed",
		answer: "当前无成品库存余额。",
		citations: [
			{
				tool_name: "balances",
				source: "inventory:balances",
				summary: "已查询成品库存余额，共 0 条",
			},
		],
		provider_metadata: {
			model: "gpt-5.6-luna",
			openai_request_id: "req_123",
			latency_ms: 1234,
			input_tokens: null,
			output_tokens: null,
		},
	});

	expect(response.status).toBe("completed");
});

test("rejects retryable tool failures", () => {
	expect(() =>
		failedQueryResponseSchema.parse({
			status: "failed",
			error: {
				category: "tool_failed",
				retryable: true,
			},
		}),
	).toThrow();
});

test("rejects unknown failure categories", () => {
	expect(() =>
		failedQueryResponseSchema.parse({
			status: "failed",
			error: {
				category: "provider_error",
				retryable: false,
			},
		}),
	).toThrow();
});
