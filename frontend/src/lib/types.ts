export interface Student {
  id: string;
  name: string;
  username: string;
  age_group: string;
  created_at?: string;
  updated_at?: string;
  educator_id?: string;
}

export interface PlanningNote {
  id: string;
  title: string;
  content: string;
  category?: string;
  created_at?: string;
  updated_at?: string;
}

export interface GreatStory {
  id: string;
  title: string;
  topic?: string;
  content: string;
  age_group?: string;
  story_type?: string;
  created_at?: string;
}

export interface Conversation {
  id: string;
  session_id: string;
  title: string;
  interface_type: string;
  created_at?: string;
  updated_at?: string;
}

export interface Activity {
  id: string;
  type: string;
  content?: string;
  subject?: string;
  created_at?: string;
}

export interface Educator {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface SchoolInfo {
  id: string;
  name?: string;
  school_name?: string;
  school_type?: string;
  code?: string;
  school_code?: string;
  license_count?: number;
  educator_count?: number;
}

export interface SafetyAlert {
  id: string;
  student_id: string;
  student_name?: string;
  content: string;
  status: string;
  created_at?: string;
}

export interface AuditLog {
  id: string;
  action: string;
  details?: string;
  created_at?: string;
}

export interface LessonPlanRequest {
  topic: string;
  age_group: string;
  subject?: string;
  duration?: string;
  additional_context?: string;
}

export interface GreatStoryRequest {
  topic: string;
  age_group: string;
  story_type?: string;
  additional_context?: string;
}

export interface CreateStudentRequest {
  name: string;
  username: string;
  password: string;
  age_group: string;
  consent_given: boolean;
}

export interface CreateNoteRequest {
  title: string;
  content: string;
  category?: string;
}
