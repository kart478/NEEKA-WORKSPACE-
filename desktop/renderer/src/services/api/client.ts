export type ApiRequest = { method?: string; path: string; body?: unknown; query?: Record<string, string> };

export const apiClient = {
  request<T>(request: ApiRequest): Promise<T> { return window.neeka.request(request) as Promise<T>; },
  health() { return window.neeka.health(); },
};

export const usersApi = {
  list: <T = unknown[]>() => apiClient.request<T>({ path: "/api/v1/users" }),
  create: <T = unknown>(body: { name: string; email: string; role?: string }) => apiClient.request<T>({
    method: "POST",
    path: "/api/v1/users",
    body,
  }),
};

export const projectsApi = {
  list: <T = unknown[]>() => apiClient.request<T>({ path: "/api/v1/projects" }),
  create: <T = unknown>(body: { name: string; description?: string; owner_id: string }) => apiClient.request<T>({
    method: "POST",
    path: "/api/v1/projects",
    body,
  }),
  get: <T = unknown>(projectId: string) => apiClient.request<T>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}` }),
  members: <T = unknown[]>(projectId: string) => apiClient.request<T>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/members` }),
  artifacts: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/artifacts`,
    query: { actor_id: actorId },
  }),
};