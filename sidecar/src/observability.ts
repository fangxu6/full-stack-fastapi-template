type QueryOutcome = "completed" | "failed";

type QueryResultLog = {
	httpStatus: number;
	outcome: QueryOutcome;
	requestId: string | null;
};

type InfoLogger = {
	info: (message: string) => void;
};

export function logQueryResult(
	logger: InfoLogger,
	{ httpStatus, outcome, requestId }: QueryResultLog,
): void {
	logger.info(
		JSON.stringify({
			event: "inventory_query_result",
			request_id: requestId,
			outcome,
			http_status: httpStatus,
		}),
	);
}
