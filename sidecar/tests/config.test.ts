import { expect, test } from "bun:test";

import { loadConfig } from "../src/config";

const validEnvironment = {
	AI_INTERNAL_BASE_URL: "http://backend:8000",
	AI_INTERNAL_SERVICE_TOKEN: "internal-service-token",
	AI_ORCHESTRATOR_SERVICE_TOKEN: "orchestrator-service-token",
	OPENAI_API_KEY: "sk-test",
	OPENAI_MODEL: "gpt-5.6-luna",
} as const;

test("loads the approved sidecar configuration", () => {
	expect(loadConfig(validEnvironment)).toEqual({
		...validEnvironment,
		OPENAI_REASONING_EFFORT: "medium",
	});
});

test("fails closed when the internal service token is missing", () => {
	const { AI_INTERNAL_SERVICE_TOKEN: _, ...environment } = validEnvironment;

	expect(() => loadConfig(environment)).toThrow(
		"AI_INTERNAL_SERVICE_TOKEN must be configured",
	);
});
