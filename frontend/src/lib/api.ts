import type {
  Student, PlanningNote, GreatStory, Conversation, Activity,
  Educator, SchoolInfo, SafetyAlert, AuditLog,
  LessonPlanRequest, AlignRequest, DifferentiateRequest, GreatStoryRequest,
  SavedLessonPlan, SaveLessonPlanRequest, UpdateSavedLessonPlanRequest,
  CreateStudentRequest, CreateNoteRequest,
  SignupRequest, ResetPasswordRequest, ChangePasswordRequest,
  UpdateEmailRequest, UpdateProfileRequest,
  JoinSchoolRequest, SchoolSetupRequest,
} from './types';

const BASE = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
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

function unwrapList<K extends string, T>(res: unknown, key: K): Record<K, T[]> {
  let arr: T[] = [];
  if (Array.isArray(res)) {
    arr = res as T[];
  } else if (res && typeof res === 'object') {
    const v = (res as Record<string, unknown>)[key];
    if (Array.isArray(v)) arr = v as T[];
  }
  return { [key]: arr } as Record<K, T[]>;
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
      const errData: { detail?: unknown; message?: unknown } = await res.json();
      const raw = errData.detail ?? errData.message;
      if (typeof raw === 'string') {
        msg = raw;
      } else if (Array.isArray(raw)) {
        msg = raw
          .map((d: unknown) => {
            if (d && typeof d === 'object' && 'msg' in d) {
              return String((d as { msg: unknown }).msg);
            }
            return typeof d === 'string' ? d : JSON.stringify(d);
          })
          .join('; ');
      } else if (raw != null) {
        msg = JSON.stringify(raw);
      }
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
  full_name?: string;
  role?: string;
  user_type?: string;
  is_admin?: boolean;
  id?: string;
  school_id?: string;
  school_name?: string;
  institution_name?: string;
}

export interface StudentUser {
  id?: string;
  username: string;
  full_name?: string;
  age_group?: string;
  educator_id?: string;
  is_student?: true;
}

export interface AuthResponse {
  token: string;
  user: User | StudentUser;
}

export interface SignupResponse {
  success: boolean;
  user_id: string;
  message?: string;
}

export interface SessionResponse {
  authenticated: boolean;
  user_type?: string;
  user?: User | StudentUser;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const auth = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }),
  signup: (data: SignupRequest) =>
    api.post<SignupResponse>('/auth/signup', data),
  studentLogin: (username: string, password: string) =>
    api.post<AuthResponse>('/auth/login/student', { username, password }),
  session: () => api.get<SessionResponse>('/auth/session'),
  logout: () => api.post<{ message: string }>('/auth/logout'),
  forgotPassword: (email: string) =>
    api.post<{ message: string }>('/auth/forgot-password', { email }),
  resetPassword: (data: ResetPasswordRequest) =>
    api.post<{ message: string }>('/auth/reset-password', data),
  changePassword: (data: ChangePasswordRequest) =>
    api.post<{ message: string }>('/auth/change-password', data),
  joinSchool: (data: JoinSchoolRequest) =>
    api.post<AuthResponse>('/auth/school-join', data),
  setupSchool: (data: SchoolSetupRequest) =>
    api.post<AuthResponse>('/auth/school-setup', data),
};

export const users = {
  me: () => api.get<User>('/users/me'),
  updateMe: (data: UpdateProfileRequest) =>
    api.patch<User>('/users/me', data),
  updateEmail: (data: UpdateEmailRequest) =>
    api.put<{ success: boolean; message?: string }>('/users/me/email', data),
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
  align: (data: AlignRequest) => api.post<{ content: string }>('/tools/align', data),
  differentiate: (data: DifferentiateRequest) => api.post<{ content: string }>('/tools/differentiate', data),
  greatStory: (data: GreatStoryRequest) => api.post<{ content: string }>('/tools/great-story', data),
  listGreatStories: async (): Promise<{ stories: GreatStory[] }> =>
    unwrapList<'stories', GreatStory>(await api.get<unknown>('/tools/great-story'), 'stories'),
  getGreatStory: (id: string) => api.get<GreatStory>(`/tools/great-story/${id}`),
  deleteGreatStory: (id: string) => api.delete<{ message: string }>(`/tools/great-story/${id}`),
  saveLessonPlan: (data: SaveLessonPlanRequest) =>
    api.post<SavedLessonPlan>('/tools/lesson-plans', data),
  listSavedLessonPlans: async (): Promise<{ plans: SavedLessonPlan[] }> =>
    unwrapList<'plans', SavedLessonPlan>(await api.get<unknown>('/tools/lesson-plans'), 'plans'),
  getSavedLessonPlan: (id: string) => api.get<SavedLessonPlan>(`/tools/lesson-plans/${id}`),
  updateSavedLessonPlan: (id: string, data: UpdateSavedLessonPlanRequest) =>
    api.put<SavedLessonPlan>(`/tools/lesson-plans/${id}`, data),
  deleteSavedLessonPlan: (id: string) =>
    api.delete<{ success: boolean }>(`/tools/lesson-plans/${id}`),
  listConversations: async (interfaceType: string): Promise<{ conversations: Conversation[] }> =>
    unwrapList<'conversations', Conversation>(
      await api.get<unknown>(`/tools/conversations?interface_type=${encodeURIComponent(interfaceType)}`),
      'conversations',
    ),
  createConversation: (data: { interface_type: string; title?: string }) =>
    api.post<{ session_id: string }>('/tools/conversations', data),
  getMessages: async (sessionId: string, interfaceType: string = 'companion'): Promise<{ messages: ChatMessage[] }> =>
    unwrapList<'messages', ChatMessage>(
      await api.get<unknown>(`/tools/conversations/${sessionId}/messages?interface_type=${encodeURIComponent(interfaceType)}`),
      'messages',
    ),
  renameConversation: (id: string, title: string) =>
    api.put<{ message: string }>(`/tools/conversations/${id}`, { title }),
  deleteConversation: (id: string) => api.delete<{ message: string }>(`/tools/conversations/${id}`),
  studentTutor: (data: { message: string; subject?: string; history?: ChatMessage[]; session_id?: string }) =>
    api.post<{ response: string; session_id?: string }>('/tools/chat', { ...data, interface_type: 'student' }),
  studentChat: (data: {
    message: string;
    session_id?: string;
    subjects?: string[];
    year_level?: string;
    history?: ChatMessage[];
  }) =>
    api.post<{ response: string; session_id?: string }>('/tools/chat', {
      ...data,
      interface_type: 'student',
    }),
  studentWorkFeedback: (data: {
    work_file: File;
    rubric_file?: File | null;
    session_id?: string;
    year_level?: string;
    subjects?: string[];
  }) => {
    const fd = new FormData();
    fd.append('work_file', data.work_file);
    if (data.rubric_file) fd.append('rubric_file', data.rubric_file);
    if (data.session_id) fd.append('session_id', data.session_id);
    if (data.year_level) fd.append('year_level', data.year_level);
    if (data.subjects && data.subjects.length > 0) {
      fd.append('subjects', JSON.stringify(data.subjects));
    }
    return api.postForm<{ response: string; session_id?: string }>(
      '/tools/student/work-feedback',
      fd,
    );
  },
};

