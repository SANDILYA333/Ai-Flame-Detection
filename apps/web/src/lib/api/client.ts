/**
 * Production-ready typed HTTP API Client for SIH26162
 */

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly statusText: string;
  public readonly data: unknown;
  public readonly isNetworkError: boolean;

  constructor({
    message,
    status = 500,
    statusText = "Internal Error",
    data = null,
    isNetworkError = false,
  }: {
    message: string;
    status?: number;
    statusText?: string;
    data?: unknown;
    isNetworkError?: boolean;
  }) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.statusText = statusText;
    this.data = data;
    this.isNetworkError = isNetworkError;
  }
}

export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/+$/, "");
  }
  // Default to local FastAPI backend in development
  return "http://localhost:8000";
}

export interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
  params?: Record<string, string | number | boolean | undefined | null>;
}

export async function apiFetch<T>(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const { timeoutMs = 12000, params, signal: customSignal, ...fetchInit } = options;
  const baseUrl = getApiBaseUrl();

  // 1. Build URL with query parameters
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = new URL(`${baseUrl}${cleanEndpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        url.searchParams.append(key, String(val));
      }
    });
  }

  // 2. Set up timeout controller
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (customSignal) {
    customSignal.addEventListener("abort", () => controller.abort());
  }

  try {
    const response = await fetch(url.toString(), {
      ...fetchInit,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...fetchInit.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // 3. Handle non-2xx HTTP responses
    if (!response.ok) {
      let errorBody: unknown = null;
      try {
        errorBody = await response.json();
      } catch {
        errorBody = await response.text().catch(() => null);
      }

      const errorMessage =
        typeof errorBody === "object" && errorBody !== null && "detail" in errorBody
          ? String((errorBody as any).detail)
          : `HTTP ${response.status}: ${response.statusText}`;

      throw new ApiClientError({
        message: errorMessage,
        status: response.status,
        statusText: response.statusText,
        data: errorBody,
      });
    }

    // 4. Parse successful JSON response
    const json = (await response.json()) as T;
    return json;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof ApiClientError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError({
        message: `API request to ${cleanEndpoint} timed out after ${timeoutMs}ms`,
        status: 408,
        statusText: "Request Timeout",
        isNetworkError: true,
      });
    }

    throw new ApiClientError({
      message: error instanceof Error ? error.message : "Network request failed",
      status: 0,
      statusText: "Network Error",
      isNetworkError: true,
      data: error,
    });
  }
}
