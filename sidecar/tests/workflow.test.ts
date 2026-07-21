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

test("parses a JSON text response when the provider omits the structured object", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => ({
				text: JSON.stringify({
					answer: "当前无成品库存余额。",
					citations: [
						{
							source: "inventory:balances",
							summary: "已查询成品库存余额，共 0 条",
							tool_name: "balances",
						},
					],
				}),
			}),
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "成品库存还有多少？",
			requestId: "request-123",
			runId,
		}),
	).toMatchObject({
		status: "completed",
		answer: "当前无成品库存余额。",
	});
});

test("normalizes the provider's Chinese text envelope after its cited tool executes", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => ({
				text: JSON.stringify({
					库存类型: "成品",
					库存余额: [],
					说明: "当前无成品库存余额记录。",
					citation: {
						tool_name: "balances",
						source: "成品库存余额查询工具",
						summary: "已查询成品库存余额，共 0 条",
					},
				}),
				toolResults: [{ payload: { toolName: "balances" } }],
			}),
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "成品库存还有多少？",
			requestId: "request-123",
			runId,
		}),
	).toMatchObject({
		status: "completed",
		answer: "当前无成品库存余额记录。",
		citations: [
			{
				tool_name: "balances",
				source: "inventory:balances",
			},
		],
	});
});

test("accepts a natural-language answer after an inventory tool executes", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => ({
				text: "当前成品库存余额已查询，共 290 条记录。",
				toolResults: [{ payload: { toolName: "balances" } }],
			}),
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "成品库存还有多少？",
			requestId: "request-123",
			runId,
		}),
	).toMatchObject({
		status: "completed",
		answer: "当前成品库存余额已查询，共 290 条记录。",
		citations: [
			{
				tool_name: "balances",
				source: "inventory:balances",
			},
		],
	});
});

test("rejects non-JSON text responses", async () => {
	const workflow = createInventoryWorkflow({
		providerApiKey: "provider-key",
		providerBaseUrl: "http://llm-gateway:8080/v1",
		providerName: "internal-gateway",
		createAgent: () => ({
			generate: async () => ({ text: "当前无成品库存余额。" }),
		}),
		internalBaseUrl: "http://backend:8000",
		internalServiceToken: "internal-token",
	});

	expect(
		await workflow({
			actorGrant: "grant",
			question: "成品库存还有多少？",
			requestId: "request-123",
			runId,
		}),
	).toEqual({
		status: "failed",
		error: { category: "invalid_response", retryable: false },
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
