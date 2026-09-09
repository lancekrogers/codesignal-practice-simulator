export function timeResponse(session, originalTime) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: true,
      data: {
        session,
        observed_at: originalTime.observed_at,
        elapsed_seconds: originalTime.elapsed_seconds,
        remaining_seconds: session.status === "active"
          ? originalTime.remaining_seconds
          : 0,
      },
    }),
  };
}

export function timerSeconds(value) {
  const parts = value.split(":").map(Number);
  return parts.length === 2
    ? parts[0] * 60 + parts[1]
    : parts[0] * 3600 + parts[1] * 60 + parts[2];
}
