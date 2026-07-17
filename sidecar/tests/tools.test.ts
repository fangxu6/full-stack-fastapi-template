import { expect, test } from "bun:test";

import {
	createInventoryToolClient,
	InventoryToolInvalidResponseError,
} from "../src/tools";

const actorUserId = "0d9e3194-3dd6-4ac8-8a3a-65e4a9f69ee0";
const runId = "9a6a7fb3-c9bd-42ae-a9a1-2c173617f5b2";

function actorGrantWithSubject(subject: string) {
	const payload = Buffer.from(JSON.stringify({ sub: subject })).toString(
		"base64url",
	);
	return `header.${payload}.signature`;
}

test("forwards the verified grant context to the balances projection", async () => {
	let receivedRequest: Request | undefined;
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async (input, init) => {
			receivedRequest = new Request(input, init);
			return Response.json({
				tool_name: "balances",
				source: "inventory:balances",
				result: { count: 0, data: [] },
			});
		},
		serviceToken: "internal-service-token",
	});

	const result = await client.readBalances(
		{
			actorGrant: actorGrantWithSubject(actorUserId),
			requestId: "request-123",
			runId,
		},
		{ ledger_kind: "RAW" },
	);

	expect(receivedRequest?.url).toBe(
		"http://backend:8000/api/v1/internal/ai/inventory/balances",
	);
	expect(receivedRequest?.headers.get("X-AI-Service-Token")).toBe(
		"internal-service-token",
	);
	expect(receivedRequest?.headers.get("X-AI-Actor-Grant")).toBe(
		actorGrantWithSubject(actorUserId),
	);
	expect(receivedRequest?.headers.get("X-Request-ID")).toBe("request-123");
	expect(await receivedRequest?.json()).toEqual({
		actor_user_id: actorUserId,
		ledger_kind: "RAW",
		limit: 20,
		run_id: runId,
		skip: 0,
	});
	expect(result.source).toBe("inventory:balances");
});

test("calls the processing-units projection with bounded pagination", async () => {
	let receivedRequest: Request | undefined;
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async (input, init) => {
			receivedRequest = new Request(input, init);
			return Response.json({
				tool_name: "processing_units",
				source: "inventory:processing_units",
				result: { count: 0, data: [] },
			});
		},
		serviceToken: "internal-service-token",
	});

	const result = await client.readProcessingUnits(
		{
			actorGrant: actorGrantWithSubject(actorUserId),
			requestId: "request-123",
			runId,
		},
		{ name: "纺织厂" },
	);

	expect(receivedRequest?.url).toBe(
		"http://backend:8000/api/v1/internal/ai/inventory/processing-units",
	);
	expect(await receivedRequest?.json()).toEqual({
		actor_user_id: actorUserId,
		limit: 20,
		name: "纺织厂",
		run_id: runId,
		skip: 0,
	});
	expect(result.source).toBe("inventory:processing_units");
});

test("calls the receiving-units projection with bounded pagination", async () => {
	let receivedRequest: Request | undefined;
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async (input, init) => {
			receivedRequest = new Request(input, init);
			return Response.json({
				tool_name: "receiving_units",
				source: "inventory:receiving_units",
				result: { count: 0, data: [] },
			});
		},
		serviceToken: "internal-service-token",
	});

	const result = await client.readReceivingUnits({
		actorGrant: actorGrantWithSubject(actorUserId),
		requestId: "request-123",
		runId,
	});

	expect(receivedRequest?.url).toBe(
		"http://backend:8000/api/v1/internal/ai/inventory/receiving-units",
	);
	expect(await receivedRequest?.json()).toEqual({
		actor_user_id: actorUserId,
		limit: 20,
		run_id: runId,
		skip: 0,
	});
	expect(result.source).toBe("inventory:receiving_units");
});

test("rejects a processing-units response labelled as receiving units", async () => {
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async () =>
			Response.json({
				tool_name: "receiving_units",
				source: "inventory:receiving_units",
				result: { count: 0, data: [] },
			}),
		serviceToken: "internal-service-token",
	});

	await expect(
		client.readProcessingUnits({
			actorGrant: actorGrantWithSubject(actorUserId),
			requestId: "request-123",
			runId,
		}),
	).rejects.toBeInstanceOf(InventoryToolInvalidResponseError);
});

test("calls the documents projection without deleted records", async () => {
	let receivedRequest: Request | undefined;
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async (input, init) => {
			receivedRequest = new Request(input, init);
			return Response.json({
				tool_name: "documents",
				source: "inventory:documents",
				result: { count: 0, data: [] },
			});
		},
		serviceToken: "internal-service-token",
	});

	const result = await client.readDocuments(
		{
			actorGrant: actorGrantWithSubject(actorUserId),
			requestId: "request-123",
			runId,
		},
		{ document_type: "FINISHED_SHIPMENT" },
	);

	expect(receivedRequest?.url).toBe(
		"http://backend:8000/api/v1/internal/ai/inventory/documents",
	);
	expect(await receivedRequest?.json()).toEqual({
		actor_user_id: actorUserId,
		document_type: "FINISHED_SHIPMENT",
		limit: 20,
		run_id: runId,
		skip: 0,
	});
	expect(result.source).toBe("inventory:documents");
});

test("calls the ledger projection with its required balance key", async () => {
	let receivedRequest: Request | undefined;
	const processingUnitId = "cdd5e5e7-5a9e-49d9-8e5f-c3fb3c0889da";
	const client = createInventoryToolClient({
		baseUrl: "http://backend:8000",
		fetch: async (input, init) => {
			receivedRequest = new Request(input, init);
			return Response.json({
				tool_name: "ledger",
				source: "inventory:ledger",
				result: { count: 0, data: [] },
			});
		},
		serviceToken: "internal-service-token",
	});

	const result = await client.readLedger(
		{
			actorGrant: actorGrantWithSubject(actorUserId),
			requestId: "request-123",
			runId,
		},
		{
			item_name: "全棉坯布",
			ledger_kind: "RAW",
			processing_unit_id: processingUnitId,
			wool_content: "0%",
		},
	);

	expect(receivedRequest?.url).toBe(
		"http://backend:8000/api/v1/internal/ai/inventory/ledger",
	);
	expect(await receivedRequest?.json()).toEqual({
		actor_user_id: actorUserId,
		item_name: "全棉坯布",
		ledger_kind: "RAW",
		limit: 20,
		processing_unit_id: processingUnitId,
		run_id: runId,
		skip: 0,
		wool_content: "0%",
	});
	expect(result.source).toBe("inventory:ledger");
});
