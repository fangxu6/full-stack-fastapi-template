import type { z } from "zod";

import { authorizeBffRequest } from "./auth";
import {
	failedQueryResponseSchema,
	type failureCategorySchema,
	type QueryRequest,
	type QueryResponse,
	queryRequestSchema,
	queryResponseSchema,
} from "./protocol";

type InventoryWorkflowInput = {
	actorGrant: string;
	request: QueryRequest;
	requestId: string;
};

type InventoryAppConfig = {
	orchestratorServiceToken: string;
	runQuery: (input: InventoryWorkflowInput) => Promise<QueryResponse>;
};

function failedResponse(
	category: z.infer<typeof failureCategorySchema>,
	status: number,
): Response {
	return Response.json(
		failedQueryResponseSchema.parse({
			status: "failed",
			error: {
				category,
				retryable:
					category === "timeout" ||
					category === "rate_limited" ||
					category === "provider_unavailable",
			},
		}),
		{ status },
	);
}

export function createInventoryApp({
	orchestratorServiceToken,
	runQuery,
}: InventoryAppConfig) {
	return async function handleInventoryQuery(
		request: Request,
	): Promise<Response> {
		const { pathname } = new URL(request.url);
		if (pathname === "/health" && request.method === "GET") {
			return Response.json({ status: "ok" });
		}
		if (pathname !== "/v1/inventory/query") {
			return new Response(null, { status: 404 });
		}
		if (request.method !== "POST") {
			return new Response(null, { status: 405 });
		}

		try {
			authorizeBffRequest(
				request.headers.get("X-AI-Orchestrator-Token"),
				orchestratorServiceToken,
			);
		} catch {
			return failedResponse("tool_rejected", 401);
		}

		const actorGrant = request.headers.get("X-AI-Actor-Grant");
		const requestId = request.headers.get("X-Request-ID");
		if (!actorGrant || !requestId) {
			return failedResponse("invalid_response", 400);
		}

		let parsedRequest: QueryRequest;
		try {
			parsedRequest = queryRequestSchema.parse(await request.json());
		} catch {
			return failedResponse("invalid_response", 400);
		}

		try {
			const response = await runQuery({
				actorGrant,
				request: parsedRequest,
				requestId,
			});
			return Response.json(queryResponseSchema.parse(response));
		} catch {
			return failedResponse("invalid_response", 502);
		}
	};
}
