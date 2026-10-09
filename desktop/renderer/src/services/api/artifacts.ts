import { apiClient } from "./client";

export const artifactsApi = {
  list: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/artifacts`, query: { actor_id: actorId },
  }),
};