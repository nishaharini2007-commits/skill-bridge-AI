import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('skillbridge-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function messageFromError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (responseMessage) return responseMessage
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail?.message) return detail.message
    if (error.code === 'ERR_NETWORK') return 'Could not connect to SkillBridge API. Start the backend and retry.'
    return error.message || 'The request could not be completed.'
  }
  return error instanceof Error ? error.message : 'Something went wrong.'
}

export async function request<T>(promise: Promise<{ data: { success: boolean; data: T } }>): Promise<T> {
  const response = await promise
  return response.data.data
}

export const authService = {
  login: (email: string, password: string) => request<{ token: string; user: User }>(api.post('/auth/login', { email, password })),
  register: (payload: { name: string; email: string; password: string; role: string }) => request<{ token: string; user: User }>(api.post('/auth/register', payload)),
  me: () => request<User>(api.get('/auth/me')),
}

export const studentService = {
  dashboard: () => request<Dashboard>(api.get('/student/dashboard')),
  institutionCourses: () => request<InstitutionAssignedCourse[]>(api.get('/student/institution-courses')),
  assignedMentor: () => request<StudentMentor | null>(api.get('/student/mentor')),
  profile: () => request<Profile>(api.get('/student/profile')),
  updateProfile: (payload: Profile) => request<Profile>(api.put('/student/profile', payload)),
  careerRoles: () => request<CareerRole[]>(api.get('/student/career-roles')),
  setCareer: (career_goal: string) => request<{ career_goal: string }>(api.put('/student/career', { career_goal })),
  skills: () => request<Skill[]>(api.get('/student/skills')),
  skillGap: () => request<SkillGap>(api.get('/skill-gap')),
  projectMarketplace: () => request<IndustryProject[]>(api.get('/student/project-marketplace')),
  applyToProject: (id: number) => request<{ application_id: number; status: string }>(api.post(`/student/project-marketplace/${id}/applications`)),
  jobVacancies: () => request<JobVacancy[]>(api.get('/student/job-vacancies')),
  applyToJob: (id: number, consent: JobApplicationConsentInput) => request<{ application_id: number; status: string }>(api.post(`/student/job-vacancies/${id}/applications`, consent)),
  applications: () => request<StudentApplication[]>(api.get('/student/applications')),
  learningProfile: () => request<LearningProfile>(api.get('/student/learning-profile')),
  updateLearningProfile: (payload: Partial<LearningProfile>) => request<LearningProfile>(api.put('/student/learning-profile', payload)),
  learningAnalysis: () => request<LearningAnalysis>(api.get('/student/skill-gap-analysis')),
  passport: () => request<Passport>(api.get('/student/passport')),
  progress: () => request<Progress>(api.get('/student/progress')),
}

export const learningRoadmapService = {
  get: () => request<LearningRoadmap>(api.get('/student/learning-roadmap')),
  refresh: () => request<LearningRoadmap>(api.post('/student/learning-roadmap/refresh')),
  updateTask: (id: number, status: LearningTask['status']) =>
    request<LearningRoadmap>(api.patch(`/student/learning-roadmap/tasks/${id}`, { status })),
}

export const assessmentService = {
  get: () => request<Assessment>(api.get('/assessment')),
  submit: (answers: { question_id: number; answer: string }[]) => request<AssessmentResult>(api.post('/assessment/submit', { answers })),
}

export const roadmapService = {
  get: () => request<Roadmap>(api.get('/roadmap')),
  complete: (id: number) => request<Roadmap>(api.post(`/roadmap/tasks/${id}/complete`)),
}

export const projectService = {
  list: () => request<Project[]>(api.get('/projects')),
  get: (id: number) => request<IndustryProject>(api.get(`/projects/${id}`)),
  create: (payload: ProjectInput) => request<Project>(api.post('/projects', payload)),
  apply: (id: number) => request<{ status: string }>(api.post(`/projects/${id}/apply`)),
  submit: (id: number, payload: SubmissionInput) => request<{ submission_id: number; status: string; submitted_at: string }>(api.post(`/projects/${id}/submission`, payload)),
  submissions: () => request<Submission[]>(api.get('/mentor/submissions')),
  evaluate: (id: number, payload: EvaluationInput) => request<{ overall_score: number; verified_skills: string[] }>(api.post(`/projects/submissions/${id}/evaluate`, payload)),
}