type ChatSession = { id: string; subject?: string; created_at?: string; message_count?: number; last_message?: string };
type ConsentRecord = { type: string; granted_at: string };

export const studentsMgmt = {
  list: async (): Promise<{ students: Student[] }> =>
    unwrapList<'students', Student>(await api.get<unknown>('/students/'), 'students'),
  get: (id: string) => api.get<Student>(`/students/${id}`),
  create: (data: CreateStudentRequest) => api.post<Student>('/students/', data),
  update: (id: string, data: Partial<Student>) => api.put<Student>(`/students/${id}`, data),
  delete: (id: string) => api.delete<{ message: string }>(`/students/${id}`),
  activities: async (id: string): Promise<{ activities: Activity[] }> =>
    unwrapList<'activities', Activity>(await api.get<unknown>(`/students/${id}/activities`), 'activities'),
  learningJourney: (id: string) => api.get<{ journey: Record<string, unknown> }>(`/students/${id}/learning-journey`),
  grantAccess: (id: string, data: { educator_email: string }) => api.post<{ message: string }>(`/students/${id}/grant-access`, data),
  consent: async (id: string): Promise<{ consent_records: ConsentRecord[] }> =>
    unwrapList<'consent_records', ConsentRecord>(await api.get<unknown>(`/students/${id}/consent`), 'consent_records'),
  safetyAlerts: async (id: string): Promise<{ alerts: SafetyAlert[] }> =>
    unwrapList<'alerts', SafetyAlert>(await api.get<unknown>(`/students/${id}/safety-alerts`), 'alerts'),
  revokeAccess: (studentId: string, educatorId: string) =>
    api.delete<{ message: string }>(`/students/${studentId}/revoke-access/${educatorId}`),
  chatHistory: async (id: string): Promise<{ sessions: ChatSession[] }> =>
    unwrapList<'sessions', ChatSession>(await api.get<unknown>(`/students/${id}/chat-history`), 'sessions'),
};

export const notes = {
  list: async (): Promise<{ notes: PlanningNote[] }> =>
    unwrapList<'notes', PlanningNote>(await api.get<unknown>('/notes/'), 'notes'),
  create: (data: CreateNoteRequest) => api.post<PlanningNote>('/notes/', data),
  update: (id: string, data: Partial<CreateNoteRequest>) => api.put<PlanningNote>(`/notes/${id}`, data),
  delete: (id: string) => api.delete<{ message: string }>(`/notes/${id}`),
};

export const schools = {
  mine: async (): Promise<SchoolInfo | null> => {
    const res = await api.get<{ school: SchoolInfo | null }>('/schools/mine');
    return res.school ?? null;
  },
  educators: async (schoolId: string): Promise<{ educators: Educator[] }> =>
    unwrapList<'educators', Educator>(await api.get<unknown>(`/schools/${schoolId}/educators`), 'educators'),
  removeEducator: (schoolId: string, educatorId: string) =>
    api.delete<{ message: string }>(`/schools/${schoolId}/educators/${educatorId}`),
  rotateInviteCode: (schoolId: string) =>
    api.post<{ invite_code: string }>(`/schools/${schoolId}/invite-code/rotate`, {}),
};

export const dataApi = {
  export: () => api.get<Record<string, unknown>>('/data/export'),
  retentionStatus: () => api.get<{ status: string }>('/data/retention-status'),
  auditLogs: async (studentId?: string): Promise<{ logs: AuditLog[] }> =>
    unwrapList<'logs', AuditLog>(
      await api.get<unknown>(`/data/audit-logs${studentId ? `?student_id=${studentId}` : ''}`),
      'logs',
    ),
  safetyAlerts: async (): Promise<{ alerts: SafetyAlert[] }> =>
    unwrapList<'alerts', SafetyAlert>(await api.get<unknown>('/data/safety-alerts'), 'alerts'),
  reviewAlert: (alertId: string) => api.post<{ message: string }>(`/data/safety-alerts/${alertId}/review`),
};

export const PD_EXPERT_ALLOWED_EMAILS = ['guideaichat@gmail.com', 'ben@hmswairoa.net'];
