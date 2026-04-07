import type {
  Student, PlanningNote, GreatStory, Conversation, Activity,
  Educator, SchoolInfo, SafetyAlert, AuditLog,
  LessonPlanRequest, GreatStoryRequest, CreateStudentRequest, CreateNoteRequest,
} from './types';

const BASE = '/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function getToken(): string | null {
  return localStorage.getItem('guide_token');
}

export function setToken(token: string) {
  localStorage.setItem('guide_token', token);
}

export function clearToken() {
  localStorage.removeItem('guide_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const errData: { detail?: string; message?: string } = await res.json();
      msg = errData.detail || errData.message || msg;
    } catch {
      // response body not JSON
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: 'POST', body: formData }),
};

export interface User {
  email: string;
  name: string;
  role: string;
  school_id?: string;
  school_name?: string;
  institution?: string;
}

export interface StudentUser {
  username: string;
  name: string;
  role: 'student';
  student_id: string;
}

export interface AuthResponse {
  token: string;
  user: User | StudentUser;
}

export interface SessionResponse {
  authenticated: boolean;
  user?: User | StudentUser;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const auth = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }),
  signup: (data: { name: string; email: string; password: string; role?: string }) =>
    api.post<AuthResponse>('/auth/signup', data),
  studentLogin: (username: string, password: string) =>
    api.post<AuthResponse>('/auth/login/student', { username, password }),
  session: () => api.get<SessionResponse>('/auth/session'),
  logout: () => api.post<{ message: string }>('/auth/logout'),
  forgotPassword: (email: string) =>
    api.post<{ message: string }>('/auth/forgot-password', { email }),
  resetPassword: (token: string, new_password: string) =>
    api.post<{ message: string }>('/auth/reset-password', { token, new_password }),
  changePassword: (current_password: string, new_password: string) =>
    api.post<{ message: string }>('/auth/change-password', { current_password, new_password }),
  joinSchool: (school_code: string) =>
    api.post<{ message: string }>('/auth/school-join', { school_code }),
  setupSchool: (data: { school_name: string; school_type?: string; setup_token?: string }) =>
    api.post<{ school_id: string; school_code: string }>('/auth/school-setup', data),
};

export const users = {
  me: () => api.get<User>('/users/me'),
  updateMe: (data: Partial<{ name: string; institution: string }>) =>
    api.patch<User>('/users/me', data),
  updateEmail: (email: string) => api.put<User>('/users/me/email', { email }),
  deleteAccount: () => api.delete<{ message: string }>('/users/me'),
};

export const tools = {
  chat: (data: { message: string; history?: ChatMessage[]; interface_type?: string }) =>
    api.post<{ response: string }>('/tools/chat', data),
  companionChat: (data: { message: string; history?: ChatMessage[]; card_id?: string; session_id?: string }) =>
    api.post<{ response: string; session_id?: string }>('/tools/companion/chat', data),
  imaginariumChat: (data: { message: string; history?: ChatMessage[]; session_id?: string }) =>
    api.post<{ response: string; session_id?: string }>('/tools/imaginarium/chat', data),
  pdExpertChat: (data: { message: string; history?: ChatMessage[]; session_id?: string }) =>
    api.post<{ response: string; session_id?: string }>('/tools/pd-expert/chat', data),
  lessonPlan: (data: LessonPlanRequest) => api.post<{ content: string }>('/tools/lesson-plan', data),
  align: (data: LessonPlanRequest) => api.post<{ content: string }>('/tools/align', data),
  differentiate: (data: LessonPlanRequest) => api.post<{ content: string }>('/tools/differentiate', data),
  greatStory: (data: GreatStoryRequest) => api.post<{ content: string }>('/tools/great-story', data),
  listGreatStories: () => api.get<{ stories: GreatStory[] }>('/tools/great-story'),
  getGreatStory: (id: string) => api.get<GreatStory>(`/tools/great-story/${id}`),
  deleteGreatStory: (id: string) => api.delete<{ message: string }>(`/tools/great-story/${id}`),
  listConversations: (interfaceType: string) =>
    api.get<{ conversations: Conversation[] }>(`/tools/conversations?interface=${interfaceType}`),
  createConversation: (data: { interface_type: string; title?: string }) =>
    api.post<{ session_id: string }>('/tools/conversations', data),
  getMessages: (sessionId: string) =>
    api.get<{ messages: ChatMessage[] }>(`/tools/conversations/${sessionId}/messages`),
  renameConversation: (id: string, title: string) =>
    api.put<{ message: string }>(`/tools/conversations/${id}`, { title }),
  deleteConversation: (id: string) => api.delete<{ message: string }>(`/tools/conversations/${id}`),
  studentTutor: (data: { message: string; subject?: string; history?: ChatMessage[]; session_id?: string }) =>
    api.post<{ response: string; session_id?: string }>('/tools/chat', { ...data, interface_type: 'student' }),
};

