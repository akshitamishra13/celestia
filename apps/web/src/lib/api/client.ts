const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
const TOKEN_KEY = "astrolive_access_token";

export function getAccessToken() {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

type ApiErrorBody = {
  detail?: string | Array<{ msg: string }>;
  error?: { message?: string };
};

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const validationMessage = Array.isArray(body.detail) ? body.detail[0]?.msg.replace(/^Value error, /, "") : undefined;
    const message = validationMessage ?? (typeof body.detail === "string" ? body.detail : body.error?.message) ?? "Unable to complete the request.";
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}
