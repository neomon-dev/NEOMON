const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001/api/v1";

type ErrorPayload = {
  error?: string;
  message?: string;
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
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

export function resolveApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = apiBaseUrl.replace(/\/+$/, "");
  let normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // If base already ends with /api/v1
  if (base.endsWith("/api/v1")) {
    if (normalizedPath.startsWith("/api/v1/")) {
      normalizedPath = normalizedPath.slice(7);
    }
    return `${base}${normalizedPath}`;
  }

  // Base does not end with /api/v1
  if (normalizedPath.startsWith("/api/v1/")) {
    return `${base}${normalizedPath}`;
  }

  // Ensure standard /api/v1 prefix is included
  return `${base}/api/v1${normalizedPath}`;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("neomon_session_token");
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  if (init?.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const mergedInit: RequestInit = {
    ...init,
    headers,
    credentials: init?.credentials ?? "include",
  };

  const targetUrl = resolveApiUrl(path);

  let response: Response;
  try {
    response = await fetch(targetUrl, mergedInit);
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
    const detailsArray = Array.isArray(errorPayload?.detail)
      ? errorPayload.detail
      : Array.isArray(errorPayload?.details)
      ? errorPayload.details
      : undefined;
    const validationDetails = detailsArray
      ?.map((detail) => `${detail.loc?.join(".") ?? "request"}: ${detail.msg ?? "invalid value"}`)
      .join("; ");
    const detailString = typeof errorPayload?.detail === "string" ? errorPayload.detail : undefined;
    const message = validationDetails || detailString || errorPayload?.message || `Backend request failed (${response.status}).`;
    throw new ApiError(message, response.status, errorPayload?.error);
  }

  if (payload === undefined) {
    throw new Error("The backend returned an empty response.");
  }
  return payload as T;
}

export { apiBaseUrl };
