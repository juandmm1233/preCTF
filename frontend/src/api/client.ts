export type User = {
  id: string;
  email: string;
  student_code: string;
  full_name: string;
  score: number;
  is_admin: boolean;
  created_at: string;
};

export type LevelStatus = "locked" | "available" | "completed";

export type LevelCard = {
  id: number;
  order_index: number;
  slug: string;
  title: string;
  vector_name: string;
  lab_endpoint: string;
  description: string;
  points: number;
  hint_cost: number;
  is_bonus: boolean;
  status: LevelStatus;
  hint_used: boolean;
  completed_at: string | null;
};

export type Dashboard = {
  user: User;
  completed: number;
  total: number;
  levels: LevelCard[];
  access_token: string | null;
  token_expires_at: string | null;
};

export type SubmitResult = {
  ok: boolean;
  result: "correct" | "incorrect" | "honeypot" | "already_completed";
  points: number;
  points_delta: number;
  unlocked_next: boolean;
  message: string;
  token: string | null;
};

export type HintResult = {
  hint: string;
  already_used: boolean;
  points_delta: number;
  score: number;
};

const TOKEN_KEY = "prectf_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseError(res: Response): Promise<string> {
  const data = await res.json().catch(() => null);
  if (data?.detail?.message) return data.detail.message;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  return "Error inesperado.";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    if (!path.startsWith("/api/auth/login")) {
      window.location.assign("/login");
    }
  }
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  register: (body: {
    email: string;
    student_code: string;
    full_name: string;
    password: string;
  }) => request<{ access_token: string }>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (identifier: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  submit: (levelId: number, flag: string) =>
    request<SubmitResult>(`/api/levels/${levelId}/submit`, {
      method: "POST",
      body: JSON.stringify({ flag }),
    }),
  hint: (levelId: number) =>
    request<HintResult>(`/api/levels/${levelId}/hint`, { method: "POST" }),
};
