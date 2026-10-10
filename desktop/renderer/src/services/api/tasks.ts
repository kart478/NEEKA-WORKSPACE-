import { apiClient } from "./client";

export const tasksApi = {
  listByProject: <T = unknown[]>(projectId: string) => apiClient.request<T>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/tasks` }),
  get: <T = unknown>(taskId: string) => apiClient.request<T>({ path: `/api/v1/tasks/${encodeURIComponent(taskId)}` }),
  create: <T = unknown>(projectId: string, body: { title: string; description?: string; creator_id: string; priority?: string }) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/tasks`,
    body,
  }),
  update: <T = unknown>(taskId: string, body: { title?: string; description?: string; priority?: string }) => apiClient.request<T>({
    method: "PATCH",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}`,
    body,
  }),
  assign: <T = unknown>(taskId: string, body: { user_id: string; actor_id: string }) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/assign`,
    body,
  }),
  start: <T = unknown>(taskId: string, actorId: string) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/start`,
    body: { actor_id: actorId },
  }),
  complete: <T = unknown>(taskId: string, actorId: string) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/complete`,
    body: { actor_id: actorId },
  }),
  block: <T = unknown>(taskId: string, actorId: string) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/block`,
    body: { actor_id: actorId },
  }),
  cancel: <T = unknown>(taskId: string, actorId: string) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/cancel`,
    body: { actor_id: actorId },
  }),
  dependencies: <T = unknown[]>(taskId: string) => apiClient.request<T>({ path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dependencies` }),
  addDependency: <T = unknown>(taskId: string, body: { depends_on_id: string; actor_id: string }) => apiClient.request<T>({
    method: "POST",
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dependencies`,
    body,
  }),
};