import type { AuthResponse } from "@/types/auth";
import { apiRequest } from "./client";

export function getCurrentUser() {
  return apiRequest<AuthResponse>("/auth/me");
}

export function login(email: string, password: string) {
  return apiRequest<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function signup(name: string, email: string, password: string) {
  return apiRequest<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify({ name, email, password }) });
}
