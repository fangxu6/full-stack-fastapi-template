export type SidecarConfig = {
	AI_INTERNAL_BASE_URL: string;
	AI_INTERNAL_SERVICE_TOKEN: string;
	AI_ORCHESTRATOR_SERVICE_TOKEN: string;
	AI_PROVIDER_API_KEY: string;
	AI_PROVIDER_ALLOW_INSECURE_HTTP: boolean;
	AI_PROVIDER_BASE_URL: string;
	AI_PROVIDER_MODEL: "gpt-5.6-luna";
	AI_PROVIDER_NAME: string;
	AI_PROVIDER_REASONING_EFFORT: "medium";
};

type Environment = Record<string, string | undefined>;
type RequiredConfigKey = Exclude<
	keyof SidecarConfig,
	"AI_PROVIDER_ALLOW_INSECURE_HTTP"
>;

function required(environment: Environment, name: RequiredConfigKey): string {
	const value = environment[name]?.trim();
	if (!value) {
		throw new Error(`${name} must be configured`);
	}
	return value;
}

function optionalBoolean(environment: Environment, name: string): boolean {
	const value = environment[name]?.trim().toLowerCase();
	if (!value) return false;
	if (value === "true") return true;
	if (value === "false") return false;
	throw new Error(`${name} must be true or false`);
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

function validateProviderBaseUrl(
	value: string,
	allowInsecureHttp: boolean,
): string {
	try {
		const url = new URL(value);
		if (
			(url.protocol !== "http:" && url.protocol !== "https:") ||
			url.username ||
			url.password
		) {
			throw new Error();
		}
		if (url.protocol === "http:" && !allowInsecureHttp) {
			throw new Error(
				"AI_PROVIDER_BASE_URL requires AI_PROVIDER_ALLOW_INSECURE_HTTP=true for HTTP",
			);
		}
		return value;
	} catch (error) {
		if (error instanceof Error && error.message.includes("requires")) {
			throw error;
		}
		throw new Error(
			"AI_PROVIDER_BASE_URL must be an HTTP(S) URL without credentials",
		);
	}
}

function validateProviderName(value: string): string {
	if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(value)) {
		throw new Error(
			"AI_PROVIDER_NAME must use lowercase letters, numbers, hyphens, or underscores",
		);
	}
	return value;
}

export function loadConfig(environment: Environment): SidecarConfig {
	const model = required(environment, "AI_PROVIDER_MODEL");
	if (model !== "gpt-5.6-luna") {
		throw new Error("AI_PROVIDER_MODEL must be gpt-5.6-luna");
	}
	const allowInsecureHttp = optionalBoolean(
		environment,
		"AI_PROVIDER_ALLOW_INSECURE_HTTP",
	);

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
		AI_PROVIDER_API_KEY: required(environment, "AI_PROVIDER_API_KEY"),
		AI_PROVIDER_ALLOW_INSECURE_HTTP: allowInsecureHttp,
		AI_PROVIDER_BASE_URL: validateProviderBaseUrl(
			required(environment, "AI_PROVIDER_BASE_URL"),
			allowInsecureHttp,
		),
		AI_PROVIDER_MODEL: model,
		AI_PROVIDER_NAME: validateProviderName(
			required(environment, "AI_PROVIDER_NAME"),
		),
		AI_PROVIDER_REASONING_EFFORT: "medium",
	};
}
