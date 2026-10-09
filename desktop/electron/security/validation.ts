const allowedMethods = new Set(["GET", "POST", "PATCH", "DELETE"]);

export interface ApiRequest {
  method?: string;
  path: string;
  body?: unknown;
  query?: Record<string, string>;
}

export function validateApiRequest(request: ApiRequest): Required<Pick<ApiRequest, "method" | "path">> & ApiRequest {
  if (!request || typeof request.path !== "string" || !request.path.startsWith("/api/v1/")) {
    throw new Error("Only NEEKA API paths are allowed");
  }
  if (request.path.includes("//") || request.path.includes("..") || request.path.includes("\\")) {
    throw new Error("Invalid API path");
  }
  const method = (request.method || "GET").toUpperCase();
  if (!allowedMethods.has(method)) throw new Error("Invalid API method");
  if (request.query && Object.keys(request.query).some((key) => !/^[A-Za-z0-9_.-]+$/.test(key))) {
    throw new Error("Invalid API query");
  }
  return { ...request, method };
}