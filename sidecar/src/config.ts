export type SidecarConfig = {
	AI_INTERNAL_BASE_URL: string;
	AI_INTERNAL_SERVICE_TOKEN: string;
	AI_ORCHESTRATOR_SERVICE_TOKEN: string;
	OPENAI_API_KEY: string;
	OPENAI_MODEL: "gpt-5.6-luna";
	OPENAI_REASONING_EFFORT: "medium";
};

type Environment = Record<string, string | undefined>;

function required(environment: Environment, name: keyof SidecarConfig): string {
	const value = environment[name]?.trim();
	if (!value) {
		throw new Error(`${name} must be configured`);
	}
	return value;
}

function validateInternalBaseUrl(value: string): string {
	try {
		const url = new URL(value);
		if (
			(url.protocol !== "http:" && url.protocol !== "https:") ||
			url.username ||
			url.password
		) {
			throw new Error();
		}
		return value;
	} catch {
		throw new Error(
			"AI_INTERNAL_BASE_URL must be an HTTP(S) URL without credentials",
		);
	}
}

export function loadConfig(environment: Environment): SidecarConfig {
	const model = required(environment, "OPENAI_MODEL");
	if (model !== "gpt-5.6-luna") {
		throw new Error("OPENAI_MODEL must be gpt-5.6-luna");
	}

	return {
		AI_INTERNAL_BASE_URL: validateInternalBaseUrl(
			required(environment, "AI_INTERNAL_BASE_URL"),
		),
		AI_INTERNAL_SERVICE_TOKEN: required(
			environment,
			"AI_INTERNAL_SERVICE_TOKEN",
		),
		AI_ORCHESTRATOR_SERVICE_TOKEN: required(
			environment,
			"AI_ORCHESTRATOR_SERVICE_TOKEN",
		),
		OPENAI_API_KEY: required(environment, "OPENAI_API_KEY"),
		OPENAI_MODEL: model,
		OPENAI_REASONING_EFFORT: "medium",
	};
}
