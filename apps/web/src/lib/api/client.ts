const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

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
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const validationMessage = Array.isArray(body.detail) ? body.detail[0]?.msg.replace(/^Value error, /, "") : undefined;
    const message = validationMessage ?? (typeof body.detail === "string" ? body.detail : body.error?.message) ?? "Unable to complete the request.";
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}
