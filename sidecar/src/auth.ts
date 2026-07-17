import { timingSafeEqual } from "node:crypto";

export function authorizeBffRequest(
	suppliedToken: string | null,
	expectedToken: string,
): void {
	if (
		!suppliedToken ||
		suppliedToken.length !== expectedToken.length ||
		!timingSafeEqual(Buffer.from(suppliedToken), Buffer.from(expectedToken))
	) {
		throw new Error("Unauthorized orchestrator request");
	}
}
