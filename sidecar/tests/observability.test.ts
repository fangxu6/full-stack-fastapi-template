import { expect, test } from "bun:test";

import { logQueryResult } from "../src/observability";

test("logs only the allowlisted query result metadata", () => {
	let message: string | undefined;

	logQueryResult(
		{
			info: (value) => {
				message = value;
			},
		},
		{
			httpStatus: 200,
			outcome: "completed",
			requestId: "request-123",
		},
	);

	expect(message).toBe(
		'{"event":"inventory_query_result","request_id":"request-123","outcome":"completed","http_status":200}',
	);
});
