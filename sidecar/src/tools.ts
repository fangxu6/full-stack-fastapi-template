import { z } from "zod";

type FetchFunction = (
	input: RequestInfo | URL,
	init?: RequestInit,
) => Promise<Response>;

type ToolContext = {
	actorGrant: string;
	requestId: string;
	runId: string;
};

export type InventoryToolContext = ToolContext;

type InventoryToolClientConfig = {
	baseUrl: string;
	fetch: FetchFunction;
	serviceToken: string;
};

const balancesInputSchema = z
	.object({
		ledger_kind: z.enum(["RAW", "FINISHED"]),
		skip: z.number().int().nonnegative().default(0),
		limit: z.number().int().min(1).max(20).default(20),
		processing_unit_id: z.uuid().optional(),
		item_name: z.string().trim().min(1).max(255).optional(),
	})
	.strict();

const balancesResponseSchema = z
	.object({
		tool_name: z.literal("balances"),
		source: z.literal("inventory:balances"),
		result: z.unknown(),
	})
	.strict();

const unitsInputSchema = z
	.object({
		skip: z.number().int().nonnegative().default(0),
		limit: z.number().int().min(1).max(20).default(20),
		name: z.string().trim().min(1).max(255).optional(),
		is_active: z.boolean().optional(),
	})
	.strict();

const processingUnitsResponseSchema = z
	.object({
		tool_name: z.literal("processing_units"),
		source: z.literal("inventory:processing_units"),
		result: z.unknown(),
	})
	.strict();

const receivingUnitsResponseSchema = z
	.object({
		tool_name: z.literal("receiving_units"),
		source: z.literal("inventory:receiving_units"),
		result: z.unknown(),
	})
	.strict();

const documentsInputSchema = z
	.object({
		skip: z.number().int().nonnegative().default(0),
		limit: z.number().int().min(1).max(20).default(20),
		document_type: z
			.enum([
				"RAW_RECEIPT",
				"RAW_RETURN",
				"FINISHED_RECEIPT",
				"FINISHED_SHIPMENT",
			])
			.optional(),
		business_date_from: z.iso.date().optional(),
		business_date_to: z.iso.date().optional(),
		processing_unit_id: z.uuid().optional(),
		receiving_unit_id: z.uuid().optional(),
		document_number: z.string().trim().min(1).max(64).optional(),
	})
	.strict();

const documentsResponseSchema = z
	.object({
		tool_name: z.literal("documents"),
		source: z.literal("inventory:documents"),
		result: z.unknown(),
	})
	.strict();

const ledgerInputSchema = z
	.object({
		ledger_kind: z.enum(["RAW", "FINISHED"]),
		processing_unit_id: z.uuid(),
		item_name: z.string().trim().min(1).max(255),
		wool_content: z.string().trim().min(1).max(255),
		skip: z.number().int().nonnegative().default(0),
		limit: z.number().int().min(1).max(20).default(20),
		item_code: z.string().trim().max(255).optional(),
		color_code: z.string().trim().max(255).optional(),
		dye_lot_no: z.string().trim().max(255).optional(),
	})
	.strict();

const ledgerResponseSchema = z
	.object({
		tool_name: z.literal("ledger"),
		source: z.literal("inventory:ledger"),
		result: z.unknown(),
	})
	.strict();

export class InventoryToolRejectedError extends Error {
	constructor() {
		super("Inventory tool request was rejected");
	}
}

export class InventoryToolFailedError extends Error {
	constructor() {
		super("Inventory tool request failed");
	}
}

export class InventoryToolInvalidResponseError extends Error {
	constructor() {
		super("Inventory tool returned an invalid response");
	}
}

function getActorUserId(actorGrant: string): string {
	const parts = actorGrant.split(".");
	if (parts.length !== 3) {
		throw new InventoryToolRejectedError();
	}

	try {
		const payload: unknown = JSON.parse(
			Buffer.from(parts[1], "base64url").toString("utf-8"),
		);
		const parsed = z.object({ sub: z.uuid() }).strict().safeParse(payload);
		if (!parsed.success) {
			throw new InventoryToolRejectedError();
		}
		return parsed.data.sub;
	} catch (error) {
		if (error instanceof InventoryToolRejectedError) {
			throw error;
		}
		throw new InventoryToolRejectedError();
	}
}

function createToolUrl(baseUrl: string, path: string): string {
	return new URL(path, `${baseUrl.replace(/\/$/, "")}/`).toString();
}

export function createInventoryToolClient({
	baseUrl,
	fetch,
	serviceToken,
}: InventoryToolClientConfig) {
	async function postTool<T>(
		path: string,
		context: ToolContext,
		body: object,
		responseSchema: z.ZodType<T>,
	): Promise<T> {
		const response = await fetch(createToolUrl(baseUrl, path), {
			body: JSON.stringify({
				actor_user_id: getActorUserId(context.actorGrant),
				...body,
				run_id: context.runId,
			}),
			headers: {
				"Content-Type": "application/json",
				"X-AI-Actor-Grant": context.actorGrant,
				"X-AI-Service-Token": serviceToken,
				"X-Request-ID": context.requestId,
			},
			method: "POST",
		});

		if (response.status === 401 || response.status === 403) {
			throw new InventoryToolRejectedError();
		}
		if (!response.ok) {
			throw new InventoryToolFailedError();
		}

		try {
			return responseSchema.parse(await response.json());
		} catch (error) {
			if (error instanceof z.ZodError || error instanceof SyntaxError) {
				throw new InventoryToolInvalidResponseError();
			}
			throw error;
		}
	}

	return {
		async readBalances(
			context: ToolContext,
			input: z.input<typeof balancesInputSchema>,
		) {
			return postTool(
				"/api/v1/internal/ai/inventory/balances",
				context,
				balancesInputSchema.parse(input),
				balancesResponseSchema,
			);
		},

		async readProcessingUnits(
			context: ToolContext,
			input: z.input<typeof unitsInputSchema> = {},
		) {
			return postTool(
				"/api/v1/internal/ai/inventory/processing-units",
				context,
				unitsInputSchema.parse(input),
				processingUnitsResponseSchema,
			);
		},

		async readReceivingUnits(
			context: ToolContext,
			input: z.input<typeof unitsInputSchema> = {},
		) {
			return postTool(
				"/api/v1/internal/ai/inventory/receiving-units",
				context,
				unitsInputSchema.parse(input),
				receivingUnitsResponseSchema,
			);
		},

		async readDocuments(
			context: ToolContext,
			input: z.input<typeof documentsInputSchema>,
		) {
			return postTool(
				"/api/v1/internal/ai/inventory/documents",
				context,
				documentsInputSchema.parse(input),
				documentsResponseSchema,
			);
		},

		async readLedger(
			context: ToolContext,
			input: z.input<typeof ledgerInputSchema>,
		) {
			return postTool(
				"/api/v1/internal/ai/inventory/ledger",
				context,
				ledgerInputSchema.parse(input),
				ledgerResponseSchema,
			);
		},
	};
}

export type InventoryToolClient = ReturnType<typeof createInventoryToolClient>;
