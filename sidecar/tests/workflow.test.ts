import { expect, test } from "bun:test";

import {
	InventoryToolFailedError,
	InventoryToolInvalidResponseError,
	InventoryToolRejectedError,
} from "../src/tools";
import {
	createInventoryWorkflow,
	createProviderModelConfig,
} from "../src/workflow";

const runId = "9a6a7fb3-c9bd-42ae-a9a1-2c173617f5b2";

test("uses the configured provider URL for the OpenAI-compatible transport", () => {
	expect(
		createProviderModelConfig({
			apiKey: "provider-key",
			baseUrl: "http://llm-gateway:8080/v1",
		}),
	).toEqual({
		apiKey: "provider-key",
		id: "openai/gpt-5.6-luna",
		url: "http://llm-gateway:8080/v1",
	});
});

test("returns a completed structured response with provider metadata", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => ({
				object: {
					answer: "当前无成品库存余额。",
					citations: [
						{
							source: "inventory:balances",
							summary: "已查询成品库存余额，共 0 条",
							tool_name: "balances",
						},
					],
				},
				response: { headers: { "x-request-id": "req_123" } },
				usage: { inputTokens: 12, outputTokens: 34 },
			}),
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	const response = await workflow({
		actorGrant:
			"header.eyJzdWIiOiIwZDllMzE5NC0zZGQ2LTRhYzgtOGEzYS02NWU0YTlmNjllZTAifQ.signature",
		question: "成品库存还有多少？",
		requestId: "request-123",
		runId,
	});

	expect(response).toMatchObject({
		status: "completed",
		answer: "当前无成品库存余额。",
		provider_metadata: {
			input_tokens: 12,
			model: "gpt-5.6-luna",
			provider: "internal-gateway",
			provider_request_id: "req_123",
			output_tokens: 34,
		},
	});
});

test("maps an OpenAI rate limit to a retryable structured failure", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => {
				throw Object.assign(new Error("rate limited"), { status: 429 });
			},
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "查询库存",
			requestId: "request-123",
			runId,
		}),
	).toEqual({
		status: "failed",
		error: { category: "rate_limited", retryable: true },
	});
});

test("maps internal authorization rejection to a non-retryable failure", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => {
				throw new InventoryToolRejectedError();
			},
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "查询库存",
			requestId: "request-123",
			runId,
		}),
	).toEqual({
		status: "failed",
		error: { category: "tool_rejected", retryable: false },
	});
});

test("maps an internal tool failure to a non-retryable structured failure", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => {
				throw new InventoryToolFailedError();
			},
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "查询库存",
			requestId: "request-123",
			runId,
		}),
	).toEqual({
		status: "failed",
		error: { category: "tool_failed", retryable: false },
	});
});

test("maps an invalid internal tool response to a non-retryable failure", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => {
				throw new InventoryToolInvalidResponseError();
			},
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "查询库存",
			requestId: "request-123",
			runId,
		}),
	).toEqual({
		status: "failed",
		error: { category: "invalid_response", retryable: false },
	});
});
