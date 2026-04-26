export interface Student {
  id: string;
  full_name: string;
  username: string;
  age_group?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  educator_id?: string;
  educator_name?: string;
  educator_email?: string;
}

export interface PlanningNote {
  id: string;
  title: string;
  content: string;
  chapters?: string;
  images?: string;
  materials?: string;
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

export type SavedLessonPlanKind = 'lesson_plan' | 'alignment' | 'differentiation';

export interface SavedLessonPlan {
  id: string;
  title: string;
  /** Current/edited version (what we display by default). */
  content: string;
  /** Immutable AI-generated original captured at first save. */
  original_content?: string;
  age_group?: string;
  kind: SavedLessonPlanKind;
  topic?: string;
  subject?: string;
  duration?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SaveLessonPlanRequest {
  title: string;
  /** Current/edited version the user wants to keep working from. */
  content: string;
  /** Immutable AI-generated original; defaults to content if omitted. */
  original_content?: string;
  age_group?: string;
  kind: SavedLessonPlanKind;
  topic?: string;
  subject?: string;
  duration?: string;
  description?: string;
}

export interface UpdateSavedLessonPlanRequest {
  title?: string;
  content?: string;
  age_group?: string;
  kind?: SavedLessonPlanKind;
  topic?: string;
  subject?: string;
  duration?: string;
  description?: string;
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
  activity_type: string;
  prompt_text?: string;
  response_text?: string;
  session_id?: string;
  subject?: string;
  created_at?: string;
}

export interface Educator {
  id: string;
  full_name?: string;
  email: string;
  role: string;
  created_at?: string;
}

export interface SchoolInfo {
  id: string;
  name?: string;
  school_name?: string;
  school_type?: string;
  code?: string;
  school_code?: string;
  invite_code?: string;
  license_count?: number;
  educator_count?: number;
}

export interface SafetyAlert {
  id: string;
  student_id?: string;
  student_name?: string;
  alert_type?: string;
  content_snippet?: string;
  severity?: string;
  is_reviewed?: boolean;
  reviewed_by?: string;
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
  planning_type?: string;
  curriculum_type?: string;
  year_level?: string;
  subject?: string;
  duration?: string;
  additional_context?: string;
}

export interface AlignRequest {
  topic?: string;
  content?: string;
  age_group: string;
  year_level?: string;
  subject?: string;
  duration?: string;
  additional_context?: string;
}

export interface DifferentiateRequest {
  topic?: string;
  lesson_description?: string;
  class_composition?: string;
  focus_area?: string;
  age_group: string;
  subject?: string;
  duration?: string;
  additional_context?: string;
}

export interface GreatStoryRequest {
  theme: string;
  age_group: string;
  format_style?: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name: string;
  confirm_password: string;
  agree_terms: boolean;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface UpdateEmailRequest {
  new_email: string;
  current_password: string;
}

export interface UpdateProfileRequest {
  full_name?: string;
  institution_name?: string;
}

export interface JoinSchoolRequest {
  invite_code: string;
  email: string;
  password: string;
  full_name: string;
  confirm_password: string;
  agree_terms: boolean;
}

export interface SchoolSetupRequest {
  school_name: string;
  admin_email?: string;
  admin_password?: string;
  admin_name?: string;
  confirm_password?: string;
}

export interface CreateStudentRequest {
  username: string;
  password: string;
  full_name: string;
  age_group?: string;
  parent_name?: string;
  parent_email?: string;
  consent_method?: string;
}

export interface CreateNoteRequest {
  title: string;
  content: string;
  chapters?: string;
  images?: string;
  materials?: string;
}