export const studentsMgmt = {
  list: () => api.get<{ students: Student[] }>('/students/'),
  get: (id: string) => api.get<Student>(`/students/${id}`),
  create: (data: CreateStudentRequest) => api.post<Student>('/students/', data),
  update: (id: string, data: Partial<Student>) => api.put<Student>(`/students/${id}`, data),
  delete: (id: string) => api.delete<{ message: string }>(`/students/${id}`),
  activities: (id: string) => api.get<{ activities: Activity[] }>(`/students/${id}/activities`),
  learningJourney: (id: string) => api.get<{ journey: Record<string, unknown> }>(`/students/${id}/learning-journey`),
  grantAccess: (id: string, data: { educator_email: string }) => api.post<{ message: string }>(`/students/${id}/grant-access`, data),
  consent: (id: string) => api.get<{ consent_records: Array<{ type: string; granted_at: string }> }>(`/students/${id}/consent`),
  safetyAlerts: (id: string) => api.get<{ alerts: SafetyAlert[] }>(`/students/${id}/safety-alerts`),
  revokeAccess: (studentId: string, educatorId: string) =>
    api.delete<{ message: string }>(`/students/${studentId}/revoke-access/${educatorId}`),
  chatHistory: (id: string) =>
    api.get<{ sessions: Array<{ id: string; subject?: string; created_at?: string; message_count?: number; last_message?: string }> }>(`/students/${id}/chat-history`),
};

export const notes = {
  list: () => api.get<{ notes: PlanningNote[] }>('/notes/'),
  create: (data: CreateNoteRequest) => api.post<PlanningNote>('/notes/', data),
  update: (id: string, data: Partial<CreateNoteRequest>) => api.put<PlanningNote>(`/notes/${id}`, data),
  delete: (id: string) => api.delete<{ message: string }>(`/notes/${id}`),
};

export const schools = {
  mine: () => api.get<SchoolInfo>('/schools/mine'),
  educators: (schoolId: string) => api.get<{ educators: Educator[] }>(`/schools/${schoolId}/educators`),
  removeEducator: (schoolId: string, educatorId: string) =>
    api.delete<{ message: string }>(`/schools/${schoolId}/educators/${educatorId}`),
};

export const dataApi = {
  export: () => api.get<Record<string, unknown>>('/data/export'),
  retentionStatus: () => api.get<{ status: string }>('/data/retention-status'),
  auditLogs: (studentId?: string) =>
    api.get<{ logs: AuditLog[] }>(`/data/audit-logs${studentId ? `?student_id=${studentId}` : ''}`),
  safetyAlerts: () => api.get<{ alerts: SafetyAlert[] }>('/data/safety-alerts'),
  reviewAlert: (alertId: string) => api.post<{ message: string }>(`/data/safety-alerts/${alertId}/review`),
};

export const PD_EXPERT_ALLOWED_EMAILS = ['guideaichat@gmail.com', 'ben@hmswairoa.net'];