export const opportunityService = {
  matches: () => request<Opportunity[]>(api.get('/opportunities/matches')),
}

export const industryService = {
  dashboard: () => request<IndustryDashboard>(api.get('/industry/dashboard')),
  portalDashboard: () => request<IndustryPortalDashboard>(api.get('/industry/portal/dashboard')),
  companyProfile: () => request<CompanyProfile>(api.get('/industry/company-profile')),
  updateCompanyProfile: (payload: CompanyProfile) => request<CompanyProfile>(api.put('/industry/company-profile', payload)),
  demoCompanies: () => request<DemoCompany[]>(api.get('/industry/demo-companies')),
  projects: () => request<IndustryProject[]>(api.get('/industry/portal/projects')),
  createProject: (payload: IndustryProjectInput) => request<IndustryProject>(api.post('/industry/portal/projects', {
    ...payload, category: payload.domain, acceptance_criteria: payload.evaluation_criteria,
    deliverables: payload.deliverables ?? [], instructions: payload.instructions ?? '',
    references: payload.references ?? [], duration_weeks: payload.duration_weeks ?? null,
    participation: payload.participation ?? 'Individual', team_size_min: payload.team_size_min ?? 1,
    team_size_max: payload.team_size_max ?? 1, publication_status: payload.publication_status ?? 'PUBLISHED',
  })),
  updateProject: (id: number, payload: IndustryProjectInput) => request<IndustryProject>(api.put(`/industry/portal/projects/${id}`, {
    ...payload, category: payload.domain, acceptance_criteria: payload.evaluation_criteria,
    deliverables: payload.deliverables ?? [], instructions: payload.instructions ?? '',
    references: payload.references ?? [], duration_weeks: payload.duration_weeks ?? null,
    participation: payload.participation ?? 'Individual', team_size_min: payload.team_size_min ?? 1,
    team_size_max: payload.team_size_max ?? 1, publication_status: payload.publication_status ?? 'PUBLISHED',
  })),
  setProjectStatus: (id: number, status: 'OPEN' | 'CLOSED') => request<IndustryProject>(api.patch(`/industry/portal/projects/${id}/status?publication_status=${status === 'OPEN' ? 'PUBLISHED' : 'CLOSED'}`)),
  submissions: (params?: { status_filter?: string; project_id?: number }) => request<IndustrySubmission[]>(api.get('/industry/project-submissions', { params })),
  reviewSubmission: (id: number, payload: SubmissionReviewInput) => request<{ id: number; decision: string; reviewed_at: string }>(api.post(`/industry/project-submissions/${id}/reviews`, payload)),
  portalNotifications: () => request<PortalNotification[]>(api.get('/industry/notifications')),
  portalNotificationsRead: (id: number) => request<{ id: number; read: boolean }>(api.patch(`/notifications/${id}/read`)),
  jobApplicationAnalysis: (vacancy_id?: number) => request<JobApplicationAnalysis[]>(api.get('/industry/job-applications/analysis', { params: { vacancy_id } })),
  jobRequirements: (id: number) => request<JobRequirementInput>(api.get(`/industry/job-vacancies/${id}/requirements`)),
  setJobRequirements: (id: number, payload: JobRequirementInput) => request<{ vacancy_id: number; openings: number }>(api.put(`/industry/job-vacancies/${id}/requirements`, payload)),
  requestApplicantProfiles: (applicationId: number, profile_types: ProfileType[]) => request<ProfileAccessRecord>(api.post(`/industry/job-applications/${applicationId}/profile-access-request`, { profile_types })),
  applicantProfiles: (applicationId: number) => request<{ profile_access_status: string; profiles: Partial<Record<ProfileType, string>> }>(api.get(`/industry/job-applications/${applicationId}/profiles`)),
  projectApplications: (id: number) => request<IndustryProjectApplication[]>(api.get(`/industry/projects/${id}/applications`)),
  reviewProjectApplication: (id: number, payload: ApplicationReviewInput) => request<{ application_id: number; status: string; note: string }>(api.patch(`/industry/project-applications/${id}/review`, payload)),
  vacancies: () => request<JobVacancy[]>(api.get('/industry/portal/job-vacancies')),
  createVacancy: (payload: JobVacancyInput) => request<JobVacancy>(api.post('/industry/portal/job-vacancies', payload)),
  updateVacancy: (id: number, payload: JobVacancyInput) => request<JobVacancy>(api.put(`/industry/portal/job-vacancies/${id}`, payload)),
  setVacancyStatus: (id: number, status: 'OPEN' | 'CLOSED' | 'DRAFT') => request<JobVacancy>(api.patch(`/industry/portal/job-vacancies/${id}/status?vacancy_status=${status}`)),
  vacancyApplications: (id: number) => request<JobApplicationReview[]>(api.get(`/industry/job-vacancies/${id}/applications`)),
  updateJobApplication: (id: number, payload: ApplicationReviewInput) => request<{ application_id: number; status: string }>(api.post(`/industry/job-applications/${id}/status`, payload)),
  extract: (description: string) => request<{ skills: { name: string; category: string }[]; groups: Record<string, string[]>; engine: string }>(api.post('/industry/skills/extract', { description })),
  requirement: (payload: { role_name: string; skill_name: string; required_level: number }) => request<{ role: string; skill: string }>(api.post('/industry/requirements', payload)),
  talent: () => request<Talent[]>(api.get('/industry/talent')),
}

