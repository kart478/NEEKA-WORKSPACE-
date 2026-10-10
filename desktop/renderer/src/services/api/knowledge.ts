import { apiClient } from "./client";

export const knowledgeApi = {
  project: <T = unknown>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/knowledge`,
    query: { actor_id: actorId },
  }),
  search: <T = unknown[]>(projectId: string, keyword: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/knowledge/search`,
    query: { keyword, actor_id: actorId },
  }),
  documents: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/documents`,
    query: { actor_id: actorId },
  }),
  requirements: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/requirements`,
    query: { actor_id: actorId },
  }),
  decisions: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/decisions`,
    query: { actor_id: actorId },
  }),
  notes: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/notes`,
    query: { actor_id: actorId },
  }),
  references: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/references`,
    query: { actor_id: actorId },
  }),
};