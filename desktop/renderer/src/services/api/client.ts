export type ApiRequest = { method?: string; path: string; body?: unknown; query?: Record<string, string> };

export const apiClient = {
  request<T>(request: ApiRequest): Promise<T> { return window.neeka.request(request) as Promise<T>; },
  health() { return window.neeka.health(); },
};

export const projectsApi = {
  list: () => apiClient.request<unknown[]>({ path: "/api/v1/projects" }),
};