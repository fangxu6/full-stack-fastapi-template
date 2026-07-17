import { expect, test } from "bun:test";

import { authorizeBffRequest } from "../src/auth";

test("rejects a missing BFF service token", () => {
	expect(() => authorizeBffRequest(null, "expected-token")).toThrow(
		"Unauthorized orchestrator request",
	);
});
