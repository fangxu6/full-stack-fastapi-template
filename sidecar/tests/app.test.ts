import { expect, test } from "bun:test";

import { createInventoryApp } from "../src/app";

const runId = "9a6a7fb3-c9bd-42ae-a9a1-2c173617f5b2";

test("returns an unauthenticated health response", async () => {
	const app = createInventoryApp({
		orchestratorServiceToken: "orchestrator-token",
		runQuery: async () => {
			throw new Error("health checks must not run the inventory workflow");
		},
	});

	const response = await app(new Request("http://sidecar/health"));

	expect(response.status).toBe(200);
	expect(await response.json()).toEqual({ status: "ok" });
});

test("forwards an authenticated BFF query to the inventory workflow", async () => {
	let workflowInput: unknown;
	const app = createInventoryApp({
		orchestratorServiceToken: "orchestrator-token",
		runQuery: async (input) => {
			workflowInput = input;
			return {
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
					provider: "internal-gateway",
					model: "gpt-5.6-luna",
					provider_request_id: null,
					latency_ms: 123,
					input_tokens: null,
					output_tokens: null,
				},
			};
		},
	});

	const response = await app(
		new Request("http://sidecar/v1/inventory/query", {
			body: JSON.stringify({ question: "成品库存还有多少？", run_id: runId }),
			headers: {
				"Content-Type": "application/json",
				"X-AI-Actor-Grant": "actor-grant",
				"X-AI-Orchestrator-Token": "orchestrator-token",
				"X-Request-ID": "request-123",
			},
			method: "POST",
		}),
	);

	expect(response.status).toBe(200);
	expect(workflowInput).toEqual({
		actorGrant: "actor-grant",
		request: { question: "成品库存还有多少？", run_id: runId },
		requestId: "request-123",
	});
	expect(await response.json()).toMatchObject({ status: "completed" });
});
