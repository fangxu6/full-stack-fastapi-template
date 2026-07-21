import { expect, test } from "bun:test";

import {
	compactBalancesForModel,
	createInventoryTools,
} from "../src/mastra-tools";
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

test("compacts balance data before it becomes model context", () => {
	const result = compactBalancesForModel({
		count: 12,
		data: Array.from({ length: 6 }, (_, index) => ({
			item_name: `item-${index}`,
			item_code: null,
			wool_content: "100%",
			color_code: null,
			dye_lot_no: null,
			rolls_balance: 1,
			meters_balance: "10.5",
			processing_unit_id: "not included in model context",
		})),
	});

	expect(result).toEqual({
		total_balance_count: 12,
		sampled_balance_count: 5,
		balances: [
			{
				item_name: "item-0",
				item_code: null,
				wool_content: "100%",
				color_code: null,
				dye_lot_no: null,
				rolls_balance: 1,
				meters_balance: "10.5",
			},
			{
				item_name: "item-1",
				item_code: null,
				wool_content: "100%",
				color_code: null,
				dye_lot_no: null,
				rolls_balance: 1,
				meters_balance: "10.5",
			},
			{
				item_name: "item-2",
				item_code: null,
				wool_content: "100%",
				color_code: null,
				dye_lot_no: null,
				rolls_balance: 1,
				meters_balance: "10.5",
			},
			{
				item_name: "item-3",
				item_code: null,
				wool_content: "100%",
				color_code: null,
				dye_lot_no: null,
				rolls_balance: 1,
				meters_balance: "10.5",
			},
			{
				item_name: "item-4",
				item_code: null,
				wool_content: "100%",
				color_code: null,
				dye_lot_no: null,
				rolls_balance: 1,
				meters_balance: "10.5",
			},
		],
	});
});
