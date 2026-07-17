import { expect, test } from "bun:test";

import { createInventoryTools } from "../src/mastra-tools";
import { createInventoryToolClient } from "../src/tools";

test("registers only the five approved inventory tools", () => {
	const tools = createInventoryTools({
		client: createInventoryToolClient({
			baseUrl: "http://backend:8000",
			fetch,
			serviceToken: "internal-service-token",
		}),
		context: {
			actorGrant:
				"header.eyJzdWIiOiIwZDllMzE5NC0zZGQ2LTRhYzgtOGEzYS02NWU0YTlmNjllZTAifQ.signature",
			requestId: "request-123",
			runId: "9a6a7fb3-c9bd-42ae-a9a1-2c173617f5b2",
		},
	});

	expect(Object.keys(tools).sort()).toEqual([
		"balances",
		"documents",
		"ledger",
		"processing_units",
		"receiving_units",
	]);
});
