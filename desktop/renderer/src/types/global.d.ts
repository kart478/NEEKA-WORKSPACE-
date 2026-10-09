export {};

declare global {
  interface Window {
    neeka: {
      health: () => Promise<{ state: string; health?: { status: string; service?: string }; error?: string }>;
      request: (request: { method?: string; path: string; body?: unknown; query?: Record<string, string> }) => Promise<unknown>;
    };
  }
}