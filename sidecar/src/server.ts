import { createInventoryApp } from "./app";
import { loadConfig } from "./config";
import { logQueryResult } from "./observability";
import { createInventoryWorkflow } from "./workflow";

const config = loadConfig(Bun.env);
const workflow = createInventoryWorkflow({
	providerApiKey: config.AI_PROVIDER_API_KEY,
	providerBaseUrl: config.AI_PROVIDER_BASE_URL,
	providerName: config.AI_PROVIDER_NAME,
	internalBaseUrl: config.AI_INTERNAL_BASE_URL,
	internalServiceToken: config.AI_INTERNAL_SERVICE_TOKEN,
});

const app = createInventoryApp({
	orchestratorServiceToken: config.AI_ORCHESTRATOR_SERVICE_TOKEN,
	runQuery: async (input) => {
		try {
			const response = await workflow({
				actorGrant: input.actorGrant,
				question: input.request.question,
				requestId: input.requestId,
				runId: input.request.run_id,
			});
			logQueryResult(console, {
				httpStatus: 200,
				outcome: response.status,
				requestId: input.requestId,
			});
			return response;
		} catch (error) {
			logQueryResult(console, {
				httpStatus: 502,
				outcome: "failed",
				requestId: input.requestId,
			});
			throw error;
		}
	},
});

Bun.serve({
	fetch: app,
	hostname: "0.0.0.0",
	port: 3000,
});
