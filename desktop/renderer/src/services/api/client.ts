export type ApiRequest = { method?: string; path: string; body?: unknown; query?: Record<string, string> };

function bridge(): NonNullable<Window["neeka"]> {
  const candidate = window.neeka;
  if (!candidate?.request || !candidate?.health) {
    throw new Error("The desktop bridge is unavailable. Restart NEEKA Work Engine.");
  }
  return candidate;
}

export const apiClient = {
  async request<T>(request: ApiRequest): Promise<T> { return bridge().request(request) as Promise<T>; },
  async health() { return bridge().health(); },
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