export const mentorService = {
  dashboard: () => request<{ pending_evaluations: number; evaluated: number; submissions: Submission[] }>(api.get('/mentor/dashboard')),
  submissions: projectService.submissions,
}

export const institutionService = {
  analytics: () => request<InstitutionAnalytics>(api.get('/institution/analytics')),
  mentors: () => request<InstitutionMentorDirectory>(api.get('/institution/mentors')),
  createMentor: (payload: InstitutionMentorCreateInput) => request<InstitutionMentor>(api.post('/institution/mentors', payload)),
  associateMentor: (email: string) => request<InstitutionMentor>(api.post('/institution/mentors/associate', { email })),
  updateMentor: (mentorId: number, payload: InstitutionMentorUpdateInput) => request<InstitutionMentor>(api.put(`/institution/mentors/${mentorId}`, payload)),
  student: (id: number) => request<InstitutionStudentDetail>(api.get(`/institution/students/${id}`)),
  assignCourse: (studentId: number, courseId: number) => request<{ id: number; course_id: number; status: string }>(api.post(`/institution/students/${studentId}/courses`, { course_id: courseId })),
  updateCourse: (id: number, status: InstitutionCourseStatus, score: number | null) => request<{ id: number; status: string; completed_at: string | null }>(api.patch(`/institution/course-enrollments/${id}`, { status, score })),
  updateMentorship: (studentId: number, payload: InstitutionMentorshipInput) => request<{ student_id: number; status: InstitutionMentorshipStatus; mentor_name: string | null; follow_up_date: string | null }>(api.put(`/institution/students/${studentId}/mentorship`, payload)),
}

export const studentPortalService = {
  sharing: () => request<{ share_social_links: boolean }>(api.get('/student/profile-sharing')),
  updateSharing: (share_social_links: boolean) => request<{ share_social_links: boolean }>(api.put('/student/profile-sharing', { share_social_links })),
  submissions: () => request<IndustrySubmission[]>(api.get('/student/project-submissions')),
  notifications: () => request<PortalNotification[]>(api.get('/student/notifications')),
  markNotificationRead: (id: number) => request<{ id: number; read: boolean }>(api.patch(`/notifications/${id}/read`)),
  applicationStatusHistory: () => request<ApplicationStatusUpdate[]>(api.get('/student/application-status-history')),
  profileAccess: () => request<ProfileAccessRecord[]>(api.get('/student/job-profile-access')),
  respondProfileAccess: (id: number, decision: 'GRANTED' | 'DECLINED', granted_profile_types: ProfileType[]) =>
    request<ProfileAccessRecord>(api.post(`/student/job-applications/${id}/profile-access-response`, { decision, granted_profile_types })),
  revokeProfileAccess: (id: number, profile_types?: ProfileType[]) =>
    request<ProfileAccessRecord>(api.post(`/student/job-applications/${id}/profile-access-revoke`, { profile_types })),
}

