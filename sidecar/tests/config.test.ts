import { expect, test } from "bun:test";

import { loadConfig } from "../src/config";

const validEnvironment = {
	AI_INTERNAL_BASE_URL: "http://backend:8000",
	AI_INTERNAL_SERVICE_TOKEN: "internal-service-token",
	AI_ORCHESTRATOR_SERVICE_TOKEN: "orchestrator-service-token",
	AI_PROVIDER_API_KEY: "provider-key",
	AI_PROVIDER_BASE_URL: "https://provider.example.com/v1",
	AI_PROVIDER_NAME: "internal-gateway",
	AI_PROVIDER_MODEL: "gpt-5.6-luna",
} as const;

test("loads the approved sidecar configuration", () => {
	expect(loadConfig(validEnvironment)).toEqual({
		...validEnvironment,
		AI_PROVIDER_ALLOW_INSECURE_HTTP: false,
		AI_PROVIDER_REASONING_EFFORT: "medium",
		AI_SIDECAR_HOST: "127.0.0.1",
	});
});

test("allows an explicit all-interface bind only for container deployment", () => {
	expect(
		loadConfig({ ...validEnvironment, AI_SIDECAR_HOST: "0.0.0.0" })
			.AI_SIDECAR_HOST,
	).toBe("0.0.0.0");
});

test("rejects sidecar binds to arbitrary network interfaces", () => {
	expect(() =>
		loadConfig({ ...validEnvironment, AI_SIDECAR_HOST: "192.168.1.20" }),
	).toThrow("AI_SIDECAR_HOST must be 127.0.0.1 or 0.0.0.0");
});

test("allows an HTTP provider endpoint only with an explicit opt-in", () => {
	const environment = {
		...validEnvironment,
		AI_PROVIDER_ALLOW_INSECURE_HTTP: "true",
		AI_PROVIDER_BASE_URL: "http://llm-gateway:8080/v1",
	};

	expect(loadConfig(environment).AI_PROVIDER_BASE_URL).toBe(
		"http://llm-gateway:8080/v1",
	);
});

test("fails closed when an HTTP provider endpoint lacks the explicit opt-in", () => {
	const environment = {
		...validEnvironment,
		AI_PROVIDER_BASE_URL: "http://llm-gateway:8080/v1",
	};

	expect(() => loadConfig(environment)).toThrow(
		"AI_PROVIDER_BASE_URL requires AI_PROVIDER_ALLOW_INSECURE_HTTP=true for HTTP",
	);
});

test("fails closed when the internal service token is missing", () => {
	const { AI_INTERNAL_SERVICE_TOKEN: _, ...environment } = validEnvironment;

	expect(() => loadConfig(environment)).toThrow(
		"AI_INTERNAL_SERVICE_TOKEN must be configured",
	);
});
