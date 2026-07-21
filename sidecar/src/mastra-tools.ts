import { createTool } from "@mastra/core/tools";
import type { JSONSchema7 } from "json-schema";
import { z } from "zod";

import type { InventoryToolClient, InventoryToolContext } from "./tools";

type InventoryToolsConfig = {
	client: InventoryToolClient;
	context: InventoryToolContext;
};

const MAX_BALANCE_CONTEXT_RECORDS = 5;

const nullableUuid = z.uuid().nullable();
const nullableShortText = z.string().trim().min(1).max(255).nullable();
const pagingInput = {
	limit: z.number().int().min(1).max(20),
	skip: z.number().int().nonnegative(),
};
const balancesInputSchema = z
	.object({
		ledger_kind: z.enum(["RAW", "FINISHED"]),
		processing_unit_id: nullableUuid,
		item_name: nullableShortText,
		...pagingInput,
	})
	.strict();
const unitsInputSchema = z
	.object({
		name: nullableShortText,
		is_active: z.boolean().nullable(),
		...pagingInput,
	})
	.strict();
const documentsInputSchema = z
	.object({
		document_type: z
			.enum([
				"RAW_RECEIPT",
				"RAW_RETURN",
				"FINISHED_RECEIPT",
				"FINISHED_SHIPMENT",
			])
			.nullable(),
		business_date_from: z.iso.date().nullable(),
		business_date_to: z.iso.date().nullable(),
		processing_unit_id: nullableUuid,
		receiving_unit_id: nullableUuid,
		document_number: z.string().trim().min(1).max(64).nullable(),
		...pagingInput,
	})
	.strict();
const ledgerInputSchema = z
	.object({
		ledger_kind: z.enum(["RAW", "FINISHED"]),
		processing_unit_id: z.uuid(),
		item_name: z.string().trim().min(1).max(255),
		wool_content: z.string().trim().min(1).max(255),
		item_code: z.string().trim().max(255).nullable(),
		color_code: z.string().trim().max(255).nullable(),
		dye_lot_no: z.string().trim().max(255).nullable(),
		...pagingInput,
	})
	.strict();

const balanceContextSchema = z.object({
	count: z.number().int().nonnegative(),
	data: z.array(
		z.object({
			item_name: z.string(),
			item_code: z.string().nullable(),
			wool_content: z.string(),
			color_code: z.string().nullable(),
			dye_lot_no: z.string().nullable(),
			rolls_balance: z.union([z.number(), z.string()]),
			meters_balance: z.union([z.number(), z.string()]),
		}),
	),
});

function toToolSchema(schema: z.ZodType): JSONSchema7 {
	return z.toJSONSchema(schema) as JSONSchema7;
}

export function compactBalancesForModel(result: unknown) {
	const parsed = balanceContextSchema.parse(result);
	const balances = parsed.data.slice(0, MAX_BALANCE_CONTEXT_RECORDS);
	return {
		total_balance_count: parsed.count,
		sampled_balance_count: balances.length,
		balances,
	};
}

export function createInventoryTools({
	client,
	context,
}: InventoryToolsConfig) {
	return {
		balances: createTool({
			id: "balances",
			description: "查询来料或成品库存余额，仅返回最多 20 条只读记录。",
			strict: true,
			inputSchema: toToolSchema(balancesInputSchema),
			execute: async (input) => {
				const parsed = balancesInputSchema.parse(input);
				const response = await client.readBalances(context, {
					...parsed,
					processing_unit_id: parsed.processing_unit_id ?? undefined,
					item_name: parsed.item_name ?? undefined,
				});
				return {
					source: response.source,
					...compactBalancesForModel(response.result),
				};
			},
		}),
		processing_units: createTool({
			id: "processing_units",
			description: "查询加工单位，仅返回最多 20 条只读记录。",
			strict: true,
			inputSchema: toToolSchema(unitsInputSchema),
			execute: (input) => {
				const parsed = unitsInputSchema.parse(input);
				return client.readProcessingUnits(context, {
					...parsed,
					is_active: parsed.is_active ?? undefined,
					name: parsed.name ?? undefined,
				});
			},
		}),
		receiving_units: createTool({
			id: "receiving_units",
			description: "查询收货单位，仅返回最多 20 条只读记录。",
			strict: true,
			inputSchema: toToolSchema(unitsInputSchema),
			execute: (input) => {
				const parsed = unitsInputSchema.parse(input);
				return client.readReceivingUnits(context, {
					...parsed,
					is_active: parsed.is_active ?? undefined,
					name: parsed.name ?? undefined,
				});
			},
		}),
		documents: createTool({
			id: "documents",
			description: "查询库存业务单据，不包含已删除记录，最多返回 20 条。",
			strict: true,
			inputSchema: toToolSchema(documentsInputSchema),
			execute: (input) => {
				const parsed = documentsInputSchema.parse(input);
				return client.readDocuments(context, {
					...parsed,
					business_date_from: parsed.business_date_from ?? undefined,
					business_date_to: parsed.business_date_to ?? undefined,
					document_number: parsed.document_number ?? undefined,
					document_type: parsed.document_type ?? undefined,
					processing_unit_id: parsed.processing_unit_id ?? undefined,
					receiving_unit_id: parsed.receiving_unit_id ?? undefined,
				});
			},
		}),
		ledger: createTool({
			id: "ledger",
			description: "查询某库存余额键对应的台账变动，最多返回 20 条只读记录。",
			strict: true,
			inputSchema: toToolSchema(ledgerInputSchema),
			execute: (input) => {
				const parsed = ledgerInputSchema.parse(input);
				return client.readLedger(context, {
					...parsed,
					color_code: parsed.color_code ?? undefined,
					dye_lot_no: parsed.dye_lot_no ?? undefined,
					item_code: parsed.item_code ?? undefined,
				});
			},
		}),
	};
}
