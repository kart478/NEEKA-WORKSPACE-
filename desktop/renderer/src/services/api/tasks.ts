import { apiClient } from "./client";

export const tasksApi = {
  get: <T = unknown>(taskId: string) => apiClient.request<T>({ path: `/api/v1/tasks/${encodeURIComponent(taskId)}` }),
};