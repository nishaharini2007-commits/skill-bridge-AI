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
  profile: () => request<Profile>(api.get('/student/profile')),
  updateProfile: (payload: Profile) => request<Profile>(api.put('/student/profile', payload)),
  careerRoles: () => request<CareerRole[]>(api.get('/student/career-roles')),
  setCareer: (career_goal: string) => request<{ career_goal: string }>(api.put('/student/career', { career_goal })),
  skills: () => request<Skill[]>(api.get('/student/skills')),
  skillGap: () => request<SkillGap>(api.get('/skill-gap')),
  projectMarketplace: () => request<IndustryProject[]>(api.get('/student/project-marketplace')),
  applyToProject: (id: number) => request<{ application_id: number; status: string }>(api.post(`/student/project-marketplace/${id}/applications`)),
  jobVacancies: () => request<JobVacancy[]>(api.get('/student/job-vacancies')),
  applyToJob: (id: number) => request<{ application_id: number; status: string }>(api.post(`/student/job-vacancies/${id}/applications`)),
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
  get: (id: number) => request<Project>(api.get(`/projects/${id}`)),
  create: (payload: ProjectInput) => request<Project>(api.post('/projects', payload)),
  apply: (id: number) => request<{ status: string }>(api.post(`/projects/${id}/apply`)),
  submit: (id: number, payload: SubmissionInput) => request<{ status: string }>(api.post(`/projects/${id}/submit`, payload)),
  submissions: () => request<Submission[]>(api.get('/mentor/submissions')),
  evaluate: (id: number, payload: EvaluationInput) => request<{ overall_score: number; verified_skills: string[] }>(api.post(`/projects/submissions/${id}/evaluate`, payload)),
}

export const opportunityService = {
  matches: () => request<Opportunity[]>(api.get('/opportunities/matches')),
}

export const industryService = {
  dashboard: () => request<IndustryDashboard>(api.get('/industry/dashboard')),
  projects: () => request<IndustryProject[]>(api.get('/industry/projects')),
  createProject: (payload: IndustryProjectInput) => request<IndustryProject>(api.post('/industry/projects', payload)),
  updateProject: (id: number, payload: IndustryProjectInput) => request<IndustryProject>(api.patch(`/industry/projects/${id}`, payload)),
  setProjectStatus: (id: number, status: 'OPEN' | 'CLOSED') => request<IndustryProject>(api.patch(`/industry/projects/${id}/status`, { status })),
  projectApplications: (id: number) => request<IndustryProjectApplication[]>(api.get(`/industry/projects/${id}/applications`)),
  reviewProjectApplication: (id: number, payload: ApplicationReviewInput) => request<{ application_id: number; status: string; note: string }>(api.patch(`/industry/project-applications/${id}/review`, payload)),
  vacancies: () => request<JobVacancy[]>(api.get('/industry/job-vacancies')),
  createVacancy: (payload: JobVacancyInput) => request<JobVacancy>(api.post('/industry/job-vacancies', payload)),
  updateVacancy: (id: number, payload: JobVacancyInput) => request<JobVacancy>(api.patch(`/industry/job-vacancies/${id}`, payload)),
  setVacancyStatus: (id: number, status: 'OPEN' | 'CLOSED') => request<JobVacancy>(api.patch(`/industry/job-vacancies/${id}/status`, { status })),
  vacancyApplications: (id: number) => request<JobApplicationReview[]>(api.get(`/industry/job-vacancies/${id}/applications`)),
  updateJobApplication: (id: number, payload: ApplicationReviewInput) => request<{ application_id: number; status: string; note: string }>(api.patch(`/industry/job-applications/${id}`, payload)),
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
}

export type User = { id: number; name: string; email: string; role: 'student' | 'industry' | 'mentor' | 'institution' }
export type Skill = { id: number; name: string; category: string; proficiency: number; verification_status: string; evidence: string }
export type SkillGapItem = { skill_id: number; skill: string; category: string; required: number; current: number; gap: number; priority: string; priority_score: number }
export type CandidateMatch = {
  match_percent: number; matched_skills: string[]; skills_to_improve: string[];
  skill_details: { skill: string; required_level: number; current_level: number; matched: boolean; evidence: string[] }[];
  explanation: string; decision_note: string;
}
export type IndustryProject = Project & { eligibility: string; required_skill_levels: Record<string, number>; candidate_match: CandidateMatch | null }
export type IndustryProjectInput = ProjectInput & { eligibility: string; required_skill_levels: Record<string, number> }
export type JobVacancyInput = {
  title: string; description: string; location: string; employment_type: 'Full-time' | 'Part-time' | 'Internship' | 'Contract';
  eligibility: string; required_skill_levels: Record<string, number>; deadline: string;
}
export type JobVacancy = JobVacancyInput & {
  id: number; status: string; company: string; application_count: number;
  application_status: string | null; company_note: string; candidate_match: CandidateMatch | null;
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
export type SubmissionInput = { description: string; github_url: string; evidence: string }
export type EvaluationInput = { technical_quality: number; problem_solving: number; code_quality: number; communication: number; innovation: number; feedback: string }
export type Submission = { id: number; project_id: number; project: string; student: string; student_id: number; description: string; github_url: string; evidence: string; submitted_at: string; evaluated: boolean; feedback: string }
export type Opportunity = { id: number; title: string; type: string; description: string; company: string; location: string; eligibility: string; required_skills: string[]; matched_skills: string[]; missing_skills: string[]; match_score: number }
export type Passport = { student: { name: string; email: string; college: string; department: string; career_goal: string }; readiness: number; skills: Skill[]; projects: { title: string; status: string; score: number | null }[]; assessments: { title: string; score: number; completed_at: string | null }[]; certifications: { name: string; issuer: string }[]; evaluations: number }
export type Progress = { readiness: number; assessment_completion: number; roadmap_completion: number; project_completion: number; verified_skills: number; skills: { skill: string; proficiency: number }[] }
export type IndustryDashboard = { company: string; project_count: number; application_count: number; open_projects: number; top_skills: { skill: string; demand: number }[]; projects: Project[] }
export type InstitutionAnalytics = { total_students: number; assessment_completion: number; average_readiness: number; top_skill_gaps: { skill: string; students: number }[]; industry_demand: { skill: string; demand: number }[]; project_participation: number; verified_skills: number; readiness_distribution: { student: string; readiness: number }[] }
export type Talent = { name: string; college: string; career_goal: string; readiness: number; skills: string[] }

export default api
