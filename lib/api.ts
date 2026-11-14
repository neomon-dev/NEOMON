const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

type ErrorPayload = {
  error?: string;
  message?: string;
  details?: Array<{ loc?: Array<string | number>; msg?: string }>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("neomon_session_token");
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const mergedInit: RequestInit = {
    ...init,
    headers,
    credentials: init?.credentials ?? "include",
  };

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, mergedInit);
  } catch {
    throw new Error(`Cannot reach the NEOMON backend at ${apiBaseUrl}. Start the FastAPI server and try again.`);
  }

  const rawBody = await response.text();
  let payload: T | ErrorPayload | undefined;
  if (rawBody) {
    try {
      payload = JSON.parse(rawBody) as T | ErrorPayload;
    } catch {
      payload = undefined;
    }
  }

  if (!response.ok) {
    const errorPayload = payload as ErrorPayload | undefined;
    const validationDetails = errorPayload?.details
      ?.map((detail) => `${detail.loc?.join(".") ?? "request"}: ${detail.msg ?? "invalid value"}`)
      .join("; ");
    const message = validationDetails || errorPayload?.message || `Backend request failed (${response.status}).`;
    throw new ApiError(message, response.status, errorPayload?.error);
  }

  if (payload === undefined) {
    throw new Error("The backend returned an empty response.");
  }
  return payload as T;
}

export { apiBaseUrl };
