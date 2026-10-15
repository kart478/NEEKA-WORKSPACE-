import { apiClient } from "./client";

export type DevMetadataInput = {
  actor_id: string;
  work_type?: string;
  severity?: string;
  stage?: string;
  workflow_type?: string;
  acceptance_criteria?: string;
  reproduction_steps?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  affected_component?: string;
  test_requirements?: string;
  verification_result?: string;
  review_outcome?: string;
  blocking_task_ids?: string[];
};

export const devApi = {
  listTasks: <T = unknown[]>(projectId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/dev-tasks`, query: { actor_id: actorId },
  }),
  getMetadata: <T = unknown>(taskId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dev-metadata`, query: { actor_id: actorId },
  }),
  createMetadata: <T = unknown>(taskId: string, body: DevMetadataInput) => apiClient.request<T>({
    method: "POST", path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dev-metadata`, body,
  }),
  updateMetadata: <T = unknown>(taskId: string, body: Partial<DevMetadataInput> & { actor_id: string }) => apiClient.request<T>({
    method: "PATCH", path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dev-metadata`, body,
  }),
  transition: <T = unknown>(taskId: string, stage: string, actorId: string) => apiClient.request<T>({
    method: "POST", path: `/api/v1/tasks/${encodeURIComponent(taskId)}/dev-transition`, body: { stage, actor_id: actorId },
  }),
  releaseReadiness: <T = unknown>(projectId: string, taskId: string, actorId: string) => apiClient.request<T>({
    path: `/api/v1/projects/${encodeURIComponent(projectId)}/release-readiness`, query: { task_id: taskId, actor_id: actorId },
  }),
};