export type User = { id: number; name: string; email: string; role: 'student' | 'industry' | 'mentor' | 'institution' }
export type Skill = { id: number; name: string; category: string; proficiency: number; verification_status: string; evidence: string }
export type SkillGapItem = { skill_id: number; skill: string; category: string; required: number; current: number; gap: number; priority: string; priority_score: number }
export type CandidateMatch = {
  match_percent: number; matched_skills: string[]; skills_to_improve: string[];
  skill_details: { skill: string; required_level: number; current_level: number; matched: boolean; evidence: string[] }[];
  explanation: string; decision_note: string;
}
export type IndustryProject = Project & {
  eligibility: string; required_skill_levels: Record<string, number>; candidate_match: CandidateMatch | null;
  category?: string; deliverables?: string[]; instructions?: string; duration_weeks?: number | null;
  participation?: 'Individual' | 'Team'; team_size_min?: number; team_size_max?: number;
  references?: string[]; publication_status?: 'DRAFT' | 'PUBLISHED' | 'CLOSED';
}
export type IndustryProjectInput = ProjectInput & {
  eligibility: string; required_skill_levels: Record<string, number>; deliverables?: string[]; instructions?: string;
  references?: string[]; duration_weeks?: number | null; participation?: 'Individual' | 'Team';
  team_size_min?: number; team_size_max?: number; publication_status?: 'DRAFT' | 'PUBLISHED' | 'CLOSED';
}
export type IndustryPortalDashboard = {
  active_projects: number; submissions_awaiting_review: number; published_opportunities: number;
  applications_received: number; shortlisted_candidates: number; eligible_candidates: number | null;
  eligible_candidates_note: string;
  job_vacancies_total: number; job_vacancies_open: number; job_applications_total: number;
  job_applications_awaiting_review: number; job_applications_shortlisted: number;
  job_applications_interview: number; job_applications_selected: number;
}
export type CompanyProfile = {
  company_name: string; industry_type: string; description: string; website: string; company_email: string;
  contact_person: string; contact_title: string; phone: string; logo_url: string; verification_status: string;
  is_demo?: boolean; account_status?: string;
}
export type DemoCompany = {
  company_key: string; company_name: string; category: string; description: string;
  website: string; logo_text: string; account_status: string; is_demo: boolean;
}
export type IndustrySubmission = {
  id: number; project_id: number; project_title: string; student_id: number; student_name: string;
  college: string; department: string; year: number; submitted_at: string | null; summary: string;
  description: string; github_url: string; demo_url: string; report_url: string; evidence: string;
  skills_used: string[]; status: string; decision: string | null; revision_count: number;
  linkedin_url?: string; github_profile_url?: string;
  reviews?: { reviewer: string; decision: string; overall_feedback: string; technical_feedback: string;
    code_quality_feedback: string; problem_solving_feedback: string; strengths: string; improvement_areas: string;
    recommended_skills: string[]; rating: number | null; revision_instructions: string; reviewed_at: string }[];
}
export type SubmissionReviewInput = {
  decision: 'NEEDS_REVISION' | 'ACCEPTED' | 'REJECTED'; overall_feedback: string;
  technical_feedback: string; code_quality_feedback: string; problem_solving_feedback: string;
  strengths: string; improvement_areas: string; recommended_skills: string[]; rating: number | null;
  revision_instructions: string;
}
export type JobRequirementInput = {
  mandatory_education: string; mandatory_department: string; mandatory_certifications: string[];
  experience_requirement: string; internship_duration: string; openings: number; application_instructions: string;
}
export type JobApplicationAnalysis = JobApplicationReview & {
  vacancy_id: number; opportunity_title: string; opportunity_type: string; year: number;
  eligibility: 'ELIGIBLE' | 'PARTIALLY ELIGIBLE' | 'NOT CURRENTLY ELIGIBLE' | 'ASSESSMENT PENDING';
  eligibility_reasons: string[] | string; course_data_available: false;
  course_completion_status: 'Course Data Unavailable'; course_completion_percent: null;
  internal_note: string;
}
export type PortalNotification = { id: number; title: string; message: string; kind: string; read: boolean; created_at: string }
export type ApplicationStatusUpdate = { application_id: number; status: string; note: string; changed_at: string }
export type JobVacancyInput = {
  title: string; description: string; location: string; employment_type: 'Full-time' | 'Part-time' | 'Internship' | 'Contract';
  eligibility: string; required_skill_levels: Record<string, number>; preferred_skills: string[];
  experience_level: string; deadline: string; status?: 'DRAFT' | 'OPEN' | 'CLOSED';
}
export type JobVacancy = JobVacancyInput & {
  id: number; status: string; company: string; application_count: number;
  application_status: string | null; company_note: string; candidate_match: CandidateMatch | null;
  company_category: string; is_demo: boolean; demo_label: string; preferred_skills: string[];
  experience_level: string; posted_at: string | null;
}
export type ApplicationReviewInput = { status: 'REVIEWING' | 'SHORTLISTED' | 'INTERVIEW' | 'SELECTED' | 'NOT_SELECTED'; note: string }
export type IndustryProjectApplication = {
  application_id: number; student_id: number; student_name: string; college: string; department: string;
  career_goal: string; applied_at: string | null; project_status: string; review_status: string; company_note: string;
  submission: { description: string; github_url: string; evidence: string } | null;
  candidate_match: CandidateMatch; eligibility: string;
}
export type JobApplicationReview = {
  application_id: number; student_id: number; student_name: string; college: string; department: string;
  career_goal: string; applied_at: string | null; status: string; note: string; candidate_match: CandidateMatch;
  profile_access_status?: ProfileAccessRecord['profile_access_status']; requested_profile_types?: ProfileType[]; granted_profile_types?: ProfileType[];
}
export type ProfileType = 'linkedin' | 'github' | 'leetcode'
export type JobApplicationConsentInput = { consent_decision: 'GRANTED' | 'DECLINED'; profile_types: ProfileType[] }
export type ProfileAccessRecord = {
  job_application_id: number; job_title: string; company: string; profile_access_status: 'NOT_GRANTED' | 'REQUESTED' | 'GRANTED' | 'DENIED' | 'REVOKED';
  requested_profile_types: ProfileType[]; granted_profile_types: ProfileType[];
  consent_created_at?: string | null; consent_updated_at?: string | null; revoked_at?: string | null;
}
export type StudentApplication = {
  kind: 'project' | 'job'; id: number; listing_id: number; title: string; company: string; status: string;
  company_note: string; applied_at: string | null; evaluation_feedback: string;
}
export type LearningProfileSkill = { skill_name: string; proficiency: number; level: string; verification_status: string; evidence: string }
export type LearningProfile = {
  career_goal: string; current_skills: LearningProfileSkill[]; programming_languages: string[]; completed_courses: string[];
  completed_projects: string[]; github_url: string; linkedin_url: string; leetcode_url: string; target_companies: string[];
  study_minutes_per_day: number | null; learning_language: string; learning_format: 'Video' | 'Reading' | 'Interactive' | 'Mixed';
}
export type LearningResource = { category: string; title: string; platform: string; topic: string; difficulty: string; url: string; link_type: 'Platform search' | 'Official reference' | 'Learning reference' | 'Search results' }
export type LearningAnalysisSkill = SkillGapItem & {
  required_level: string; current_level: string; status: string; why_it_matters: string;
  prerequisites: { skill: string; current: number; level: string }[];
}
export type LearningAnalysis = {
  career_goal: string; engine: 'rule-based'; provisional: boolean; provisional_reasons: string[];
  readiness: number | null; readiness_calculation: string; skills: LearningAnalysisSkill[];
  highest_priority?: string | null; next_recommended_action: string;
  recommendations?: { skill: string; explanation: string; gap_closing_activity: string; resources: LearningResource[] }[];
}
export type LearningTask = {
  id: number; order: number; phase: number; phase_name: string; skill: string | null; title: string; why: string;
  explanation: string; prerequisites: string[]; estimated_minutes: number; resources: LearningResource[];
  practice: string; mini_project: string; status: 'Not Started' | 'In Progress' | 'Completed'; next_recommended_task: boolean;
}
export type LearningRoadmap = {
  career_goal: string; plan_version: number; engine: 'rule-based'; provisional: boolean; provisional_reasons: string[];
  readiness: number | null; estimated_days: number | null; study_minutes_per_day: number | null;
  total_tasks?: number; completed_tasks?: number; progress: number; next_recommended_task: number | null; tasks: LearningTask[];
}
export type Dashboard = { name: string; career_goal: string; readiness: number; verified_skills: number; skill_count: number; open_tasks: number; roadmap_progress: number; project_applications: number; opportunity_matches: number; assessment_count: number; top_gaps: SkillGapItem[] }
export type Profile = { id?: number; name: string; email: string; college: string; department: string; year: number; career_goal: string; bio: string; interests: string }
export type CareerRole = { id: number; name: string; description: string; skills: { name: string; required_level: number }[] }
export type SkillGap = { career_goal: string; skills: SkillGapItem[]; highest_priority: string | null; recommendations: { skill: string; course: string; practice: string; project: string; assessment: string }[] }
export type Assessment = { title: string; questions: { id: number; skill: string; question: string; options: string[] }[] }
export type AssessmentResult = { assessment_id: number; score: number; correct: number; total: number; results: { skill: string; proficiency: number }[] }
export type Roadmap = { career_goal: string; tasks: { id: number; week: number; title: string; type: string; skill: string; description: string; completed: boolean }[]; progress: number }
export type Project = { id: number; title: string; description: string; domain: string; difficulty: string; required_skills: string[]; expected_outcome: string; evaluation_criteria: string; deadline: string; status: string; company: string; applications: number; application_status: string | null; submission_status: string | null; eligibility?: string; required_skill_levels?: Record<string, number>; candidate_match?: CandidateMatch | null }
export type ProjectInput = { title: string; description: string; domain: string; difficulty: string; required_skills: string[]; expected_outcome: string; evaluation_criteria: string; deadline: string }
export type SubmissionInput = {
  summary: string; description: string; github_url: string; demo_url: string; report_url: string; evidence: string; skills_used: string[];
}
export type EvaluationInput = { technical_quality: number; problem_solving: number; code_quality: number; communication: number; innovation: number; feedback: string }
export type Submission = { id: number; project_id: number; project: string; student: string; student_id: number; description: string; github_url: string; evidence: string; submitted_at: string; evaluated: boolean; feedback: string }
export type Opportunity = { id: number; title: string; type: string; description: string; company: string; location: string; eligibility: string; required_skills: string[]; matched_skills: string[]; missing_skills: string[]; match_score: number }
export type Passport = { student: { name: string; email: string; college: string; department: string; career_goal: string }; readiness: number; skills: Skill[]; projects: { title: string; status: string; score: number | null }[]; assessments: { title: string; score: number; completed_at: string | null }[]; certifications: { name: string; issuer: string }[]; evaluations: number }
export type Progress = { readiness: number; assessment_completion: number; roadmap_completion: number; project_completion: number; verified_skills: number; skills: { skill: string; proficiency: number }[] }
export type IndustryDashboard = { company: string; project_count: number; application_count: number; open_projects: number; top_skills: { skill: string; demand: number }[]; projects: Project[] }
export type InstitutionCourseStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED'
export type InstitutionAssignedCourse = { course_name: string; skill: string; status: InstitutionCourseStatus; assigned_at: string; completed_at: string | null; score: number | null }
export type InstitutionMentorshipStatus = 'NOT_ASSIGNED' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED'
export type InstitutionMentorshipInput = {
  mentor_id: number | null; status: InstitutionMentorshipStatus; reason: string; notes: string; follow_up_date: string | null
}
export type InstitutionMentor = {
  id: number; mentor_id: number; name: string; email: string; expertise: string; skills: string[];
  experience: number; company: string; availability: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';
  active: boolean; assigned_student_count: number;
  assigned_students: { id: number; name: string; career_goal: string; department: string; year: number; status: InstitutionMentorshipStatus }[];
}
export type InstitutionMentorCreateInput = {
  name: string; email: string; expertise: string; experience: number; password: string;
  availability: InstitutionMentor['availability'];
}
export type InstitutionMentorUpdateInput = Omit<InstitutionMentorCreateInput, 'name' | 'email' | 'password'> & { active: boolean }
export type InstitutionMentorDirectory = {
  mentors: InstitutionMentor[];
  students: { id: number; name: string; career_goal: string; department: string; skill_gaps: string[]; assigned_mentor_id: number | null; mentorship_status: InstitutionMentorshipStatus; mentorship_reason: string; mentorship_notes: string; follow_up_date: string | null }[];
  summary: { total_mentors: number; active_mentors: number; assigned_students: number; students_without_mentor: number };
}
export type StudentMentor = { name: string; expertise: string; status: InstitutionMentorshipStatus }
export type InstitutionStudent = {
  id: number; name: string; email: string; department: string; year: number; career_goal: string;
  assigned_courses: number; assigned_course_ids: number[]; completed_courses: number; courses_in_progress: number; pending_courses: number;
  course_completion_percent: number | null; course_data_available: boolean;
  assessed_skills: { skill_id: number; skill: string; proficiency: number; score: number; assessed_at: string }[];
  skill_gaps: { skill: string; required: number; current: number | null; status: string; recommended_courses: { id: number; title: string }[] }[];
  skill_gap_status: 'ASSESSMENT_PENDING' | 'SIGNIFICANT_GAPS' | 'MINOR_GAPS' | 'SKILLS_ALIGNED';
  last_assessment_at: string | null; linkedin_url: string; github_url: string;
  mentorship_status: InstitutionMentorshipStatus; mentor_id: number | null; mentor_name: string | null; mentorship_reason: string;
  needs_mentorship: boolean; mentorship_notes: string; follow_up_date: string | null;
}
export type InstitutionAnalytics = {
  institution_name: string; total_students: number; students_completed_all_courses: number; students_learning: number;
  students_with_pending_courses: number; students_with_skill_gaps: number; students_requiring_mentorship: number;
  course_catalog: { id: number; title: string; skill: string }[];
  mentors: { id: number; name: string; expertise: string }[];
  course_status_counts: { completed: number; in_progress: number; pending: number };
  department_progress: { department: string; students: number; assigned: number; completed: number; completion_percent: number | null }[];
  assessment_progress_over_time: { month: string; assessments: number; average_score: number }[];
  common_skill_gaps: { skill: string; students: number }[]; students: InstitutionStudent[];
  average_readiness: number; assessment_completion: number; top_skill_gaps: { skill: string; students: number }[];
  industry_demand: { skill: string; demand: number }[]; project_participation: number; verified_skills: number;
  readiness_distribution: { student: string; readiness: number }[];
}
export type InstitutionStudentDetail = InstitutionStudent & {
  mentors: { id: number; name: string; expertise: string }[];
  course_records: { id: number; course_id: number; course_name: string; status: InstitutionCourseStatus; assigned_at: string; completed_at: string | null; score: number | null }[];
  roadmap: { title: string; status: string; skill: string | null }[];
  industry_projects: { title: string; status: string; created_at: string | null }[];
  project_submissions: { project: string; status: string; submitted_at: string | null; feedback: string; score: number | null }[];
  job_applications: { job: string; company: string; status: string; applied_at: string | null }[];
  mentorship_history: { status: string; mentor: string | null; reason: string; notes: string; follow_up_date: string | null; created_at: string }[];
}
export type Talent = { name: string; college: string; career_goal: string; readiness: number; skills: string[] }

export default api
