import { apiClient } from "./client";

export const intelligenceApi = {
  request: <T = unknown>(path: string, body: unknown) => apiClient.request<T>({ method: "POST", path, body }),
};