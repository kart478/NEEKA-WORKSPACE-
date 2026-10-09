import { apiClient } from "./client";

export const knowledgeApi = {
  search: <T = unknown[]>(projectId: string, keyword: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/knowledge/search`,
    query: { keyword, actor_id: actorId },
  }),
};