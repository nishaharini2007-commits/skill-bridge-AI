import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Activity, ArrowDownRight, ArrowRight, Award, BarChart3, Bell, BookOpen, BriefcaseBusiness, Building2,
  Check, CheckCircle2, ChevronDown, CircleHelp, ClipboardCheck, Code2, Compass, FileText, Flame, Github, GraduationCap, Linkedin, ListChecks,
  LayoutDashboard, Lightbulb, LogOut, Menu, Plus, Search, Send, ShieldCheck, Sparkles, Target, TrendingUp,
  UserRound, Users, X,
} from 'lucide-react'
import {
  assessmentService, industryService, institutionService, mentorService, messageFromError, opportunityService,
  learningRoadmapService, projectService, studentPortalService, studentService, type Assessment, type CareerRole, type Dashboard,
  type ApplicationReviewInput, type ApplicationStatusUpdate, type CompanyProfile, type EvaluationInput, type IndustryDashboard,
  type IndustryProject, type IndustryProjectApplication, type IndustryProjectInput, type IndustrySubmission,
  type InstitutionAnalytics, type InstitutionAssignedCourse, type InstitutionMentor, type InstitutionMentorDirectory, type InstitutionMentorUpdateInput, type InstitutionStudent, type InstitutionStudentDetail, type JobApplicationAnalysis, type JobApplicationReview, type JobRequirementInput,
  type JobVacancy, type JobVacancyInput, type Opportunity, type Passport, type LearningAnalysis,
  type LearningProfile, type LearningRoadmap, type LearningTask, type Progress, type Project,
  type PortalNotification, type ProfileAccessRecord, type ProfileType, type SkillGap, type StudentApplication, type StudentMentor, type Submission, type SubmissionReviewInput,
} from './services/api'
import { useAuth } from './context/AuthContext'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type Loader<T> = () => Promise<T>

function isValidSocialProfileUrl(value: string, platform: ProfileType) {
  if (!value.trim()) return true
  try {
    const url = new URL(value.trim())
    const domain = { github: 'github.com', linkedin: 'linkedin.com', leetcode: 'leetcode.com' }[platform]
    const host = url.hostname.toLowerCase()
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password &&
      (host === domain || host.endsWith(`.${domain}`))
  } catch {
    return false
  }
}

function useLoad<T>(loader: Loader<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData(await loader()) } catch (reason) { setError(messageFromError(reason)) } finally { setLoading(false) }
  }, [loader])
  useEffect(() => { void refresh() }, [refresh])
  return { data, loading, error, refresh, setData }
}

function LoadingState() { return <div className="loading-state"><span className="spinner" /> Loading your workspace…</div> }
function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return <div className="error-state"><CircleHelp size={20} /><div><strong>We couldn't load this page</strong><p>{message}</p><button className="button button-small" onClick={retry}>Try again</button></div></div>
}
function LoadState({ loading, error, retry, children }: { loading: boolean; error: string; retry: () => void; children: ReactNode }) {
  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} retry={retry} />
  return <>{children}</>
}

function Protected({ role, children }: { role?: string; children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState />
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to={`/${user.role}/dashboard`} replace />
  return <>{children}</>
}

const dashboards = { student: '/student/dashboard', industry: '/industry/dashboard', mentor: '/mentor/dashboard', institution: '/institution/dashboard' }
const navigation = {
  student: [
    ['Overview', '/student/dashboard', LayoutDashboard], ['Skill passport', '/student/skills', Award],
    ['Career goal', '/student/career', Target], ['Assessment', '/student/assessment', ClipboardCheck],
    ['Skill gap', '/student/skill-gap', Activity], ['Skill gap analysis', '/student/learning-analysis', BarChart3],
    ['Learning profile', '/student/learning-profile', UserRound], ['Roadmap', '/student/roadmap', Compass],
    ['Industry projects', '/student/projects', BriefcaseBusiness], ['Job vacancies', '/student/jobs', BriefcaseBusiness],
    ['My applications', '/student/applications', ListChecks], ['Opportunities', '/student/opportunities', Sparkles],
    ['Progress', '/student/progress', BarChart3], ['My profile', '/student/profile', UserRound],
    ['Professional profiles & access', '/student/profile-sharing', ShieldCheck], ['Project feedback', '/student/feedback', ClipboardCheck],
    ['Notifications', '/student/notifications', Bell],
  ],
  industry: [
    ['Overview', '/industry/dashboard', LayoutDashboard], ['Company directory', '/industry/companies', Building2], ['Company profile', '/industry/profile', Building2],
    ['Skill requirements', '/industry/skills', Target], ['JD analyzer', '/industry/analyzer', Sparkles],
    ['Projects', '/industry/projects', BriefcaseBusiness], ['Job vacancies', '/industry/jobs', BriefcaseBusiness],
    ['Applications', '/industry/applications', ListChecks], ['Talent discovery', '/industry/talent', Users],
    ['Candidate analysis', '/industry/candidates', GraduationCap], ['Submissions', '/industry/submissions', ClipboardCheck],
    ['Notifications', '/industry/notifications', Bell], ['Analytics', '/industry/analytics', BarChart3],
  ],
  mentor: [
    ['Overview', '/mentor/dashboard', LayoutDashboard], ['Submissions', '/mentor/projects', BriefcaseBusiness],
    ['Evaluations', '/mentor/evaluations', ClipboardCheck],
  ],
  institution: [
    ['Overview', '/institution/dashboard', LayoutDashboard], ['Mentor Management', '/institution/mentors', Users], ['Analytics', '/institution/analytics', BarChart3],
  ],
} as const

function WorkspaceLayout({ role, children }: { role: keyof typeof navigation; children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const activeTitle = navigation[role].find((item) => location.pathname === item[1] || (item[1] !== dashboards[role] && location.pathname.startsWith(item[1] + '/')))?.[0] ?? 'Workspace'
  return <div className="workspace">
    {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <Link to="/" className="brand"><span className="brand-icon"><Sparkles size={19} /></span><span>skillbridge<span className="brand-ai">.ai</span></span></Link>
      <div className="workspace-label">{role} workspace</div>
      <nav className="side-nav">{navigation[role].map(([label, href, Icon]) => <NavLink key={href} to={href} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`}><Icon size={18} strokeWidth={1.9} /><span>{label}</span>{label === 'Assessment' && role === 'student' && <span className="nav-dot" />}</NavLink>)}</nav>
      <div className="sidebar-bottom">
        <div className="help-card"><div className="help-icon"><Lightbulb size={17} /></div><strong>Keep growing</strong><p>Small learning steps build career momentum.</p><Link to={role === 'student' ? '/student/roadmap' : dashboards[role]}>Explore your next step <ArrowRight size={13} /></Link></div>
        <div className="user-mini"><div className="avatar">{user?.name.slice(0, 1).toUpperCase()}</div><div className="user-mini-info"><strong>{user?.name}</strong><span>{role[0].toUpperCase() + role.slice(1)}</span></div><button aria-label="Log out" className="icon-button logout-button" onClick={() => { logout(); navigate('/') }}><LogOut size={17} /></button></div>
      </div>
    </aside>
    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumbs">Workspace <span>/</span> <strong>{activeTitle}</strong></div><div className="topbar-right"><span className="connection"><span /> Live workspace</span><button className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /></button><button className="top-avatar" onClick={() => navigate(role === 'student' ? '/student/profile' : dashboards[role])}>{user?.name.slice(0, 1)}</button></div></header>
      <div className="page-content">{children}</div>
      <footer className="workspace-footer"><span>SkillBridge AI</span><span>Skills, evidence & opportunity — connected.</span></footer>
    </main>
  </div>
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="heading-action">{action}</div>}</div>
}
function Panel({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>
}
function Metric({ label, value, note, icon: Icon, tone = 'blue' }: { label: string; value: string | number; note: string; icon: typeof Activity; tone?: string }) {
  return <div className="metric-card"><div className={`metric-icon tone-${tone}`}><Icon size={19} /></div><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong><span className="metric-note">{note}</span></div>
}
function ProgressBar({ value, color = 'blue' }: { value: number; color?: string }) {
  return <div className="progress-track"><span className={`progress-fill fill-${color}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>
}
function Badge({ children, tone = 'gray' }: { children: ReactNode; tone?: string }) { return <span className={`badge badge-${tone}`}>{children}</span> }
function Empty({ title, body }: { title: string; body: string }) { return <div className="empty-state"><div className="empty-icon"><Search size={19} /></div><strong>{title}</strong><p>{body}</p></div> }

function Landing() {
  return <div className="landing">
    <header className="landing-nav"><Link to="/" className="brand"><span className="brand-icon"><Sparkles size={19} /></span><span>skillbridge<span className="brand-ai">.ai</span></span></Link><nav><a href="#how-it-works">How it works</a><a href="#impact">Our impact</a><Link to="/login">Sign in</Link><Link className="button button-primary button-small" to="/register">Get started <ArrowRight size={15} /></Link></nav></header>
    <section className="hero"><div className="hero-copy"><div className="hero-pill"><span className="pulse-dot" /> INDUSTRY-ACADEMIA SKILL INTELLIGENCE</div><h1>From classroom learning to <span>industry-ready</span> skills.</h1><p>One connected journey from discovering your skill gaps to building real projects and proving what you can do.</p><div className="hero-actions"><Link to="/register" className="button button-primary">Get started <ArrowRight size={16} /></Link><a href="#how-it-works" className="button button-outline">Explore the platform</a></div><div className="hero-proof"><div className="proof-avatars"><i>A</i><i>M</i><i>R</i><i>+</i></div><span>Built around real skills.<br /><strong>Connected to real opportunity.</strong></span></div></div>
      <div className="hero-visual"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="hero-core"><div className="core-spark"><Sparkles size={24} /></div><strong>Skill<br />intelligence</strong><span>LEARN · PROVE · GROW</span></div><div className="float-card float-student"><div className="float-icon float-blue"><GraduationCap size={17} /></div><div><strong>Student</strong><span>Personalized roadmap</span></div><CheckCircle2 size={17} className="float-check" /></div><div className="float-card float-industry"><div className="float-icon float-teal"><Building2 size={17} /></div><div><strong>Industry</strong><span>Skills that matter</span></div><span className="float-status">LIVE</span></div><div className="float-card float-skill"><span className="mini-spark"><TrendingUp size={16} /></span><div><strong>Power BI</strong><span>Priority skill · Week 2</span></div><span className="skill-ring">68%</span></div><div className="hero-dot dot-one" /><div className="hero-dot dot-two" /><div className="hero-dot dot-three" /></div></section>
    <section className="trust-strip"><span>ONE CONTINUOUS SKILL JOURNEY</span><div><span><GraduationCap /> LEARN</span><ArrowRight /><span><Activity /> ASSESS</span><ArrowRight /><span><BriefcaseBusiness /> BUILD</span><ArrowRight /><span><ShieldCheck /> VERIFY</span><ArrowRight /><span><Sparkles /> MATCH</span></div></section>
    <section id="how-it-works" className="landing-section"><div className="section-intro"><div className="eyebrow">THE SKILL INTELLIGENCE LOOP</div><h2>Learning that leads somewhere.</h2><p>SkillBridge connects the full journey, so every learning step builds toward skills that industry recognizes.</p></div><div className="journey-grid">{[['01','Discover your direction','Choose a career goal grounded in what employers need.','🎯'],['02','See your skill gaps','A focused diagnostic maps what you know and what to build next.','📊'],['03','Practice with purpose','A personal roadmap connects learning, practice and real projects.','🧭'],['04','Prove what you can do','Mentors review your work and verify skills with evidence.','✅']].map(([number,title,body,emoji])=><article className="journey-card" key={number}><span className="journey-number">{number}</span><div className="journey-emoji">{emoji}</div><h3>{title}</h3><p>{body}</p></article>)}</div></section>
    <section id="impact" className="impact-section"><div><div className="eyebrow">A SHARED VIEW OF READINESS</div><h2>Three partners.<br /><span>One clearer signal.</span></h2><p>Students build demonstrable capability. Institutions see where to focus. Industry shapes the skills and experiences that open doors.</p><Link to="/register" className="text-link">Explore the SkillBridge workspace <ArrowRight size={15} /></Link></div><div className="impact-cards"><div><GraduationCap /><strong>For students</strong><span>Know your next step. Build a verified skill passport.</span></div><div><Building2 /><strong>For industry</strong><span>Turn emerging demand into meaningful projects.</span></div><div><Users /><strong>For institutions</strong><span>See readiness, participation and skills in context.</span></div></div></section>
    <section className="closing-cta"><div className="cta-spark"><Sparkles size={23} /></div><h2>Your next opportunity starts with a skill.</h2><p>Make your learning visible, relevant and ready for what comes next.</p><Link to="/register" className="button button-white">Get started <ArrowRight size={16} /></Link></section>
    <footer className="landing-footer"><Link to="/" className="brand"><span className="brand-icon"><Sparkles size={17} /></span><span>skillbridge<span className="brand-ai">.ai</span></span></Link><span>Bridging the gap between students, institutions and industry.</span><span>© 2026 SkillBridge AI</span></footer>
  </div>
}

const demoCredentials: Record<string, [string, string]> = {
  student: ['student@skillbridge.demo', 'Student@123'], industry: ['industry@skillbridge.demo', 'Industry@123'],
  institution: ['institution@skillbridge.demo', 'Institution@123'],
}
function Login({ register = false }: { register?: boolean }) {
  const { user, login, register: createAccount } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('student')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (user) return <Navigate to={dashboards[user.role]} replace />
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const account = register ? await createAccount({ name, email, password, role }) : await login(email, password)
      navigate(dashboards[account.role], { replace: true })
    } catch (reason) { setError(messageFromError(reason)) } finally { setBusy(false) }
  }
  return <div className="auth-page"><Link to="/" className="brand auth-brand"><span className="brand-icon"><Sparkles size={19} /></span><span>skillbridge<span className="brand-ai">.ai</span></span></Link><div className="auth-layout"><div className="auth-story"><div className="hero-pill"><span className="pulse-dot" /> YOUR NEXT CHAPTER STARTS HERE</div><h1>{register ? 'Build a bridge to what’s next.' : 'Welcome back to your skill journey.'}</h1><p>Bring learning, industry experience and your next opportunity into one connected workspace.</p><div className="auth-story-note"><div className="story-icon"><ShieldCheck /></div><div><strong>Skills backed by evidence</strong><span>Learn it. Apply it. Show what you can do.</span></div></div></div><div className="auth-card"><div className="auth-card-top"><span className="auth-welcome">{register ? 'Create your account' : 'Good to have you back'}</span><h2>{register ? 'Join SkillBridge AI' : 'Sign in to SkillBridge'}</h2><p>{register ? 'Choose your role and set up your workspace.' : 'Enter your details to continue to your workspace.'}</p></div><form onSubmit={submit} className="form-stack">{register && <label>Full name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></label>}<label>Email address<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Password<input required minLength={8} type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" /></label>{register && <label>Workspace role<select value={role} onChange={(e) => setRole(e.target.value)}><option value="student">Student</option><option value="industry">Industry partner</option><option value="institution">Institution</option></select></label>}{error && <div className="inline-error">{error}</div>}<button disabled={busy} className="button button-primary button-full">{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'} <ArrowRight size={16} /></button></form>{!register && <div className="demo-access"><div className="demo-access-heading"><span>DEMO ACCESS</span><span>Choose a role to fill credentials</span></div><div className="demo-chips">{Object.keys(demoCredentials).map((item) => <button key={item} onClick={() => { setEmail(demoCredentials[item][0]); setPassword(demoCredentials[item][1]) }}>{item}</button>)}</div></div>}<div className="auth-switch">{register ? 'Already have an account?' : 'New to SkillBridge?'} <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create an account'}</Link></div></div></div><div className="auth-footer">SkillBridge AI <span>·</span> Connecting learning with opportunity</div></div>
}

function StudentDashboard() {
  const { data, loading, error, refresh } = useLoad<Dashboard>(studentService.dashboard)
  const learningPlan = useLoad<LearningRoadmap>(learningRoadmapService.get)
  const learningProfile = useLoad<LearningProfile>(studentService.learningProfile)
  const assignedCourses = useLoad<InstitutionAssignedCourse[]>(studentService.institutionCourses)
  const assignedMentor = useLoad<StudentMentor | null>(studentService.assignedMentor)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="YOUR SKILL JOURNEY" title={`Good morning, ${data.name.split(' ')[0]}`} description="Your learning, evidence and next opportunities — all moving forward." action={<Link className="button button-primary" to="/student/assessment"><ClipboardCheck size={16} /> Take assessment</Link>} />
    {!data.career_goal && <div className="notice-banner"><Target size={18} /><div><strong>Choose your career direction to get started</strong><span>We’ll shape your skill gap analysis and roadmap around your goal.</span></div><Link className="button button-small button-primary" to="/student/career">Set career goal <ArrowRight size={14} /></Link></div>}
    <div className="metric-grid"><Metric label="Industry readiness" value={`${data.readiness}%`} note="Based on your current skill profile" icon={TrendingUp} tone="blue" /><Metric label="Verified skills" value={`${data.verified_skills}/${data.skill_count}`} note="Mentor-reviewed evidence" icon={ShieldCheck} tone="green" /><Metric label="Roadmap progress" value={`${learningPlan.data?.progress ?? data.roadmap_progress}%`} note={`${Math.max(0, (learningPlan.data?.total_tasks ?? data.open_tasks) - (learningPlan.data?.completed_tasks ?? 0))} learning steps to go`} icon={Compass} tone="purple" /><Metric label="Opportunity matches" value={data.opportunity_matches} note="Ranked against your skill profile" icon={Sparkles} tone="amber" /></div>
    <div className="dashboard-grid"><Panel title="Your readiness snapshot" subtitle={data.career_goal ? `Progress toward ${data.career_goal}` : 'Choose a career goal to personalize this view.'} action={<Link to="/student/skill-gap" className="text-link">View skill gap <ArrowRight size={14} /></Link>}><div className="readiness-layout"><div className="readiness-score"><span className="score-ring" style={{ '--score': `${data.readiness * 3.6}deg` } as React.CSSProperties}><span>{data.readiness}<small>%</small></span></span><div><strong>Industry readiness</strong><span>Based on required skill proficiency</span></div></div><div className="gap-list">{data.top_gaps.map((item) => <div className="gap-row" key={item.skill}><div><span>{item.skill}</span><strong>{item.current}<small> / {item.required}</small></strong></div><ProgressBar value={item.current / item.required * 100} color={item.gap > 2 ? 'coral' : item.gap > 0 ? 'blue' : 'green'} /><Badge tone={item.gap > 2 ? 'coral' : item.gap > 0 ? 'blue' : 'green'}>{item.priority}</Badge></div>)}{data.top_gaps.length === 0 && <Empty title="Your roadmap is waiting" body="Set a career goal to see the skills you need." />}</div></div></Panel>
      <Panel title="Keep your momentum" subtitle="Your next best actions"><div className="action-list"><Link to="/student/assessment"><span className="action-icon action-blue"><ClipboardCheck size={17} /></span><span><strong>{data.assessment_count ? 'Refresh your skill diagnostic' : 'Take your first skill diagnostic'}</strong><small>Get a clearer picture of where to focus</small></span><ArrowRight size={16} /></Link><Link to="/student/learning-analysis"><span className="action-icon action-purple"><Activity size={17} /></span><span><strong>Review your skill gap analysis</strong><small>See role requirements and explainable priorities</small></span><ArrowRight size={16} /></Link><Link to="/student/roadmap"><span className="action-icon action-purple"><Compass size={17} /></span><span><strong>Continue your personalized roadmap</strong><small>{data.open_tasks} learning steps still in progress</small></span><ArrowRight size={16} /></Link><Link to="/student/projects"><span className="action-icon action-teal"><BriefcaseBusiness size={17} /></span><span><strong>Build proof through a project</strong><small>Put your skills to work with industry</small></span><ArrowRight size={16} /></Link><Link to="/student/opportunities"><span className="action-icon action-amber"><Sparkles size={17} /></span><span><strong>Explore matching opportunities</strong><small>{data.opportunity_matches} opportunities based on your profile</small></span><ArrowRight size={16} /></Link></div></Panel></div>
    <Panel title="Institution-assigned courses" subtitle="Progress is recorded by your institution; course statuses are read-only here.">
      {assignedCourses.loading ? <div className="loading-state"><span className="spinner" /> Loading assigned courses…</div>
        : assignedCourses.error ? <div className="learning-dashboard-error"><span>{assignedCourses.error}</span><button className="button button-outline button-small" onClick={() => void assignedCourses.refresh()}>Retry</button></div>
          : assignedCourses.data?.length ? assignedCourses.data.map((course) => <div className="institution-record-row" key={`${course.course_name}-${course.assigned_at}`}><div><strong>{course.course_name}</strong><small>{course.skill}{course.completed_at ? ` · Completed ${new Date(course.completed_at).toLocaleDateString()}` : ''}{course.score != null ? ` · Score ${course.score}` : ''}</small></div><Badge tone={course.status === 'COMPLETED' ? 'green' : course.status === 'IN_PROGRESS' ? 'blue' : 'amber'}>{course.status.replace(/_/g, ' ')}</Badge></div>)
            : <Empty title="No courses assigned" body="Courses assigned by your institution will appear here." />}
    </Panel>
    <Panel title="Your mentor" subtitle="Institution-assigned mentor details">
      {assignedMentor.loading ? <div className="loading-state"><span className="spinner" /> Loading mentor details…</div>
        : assignedMentor.error ? <div className="learning-dashboard-error"><span>{assignedMentor.error}</span><button className="button button-outline button-small" onClick={() => void assignedMentor.refresh()}>Retry</button></div>
          : assignedMentor.data ? <div className="institution-record-row"><div><strong>{assignedMentor.data.name}</strong><small>{assignedMentor.data.expertise}</small></div><Badge tone="green">{assignedMentor.data.status.replace(/_/g, ' ')}</Badge></div>
            : <Empty title="No mentor assigned" body="Your institution can assign a mentor when mentorship support is appropriate." />}
    </Panel>
    <Panel title="Professional profiles" subtitle="Your links stay private to industry unless you grant access for a specific job application." action={<Link className="text-link" to="/student/profile-sharing">Manage access <ArrowRight size={14} /></Link>}>
      <div className="social-profile-list">
        {learningProfile.data?.linkedin_url && isValidSocialProfileUrl(learningProfile.data.linkedin_url, 'linkedin') && <a href={learningProfile.data.linkedin_url} target="_blank" rel="noopener noreferrer"><span className="social-profile-icon social-linkedin"><Linkedin size={17} /></span><span><strong>LinkedIn</strong><small>{learningProfile.data.linkedin_url}</small></span><span className="button button-outline button-small">View Profile</span></a>}
        {learningProfile.data?.github_url && isValidSocialProfileUrl(learningProfile.data.github_url, 'github') && <a href={learningProfile.data.github_url} target="_blank" rel="noopener noreferrer"><span className="social-profile-icon social-github"><Github size={17} /></span><span><strong>GitHub</strong><small>{learningProfile.data.github_url}</small></span><span className="button button-outline button-small">View Profile</span></a>}
        {learningProfile.data?.leetcode_url && isValidSocialProfileUrl(learningProfile.data.leetcode_url, 'leetcode') && <a href={learningProfile.data.leetcode_url} target="_blank" rel="noopener noreferrer"><span className="social-profile-icon social-github"><Code2 size={17} /></span><span><strong>LeetCode</strong><small>{learningProfile.data.leetcode_url}</small></span><span className="button button-outline button-small">View Profile</span></a>}
        {learningProfile.loading && <div className="social-profile-empty">Loading profile links…</div>}
        {learningProfile.error && <div className="social-profile-empty">{learningProfile.error} <button className="text-link" onClick={() => void learningProfile.refresh()}>Retry</button></div>}
        {learningProfile.data && !(learningProfile.data.linkedin_url && isValidSocialProfileUrl(learningProfile.data.linkedin_url, 'linkedin')) && !(learningProfile.data.github_url && isValidSocialProfileUrl(learningProfile.data.github_url, 'github')) && !(learningProfile.data.leetcode_url && isValidSocialProfileUrl(learningProfile.data.leetcode_url, 'leetcode')) && <div className="social-profile-empty">Add professional profile links to display them here.</div>}
      </div>
    </Panel>
    <Panel title="My Learning Roadmap" subtitle="Your versioned, rule-based plan and next practical task." action={<Link className="text-link" to="/student/roadmap">Open roadmap <ArrowRight size={14} /></Link>}>
      {learningPlan.loading ? <div className="loading-state"><span className="spinner" /> Loading your plan…</div>
        : learningPlan.error ? <div className="learning-dashboard-error"><span>{learningPlan.error}</span><button className="button button-outline button-small" onClick={() => void learningPlan.refresh()}>Retry</button></div>
          : learningPlan.data?.career_goal ? <div className="learning-dashboard-plan"><div><strong>{learningPlan.data.career_goal}</strong><span>{learningPlan.data.completed_tasks ?? 0} of {learningPlan.data.total_tasks ?? learningPlan.data.tasks.length} tasks complete</span></div><ProgressBar value={learningPlan.data.progress} /><div className="learning-dashboard-next">{learningPlan.data.tasks.find((task) => task.next_recommended_task)?.title ?? 'All planned tasks are complete'}</div></div>
            : <div className="learning-dashboard-empty"><span>Choose a career role and add current skills to generate a personalized learning plan.</span><Link className="button button-primary button-small" to="/student/learning-profile">Set up profile <ArrowRight size={14} /></Link></div>}
    </Panel>
    <div className="journey-banner"><div className="journey-banner-icon"><Flame size={20} /></div><div><strong>Skills grow when learning meets real work.</strong><span>Your verified Skill Passport brings assessments, project work and mentor feedback together.</span></div><Link to="/student/skills">Explore passport <ArrowRight size={14} /></Link></div>
  </>}</LoadState>
}

function CareerPage() {
  const { data: roles, loading, error, refresh } = useLoad<CareerRole[]>(studentService.careerRoles)
  const { data: profile, refresh: refreshProfile } = useLoad(studentService.profile)
  const [selected, setSelected] = useState('')
  const [saved, setSaved] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (profile?.career_goal) setSelected(profile.career_goal) }, [profile?.career_goal])
  async function save() { if (!selected) return; setBusy(true); setSaved(''); try { await studentService.setCareer(selected); setSaved('Career goal saved. Your skill gap and roadmap are ready.'); await refreshProfile() } catch (e) { setSaved(messageFromError(e)) } finally { setBusy(false) } }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="CAREER DIRECTION" title="Choose your next destination" description="Your career goal shapes the skills we prioritize and the roadmap we build." />
    <div className="role-grid">{roles?.map((role) => <button key={role.id} onClick={() => setSelected(role.name)} className={`role-card ${selected === role.name ? 'role-selected' : ''}`}><span className="role-card-icon"><Target size={19} /></span><span className="role-card-name">{role.name}</span><span className="role-card-description">{role.description}</span><span className="role-skill-label">CORE SKILLS</span><span className="role-skills">{role.skills.slice(0, 5).map((skill) => <Badge key={skill.name}>{skill.name}</Badge>)}</span>{selected === role.name && <span className="role-check"><Check size={15} /></span>}</button>)}</div>
    <div className="save-row"><span>{saved || 'You can revisit your career goal any time.'}</span><button className="button button-primary" disabled={!selected || busy} onClick={save}>{busy ? 'Saving…' : 'Save career goal'} <ArrowRight size={15} /></button></div>
  </LoadState>
}

function ProfilePage() {
  const { data, loading, error, refresh, setData } = useLoad(studentService.profile)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function save(event: FormEvent) { event.preventDefault(); if (!data) return; setBusy(true); setMessage(''); try { const updated = await studentService.updateProfile(data); setData(updated); setMessage('Your profile has been saved.') } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) } }
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="YOUR PROFILE" title="A little more about you" description="Help mentors and industry partners understand your learning journey." /><form className="panel profile-form" onSubmit={save}><div className="profile-avatar-large">{data.name.slice(0,1)}</div><div className="profile-fields"><label>Full name<input required value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} /></label><label>Email<input value={data.email} disabled /></label><label>College or institution<input value={data.college} onChange={(e) => setData({ ...data, college: e.target.value })} /></label><label>Department<input value={data.department} onChange={(e) => setData({ ...data, department: e.target.value })} /></label><label>Year of study<input type="number" min={1} max={8} value={data.year} onChange={(e) => setData({ ...data, year: Number(e.target.value) })} /></label><label>Interests<input value={data.interests} onChange={(e) => setData({ ...data, interests: e.target.value })} placeholder="e.g. analytics, product design" /></label><label className="field-full">Short bio<textarea rows={4} value={data.bio} onChange={(e) => setData({ ...data, bio: e.target.value })} placeholder="Tell us what you're curious about…" /></label></div><div className="form-bottom"><span>{message}</span><button disabled={busy} className="button button-primary">{busy ? 'Saving…' : 'Save profile'} <Check size={15} /></button></div></form></>}</LoadState>
}

function LearningProfilePage() {
  const profileLoad = useLoad<LearningProfile>(studentService.learningProfile)
  const roleLoad = useLoad<CareerRole[]>(studentService.careerRoles)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [skillName, setSkillName] = useState('')
  const [skillLevel, setSkillLevel] = useState(1)
  const data = profileLoad.data
  const retry = () => { void profileLoad.refresh(); void roleLoad.refresh() }
  function updateProfile(patch: Partial<LearningProfile>) {
    if (data) profileLoad.setData({ ...data, ...patch })
  }
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!data) return
    setBusy(true)
    setMessage('')
    try {
      const updated = await studentService.updateLearningProfile({
        ...data,
      })
      profileLoad.setData(updated)
      setMessage('Your learning profile has been saved.')
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  async function saveProfileLinks() {
    if (!data) return
    if (!isValidSocialProfileUrl(data.github_url, 'github') ||
        !isValidSocialProfileUrl(data.linkedin_url, 'linkedin') ||
        !isValidSocialProfileUrl(data.leetcode_url, 'leetcode')) {
      setMessage('Use official GitHub, LinkedIn, or LeetCode profile domains for each link.')
      return
    }
    setBusy(true)
    setMessage('')
    try {
      const updated = await studentService.updateLearningProfile({
        github_url: data.github_url.trim(),
        linkedin_url: data.linkedin_url.trim(),
        leetcode_url: data.leetcode_url.trim(),
      })
      profileLoad.setData(updated)
      setMessage('Your professional profile links have been saved.')
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  function addSkill() {
    if (!data || !skillName.trim()) return
    if (data.current_skills.some((item) => item.skill_name.toLowerCase() === skillName.trim().toLowerCase())) {
      setMessage('That skill is already in your profile.')
      return
    }
    updateProfile({ current_skills: [...data.current_skills, { skill_name: skillName.trim(), proficiency: skillLevel, level: '', verification_status: 'IN PROGRESS', evidence: 'Self-reported in learning profile' }] })
    setSkillName('')
    setMessage('')
  }
  return <LoadState loading={profileLoad.loading || roleLoad.loading} error={profileLoad.error || roleLoad.error} retry={retry}>
    {data && <><PageHeading eyebrow="PERSONALIZED LEARNING PROFILE" title="Tell us how you learn" description="Your self-reported skills and study preferences shape transparent, rule-based learning suggestions." action={<Badge tone="blue">Student profile</Badge>} />
      <form className="panel profile-form learning-profile-form" onSubmit={save}>
        <div className="profile-fields">
          <label>Career goal<select value={data.career_goal} onChange={(event) => updateProfile({ career_goal: event.target.value })}><option value="">Choose a configured role</option>{roleLoad.data?.map((role) => <option key={role.id} value={role.name}>{role.name}</option>)}</select></label>
          <label>Study time per day (minutes)<input type="number" min={5} max={720} value={data.study_minutes_per_day ?? ''} onChange={(event) => updateProfile({ study_minutes_per_day: event.target.value ? Number(event.target.value) : null })} placeholder="e.g. 45" /></label>
          <label>Learning language<input value={data.learning_language} maxLength={60} onChange={(event) => updateProfile({ learning_language: event.target.value })} /></label>
          <label>Preferred format<select value={data.learning_format} onChange={(event) => updateProfile({ learning_format: event.target.value as LearningProfile['learning_format'] })}><option>Mixed</option><option>Video</option><option>Reading</option><option>Interactive</option></select></label>
          <label>Programming languages<input value={data.programming_languages.join(', ')} onChange={(event) => updateProfile({ programming_languages: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="Python, JavaScript" /></label>
          <label>Completed courses<input value={data.completed_courses.join(', ')} onChange={(event) => updateProfile({ completed_courses: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="Course names, separated by commas" /></label>
          <label className="field-full">Completed projects<input value={data.completed_projects.join(', ')} onChange={(event) => updateProfile({ completed_projects: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="Project names, separated by commas" /></label>
          <label>Target companies<input value={data.target_companies.join(', ')} onChange={(event) => updateProfile({ target_companies: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="Optional, separated by commas" /></label>
        </div>
        <Panel title="Professional Profiles" subtitle="Add or edit profile links. Sharing with a company is managed separately for each job application.">
          <div className="social-link-editor">
            <div className="social-link-editor-row"><span className="social-profile-icon social-linkedin"><Linkedin size={17} /></span><label>LinkedIn profile URL<input type="url" value={data.linkedin_url} onChange={(event) => updateProfile({ linkedin_url: event.target.value })} placeholder="https://www.linkedin.com/in/username" /></label>{data.linkedin_url && isValidSocialProfileUrl(data.linkedin_url, 'linkedin') && <a className="button button-outline button-small" href={data.linkedin_url} target="_blank" rel="noopener noreferrer">View Profile</a>}</div>
            <div className="social-link-editor-row"><span className="social-profile-icon social-github"><Github size={17} /></span><label>GitHub profile URL<input type="url" value={data.github_url} onChange={(event) => updateProfile({ github_url: event.target.value })} placeholder="https://github.com/username" /></label>{data.github_url && isValidSocialProfileUrl(data.github_url, 'github') && <a className="button button-outline button-small" href={data.github_url} target="_blank" rel="noopener noreferrer">View Profile</a>}</div>
            <div className="social-link-editor-row"><span className="social-profile-icon social-github"><Code2 size={17} /></span><label>LeetCode profile URL<input type="url" value={data.leetcode_url} onChange={(event) => updateProfile({ leetcode_url: event.target.value })} placeholder="https://leetcode.com/u/username" /></label>{data.leetcode_url && isValidSocialProfileUrl(data.leetcode_url, 'leetcode') && <a className="button button-outline button-small" href={data.leetcode_url} target="_blank" rel="noopener noreferrer">View Profile</a>}</div>
          </div>
          <div className="social-links-save"><span>{message}</span><button type="button" disabled={busy} className="button button-primary button-small" onClick={() => void saveProfileLinks()}>{busy ? 'Saving…' : 'Save links'} <Check size={14} /></button></div>
        </Panel>
        <Panel title="Current skills" subtitle="Proficiency is self-reported unless evidence is separately verified. Levels range from 0 (not learned) to 5.">
          <div className="learning-skill-list">{data.current_skills.map((skill, index) => <div className="learning-skill-row" key={skill.skill_name}><strong>{skill.skill_name}</strong><span>{skill.verification_status === 'VERIFIED' ? 'Verified evidence' : 'Self-reported'}</span><select aria-label={`${skill.skill_name} proficiency`} disabled={skill.verification_status === 'VERIFIED'} value={skill.proficiency} onChange={(event) => updateProfile({ current_skills: data.current_skills.map((item, itemIndex) => itemIndex === index ? { ...item, proficiency: Number(event.target.value) } : item) })}>{[0,1,2,3,4,5].map((level) => <option key={level} value={level}>{level} — {['Not learned','Beginner','Beginner','Intermediate','Advanced','Advanced'][level]}</option>)}</select></div>)}
            <div className="learning-skill-add"><input aria-label="New skill name" value={skillName} onChange={(event) => setSkillName(event.target.value)} placeholder="Add a skill, e.g. Python" /><select aria-label="New skill proficiency" value={skillLevel} onChange={(event) => setSkillLevel(Number(event.target.value))}>{[0,1,2,3,4,5].map((level) => <option key={level} value={level}>{level} — {['Not learned','Beginner','Beginner','Intermediate','Advanced','Advanced'][level]}</option>)}</select><button type="button" className="button button-outline button-small" onClick={addSkill}><Plus size={14} /> Add skill</button></div>
          </div>
        </Panel>
        <div className="form-bottom"><span>{message || 'Completing a roadmap task will not automatically change skill proficiency.'}</span><button disabled={busy} className="button button-primary">{busy ? 'Saving…' : 'Save learning profile'} <Check size={15} /></button></div>
      </form>
    </>}
  </LoadState>
}

function LearningAnalysisPage() {
  const { data, loading, error, refresh } = useLoad<LearningAnalysis>(studentService.learningAnalysis)
  return <LoadState loading={loading} error={error} retry={refresh}>
    <PageHeading eyebrow="SKILL GAP ANALYSIS" title="A clear view of your next skills" description="Role requirements are compared with your profile using transparent, deterministic rules." action={<Link className="button button-outline button-small" to="/student/learning-profile">Update profile <ArrowRight size={14} /></Link>} />
    {!data?.career_goal ? <div className="panel"><Empty title="Choose a career goal first" body="Select one of the configured career roles and add your current skills to get a personalized comparison." /><Link className="button button-primary centered-button" to="/student/learning-profile">Set up learning profile</Link></div> : <>
      <div className="learning-summary-grid">
        <div className="learning-summary-card"><span>Target role</span><strong>{data.career_goal}</strong></div>
        <div className="learning-summary-card"><span>Provisional readiness</span><strong>{data.readiness == null ? '—' : `${data.readiness}%`}</strong></div>
        <div className="learning-summary-card"><span>Recommendation method</span><strong>Rule-based</strong></div>
      </div>
      {data.provisional && <div className="notice-banner learning-provisional"><CircleHelp size={18} /><div><strong>This analysis is provisional</strong>{data.provisional_reasons.map((reason) => <span key={reason}>{reason}</span>)}</div></div>}
      <Panel title="How readiness is calculated" subtitle={data.readiness_calculation}><p className="learning-method-note">This score is a planning indicator only. It is not a hiring, placement, or certification prediction. Assessment and verification evidence remain distinct from self-reported proficiency.</p></Panel>
      <Panel title="Role skill comparison" subtitle="Requirements come from the role's configured skill levels.">
        <div className="learning-gap-list">{data.skills.map((skill) => <article className="learning-gap-card" key={skill.skill_id}><div className="learning-gap-heading"><div><h3>{skill.skill}</h3><span>{skill.category} · {skill.why_it_matters}</span></div><Badge tone={skill.gap >= 2 ? 'coral' : skill.gap ? 'blue' : 'green'}>{skill.status}</Badge></div><div className="learning-levels"><span>Your level <strong>{skill.current}/5 · {skill.current_level}</strong></span><ProgressBar value={skill.required ? skill.current / skill.required * 100 : 100} /><span>Required <strong>{skill.required}/5 · {skill.required_level}</strong></span><span>Gap <strong>{skill.gap}</strong></span></div>{skill.prerequisites.length > 0 && <small className="learning-prerequisites">Prerequisites: {skill.prerequisites.map((item) => `${item.skill} (${item.level})`).join(', ')}</small>}</article>)}</div>
      </Panel>
      <Panel title="Personalized next steps" subtitle="These are deterministic recommendations, not AI-generated advice.">
        <div className="learning-recommendations">{(data.recommendations ?? []).map((recommendation) => <article className="learning-recommendation" key={recommendation.skill}><div className="learning-gap-heading"><div><h3>{recommendation.skill}</h3><p>{recommendation.explanation}</p></div><Badge tone="blue">Rule-based</Badge></div><p className="learning-practice">{recommendation.gap_closing_activity}</p><div className="learning-resources">{recommendation.resources.map((resource) => <a key={`${resource.platform}-${resource.url}`} href={resource.url} target="_blank" rel="noreferrer"><span>{resource.platform} · {resource.link_type}</span><strong>{resource.title}</strong><small>{resource.difficulty}</small></a>)}</div></article>)}</div>
        {(data.recommendations ?? []).length === 0 && <Empty title="No current skill gaps" body="Keep your profile and evidence current, then revisit as role requirements change." />}
      </Panel>
      <div className="notice-banner"><Lightbulb size={18} /><div><strong>Recommended next action</strong><span>{data.next_recommended_action}</span></div><Link className="button button-small button-primary" to="/student/roadmap">View learning roadmap <ArrowRight size={14} /></Link></div>
    </>}
  </LoadState>
}

function AssessmentPage() {
  const { data, loading, error, refresh } = useLoad<Assessment>(assessmentService.get)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [result, setResult] = useState<{ score: number; correct: number; total: number } | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function submit() { if (!data || Object.keys(answers).length !== data.questions.length) { setMessage('Answer every question before submitting.'); return } setBusy(true); setMessage(''); try { const outcome = await assessmentService.submit(Object.entries(answers).map(([id, answer]) => ({ question_id: Number(id), answer }))); setResult(outcome); setAnswers({}) } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) } }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="SKILL DIAGNOSTIC" title="See what you know today" description="A short, practical check-in across the skills connected to your career goal." action={<Badge tone="blue"><ClockIcon /> 10 questions · ~5 minutes</Badge>} />
    {result ? <div className="result-card"><div className="result-icon"><CheckCircle2 size={26} /></div><div className="eyebrow">ASSESSMENT COMPLETE</div><h2>{result.correct} out of {result.total} correct</h2><p>Your assessment updated your skill profile. Visit your skill gap to see refreshed priorities.</p><div className="result-score">{Math.round(result.score)}<small>% score</small></div><Link to="/student/skill-gap" className="button button-primary">See my updated skill gap <ArrowRight size={15} /></Link><button className="text-link result-retake" onClick={() => { setResult(null); void refresh() }}>Take it again</button></div>
      : <><div className="assessment-progress"><span>{Object.keys(answers).length} of {data?.questions.length ?? 0} answered</span><ProgressBar value={(Object.keys(answers).length / (data?.questions.length || 1)) * 100} /></div><div className="question-list">{data?.questions.map((question, index) => <article className="question-card" key={question.id}><div className="question-top"><span className="question-number">{String(index + 1).padStart(2, '0')}</span><Badge>{question.skill}</Badge></div><h3>{question.question}</h3><div className="answer-options">{question.options.map((option) => <button key={option} onClick={() => setAnswers({ ...answers, [question.id]: option })} className={`answer-option ${answers[question.id] === option ? 'answer-selected' : ''}`}><span className="option-radio">{answers[question.id] === option && <i />}</span>{option}</button>)}</div></article>)}</div>{message && <div className="inline-error">{message}</div>}<div className="assessment-submit"><span>Your results update your skill profile and career roadmap.</span><button className="button button-primary" disabled={busy} onClick={submit}>{busy ? 'Calculating…' : 'Submit assessment'} <ArrowRight size={15} /></button></div></>}
  </LoadState>
}
function ClockIcon() { return <Activity size={13} /> }

function SkillGapPage() {
  const { data, loading, error, refresh, setData } = useLoad<SkillGap>(studentService.skillGap)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [resultVersion, setResultVersion] = useState(0)
  const requestId = useRef(0)
  useEffect(() => () => { requestId.current += 1 }, [])
  useEffect(() => {
    if (!analyzing || analysisStartedAt == null) return
    const timer = window.setInterval(() => setElapsed(Date.now() - analysisStartedAt), 80)
    return () => window.clearInterval(timer)
  }, [analyzing, analysisStartedAt])
  async function analyzeSkillGap() {
    if (analyzing) return
    const currentRequest = ++requestId.current
    const startedAt = Date.now()
    setAnalyzing(true)
    setAnalysisError('')
    setData(null)
    setAnalysisStartedAt(startedAt)
    setElapsed(0)
    try {
      const result = await studentService.skillGap()
      const remaining = Math.max(0, 3000 - (Date.now() - startedAt))
      if (remaining) await new Promise((resolve) => window.setTimeout(resolve, remaining))
      if (requestId.current !== currentRequest) return
      setData(result)
      setResultVersion((version) => version + 1)
    } catch (reason) {
      if (requestId.current === currentRequest) setAnalysisError(messageFromError(reason))
    } finally {
      if (requestId.current === currentRequest) {
        setAnalyzing(false)
        setAnalysisStartedAt(null)
      }
    }
  }
  const chartData = useMemo(() => data?.skills.map((item) => ({ skill: item.skill, Required: item.required, Current: item.current })) ?? [], [data])
  const analysisStages = [
    'Reviewing your current skills...',
    'Comparing skills with your target career...',
    'Identifying missing and improvement skills...',
    'Preparing your personalized learning recommendations...',
  ]
  const activeStage = Math.min(analysisStages.length - 1, Math.floor(elapsed / 750))
  const progress = Math.min(96, Math.round(elapsed / 3000 * 96))
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="SKILL INTELLIGENCE" title="Your skill gap, made clear" description={data?.career_goal ? `A practical view of where you are and what ${data.career_goal} roles ask for.` : 'Choose a career goal to generate a personalized skill gap.'} action={<div className="skill-gap-heading-actions"><button className="button button-primary button-small" onClick={() => void analyzeSkillGap()} disabled={analyzing || !data?.career_goal} aria-busy={analyzing}>{analyzing ? 'Analyzing…' : 'Analyze Skill Gap'} <Sparkles size={14} /></button><Link className="button button-outline button-small" to="/student/career">Change goal <ChevronDown size={15} /></Link></div>} />
    {analysisError && <div className="inline-error skill-analysis-error" role="alert"><span>{analysisError}</span><button className="button button-outline button-small" disabled={analyzing} onClick={() => void analyzeSkillGap()}>Retry analysis <Activity size={14} /></button></div>}
    {analyzing && <section className="skill-analysis-loader" aria-live="polite" aria-label="Skill gap analysis in progress">
      <div className="skill-analysis-orbit" aria-hidden="true"><span className="skill-analysis-orbit-core"><Sparkles size={23} /></span><i /><i /><i /></div>
      <div className="eyebrow">PERSONALIZED SKILL INTELLIGENCE</div>
      <h2>AI is analyzing your skill profile...</h2>
      <p>Matching your saved skills with your selected career role.</p>
      <div className="skill-analysis-progress" role="progressbar" aria-label="Analysis progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div>
      <div className="skill-analysis-steps">{analysisStages.map((stage, index) => <div className={index < activeStage ? 'step-complete' : index === activeStage ? 'step-active' : ''} key={stage}><span>{index < activeStage ? <Check size={13} /> : index === activeStage ? <span className="skill-analysis-step-pulse" /> : String(index + 1).padStart(2, '0')}</span><span>{stage}</span></div>)}</div>
      <span className="skill-analysis-note">Using your actual profile and configured role requirements · no results are shown until analysis completes</span>
    </section>}
    {!analyzing && !data && !analysisError && <div className="panel"><Empty title="No analysis results yet" body="Click Analyze Skill Gap to compare your current profile with your selected career role." /></div>}
    {!analyzing && data && <div className="skill-analysis-results" key={resultVersion}>
    {!data?.career_goal ? <div className="panel"><Empty title="Choose a career goal first" body="We'll compare your current skills with real role requirements." /><Link className="button button-primary centered-button" to="/student/career">Choose a career goal</Link></div> : <>
      <div className="notice-banner priority-banner"><span className="priority-star"><Sparkles size={17} /></span><div><strong>{data.highest_priority ? `Your highest priority skill is ${data.highest_priority}.` : 'You are meeting the current skill targets.'}</strong><span>Priorities are calculated from required proficiency and your current demonstrated skill level.</span></div><Link className="text-link" to="/student/roadmap">View roadmap <ArrowRight size={14} /></Link></div>
      <div className="analysis-grid"><Panel title="Current vs required" subtitle="Proficiency level out of 5" className="chart-panel"><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} layout="vertical" margin={{ left: 15, right: 10 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#edf0f6" /><XAxis type="number" domain={[0,5]} tickLine={false} axisLine={false} /><YAxis dataKey="skill" type="category" width={130} tickLine={false} axisLine={false} /><Tooltip /><Legend /><Bar dataKey="Current" fill="#5068ef" radius={[0,5,5,0]} barSize={11} /><Bar dataKey="Required" fill="#dfe4f1" radius={[0,5,5,0]} barSize={11} /></BarChart></ResponsiveContainer></div></Panel><Panel title="Skill profile" subtitle="Your current proficiency shape" className="chart-panel"><div className="radar-wrap"><ResponsiveContainer width="100%" height="100%"><RadarChart data={data.skills}><PolarGrid stroke="#e9edf5" /><PolarAngleAxis dataKey="skill" tick={{ fill:'#73809a', fontSize:10 }} /><Radar name="Current" dataKey="current" stroke="#536cf2" fill="#536cf2" fillOpacity={0.18} /><Radar name="Required" dataKey="required" stroke="#14a889" fill="#14a889" fillOpacity={0.09} /><Legend /></RadarChart></ResponsiveContainer></div></Panel></div>
      <Panel title="Your priorities" subtitle="Focus first on the skills with the greatest gap"><div className="gap-table-wrap"><table className="data-table"><thead><tr><th>SKILL</th><th>REQUIRED</th><th>YOUR LEVEL</th><th>GAP</th><th>PRIORITY</th></tr></thead><tbody>{data.skills.map((item) => <tr key={item.skill}><td><strong>{item.skill}</strong><small>{item.category}</small></td><td>{item.required}/5</td><td><div className="table-level">{item.current}/5 <ProgressBar value={item.current / item.required * 100} /></div></td><td><span className={`gap-number ${item.gap > 2 ? 'gap-high' : item.gap ? 'gap-mid' : 'gap-none'}`}>{item.gap}</span></td><td><Badge tone={item.gap > 2 ? 'coral' : item.gap > 0 ? 'blue' : 'green'}>{item.priority}</Badge></td></tr>)}</tbody></table></div></Panel>
      <Panel title="Recommended next steps" subtitle="A dynamic learning chain based on your current gaps"><div className="recommendation-grid">{data.recommendations.map((item) => <article key={item.skill} className="recommendation-card"><div className="recommendation-top"><Badge tone="blue">{item.skill}</Badge><ArrowRight size={15} /></div><div className="recommendation-step"><BookOpen /><div><small>LEARN</small><strong>{item.course}</strong></div></div><div className="recommendation-step"><Activity /><div><small>PRACTICE</small><strong>{item.practice}</strong></div></div><div className="recommendation-step"><BriefcaseBusiness /><div><small>APPLY</small><strong>{item.project}</strong></div></div></article>)}</div>{data.recommendations.length === 0 && <Empty title="No priority gaps right now" body="Refresh your diagnostic as you build new capabilities." />}</Panel>
    </>}
    </div>}
  </LoadState>
}

function RoadmapPage() {
  const { data, loading, error, refresh, setData } = useLoad<LearningRoadmap>(learningRoadmapService.get)
  const [busy, setBusy] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  async function updateStatus(task: LearningTask, status: LearningTask['status']) { setBusy(task.id); setActionError(''); try { setData(await learningRoadmapService.updateTask(task.id, status)) } catch (e) { setActionError(messageFromError(e)) } finally { setBusy(null) } }
  async function refreshPlan() { setRefreshing(true); setActionError(''); try { setData(await learningRoadmapService.refresh()) } catch (e) { setActionError(messageFromError(e)) } finally { setRefreshing(false) } }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="PERSONALIZED LEARNING ROADMAP" title={data?.career_goal ? `Your ${data.career_goal} learning plan` : 'Your learning roadmap'} description="A versioned, rule-based sequence of learning, practice and portfolio tasks. Completing a task records activity, not skill mastery." action={<div className="roadmap-heading-actions"><div className="roadmap-progress-pill"><span>{data?.progress ?? 0}%</span><small>COMPLETE</small></div><button className="button button-outline button-small" onClick={() => void refreshPlan()} disabled={refreshing}>{refreshing ? 'Refreshing…' : 'Refresh plan'} <Activity size={14} /></button></div>} />
    {actionError && <div className="inline-error">{actionError}</div>}
    {data?.provisional && <div className="notice-banner learning-provisional"><CircleHelp size={18} /><div><strong>This plan is based on provisional profile evidence</strong>{data.provisional_reasons.map((reason) => <span key={reason}>{reason}</span>)}</div><Link className="text-link" to="/student/learning-profile">Update profile <ArrowRight size={14} /></Link></div>}
    {!data?.career_goal ? <div className="panel"><Empty title="Your roadmap is ready to be personalized" body="Choose a configured career goal and add your skills to generate learning tasks." /><Link className="button button-primary centered-button" to="/student/learning-profile">Set up learning profile</Link></div> : <>
      <div className="learning-roadmap-summary"><span>Plan version {data.plan_version}</span><span>{data.completed_tasks ?? 0} of {data.total_tasks ?? data.tasks.length} tasks completed</span><span>{data.estimated_days == null ? 'Add study time to estimate a schedule' : `About ${data.estimated_days} study days at ${data.study_minutes_per_day} minutes/day`}</span><span>Rule-based recommendations</span></div>
      <div className="roadmap-timeline learning-roadmap-timeline">{data.tasks.map((task) => <article className={`roadmap-task ${task.status === 'Completed' ? 'task-done' : ''}`} key={task.id}><div className="timeline-rail"><span className="timeline-dot">{task.status === 'Completed' ? <Check size={14} /> : String(task.order).padStart(2, '0')}</span></div><div className="roadmap-task-card learning-task-card"><div className="roadmap-task-head"><div><div className="task-meta"><span>PHASE {task.phase}: {task.phase_name}</span>{task.skill && <Badge tone="blue">{task.skill}</Badge>}{task.next_recommended_task && <Badge tone="purple">Next recommended</Badge>}</div><h3>{task.title}</h3></div><select aria-label={`Status for ${task.title}`} value={task.status} disabled={busy === task.id} onChange={(event) => void updateStatus(task, event.target.value as LearningTask['status'])}><option>Not Started</option><option>In Progress</option><option>Completed</option></select></div><p>{task.why}</p><p>{task.explanation}</p>{task.prerequisites.length > 0 && <div className="learning-task-detail"><strong>Prerequisites</strong><span>{task.prerequisites.join(', ')}</span></div>}<div className="learning-task-detail"><strong>Practice</strong><span>{task.practice}</span></div><div className="learning-task-detail"><strong>Mini-project</strong><span>{task.mini_project}</span></div><div className="learning-task-footer"><span><ClockIcon /> {task.estimated_minutes} minutes</span>{task.resources.length > 0 && <div className="learning-task-resources">{task.resources.map((resource) => <a key={`${resource.platform}-${resource.url}`} href={resource.url} target="_blank" rel="noreferrer">{resource.platform}: {resource.title}</a>)}</div>}</div></div></article>)}</div>
      <div className="notice-banner"><ShieldCheck size={18} /><div><strong>Learning activity does not automatically verify proficiency</strong><span>Update skill levels in your learning profile only when you have relevant evidence.</span></div><Link className="text-link" to="/student/learning-profile">Review profile <ArrowRight size={14} /></Link></div>
    </>}
  </LoadState>
}

function ProjectCard({ project, onChanged }: { project: Project; onChanged: () => void }) {
  const [showSubmit, setShowSubmit] = useState(false)
  const [summary, setSummary] = useState('')
  const [description, setDescription] = useState('')
  const [github, setGithub] = useState('')
  const [demoUrl, setDemoUrl] = useState('')
  const [reportUrl, setReportUrl] = useState('')
  const [skillsUsed, setSkillsUsed] = useState('')
  const [evidence, setEvidence] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function apply() { setBusy(true); setMessage(''); try { await studentService.applyToProject(project.id); setMessage('Application submitted. You can now submit your work.'); onChanged() } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) } }
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await projectService.submit(project.id, {
        summary, description, github_url: github, demo_url: demoUrl, report_url: reportUrl, evidence,
        skills_used: skillsUsed.split(',').map((skill) => skill.trim()).filter(Boolean),
      })
      setMessage('Project submission sent for industry review.'); setShowSubmit(false); onChanged()
    } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) }
  }
  return <article className="project-card"><div className="project-card-top"><span className="project-icon"><BriefcaseBusiness size={18} /></span><Badge tone="purple">{project.difficulty}</Badge></div><div className="project-company">{project.company} <span>·</span> {project.domain}</div><h3>{project.title}</h3><p>{project.description}</p><div className="project-skills">{project.required_skills.map((skill) => <Badge key={skill}>{skill}{project.required_skill_levels?.[skill] ? ` · ${project.required_skill_levels[skill]}/5` : ''}</Badge>)}</div>{project.eligibility && <div className="listing-eligibility"><strong>Eligibility</strong><span>{project.eligibility}</span></div>}{project.candidate_match && <CandidateMatchSummary match={project.candidate_match} /> }<div className="project-meta"><span><Users size={14} /> {project.applications} applied</span><span><Activity size={14} /> Due {project.deadline || 'Open'}</span></div>{project.submission_status === 'NEEDS_REVISION' ? <div className="project-actions"><Badge tone="amber">Revision requested</Badge><button className="button button-primary button-small" onClick={() => setShowSubmit(!showSubmit)}>Submit revision <Send size={14} /></button></div> : project.submission_status ? <div className="project-applied"><CheckCircle2 size={16} /> Submission {project.submission_status === 'SUBMITTED' ? 'awaiting review' : project.submission_status.toLowerCase().replace(/_/g, ' ')}</div> : project.application_status ? <div className="project-actions"><Badge tone="green">{project.application_status}</Badge><button className="button button-primary button-small" onClick={() => setShowSubmit(!showSubmit)}>Submit work <Send size={14} /></button></div> : <button disabled={busy} className="button button-outline button-full" onClick={() => void apply()}>{busy ? 'Applying…' : 'Apply to project'} <ArrowRight size={14} /></button>}{message && <div className={message.includes('sent') || message.includes('submitted') ? 'success-note' : 'inline-error'}>{message}</div>}{showSubmit && <form className="submission-form" onSubmit={submit}><label>Submission summary<input required maxLength={500} value={summary} onChange={(e) => setSummary(e.target.value)} /></label><label>What did you build?<textarea required minLength={10} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></label><label>GitHub repository URL<input type="url" value={github} onChange={(e) => setGithub(e.target.value)} placeholder="https://github.com/…" /></label><label>Demo URL<input type="url" value={demoUrl} onChange={(e) => setDemoUrl(e.target.value)} /></label><label>Report URL<input type="url" value={reportUrl} onChange={(e) => setReportUrl(e.target.value)} /></label><label>Skills used<input value={skillsUsed} onChange={(e) => setSkillsUsed(e.target.value)} placeholder="Python, SQL" /></label><label>Evidence or notes<input value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="Dashboard, demo, or supporting evidence" /></label><button disabled={busy} className="button button-primary button-small">{busy ? 'Sending…' : project.submission_status === 'NEEDS_REVISION' ? 'Send revision' : 'Send for evaluation'}</button></form>}</article>
}

function CandidateMatchSummary({ match }: { match: NonNullable<Project['candidate_match']> }) {
  return <div className="candidate-match-summary"><div><strong>{match.match_percent}% skill match</strong><span>{match.explanation}</span></div><small>{match.decision_note}</small></div>
}

function StudentProjectsPage() {
  const { data, loading, error, refresh } = useLoad<IndustryProject[]>(studentService.projectMarketplace)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="LEARN BY BUILDING" title="Industry projects" description="Practice on real challenges and build evidence mentors can verify." action={<Badge>{data?.length ?? 0} open projects</Badge>} />{data?.length ? <div className="project-grid">{data.map((project) => <ProjectCard key={project.id} project={project} onChanged={() => void refresh()} />)}</div> : <div className="panel"><Empty title="No open projects yet" body="Check back soon as industry partners publish new challenges." /></div>}</LoadState>
}

function StudentJobsPage() {
  const { data, loading, error, refresh } = useLoad<JobVacancy[]>(studentService.jobVacancies)
  const [busy, setBusy] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [sharing, setSharing] = useState<Record<number, ProfileType[]>>({})
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All categories')
  const categories = [...new Set((data ?? []).map((vacancy) => vacancy.company_category).filter(Boolean))].sort()
  const visibleVacancies = (data ?? []).filter((vacancy) =>
    (vacancy.title.toLowerCase().includes(search.toLowerCase()) || vacancy.company.toLowerCase().includes(search.toLowerCase()) || vacancy.description.toLowerCase().includes(search.toLowerCase())) &&
    (category === 'All categories' || vacancy.company_category === category),
  )
  function toggleProfile(id: number, profile: ProfileType) {
    const selected = sharing[id] ?? []
    setSharing({
      ...sharing,
      [id]: selected.includes(profile) ? selected.filter((item) => item !== profile) : [...selected, profile],
    })
  }
  async function apply(vacancy: JobVacancy) {
    const selected = sharing[vacancy.id] ?? []
    if (selected.length && !window.confirm(`Allow ${vacancy.company} to access your selected professional profile links for this ${vacancy.title} application? You can revoke access later.`)) return
    setBusy(vacancy.id); setMessage('')
    try {
      await studentService.applyToJob(vacancy.id, {
        consent_decision: selected.length ? 'GRANTED' : 'DECLINED',
        profile_types: selected,
      })
      setMessage(selected.length
        ? `Application submitted to ${vacancy.company}; access was granted only for the profiles you selected.`
        : `Application submitted to ${vacancy.company} without profile sharing.`)
      await refresh()
    }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(null) }
  }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="JOB VACANCIES" title="Explore student opportunities" description="Compare each role with your recorded skill levels and apply directly. Sample postings are simulated, not verified live vacancies. Match information is advisory." action={<Link className="button button-outline button-small" to="/student/applications">Track applications <ArrowRight size={14} /></Link>} />
    {message && <div className={message.includes('submitted') ? 'success-note' : 'inline-error'}>{message}</div>}
    <div className="demo-directory-controls"><label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search job title, company, or description" aria-label="Search job vacancies" /></label><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by job category"><option>All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></div>
    {visibleVacancies.length ? <div className="job-vacancy-list">{visibleVacancies.map((vacancy) => <article className="job-vacancy-card" key={vacancy.id}><div className="job-vacancy-top"><div>{vacancy.is_demo && <Badge tone="amber">{vacancy.demo_label || 'DEMO SAMPLE OPENING'}</Badge>}<div className="project-company">{vacancy.company} · {vacancy.company_category} · {vacancy.location}</div><h2>{vacancy.title}</h2><span>{vacancy.employment_type} · {vacancy.experience_level || 'Experience not specified'} · Posted {vacancy.posted_at ? new Date(vacancy.posted_at).toLocaleDateString() : 'date unavailable'}</span></div><Badge tone="purple">{vacancy.employment_type}</Badge></div><p>{vacancy.description}</p><div className="listing-eligibility"><strong>Eligibility</strong><span>{vacancy.eligibility || 'No additional criteria specified.'}</span></div><div className="project-skills">{Object.entries(vacancy.required_skill_levels).map(([name, level]) => <Badge key={name}>{name} · required level {level}/5</Badge>)}{vacancy.preferred_skills.map((skill) => <Badge key={skill} tone="purple">Preferred: {skill}</Badge>)}</div>{vacancy.candidate_match && <CandidateMatchSummary match={vacancy.candidate_match} />}{vacancy.deadline && <div className="project-meta"><span><Activity size={14} /> Apply by {vacancy.deadline}</span></div>}{vacancy.application_status ? <div className="project-actions"><Badge tone={['SHORTLISTED', 'INTERVIEW', 'SELECTED'].includes(vacancy.application_status) ? 'green' : 'blue'}>{vacancy.application_status}</Badge><Link className="text-link" to="/student/applications">View application update <ArrowRight size={14} /></Link></div> : <><section className="profile-consent-panel"><strong>Optional professional-profile sharing</strong><p>{vacancy.company} can use selected links to review your background for this role. Applying does not require profile sharing. You can later review or revoke access from Professional Profiles &amp; Access.</p>{([['linkedin', 'LinkedIn'], ['github', 'GitHub'], ['leetcode', 'LeetCode']] as [ProfileType, string][]).map(([type, label]) => <label key={type}><input type="checkbox" checked={(sharing[vacancy.id] ?? []).includes(type)} onChange={() => toggleProfile(vacancy.id, type)} /> Share my {label} profile with {vacancy.company} for this application</label>)}</section><button className="button button-outline button-full" disabled={busy === vacancy.id} onClick={() => void apply(vacancy)}>{busy === vacancy.id ? 'Applying…' : (sharing[vacancy.id] ?? []).length ? `Apply and share ${sharing[vacancy.id].length} selected profile(s)` : 'Apply without sharing profiles'} <ArrowRight size={14} /></button></>}</article>)}</div>
      : <div className="panel"><Empty title={data?.length ? 'No matching vacancies' : 'No open vacancies yet'} body={data?.length ? 'Try a different search or job category.' : 'New sample or industry vacancies will appear here when available.'} /></div>}
  </LoadState>
}

function StudentApplicationsPage() {
  const { data, loading, error, refresh } = useLoad<StudentApplication[]>(studentService.applications)
  const history = useLoad<ApplicationStatusUpdate[]>(studentPortalService.applicationStatusHistory)
  async function retry() { await Promise.all([refresh(), history.refresh()]) }
  return <LoadState loading={loading || history.loading} error={error || history.error} retry={retry}><PageHeading eyebrow="APPLICATION TRACKER" title="Your applications" description="Follow project and vacancy statuses, company messages and project evaluation feedback." action={<Link className="button button-outline button-small" to="/student/jobs">Browse vacancies <ArrowRight size={14} /></Link>} />
    {data?.length ? <div className="student-application-list">{data.map((application) => <article className="student-application-card" key={`${application.kind}-${application.id}`}><div><Badge tone={application.kind === 'job' ? 'purple' : 'blue'}>{application.kind === 'job' ? 'JOB' : 'PROJECT'}</Badge><h3>{application.title}</h3><span>{application.company} · Applied {application.applied_at ? new Date(application.applied_at).toLocaleDateString() : 'date unavailable'}</span></div><Badge tone={['SHORTLISTED', 'INTERVIEW', 'SELECTED'].includes(application.status) ? 'green' : 'blue'}>{application.status}</Badge>{application.company_note && <p><strong>Company update:</strong> {application.company_note}</p>}{application.evaluation_feedback && <p><strong>Project feedback:</strong> {application.evaluation_feedback}</p>}{application.kind === 'job' && history.data?.some((item) => item.application_id === application.id) && <details><summary>Status history</summary>{history.data.filter((item) => item.application_id === application.id).map((item, index) => <p key={`${item.changed_at}-${index}`}><strong>{item.status}</strong> · {new Date(item.changed_at).toLocaleString()}{item.note ? ` — ${item.note}` : ''}</p>)}</details>}</article>)}</div>
      : <div className="panel"><Empty title="No applications yet" body="Apply to a project or job vacancy to track its status here." /><Link className="button button-primary centered-button" to="/student/projects">Browse projects</Link></div>}
  </LoadState>
}

function OpportunitiesPage() {
  const { data, loading, error, refresh } = useLoad<Opportunity[]>(opportunityService.matches)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="NEXT-STEP MATCHING" title="Opportunities shaped around you" description="Ranked by your skill profile, current proficiency and career direction." />{data?.length ? <div className="opportunity-list">{data.map((item) => <article className="opportunity-card" key={item.id}><div className="match-score"><strong>{item.match_score}%</strong><span>MATCH</span></div><div className="opportunity-main"><div className="opportunity-meta"><Badge tone="blue">{item.type}</Badge><span>{item.company}</span><span>·</span><span>{item.location}</span></div><h3>{item.title}</h3><p>{item.description}</p><div className="match-skills">{item.matched_skills.map((skill) => <span className="matched-skill" key={skill}><Check size={12} />{skill}</span>)}{item.missing_skills.map((skill) => <span className="missing-skill" key={skill}><ArrowDownRight size={12} />{skill}</span>)}</div></div><div className="opportunity-action"><ProgressBar value={item.match_score} color="teal" /><small>{item.required_skills.length} skills considered</small><Link className="button button-outline button-small" to="/student/skills">View passport <ArrowRight size={13} /></Link></div></article>)}</div> : <div className="panel"><Empty title="No matches yet" body="Build your skill profile to get opportunities tailored to you." /></div>}</LoadState>
}

function SkillPassportPage() {
  const { data, loading, error, refresh } = useLoad<Passport>(studentService.passport)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="VERIFIED SKILL PASSPORT" title="Make your capabilities visible" description="A living record of your skills, learning evidence and industry-reviewed work." action={<Badge tone="green"><ShieldCheck size={13} /> INDUSTRY READY PROFILE</Badge>} />
    <div className="passport-hero"><div className="passport-person"><div className="passport-avatar">{data.student.name.slice(0,1)}</div><div><div className="passport-label">SKILLBRIDGE VERIFIED PROFILE</div><h2>{data.student.name}</h2><p>{data.student.career_goal || 'Career goal not set'} <span>·</span> {data.student.college || 'Institution not added'}</p></div></div><div className="passport-readiness"><span>READINESS SCORE</span><strong>{data.readiness}<small>/100</small></strong><ProgressBar value={data.readiness} color="teal" /></div></div>
    <div className="passport-grid"><Panel title="Skills & verification" subtitle="Capability paired with evidence"><div className="passport-skills">{data.skills.map((skill) => <div className="passport-skill" key={skill.id}><div className="passport-skill-mark"><Check size={15} /></div><div className="passport-skill-info"><strong>{skill.name}</strong><span>{skill.proficiency}/5 proficiency</span>{skill.evidence && <small>{skill.evidence}</small>}</div><Badge tone={skill.verification_status === 'VERIFIED' ? 'green' : 'amber'}>{skill.verification_status}</Badge></div>)}</div>{!data.skills.length && <Empty title="No skills on your passport yet" body="Take an assessment to start building your evidence." />}</Panel>
      <div className="stack-panels"><Panel title="Industry projects" subtitle={`${data.projects.length} project application${data.projects.length === 1 ? '' : 's'}`}><div className="passport-simple-list">{data.projects.map((project, index) => <div key={`${project.title}-${index}`}><span className="list-icon"><BriefcaseBusiness size={15} /></span><span><strong>{project.title}</strong><small>{project.status}{project.score != null ? ` · Mentor score ${Math.round(project.score)}/100` : ''}</small></span><Badge tone={project.status === 'EVALUATED' ? 'green' : 'blue'}>{project.status}</Badge></div>)}</div>{!data.projects.length && <Empty title="Your first project awaits" body="Apply to an industry challenge to start building proof." />}</Panel><Panel title="Learning evidence" subtitle={`${data.assessments.length} assessment${data.assessments.length === 1 ? '' : 's'} · ${data.certifications.length} certification${data.certifications.length === 1 ? '' : 's'}`}><div className="passport-simple-list">{data.assessments.map((item, index) => <div key={`a${index}`}><span className="list-icon list-blue"><ClipboardCheck size={15} /></span><span><strong>{item.title}</strong><small>{Math.round(item.score)}% score</small></span><Badge tone="blue">ASSESSMENT</Badge></div>)}{data.certifications.map((item, index) => <div key={`c${index}`}><span className="list-icon list-purple"><Award size={15} /></span><span><strong>{item.name}</strong><small>{item.issuer}</small></span><Badge tone="purple">CERTIFIED</Badge></div>)}</div>{!data.assessments.length && !data.certifications.length && <Empty title="Learning evidence builds over time" body="Assessment results and certifications appear here." />}</Panel></div></div>
  </>}</LoadState>
}

function ProgressPage() {
  const { data, loading, error, refresh } = useLoad<Progress>(studentService.progress)
  const metrics = data ? [['Readiness', data.readiness, 'Current proficiency vs career requirements'], ['Assessment', data.assessment_completion, 'Diagnostic completion'], ['Roadmap', data.roadmap_completion, 'Learning tasks marked complete'], ['Project', data.project_completion, 'Applied projects submitted']] as const : []
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="YOUR MOMENTUM" title="Progress you can point to" description="A clear view of the work you have done and the capabilities you are building." /><div className="metric-grid"><Metric label="Readiness" value={`${data.readiness}%`} note="Across career-relevant skills" icon={TrendingUp} /><Metric label="Roadmap completed" value={`${data.roadmap_completion}%`} note="Personal learning plan" icon={Compass} tone="purple" /><Metric label="Verified skills" value={data.verified_skills} note="Mentor-confirmed evidence" icon={ShieldCheck} tone="green" /><Metric label="Assessment" value={`${data.assessment_completion}%`} note="Diagnostic completion" icon={ClipboardCheck} tone="amber" /></div><div className="progress-layout"><Panel title="Journey milestones" subtitle="Learning becomes visible when you can see how far you've come"><div className="milestone-list">{metrics.map(([label,value,note])=><div className="milestone" key={label}><div><span className="milestone-check">{value === 100 ? <Check size={13} /> : <span />}</span><div><strong>{label}</strong><small>{note}</small></div></div><span className="milestone-percent">{value}%</span><ProgressBar value={value} /></div>)}</div></Panel><Panel title="Skill proficiency" subtitle="Skills currently in your profile"><div className="skill-bars">{data.skills.map((skill) => <div key={skill.skill}><span>{skill.skill}</span><strong>{skill.proficiency}/5</strong><ProgressBar value={skill.proficiency * 20} color="teal" /></div>)}</div></Panel></div></>}</LoadState>
}

function IndustryDashboard() {
  const load = useCallback(async () => Promise.all([industryService.dashboard(), industryService.portalDashboard()]), [])
  const { data, loading, error, refresh } = useLoad(load)
  const company = data?.[0]
  const counts = data?.[1]
  return <LoadState loading={loading} error={error} retry={refresh}>{company && counts && <><PageHeading eyebrow="INDUSTRY PARTNER" title={`Good to see you, ${company.company}`} description="Shape industry demand into meaningful projects and discover emerging talent." action={<Link className="button button-primary" to="/industry/projects"><Plus size={16} /> Post a project</Link>} /><div className="metric-grid"><Metric label="Open projects" value={company.open_projects} note="Challenges live in the marketplace" icon={BriefcaseBusiness} /><Metric label="Applications" value={counts.applications_received} note="Student interest across your opportunities" icon={Users} tone="teal" /><Metric label="Awaiting review" value={counts.submissions_awaiting_review} note="Project submissions needing feedback" icon={ClipboardCheck} tone="purple" /><Metric label="Shortlisted candidates" value={counts.shortlisted_candidates} note={counts.eligible_candidates_note} icon={GraduationCap} tone="amber" /></div><div className="metric-grid recruitment-metrics"><Metric label="Total vacancies" value={counts.job_vacancies_total} note="Owned by this company" icon={BriefcaseBusiness} /><Metric label="Open vacancies" value={counts.job_vacancies_open} note="Accepting student applications" icon={CheckCircle2} tone="green" /><Metric label="Job applications" value={counts.job_applications_total} note="Saved for this company's vacancies" icon={Users} tone="teal" /><Metric label="Awaiting review" value={counts.job_applications_awaiting_review} note="Applied or under review" icon={ClipboardCheck} tone="purple" /><Metric label="Shortlisted / interview" value={`${counts.job_applications_shortlisted} / ${counts.job_applications_interview}`} note="Recruitment pipeline" icon={GraduationCap} tone="amber" /><Metric label="Selected" value={counts.job_applications_selected} note="Selection status recorded" icon={CheckCircle2} tone="green" /></div><div className="industry-dashboard-grid"><Panel title="Your active projects" subtitle="Challenges that turn skills into experience" action={<Link className="text-link" to="/industry/projects">Manage projects <ArrowRight size={14} /></Link>}><div className="industry-project-list">{company.projects.slice(0, 5).map((project) => <Link to="/industry/projects" key={project.id}><span className="list-icon list-blue"><BriefcaseBusiness size={15} /></span><span><strong>{project.title}</strong><small>{project.applications} applications · {project.domain}</small></span><Badge tone="green">{project.status}</Badge><ArrowRight size={15} /></Link>)}{!company.projects.length && <Empty title="Your first project can start the loop" body="Publish a challenge to invite learners into real work." />}</div></Panel><Panel title="Skill demand signals" subtitle="Skills showing up across your work"><div className="demand-bars">{company.top_skills.map((item) => <div key={item.skill}><span>{item.skill}</span><ProgressBar value={item.demand / (company.top_skills[0]?.demand || 1) * 100} color="teal" /><strong>{item.demand}</strong></div>)}{!company.top_skills.length && <Empty title="No demand signals yet" body="Project skill requirements will show here." />}</div></Panel></div></>}</LoadState>
}

function IndustryProfilePage() {
  const { data, loading, error, refresh } = useLoad<CompanyProfile>(industryService.companyProfile)
  const [form, setForm] = useState<CompanyProfile | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => { if (data) setForm(data) }, [data])
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    setBusy(true); setMessage('')
    try { setForm(await industryService.updateCompanyProfile(form)); setMessage('Company profile saved.') }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  return <LoadState loading={loading} error={error} retry={refresh}>{form && <><PageHeading eyebrow="COMPANY PROFILE" title={form.company_name} description="Maintain your organization and recruiter contact details for students and applicants." />
    {form.is_demo && <div className="notice-banner"><Lightbulb size={18} /><div><strong>DEMO COMPANY ACCOUNT</strong><span>This synthetic account and its sample vacancies do not represent a real company registration or partnership.</span></div></div>}<form className="panel project-create-form" onSubmit={(event) => void save(event)}><div className="panel-heading"><div><h2>Organization details</h2><p>Company identity and public contact information.</p></div><Badge tone={form.is_demo ? 'amber' : form.verification_status === 'VERIFIED' ? 'green' : 'blue'}>{form.is_demo ? 'DEMO ONLY' : form.verification_status}</Badge></div>
      <div className="form-grid"><label>Company name<input required minLength={2} maxLength={180} value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} /></label><label>Industry type<input maxLength={120} value={form.industry_type} onChange={(e) => setForm({ ...form, industry_type: e.target.value })} /></label><label>Website<input type="url" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} /></label><label>Company email<input type="email" value={form.company_email} onChange={(e) => setForm({ ...form, company_email: e.target.value })} /></label><label>Contact person<input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></label><label>Contact title<input value={form.contact_title} onChange={(e) => setForm({ ...form, contact_title: e.target.value })} /></label><label>Phone<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label><label>Logo URL<input type="url" value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} /></label><label className="field-full">Company description<textarea rows={4} maxLength={4000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label></div>
      <div className="form-bottom"><span>Profile ownership remains tied to your authenticated company account.</span><button disabled={busy} className="button button-primary">{busy ? 'Saving…' : 'Save company profile'} <Check size={15} /></button></div>{message && <div className={message.includes('saved') ? 'success-note' : 'inline-error'}>{message}</div>}
    </form>{form.logo_url && <div className="profile-overview panel"><img src={form.logo_url} alt={`${form.company_name} logo`} className="company-logo" /><div><Badge tone="blue">INDUSTRY PARTNER</Badge><h2>{form.company_name}</h2><p>{form.description}</p>{form.website && <a className="text-link" href={form.website} target="_blank" rel="noreferrer">Visit website <ArrowRight size={14} /></a>}</div></div>}<div className="notice-banner"><Lightbulb size={18} /><div><strong>Make skills visible through real work</strong><span>Project requirements can inform skill gap priorities across career roles.</span></div><Link to="/industry/skills" className="text-link">Manage requirements <ArrowRight size={14} /></Link></div></>}</LoadState>
}

function IndustryCompanyDirectoryPage() {
  const { data, loading, error, refresh } = useLoad(industryService.demoCompanies)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All categories')
  const categories = [...new Set((data ?? []).map((company) => company.category))].sort()
  const visible = (data ?? []).filter((company) =>
    (company.company_name.toLowerCase().includes(search.toLowerCase()) || company.category.toLowerCase().includes(search.toLowerCase())) &&
    (category === 'All categories' || company.category === category),
  )
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="SAMPLE DIRECTORY" title="Demo company directory" description="These sample company profiles are for development and demonstration only; they do not represent registration, partnership, endorsement, or verified live vacancies." action={<Link className="button button-outline button-small" to="/industry/jobs">Manage my vacancies <ArrowRight size={14} /></Link>} />
    <div className="demo-directory-controls"><label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search company or category" aria-label="Search demo companies" /></label><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by company category"><option>All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></div>
    {visible.length ? <div className="demo-company-grid">{visible.map((company) => <article className="demo-company-card" key={company.company_key}><div className="demo-company-card-top"><span className="demo-company-logo">{company.logo_text}</span><Badge tone="amber">{company.account_status}</Badge></div><h2>{company.company_name}</h2><span className="demo-company-category">{company.category}</span><p>{company.description}</p><div className="demo-company-links">{company.website && <a href={company.website} target="_blank" rel="noopener noreferrer">Company website <ArrowRight size={13} /></a>}<Link to="/industry/jobs">Open my job workspace <ArrowRight size={13} /></Link></div></article>)}</div> : <div className="panel"><Empty title="No matching demo companies" body="Try a different company name or category." /></div>}
  </LoadState>
}

function IndustryAnalyzerPage() {
  const [description, setDescription] = useState('')
  const [result, setResult] = useState<Awaited<ReturnType<typeof industryService.extract>> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function analyze(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { setResult(await industryService.extract(description)) } catch (e) { setError(messageFromError(e)) } finally { setBusy(false) } }
  return <><PageHeading eyebrow="LOCAL AI · SKILL EXTRACTION" title="AI job description analyzer" description="Turn hiring language into structured skill signals using the local skill intelligence engine." /><div className="analyzer-layout"><form className="panel analyzer-input" onSubmit={analyze}><div className="panel-heading"><div><h2>Paste a job description</h2><p>We'll identify named capabilities and group them by type.</p></div><span className="ai-mark"><Sparkles size={16} /> LOCAL AI</span></div><label className="sr-label" htmlFor="job-description">Job description</label><textarea id="job-description" required minLength={10} maxLength={12000} rows={11} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="We are looking for a Data Analyst with Python, SQL, Power BI, Excel and statistics experience…" /><div className="analyzer-bottom"><span>{description.length}/12,000 characters · Your text stays local</span><button disabled={busy || description.length < 10} className="button button-primary">{busy ? 'Analyzing…' : 'Analyze skills'} <Sparkles size={15} /></button></div>{error && <div className="inline-error">{error}</div>}</form><div className={`panel analyzer-results ${result ? '' : 'results-empty'}`}><div className="panel-heading"><div><h2>Skill signals</h2><p>{result ? `${result.skills.length} skills found in the description` : 'Extracted skills will appear here.'}</p></div>{result && <Badge tone="green">ANALYZED</Badge>}</div>{result ? <>{Object.entries(result.groups).map(([group, skills]) => <div className="extracted-group" key={group}><div className="extracted-heading">{group}<span>{skills.length}</span></div><div className="extracted-chips">{skills.length ? skills.map((skill) => <Badge tone="blue" key={skill}>{skill}</Badge>) : <span className="muted-small">No matching skills found.</span>}</div></div>)}<div className="engine-footnote"><CheckCircle2 size={14} /> Processed with {result.engine}; no external AI key required.</div></> : <div className="analyzer-placeholder"><div className="placeholder-spark"><Sparkles size={22} /></div><strong>Demand, made clearer.</strong><span>Extracted skill signals help connect job requirements with learning priorities.</span></div>}</div></div><Panel title="Skill dictionary" subtitle="Local extraction recognizes normalized skills and common variants"><div className="dictionary-tags">{['Python', 'SQL', 'Power BI', 'Excel', 'Statistics', 'Data Visualization', 'Machine Learning', 'Cloud', 'Cybersecurity', 'Communication', 'Teamwork', 'React'].map((item) => <Badge key={item}>{item}</Badge>)}</div></Panel></>
}

function IndustrySkillsPage() {
  const [role, setRole] = useState('Data Analyst')
  const [skill, setSkill] = useState('SQL')
  const [level, setLevel] = useState(4)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function save(event: FormEvent) { event.preventDefault(); setBusy(true); setMessage(''); try { await industryService.requirement({ role_name: role, skill_name: skill, required_level: Number(level) }); setMessage(`${skill} requirement for ${role} saved. It now informs student skill gap calculations.`) } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) } }
  return <><PageHeading eyebrow="SKILL DEMAND" title="Define what roles need" description="Add or update the proficiency expectations that inform student career skill gaps." /><form onSubmit={save} className="panel requirement-form"><div className="panel-heading"><div><h2>Role skill requirement</h2><p>Requirements are shared across the platform and used in readiness analysis.</p></div><Target size={20} className="panel-heading-icon" /></div><div className="requirement-fields"><label>Career role<input required value={role} onChange={(e) => setRole(e.target.value)} placeholder="Data Analyst" /></label><label>Skill<input required value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="SQL" /></label><label>Required proficiency<select value={level} onChange={(e) => setLevel(Number(e.target.value))}>{[1,2,3,4,5].map((value) => <option key={value} value={value}>{value} / 5</option>)}</select></label><button disabled={busy} className="button button-primary">{busy ? 'Saving…' : 'Save requirement'} <Check size={15} /></button></div>{message && <div className={message.includes('saved') ? 'success-note' : 'inline-error'}>{message}</div>}</form><div className="notice-banner"><Sparkles size={18} /><div><strong>Job descriptions can help you spot emerging skills</strong><span>Use the analyzer to extract a skill list, then record the proficiency expectations here.</span></div><Link to="/industry/analyzer" className="button button-outline button-small">Open analyzer <ArrowRight size={14} /></Link></div></>
}

const blankProject: IndustryProjectInput = {
  title: '', description: '', domain: '', difficulty: 'Intermediate', required_skills: [],
  expected_outcome: '', evaluation_criteria: '', deadline: '', eligibility: '', required_skill_levels: {},
  deliverables: [], instructions: '', references: [], duration_weeks: null, participation: 'Individual',
  team_size_min: 1, team_size_max: 1, publication_status: 'PUBLISHED',
}

function skillLevelsText(values: Record<string, number>) {
  return Object.entries(values).map(([skill, level]) => `${skill}:${level}`).join(', ')
}

function parseSkillLevels(value: string): Record<string, number> {
  if (!value.trim()) return {}
  return Object.fromEntries(value.split(',').map((item) => {
    const [name, rawLevel] = item.split(':')
    const skill = name?.trim()
    const level = rawLevel == null ? 1 : Number(rawLevel.trim())
    if (!skill || !Number.isInteger(level) || level < 1 || level > 5) throw new Error('Enter skills as Name:level (1–5), separated by commas.')
    return [skill, level]
  }))
}

function IndustryProjectsPage() {
  const { data, loading, error, refresh } = useLoad<IndustryProject[]>(industryService.projects)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState<IndustryProjectInput>(blankProject)
  const [requirementsText, setRequirementsText] = useState('')
  function startEdit(project: IndustryProject) {
    setEditingId(project.id)
    setForm({
      title: project.title, description: project.description, domain: project.domain, difficulty: project.difficulty as IndustryProjectInput['difficulty'],
      required_skills: Object.keys(project.required_skill_levels), required_skill_levels: project.required_skill_levels,
      expected_outcome: project.expected_outcome, evaluation_criteria: project.evaluation_criteria,
      deadline: project.deadline, eligibility: project.eligibility,
      deliverables: project.deliverables ?? [], instructions: project.instructions ?? '',
      references: project.references ?? [], duration_weeks: project.duration_weeks ?? null,
      participation: project.participation ?? 'Individual', team_size_min: project.team_size_min ?? 1,
      team_size_max: project.team_size_max ?? 1,
      publication_status: project.publication_status ?? (project.status === 'OPEN' ? 'PUBLISHED' : project.status === 'DRAFT' ? 'DRAFT' : 'CLOSED'),
    })
    setRequirementsText(skillLevelsText(project.required_skill_levels))
    setFormOpen(true)
    setMessage('')
  }
  function resetForm() { setForm(blankProject); setRequirementsText(''); setEditingId(null); setFormOpen(false) }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      const levels = parseSkillLevels(requirementsText)
      const payload = { ...form, required_skill_levels: levels, required_skills: Object.keys(levels) }
      if (editingId) await industryService.updateProject(editingId, payload)
      else await industryService.createProject(payload)
      setMessage(editingId ? 'Project updated.' : 'Project published to the student marketplace.')
      resetForm()
      await refresh()
    } catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  async function toggleStatus(project: IndustryProject) {
    setBusy(true); setMessage('')
    try { await industryService.setProjectStatus(project.id, project.status === 'OPEN' ? 'CLOSED' : 'OPEN'); await refresh() }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  function field<K extends keyof IndustryProjectInput>(key: K, value: IndustryProjectInput[K]) { setForm((current) => ({ ...current, [key]: value })) }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="PROJECT MARKETPLACE" title="Projects that build real capability" description="Post challenges, review matched student applications and manage your own listings." action={<button className="button button-primary" onClick={() => { resetForm(); setFormOpen(true) }}><Plus size={16} /> Post a project</button>} />
    {message && <div className={message.includes('published') || message.includes('updated') ? 'success-note' : 'inline-error'}>{message}</div>}
    {formOpen && <form className="panel project-create-form" onSubmit={(event) => void save(event)}><div className="panel-heading"><div><h2>{editingId ? 'Edit industry project' : 'New industry project'}</h2><p>Set explicit skill levels and eligibility for explainable candidate matching.</p></div><button type="button" className="icon-button" aria-label="Close form" onClick={resetForm}><X size={18} /></button></div><div className="form-grid"><label>Project title<input required minLength={3} maxLength={180} value={form.title} onChange={(e) => field('title', e.target.value)} /></label><label>Category<input required value={form.domain} onChange={(e) => field('domain', e.target.value)} placeholder="Data Analytics" /></label><label>Difficulty<select value={form.difficulty} onChange={(e) => field('difficulty', e.target.value as IndustryProjectInput['difficulty'])}><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label><label>Required skills and minimum level<input required value={requirementsText} onChange={(e) => setRequirementsText(e.target.value)} placeholder="Python:3, SQL:4 (level 1–5)" /></label><label>Deadline<input type="date" value={form.deadline} onChange={(e) => field('deadline', e.target.value)} /></label><label>Duration (weeks)<input type="number" min={1} max={52} value={form.duration_weeks ?? ''} onChange={(e) => field('duration_weeks', e.target.value ? Number(e.target.value) : null)} /></label><label>Participation<select value={form.participation} onChange={(e) => field('participation', e.target.value as IndustryProjectInput['participation'])}><option>Individual</option><option>Team</option></select></label>{form.participation === 'Team' && <><label>Minimum team size<input type="number" min={2} max={20} value={form.team_size_min} onChange={(e) => field('team_size_min', Number(e.target.value))} /></label><label>Maximum team size<input type="number" min={2} max={20} value={form.team_size_max} onChange={(e) => field('team_size_max', Number(e.target.value))} /></label></>}<label>Publication status<select value={form.publication_status} onChange={(e) => field('publication_status', e.target.value as IndustryProjectInput['publication_status'])}><option value="DRAFT">Draft</option><option value="PUBLISHED">Publish</option><option value="CLOSED">Closed</option></select></label><label>Eligibility<input value={form.eligibility} onChange={(e) => field('eligibility', e.target.value)} placeholder="e.g. Open to undergraduate students" /></label><label>Expected outcome<input value={form.expected_outcome} onChange={(e) => field('expected_outcome', e.target.value)} /></label><label className="field-full">Description<textarea required minLength={10} rows={3} value={form.description} onChange={(e) => field('description', e.target.value)} /></label><label className="field-full">Instructions<textarea rows={3} value={form.instructions} onChange={(e) => field('instructions', e.target.value)} /></label><label>Deliverables (comma separated)<input value={(form.deliverables ?? []).join(', ')} onChange={(e) => field('deliverables', e.target.value.split(',').map((item) => item.trim()).filter(Boolean))} /></label><label>Reference links (comma separated)<input value={(form.references ?? []).join(', ')} onChange={(e) => field('references', e.target.value.split(',').map((item) => item.trim()).filter(Boolean))} /></label><label className="field-full">Acceptance criteria<textarea rows={2} value={form.evaluation_criteria} onChange={(e) => field('evaluation_criteria', e.target.value)} /></label></div><div className="form-bottom"><span>Only skills in the platform catalog can be selected.</span><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save project' : 'Save project'} <Send size={15} /></button></div></form>}
    <div className="industry-project-list large-list">{data?.map((project) => <article className="industry-project-row" key={project.id}><span className="list-icon list-blue"><BriefcaseBusiness size={16} /></span><div><strong>{project.title}</strong><span>{project.domain} · {project.difficulty} · {skillLevelsText(project.required_skill_levels)} · {project.applications} applications</span></div><Badge tone={project.status === 'OPEN' ? 'green' : 'blue'}>{project.status}</Badge><button className="button button-outline button-small" onClick={() => startEdit(project)}>Edit</button><button className="button button-outline button-small" disabled={busy} onClick={() => void toggleStatus(project)}>{project.status === 'OPEN' ? 'Close' : 'Reopen'}</button><Link className="button button-outline button-small" to="/industry/applications">Review candidates</Link></article>)}{data?.length === 0 && <div className="panel"><Empty title="No projects posted yet" body="Publish your first real-world challenge to start building a skill bridge." /></div>}</div>
  </LoadState>
}

const blankVacancy: JobVacancyInput = {
  title: '', description: '', location: 'Remote', employment_type: 'Full-time',
  eligibility: '', required_skill_levels: {}, preferred_skills: [], experience_level: 'Entry level',
  deadline: '', status: 'OPEN',
}
const blankJobRequirements: JobRequirementInput = {
  mandatory_education: '', mandatory_department: '', mandatory_certifications: [],
  experience_requirement: '', internship_duration: '', openings: 1, application_instructions: '',
}

function IndustryVacanciesPage() {
  const { data, loading, error, refresh } = useLoad<JobVacancy[]>(industryService.vacancies)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState<JobVacancyInput>(blankVacancy)
  const [requirementsText, setRequirementsText] = useState('')
  const [preferredSkillsText, setPreferredSkillsText] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All statuses')
  const [requirements, setRequirements] = useState<JobRequirementInput>(blankJobRequirements)
  async function startEdit(vacancy: JobVacancy) {
    setEditingId(vacancy.id)
    setForm({
      title: vacancy.title, description: vacancy.description, location: vacancy.location,
      employment_type: vacancy.employment_type, eligibility: vacancy.eligibility,
      required_skill_levels: vacancy.required_skill_levels, deadline: vacancy.deadline,
      preferred_skills: vacancy.preferred_skills, experience_level: vacancy.experience_level,
      status: vacancy.status as JobVacancyInput['status'],
    })
    setRequirementsText(skillLevelsText(vacancy.required_skill_levels))
    setPreferredSkillsText(vacancy.preferred_skills.join(', '))
    try { setRequirements(await industryService.jobRequirements(vacancy.id)) }
    catch (reason) { setMessage(messageFromError(reason)); return }
    setFormOpen(true); setMessage('')
  }
  function resetForm() { setForm(blankVacancy); setRequirementsText(''); setPreferredSkillsText(''); setRequirements(blankJobRequirements); setEditingId(null); setFormOpen(false) }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      const payload = {
        ...form,
        required_skill_levels: parseSkillLevels(requirementsText),
        preferred_skills: preferredSkillsText.split(',').map((item) => item.trim()).filter(Boolean),
      }
      const vacancy = editingId
        ? await industryService.updateVacancy(editingId, payload)
        : await industryService.createVacancy(payload)
      await industryService.setJobRequirements(vacancy.id, requirements)
      setMessage(editingId ? 'Vacancy updated.' : 'Job vacancy published.')
      resetForm(); await refresh()
    } catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  async function toggleStatus(vacancy: JobVacancy) {
    setBusy(true); setMessage('')
    try { await industryService.setVacancyStatus(vacancy.id, vacancy.status === 'OPEN' ? 'CLOSED' : 'OPEN'); await refresh() }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  const visibleVacancies = (data ?? []).filter((vacancy) =>
    (vacancy.title.toLowerCase().includes(search.toLowerCase()) || vacancy.company.toLowerCase().includes(search.toLowerCase())) &&
    (statusFilter === 'All statuses' || vacancy.status === statusFilter),
  )
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="JOB VACANCIES" title="Manage your job postings" description="Manage authenticated-company vacancies. Sample postings are clearly labeled and remain scoped to their demo account." action={<button className="button button-primary" onClick={() => { resetForm(); setFormOpen(true) }}><Plus size={16} /> Post a vacancy</button>} />
    {message && <div className={message.includes('published') || message.includes('updated') ? 'success-note' : 'inline-error'}>{message}</div>}
    {formOpen && <form className="panel project-create-form" onSubmit={(event) => void save(event)}><div className="panel-heading"><div><h2>{editingId ? 'Edit job vacancy' : 'New job vacancy'}</h2><p>Set job requirements and application details.</p></div><button type="button" className="icon-button" aria-label="Close form" onClick={resetForm}><X size={18} /></button></div><div className="form-grid"><label>Job title<input required minLength={3} maxLength={180} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label><label>Location<input value={form.location} maxLength={160} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label><label>Employment type<select value={form.employment_type} onChange={(e) => setForm({ ...form, employment_type: e.target.value as JobVacancyInput['employment_type'] })}><option>Full-time</option><option>Part-time</option><option>Internship</option><option>Contract</option></select></label><label>Status<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as JobVacancyInput['status'] })}><option value="DRAFT">Draft / unpublished</option><option value="OPEN">Published</option><option value="CLOSED">Closed</option></select></label><label>Required skills and minimum level<input value={requirementsText} onChange={(e) => setRequirementsText(e.target.value)} placeholder="Python:3, SQL:4 (level 1–5)" /></label><label>Preferred skills<input value={preferredSkillsText} onChange={(e) => setPreferredSkillsText(e.target.value)} placeholder="Git, cloud computing" /></label><label>Experience level<input maxLength={80} value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })} placeholder="Entry level · 0–1 years" /></label><label>Application deadline<input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} /></label><label>Eligibility<input value={form.eligibility} onChange={(e) => setForm({ ...form, eligibility: e.target.value })} placeholder="e.g. Open to undergraduate students" /></label><label>Required institution / education<input value={requirements.mandatory_education} onChange={(e) => setRequirements({ ...requirements, mandatory_education: e.target.value })} /></label><label>Required department<input value={requirements.mandatory_department} onChange={(e) => setRequirements({ ...requirements, mandatory_department: e.target.value })} /></label><label>Mandatory certifications<input value={requirements.mandatory_certifications.join(', ')} onChange={(e) => setRequirements({ ...requirements, mandatory_certifications: e.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} /></label><label>Experience requirement<input value={requirements.experience_requirement} onChange={(e) => setRequirements({ ...requirements, experience_requirement: e.target.value })} /></label><label>Internship duration<input value={requirements.internship_duration} onChange={(e) => setRequirements({ ...requirements, internship_duration: e.target.value })} /></label><label>Openings<input type="number" min={1} max={10000} value={requirements.openings} onChange={(e) => setRequirements({ ...requirements, openings: Number(e.target.value) })} /></label><label className="field-full">Application instructions<textarea rows={2} value={requirements.application_instructions} onChange={(e) => setRequirements({ ...requirements, application_instructions: e.target.value })} /></label><label className="field-full">Job description<textarea required minLength={10} maxLength={12000} rows={5} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label></div><div className="form-bottom"><span>Only skills in the platform catalog can be selected.</span><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save vacancy' : 'Save vacancy'} <Send size={15} /></button></div></form>}
    <div className="demo-directory-controls"><label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search your job title or company" aria-label="Search job vacancies" /></label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter vacancies by status"><option>All statuses</option><option value="OPEN">Open</option><option value="CLOSED">Closed</option><option value="DRAFT">Draft</option></select></div>
    {visibleVacancies.length ? <div className="job-vacancy-list">{visibleVacancies.map((vacancy) => <article className="job-vacancy-card" key={vacancy.id}><div className="job-vacancy-top"><div><Badge tone={vacancy.is_demo ? 'amber' : vacancy.status === 'OPEN' ? 'green' : 'blue'}>{vacancy.is_demo ? vacancy.demo_label || 'DEMO SAMPLE OPENING' : vacancy.status === 'OPEN' ? 'PUBLISHED' : vacancy.status}</Badge><h2>{vacancy.title}</h2><span>{vacancy.company} · {vacancy.employment_type} · {vacancy.location}</span></div><div className="project-row-stat"><strong>{vacancy.application_count}</strong><small>applications</small></div></div><p>{vacancy.description}</p><div className="project-skills">{Object.entries(vacancy.required_skill_levels).map(([name, level]) => <Badge key={name}>{name} · required {level}/5</Badge>)}{vacancy.preferred_skills.map((skill) => <Badge key={skill} tone="purple">Preferred: {skill}</Badge>)}</div><div className="job-vacancy-meta"><span>{vacancy.experience_level || 'Experience not specified'}</span><span>Posted {vacancy.posted_at ? new Date(vacancy.posted_at).toLocaleDateString() : 'date unavailable'}</span><span>Deadline {vacancy.deadline || 'not specified'}</span></div><div className="job-vacancy-actions"><button className="button button-outline button-small" onClick={() => void startEdit(vacancy)}>Edit</button><button className="button button-outline button-small" disabled={busy} onClick={() => void toggleStatus(vacancy)}>{vacancy.status === 'OPEN' ? 'Close vacancy' : 'Publish vacancy'}</button><Link className="button button-outline button-small" to="/industry/applications">Review applicants</Link></div></article>)}</div>
      : <div className="panel"><Empty title={data?.length ? 'No matching vacancies' : 'No vacancies posted yet'} body={data?.length ? 'Change your search or status filter.' : 'Create a job vacancy to reach students whose skills match your requirements.'} /></div>}
  </LoadState>
}

function ProjectApplicantCard({ application, onChanged }: { application: IndustryProjectApplication; onChanged: () => void }) {
  const [status, setStatus] = useState<ApplicationReviewInput['status']>(application.review_status === 'APPLIED' ? 'REVIEWING' : application.review_status as ApplicationReviewInput['status'])
  const [note, setNote] = useState(application.company_note)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function save() {
    setBusy(true); setMessage('')
    try { await industryService.reviewProjectApplication(application.application_id, { status, note }); setMessage('Candidate update saved.'); onChanged() }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  return <article className="candidate-review-card"><div className="candidate-review-header"><div><h3>{application.student_name}</h3><span>{application.career_goal} · {application.department || application.college || 'Student'}</span></div><Badge tone="blue">{application.review_status}</Badge></div><CandidateMatchSummary match={application.candidate_match} />{application.submission && <div className="candidate-submission"><strong>Project submission</strong><p>{application.submission.description}</p>{application.submission.github_url && <a href={application.submission.github_url} target="_blank" rel="noreferrer">{application.submission.github_url}</a>}{application.submission.evidence && <p>{application.submission.evidence}</p>}</div>}<div className="candidate-review-controls"><select value={status} onChange={(event) => setStatus(event.target.value as ApplicationReviewInput['status'])}><option value="REVIEWING">Reviewing</option><option value="SHORTLISTED">Shortlisted</option><option value="INTERVIEW">Interview</option><option value="SELECTED">Selected</option><option value="NOT_SELECTED">Not selected</option></select><input maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional message to the student" /><button className="button button-primary button-small" disabled={busy} onClick={() => void save()}>{busy ? 'Saving…' : 'Save company update'}</button></div>{message && <div className={message.includes('saved') ? 'success-note' : 'inline-error'}>{message}</div>}</article>
}

function JobApplicantCard({ application, onChanged }: { application: JobApplicationReview; onChanged: () => void }) {
  const [status, setStatus] = useState<ApplicationReviewInput['status']>(application.status === 'APPLIED' ? 'REVIEWING' : application.status as ApplicationReviewInput['status'])
  const [note, setNote] = useState(application.note)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [profileSelection, setProfileSelection] = useState<ProfileType[]>([])
  const [profiles, setProfiles] = useState<Partial<Record<ProfileType, string>> | null>(null)
  const [showCandidate, setShowCandidate] = useState(false)
  const profileNames: Record<ProfileType, string> = { linkedin: 'LinkedIn', github: 'GitHub', leetcode: 'LeetCode' }
  async function save() {
    setBusy(true); setMessage('')
    try { await industryService.updateJobApplication(application.application_id, { status, note }); setMessage('Candidate update saved.'); onChanged() }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  async function requestAccess() {
    if (!profileSelection.length) { setMessage('Select at least one profile type to request.'); return }
    setBusy(true); setMessage('')
    try {
      await industryService.requestApplicantProfiles(application.application_id, profileSelection)
      setMessage('Profile access request sent. Links remain hidden until the student responds.')
      onChanged()
    } catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  async function viewProfiles() {
    setBusy(true); setMessage('')
    try {
      const result = await industryService.applicantProfiles(application.application_id)
      setProfiles(result.profiles)
    } catch (reason) { setProfiles(null); setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  function toggleProfile(type: ProfileType) {
    setProfileSelection((selected) => selected.includes(type) ? selected.filter((item) => item !== type) : [...selected, type])
  }
  return <article className="candidate-review-card"><div className="candidate-review-header"><div><h3>{application.student_name}</h3><span>{application.career_goal} · {application.department || application.college || 'Student'} · Applied {application.applied_at ? new Date(application.applied_at).toLocaleDateString() : 'date unavailable'}</span></div><div className="candidate-review-actions"><Badge tone="blue">{application.status}</Badge><button className="button button-outline button-small" onClick={() => setShowCandidate(!showCandidate)}>{showCandidate ? 'Hide candidate details' : 'View Candidate'}</button></div></div>{showCandidate && <><CandidateMatchSummary match={application.candidate_match} /><div className="candidate-skill-details">{application.candidate_match.skill_details.map((skill) => <Badge key={skill.skill} tone={skill.matched ? 'green' : 'amber'}>{skill.skill}: {skill.current_level}/{skill.required_level}</Badge>)}</div></>}
    <section className="profile-consent-panel"><div className="candidate-review-header"><strong>Professional profile access</strong><Badge tone={application.profile_access_status === 'GRANTED' ? 'green' : application.profile_access_status === 'REQUESTED' ? 'amber' : 'blue'}>{(application.profile_access_status ?? 'NOT_GRANTED').replace(/_/g, ' ')}</Badge></div>
      {application.granted_profile_types?.length ? <><p>Student permission is granted for: {application.granted_profile_types.map((type) => profileNames[type]).join(', ')}.</p><button className="button button-outline button-small" disabled={busy} onClick={() => void viewProfiles()}>{busy ? 'Loading…' : 'View permitted profiles'}</button></> : <p>Student permission required. Profile links are not included in applicant data until the student grants access.</p>}
      {profiles && <div className="permitted-profile-links">{(['linkedin', 'github', 'leetcode'] as ProfileType[]).map((type) => profiles[type] && <a key={type} href={profiles[type]} target="_blank" rel="noopener noreferrer">{type === 'linkedin' ? <Linkedin size={15} /> : type === 'github' ? <Github size={15} /> : <Code2 size={15} />}{profileNames[type]} profile</a>)}</div>}
      {application.profile_access_status !== 'REQUESTED' && <><div className="profile-request-options">{(['linkedin', 'github', 'leetcode'] as ProfileType[]).map((type) => <label key={type}><input type="checkbox" checked={profileSelection.includes(type)} onChange={() => toggleProfile(type)} /> Request {profileNames[type]}</label>)}</div><button className="button button-outline button-small" disabled={busy || !profileSelection.length} onClick={() => void requestAccess()}>{busy ? 'Sending…' : 'Request Profile Access'}</button></>}
    </section>
    <div className="candidate-review-controls"><select value={status} onChange={(event) => setStatus(event.target.value as ApplicationReviewInput['status'])}><option value="REVIEWING">Reviewing</option><option value="SHORTLISTED">Shortlisted</option><option value="INTERVIEW">Interview</option><option value="SELECTED">Selected</option><option value="NOT_SELECTED">Not selected</option></select><input maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional message to the student" /><button className="button button-primary button-small" disabled={busy} onClick={() => void save()}>{busy ? 'Saving…' : 'Save company update'}</button></div>{message && <div className={message.includes('sent') || message.includes('saved') ? 'success-note' : 'inline-error'}>{message}</div>}</article>
}

function IndustryApplicationsPage() {
  const projectsLoad = useLoad<IndustryProject[]>(industryService.projects)
  const vacanciesLoad = useLoad<JobVacancy[]>(industryService.vacancies)
  const [kind, setKind] = useState<'project' | 'job'>('project')
  const [listingId, setListingId] = useState<number | null>(null)
  const [candidateSearch, setCandidateSearch] = useState('')
  const [candidateStatus, setCandidateStatus] = useState('All statuses')
  const [candidateSort, setCandidateSort] = useState('Newest first')
  const appLoader = useCallback(async () => {
    if (listingId == null) return []
    return kind === 'project' ? industryService.projectApplications(listingId) : industryService.vacancyApplications(listingId)
  }, [kind, listingId])
  const applications = useLoad<IndustryProjectApplication[] | JobApplicationReview[]>(appLoader)
  const listings = kind === 'project' ? projectsLoad.data ?? [] : vacanciesLoad.data ?? []
  const selectedTitle = listings.find((listing) => listing.id === listingId)?.title
  const visibleApplications = [...(applications.data ?? [])]
    .filter((item) => {
      const status = 'review_status' in item ? item.review_status : item.status
      return item.student_name.toLowerCase().includes(candidateSearch.toLowerCase()) &&
        (candidateStatus === 'All statuses' || status === candidateStatus)
    })
    .sort((left, right) => {
      const leftDate = left.applied_at ? new Date(left.applied_at).getTime() : 0
      const rightDate = right.applied_at ? new Date(right.applied_at).getTime() : 0
      return candidateSort === 'Newest first' ? rightDate - leftDate : leftDate - rightDate
    })
  async function refreshListings() { await Promise.all([projectsLoad.refresh(), vacanciesLoad.refresh()]) }
  return <LoadState loading={projectsLoad.loading || vacanciesLoad.loading} error={projectsLoad.error || vacanciesLoad.error} retry={refreshListings}><PageHeading eyebrow="COMPANY SHORTLISTING" title="Review student applications" description="Skill comparisons are advisory. Choose candidates for interviews or next steps based on your review." />
    <div className="application-review-layout"><section className="panel"><div className="panel-heading"><div><h2>Choose a listing</h2><p>Only your company's listings and applicants are shown.</p></div></div><div className="review-listing-tabs"><button className={kind === 'project' ? 'button button-primary button-small' : 'button button-outline button-small'} onClick={() => { setKind('project'); setListingId(null) }}>Projects</button><button className={kind === 'job' ? 'button button-primary button-small' : 'button button-outline button-small'} onClick={() => { setKind('job'); setListingId(null) }}>Job vacancies</button></div><div className="review-listings">{listings.map((listing) => <button key={listing.id} className={`review-listing ${listing.id === listingId ? 'review-listing-active' : ''}`} onClick={() => setListingId(listing.id)}><span>{listing.title}</span><Badge>{'applications' in listing ? listing.applications : listing.application_count} applicants</Badge></button>)}{listings.length === 0 && <Empty title={`No ${kind === 'project' ? 'projects' : 'vacancies'} yet`} body="Create a listing to start receiving student applications." />}</div></section><section className="application-review-results"><h2>{selectedTitle || 'Select a listing to see applicants'}</h2>{listingId != null && <LoadState loading={applications.loading} error={applications.error} retry={applications.refresh}>{applications.data?.length ? <><div className="demo-directory-controls applicant-filters"><label><Search size={15} /><input value={candidateSearch} onChange={(event) => setCandidateSearch(event.target.value)} placeholder="Search applicant name" aria-label="Search applicants" /></label><select value={candidateStatus} onChange={(event) => setCandidateStatus(event.target.value)} aria-label="Filter applications by status"><option>All statuses</option><option value="APPLIED">Applied</option><option value="REVIEWING">Under review</option><option value="SHORTLISTED">Shortlisted</option><option value="INTERVIEW">Interview</option><option value="SELECTED">Selected</option><option value="NOT_SELECTED">Rejected</option></select><select value={candidateSort} onChange={(event) => setCandidateSort(event.target.value)} aria-label="Sort applications"><option>Newest first</option><option>Oldest first</option></select></div>{visibleApplications.length ? <div className="candidate-review-list">{kind === 'project' ? visibleApplications.map((application) => <ProjectApplicantCard key={application.application_id} application={application as IndustryProjectApplication} onChanged={() => void applications.refresh()} />) : visibleApplications.map((application) => <JobApplicantCard key={application.application_id} application={application as JobApplicationReview} onChanged={() => void applications.refresh()} />)}</div> : <div className="panel"><Empty title="No matching applicants" body="Try a different name or status filter." /></div>}</> : <div className="panel"><Empty title="No applications received" body="Student applications will appear here for company review." /></div>}</LoadState>}</section></div>
  </LoadState>
}

function IndustrySubmissionCard({ submission, onChanged }: { submission: IndustrySubmission; onChanged: () => void }) {
  const [decision, setDecision] = useState<SubmissionReviewInput['decision']>('NEEDS_REVISION')
  const [feedback, setFeedback] = useState<SubmissionReviewInput>({
    decision: 'NEEDS_REVISION', overall_feedback: '', technical_feedback: '', code_quality_feedback: '',
    problem_solving_feedback: '', strengths: '', improvement_areas: '', recommended_skills: [],
    rating: null, revision_instructions: '',
  })
  const [skillsText, setSkillsText] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function review(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await industryService.reviewSubmission(submission.id, {
        ...feedback, decision, recommended_skills: skillsText.split(',').map((skill) => skill.trim()).filter(Boolean),
      })
      setMessage('Review saved and student notified.'); onChanged()
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  return <article className="candidate-review-card">
    <div className="candidate-review-header"><div><h3>{submission.project_title}</h3><span>{submission.student_name} · {submission.department || submission.college || 'Student'} · {submission.submitted_at ? new Date(submission.submitted_at).toLocaleDateString() : 'Submission date unavailable'}</span></div><Badge tone={submission.decision === 'ACCEPTED' ? 'green' : submission.decision ? 'amber' : 'blue'}>{submission.decision ?? submission.status}</Badge></div>
    <p><strong>{submission.summary}</strong></p><p>{submission.description}</p>
    <div className="project-skills">{submission.skills_used.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
    <div className="candidate-submission">{submission.github_url && <a href={submission.github_url} target="_blank" rel="noopener noreferrer">Project repository</a>}{submission.demo_url && <a href={submission.demo_url} target="_blank" rel="noopener noreferrer">Live demo</a>}{submission.report_url && <a href={submission.report_url} target="_blank" rel="noopener noreferrer">Project report</a>}{submission.evidence && <p>{submission.evidence}</p>}</div>
    <form className="submission-form" onSubmit={(event) => void review(event)}><label>Decision<select value={decision} onChange={(event) => setDecision(event.target.value as SubmissionReviewInput['decision'])}><option value="NEEDS_REVISION">Request revision</option><option value="ACCEPTED">Accept</option><option value="REJECTED">Reject</option></select></label><label>Overall feedback<textarea required rows={2} value={feedback.overall_feedback} onChange={(event) => setFeedback({ ...feedback, overall_feedback: event.target.value })} /></label><label>Technical feedback<textarea rows={2} value={feedback.technical_feedback} onChange={(event) => setFeedback({ ...feedback, technical_feedback: event.target.value })} /></label><label>Code quality feedback<textarea rows={2} value={feedback.code_quality_feedback} onChange={(event) => setFeedback({ ...feedback, code_quality_feedback: event.target.value })} /></label><label>Problem-solving feedback<textarea rows={2} value={feedback.problem_solving_feedback} onChange={(event) => setFeedback({ ...feedback, problem_solving_feedback: event.target.value })} /></label><label>Strengths<textarea rows={2} value={feedback.strengths} onChange={(event) => setFeedback({ ...feedback, strengths: event.target.value })} /></label><label>Areas to improve<textarea rows={2} value={feedback.improvement_areas} onChange={(event) => setFeedback({ ...feedback, improvement_areas: event.target.value })} /></label><label>Recommended skills<input value={skillsText} onChange={(event) => setSkillsText(event.target.value)} placeholder="Python, testing" /></label><label>Rating (1–5)<input type="number" min={1} max={5} value={feedback.rating ?? ''} onChange={(event) => setFeedback({ ...feedback, rating: event.target.value ? Number(event.target.value) : null })} /></label>{decision === 'NEEDS_REVISION' && <label>Revision instructions<textarea required rows={2} value={feedback.revision_instructions} onChange={(event) => setFeedback({ ...feedback, revision_instructions: event.target.value })} /></label>}<button className="button button-primary button-small" disabled={busy}>{busy ? 'Saving…' : 'Submit review'}</button></form>
    {submission.reviews?.map((review, index) => <details key={`${review.reviewed_at}-${index}`}><summary>Earlier review: {review.decision}</summary><p>{review.overall_feedback}</p>{review.revision_instructions && <p>Revision instructions: {review.revision_instructions}</p>}</details>)}
    {message && <div className={message.includes('saved') ? 'success-note' : 'inline-error'}>{message}</div>}
  </article>
}

function IndustrySubmissionsPage() {
  const { data, loading, error, refresh } = useLoad<IndustrySubmission[]>(() => industryService.submissions())
  const [filter, setFilter] = useState('')
  const visible = data?.filter((item) => !filter || (item.decision ?? item.status) === filter) ?? []
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="PROJECT REVIEW" title="Student submissions" description="Review project evidence, give structured feedback, request revisions, and record final decisions." />
    <div className="review-listing-tabs"><label>Filter status<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="">All submissions</option><option value="SUBMITTED">Awaiting review</option><option value="NEEDS_REVISION">Needs revision</option><option value="ACCEPTED">Accepted</option><option value="REJECTED">Rejected</option></select></label></div>
    {visible.length ? <div className="candidate-review-list">{visible.map((submission) => <IndustrySubmissionCard key={submission.id} submission={submission} onChanged={() => void refresh()} />)}</div> : <div className="panel"><Empty title="No submissions in this view" body="Student submissions for your projects will appear here." /></div>}
  </LoadState>
}

function StudentProfileSharingPage() {
  const { data, loading, error, refresh, setData } = useLoad(studentPortalService.profileAccess)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [selections, setSelections] = useState<Record<number, ProfileType[]>>({})
  const profileNames: Record<ProfileType, string> = { linkedin: 'LinkedIn', github: 'GitHub', leetcode: 'LeetCode' }
  async function respond(record: ProfileAccessRecord, decision: 'GRANTED' | 'DECLINED') {
    const selected = selections[record.job_application_id] ?? []
    if (decision === 'GRANTED' && (!selected.length || !window.confirm(`Grant ${record.company} access to the selected profile links for ${record.job_title}?`))) return
    if (decision === 'DECLINED' && !window.confirm(`Decline ${record.company}'s profile access request for ${record.job_title}?`)) return
    setBusy(true); setMessage('')
    try {
      const updated = await studentPortalService.respondProfileAccess(record.job_application_id, decision, decision === 'GRANTED' ? selected : [])
      setData((data ?? []).map((item) => item.job_application_id === updated.job_application_id ? { ...item, ...updated } : item))
      setMessage(decision === 'GRANTED' ? 'Selected access granted to this company for this application.' : 'Profile access request declined.')
    }
    catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  async function revoke(record: ProfileAccessRecord, type?: ProfileType) {
    const label = type ? profileNames[type] : 'all professional profile links'
    if (!window.confirm(`Revoke ${record.company}'s access to ${label} for ${record.job_title}?`)) return
    setBusy(true); setMessage('')
    try {
      const updated = await studentPortalService.revokeProfileAccess(record.job_application_id, type ? [type] : undefined)
      setData((data ?? []).map((item) => item.job_application_id === updated.job_application_id ? { ...item, ...updated } : item))
      setMessage(`${label} access revoked for ${record.company}.`)
    } catch (reason) { setMessage(messageFromError(reason)) }
    finally { setBusy(false) }
  }
  function toggleSelection(applicationId: number, type: ProfileType) {
    const selected = selections[applicationId] ?? []
    setSelections({ ...selections, [applicationId]: selected.includes(type) ? selected.filter((item) => item !== type) : [...selected, type] })
  }
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="STUDENT PRIVACY" title="Professional Profiles & Access" description="Manage profile links and decide, application by application, which companies can see them." action={<Link className="button button-outline button-small" to="/student/learning-profile">Edit profile links <ArrowRight size={14} /></Link>} />
    {message && <div className={message.includes('revoked') || message.includes('granted') || message.includes('declined') ? 'success-note' : 'inline-error'}>{message}</div>}
    {data.length ? <div className="candidate-review-list">{data.map((record) => <article className="candidate-review-card" key={record.job_application_id}>
      <div className="candidate-review-header"><div><h3>{record.company}</h3><span>{record.job_title} · Application #{record.job_application_id}</span></div><Badge tone={record.profile_access_status === 'GRANTED' ? 'green' : record.profile_access_status === 'REQUESTED' ? 'amber' : 'blue'}>{record.profile_access_status.replace(/_/g, ' ')}</Badge></div>
      {record.granted_profile_types.length > 0 && <div className="profile-access-list"><strong>Currently shared with this company</strong>{record.granted_profile_types.map((type) => <div key={type}><span>{profileNames[type]}</span><button className="button button-outline button-small" disabled={busy} onClick={() => void revoke(record, type)}>Revoke access</button></div>)}<button className="button button-outline button-small" disabled={busy} onClick={() => void revoke(record)}>Revoke all for this application</button></div>}
      {record.profile_access_status === 'REQUESTED' && <section className="profile-consent-panel"><strong>Access request from {record.company}</strong><p>{record.company} wants to review these links for your {record.job_title} application. Select which requested profiles to grant. Leaving all unselected does not grant access.</p>
        {record.requested_profile_types.map((type) => <label key={type}><input type="checkbox" checked={(selections[record.job_application_id] ?? []).includes(type)} onChange={() => toggleSelection(record.job_application_id, type)} /> Grant {profileNames[type]} access</label>)}
        <div className="candidate-review-controls"><button className="button button-primary button-small" disabled={busy || !(selections[record.job_application_id] ?? []).length} onClick={() => void respond(record, 'GRANTED')}>Grant selected access</button><button className="button button-outline button-small" disabled={busy} onClick={() => void respond(record, 'DECLINED')}>Decline request</button></div>
      </section>}
      {record.profile_access_status === 'NOT_GRANTED' && <p>Profile links are private for this application. The company must request access, and you must decide before any links are shared.</p>}
    </article>)}</div> : <div className="panel"><Empty title="No job-specific profile access yet" body="When you apply for a job, you can choose which profile links to share. Any later company requests will appear here." /></div>}
  </>}</LoadState>
}

function StudentFeedbackPage() {
  const { data, loading, error, refresh } = useLoad<IndustrySubmission[]>(studentPortalService.submissions)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="PROJECT FEEDBACK" title="Submission history and feedback" description="Review the feedback, revision instructions, and decisions shared by industry partners." />
    {data?.length ? <div className="candidate-review-list">{data.map((submission) => <article className="candidate-review-card" key={submission.id}><div className="candidate-review-header"><div><h3>{submission.project_title}</h3><span>Submitted {submission.submitted_at ? new Date(submission.submitted_at).toLocaleDateString() : 'date unavailable'} · {submission.revision_count} revision(s)</span></div><Badge tone={submission.decision === 'ACCEPTED' ? 'green' : submission.decision ? 'amber' : 'blue'}>{submission.decision ?? submission.status}</Badge></div><p>{submission.summary}</p>{submission.reviews?.map((review, index) => <section className="panel" key={`${review.reviewed_at}-${index}`}><h4>{review.decision.replace(/_/g, ' ')} · {new Date(review.reviewed_at).toLocaleDateString()}</h4><p>{review.overall_feedback}</p>{review.technical_feedback && <p><strong>Technical:</strong> {review.technical_feedback}</p>}{review.code_quality_feedback && <p><strong>Code quality:</strong> {review.code_quality_feedback}</p>}{review.problem_solving_feedback && <p><strong>Problem solving:</strong> {review.problem_solving_feedback}</p>}{review.strengths && <p><strong>Strengths:</strong> {review.strengths}</p>}{review.improvement_areas && <p><strong>Improve:</strong> {review.improvement_areas}</p>}{review.revision_instructions && <p><strong>Revision instructions:</strong> {review.revision_instructions}</p>}{review.recommended_skills.length > 0 && <p><strong>Recommended skills:</strong> {review.recommended_skills.join(', ')}</p>}</section>)}</article>)}</div> : <div className="panel"><Empty title="No project feedback yet" body="Submit work to an industry project to see partner feedback here." /></div>}
  </LoadState>
}

function PortalNotificationsPage({ role }: { role: 'student' | 'industry' }) {
  const loader = useCallback(() => role === 'student' ? studentPortalService.notifications() : industryService.portalNotifications(), [role])
  const { data, loading, error, refresh, setData } = useLoad<PortalNotification[]>(loader)
  const [message, setMessage] = useState('')
  async function markRead(id: number) {
    setMessage('')
    try {
      if (role === 'student') await studentPortalService.markNotificationRead(id)
      else await industryService.portalNotificationsRead(id)
      setData((data ?? []).map((item) => item.id === id ? { ...item, read: true } : item))
    } catch (reason) { setMessage(messageFromError(reason)) }
  }
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="ACTIVITY" title="Notifications" description="Updates about submissions, reviews, and application status changes." />
    {message && <div className="inline-error">{message}</div>}
    {data?.length ? <div className="candidate-review-list">{data.map((item) => <article className="candidate-review-card" key={item.id}><div className="candidate-review-header"><div><h3>{item.title}</h3><span>{new Date(item.created_at).toLocaleString()} · {item.kind}</span></div>{!item.read && <Badge tone="teal">NEW</Badge>}</div><p>{item.message}</p>{!item.read && <button className="button button-outline button-small" onClick={() => void markRead(item.id)}>Mark as read</button>}</article>)}</div> : <div className="panel"><Empty title="You're all caught up" body="New platform updates will appear here." /></div>}
  </LoadState>
}

function IndustryCandidateAnalysisPage() {
  const { data, loading, error, refresh } = useLoad<JobApplicationAnalysis[]>(industryService.jobApplicationAnalysis)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="CANDIDATE REVIEW" title="Role-based eligibility analysis" description="Assess applications against recorded skills and explicit vacancy requirements. Course completion is not asserted because the platform has no course progress data." />
    {data?.length ? <div className="candidate-review-list">{data.map((candidate) => <article className="candidate-review-card" key={candidate.application_id}><div className="candidate-review-header"><div><h3>{candidate.student_name}</h3><span>{candidate.opportunity_title} · {candidate.department || candidate.college} · Year {candidate.year}</span></div><Badge tone={candidate.eligibility === 'ELIGIBLE' ? 'green' : candidate.eligibility === 'ASSESSMENT PENDING' ? 'amber' : 'blue'}>{candidate.eligibility}</Badge></div><CandidateMatchSummary match={candidate.candidate_match} /><p>{Array.isArray(candidate.eligibility_reasons) ? candidate.eligibility_reasons.join(' ') : candidate.eligibility_reasons}</p><div className="notice-banner"><BookOpen size={16} /><div><strong>Course completion: Course Data Unavailable</strong><span>No enrollment or course-completion records are available, so completion is not inferred.</span></div></div>{candidate.internal_note && <p><strong>Recruiter note:</strong> {candidate.internal_note}</p>}</article>)}</div> : <div className="panel"><Empty title="No job applications yet" body="Candidate analyses will appear after students apply to your vacancies." /></div>}
  </LoadState>
}

function IndustryTalentPage() {
  const { data, loading, error, refresh } = useLoad<Awaited<ReturnType<typeof industryService.talent>>>(industryService.talent)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="TALENT DISCOVERY" title="Meet emerging talent" description="Explore students' career direction, readiness and self-reported skill profiles." />{data?.length ? <div className="talent-grid">{data.map((person) => <article className="talent-card" key={person.name}><div className="talent-top"><div className="avatar">{person.name.slice(0,1)}</div><Badge tone="teal">{person.readiness}% ready</Badge></div><h3>{person.name}</h3><p>{person.career_goal} <span>·</span> {person.college}</p><ProgressBar value={person.readiness} color="teal" /><div className="talent-skills">{person.skills.slice(0,5).map((skill) => <Badge key={skill}>{skill}</Badge>)}</div></article>)}</div> : <div className="panel"><Empty title="No student profiles available" body="Student profiles will appear when they join the platform." /></div>}</LoadState>
}

function IndustryAnalyticsPage() {
  const { data, loading, error, refresh } = useLoad<IndustryDashboard>(industryService.dashboard)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="INDUSTRY SIGNALS" title="A clearer view of demand" description="See how project requirements translate into skill demand from your organization." /><div className="metric-grid"><Metric label="Total demand signals" value={data.top_skills.reduce((sum,item)=>sum+item.demand,0)} note="Across active project requirements" icon={Activity} /><Metric label="Applications received" value={data.application_count} note="Interest across your project list" icon={Users} tone="teal" /><Metric label="Active challenges" value={data.open_projects} note="Currently open to applicants" icon={BriefcaseBusiness} tone="purple" /><Metric label="Distinct skills" value={data.top_skills.length} note="Skills in your project portfolio" icon={Target} tone="amber" /></div><Panel title="Skill demand by project" subtitle="Demand is counted from published project requirements"><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.top_skills} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf0f6" /><XAxis dataKey="skill" tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} /><Tooltip /><Bar dataKey="demand" fill="#13a98a" radius={[5,5,0,0]} barSize={36} /></BarChart></ResponsiveContainer></div></Panel></>}</LoadState>
}

function MentorDashboard() {
  const { data, loading, error, refresh } = useLoad(mentorService.dashboard)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="MENTOR WORKSPACE" title="Guide skills with evidence" description="Review real submissions, give meaningful feedback and verify demonstrated capabilities." action={<Link className="button button-primary" to="/mentor/evaluations">Review submissions <ArrowRight size={15} /></Link>} /><div className="metric-grid"><Metric label="Waiting for review" value={data.pending_evaluations} note="Student submissions ready to evaluate" icon={ClipboardCheck} tone="amber" /><Metric label="Evaluations completed" value={data.evaluated} note="Mentor feedback shared" icon={CheckCircle2} tone="green" /><Metric label="Submissions received" value={data.submissions.length} note="Across the industry marketplace" icon={BriefcaseBusiness} /><Metric label="Skills verified" value={data.submissions.filter((item) => item.evaluated).length} note="Students with mentor evidence" icon={ShieldCheck} tone="purple" /></div><Panel title="Latest submissions" subtitle="Review learner work and help make their skills visible"><SubmissionList submissions={data.submissions.slice(0,4)} onEvaluated={refresh} /></Panel></>}</LoadState>
}

function SubmissionList({ submissions, onEvaluated }: { submissions: Submission[]; onEvaluated: () => void }) {
  const [selected, setSelected] = useState<number | null>(null)
  const [scores, setScores] = useState<EvaluationInput>({ technical_quality: 4, problem_solving: 4, code_quality: 4, communication: 4, innovation: 4, feedback: '' })
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function evaluate(event: FormEvent) { event.preventDefault(); if (selected == null) return; setBusy(true); setMessage(''); try { const result = await projectService.evaluate(selected, scores); setMessage(`Evaluation saved · ${Math.round(result.overall_score)}/100 · verified: ${result.verified_skills.join(', ') || 'none'}`); setSelected(null); await onEvaluated() } catch (e) { setMessage(messageFromError(e)) } finally { setBusy(false) } }
  return <div className="submission-list">{message && <div className={message.startsWith('Evaluation') ? 'success-note' : 'inline-error'}>{message}</div>}{submissions.map((item) => <article className="submission-card" key={item.id}><div className="submission-card-head"><div className="submission-icon"><FileText size={17} /></div><div><h3>{item.project}</h3><p>{item.student} <span>·</span> Submitted {new Date(item.submitted_at).toLocaleDateString()}</p></div><Badge tone={item.evaluated ? 'green' : 'amber'}>{item.evaluated ? 'EVALUATED' : 'NEEDS REVIEW'}</Badge></div><p className="submission-description">{item.description}</p>{item.github_url && <a className="text-link" href={item.github_url} target="_blank" rel="noreferrer">Open project evidence <ArrowRight size={13} /></a>}{item.feedback && <div className="mentor-feedback"><strong>Mentor feedback</strong><span>{item.feedback}</span></div>}{!item.evaluated && <button className="button button-outline button-small" onClick={() => setSelected(selected === item.id ? null : item.id)}>{selected === item.id ? 'Close evaluation' : 'Evaluate submission'} <ClipboardCheck size={14} /></button>}{selected === item.id && <form className="evaluation-form" onSubmit={evaluate}><div className="evaluation-score-grid">{(['technical_quality','problem_solving','code_quality','communication','innovation'] as const).map((key) => <label key={key}>{key.replace(/_/g,' ')}<select value={scores[key]} onChange={(e) => setScores({ ...scores, [key]: Number(e.target.value) })}>{[1,2,3,4,5].map((score) => <option value={score} key={score}>{score} / 5</option>)}</select></label>)}</div><label className="field-full">Feedback<textarea required minLength={3} rows={3} value={scores.feedback} onChange={(e) => setScores({ ...scores, feedback: e.target.value })} placeholder="Share specific, constructive feedback…" /></label><button className="button button-primary button-small" disabled={busy}>{busy ? 'Saving…' : 'Save evaluation & verify skills'} <ShieldCheck size={14} /></button></form>}</article>)}{!submissions.length && <Empty title="No project submissions yet" body="Student work submitted for evaluation will appear here." />}</div>
}

function MentorSubmissionsPage() {
  const { data, loading, error, refresh } = useLoad<Submission[]>(mentorService.submissions)
  return <LoadState loading={loading} error={error} retry={refresh}><PageHeading eyebrow="MENTOR REVIEW" title="Submissions & evaluations" description="Assess applied skills against the project work and share feedback students can act on." /><Panel title="Student project submissions" subtitle="Evaluation updates the student's verified Skill Passport"><SubmissionList submissions={data ?? []} onEvaluated={refresh} /></Panel></LoadState>
}

function InstitutionAnalyticsDashboard() {
  const { data, loading, error, refresh } = useLoad<InstitutionAnalytics>(institutionService.analytics)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="INSTITUTIONAL SKILL INTELLIGENCE" title="Understand readiness at a glance" description="Connect student assessment, industry demand and applied project participation." /><div className="metric-grid"><Metric label="Students in view" value={data.total_students} note="Across demo institution cohorts" icon={GraduationCap} /><Metric label="Average readiness" value={`${data.average_readiness}%`} note="Industry role-aligned proficiency" icon={TrendingUp} tone="teal" /><Metric label="Assessment completion" value={`${data.assessment_completion}%`} note="Students with a completed diagnostic" icon={ClipboardCheck} tone="purple" /><Metric label="Verified skills" value={data.verified_skills} note="Confirmed through reviewed project work" icon={ShieldCheck} tone="amber" /></div><div className="institution-chart-grid"><Panel title="Student readiness" subtitle="Current readiness calculated from profile data"><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.readiness_distribution} margin={{ top: 10, right: 12, left: -10, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf0f6" /><XAxis dataKey="student" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} /><YAxis domain={[0,100]} tickLine={false} axisLine={false} /><Tooltip /><Bar dataKey="readiness" fill="#536cf2" radius={[5,5,0,0]} barSize={30} /></BarChart></ResponsiveContainer></div></Panel><Panel title="Industry demand" subtitle="Demand-weighted career skill requirements"><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.industry_demand.slice(0,6)} layout="vertical" margin={{ left: 10, right: 10 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#edf0f6" /><XAxis type="number" tickLine={false} axisLine={false} /><YAxis type="category" dataKey="skill" width={118} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="demand" fill="#13a98a" radius={[0,5,5,0]} barSize={13}>{data.industry_demand.slice(0,6).map((_,index)=><Cell key={index} fill={['#13a98a','#536cf2','#f4a43c','#a28af4','#55b99e','#6c9cf1'][index%6]} />)}</Bar></BarChart></ResponsiveContainer></div></Panel></div><div className="institution-lower"><Panel title="Most common skill gaps" subtitle="Students with a gap against their selected career goal"><div className="demand-bars">{data.top_skill_gaps.map((item) => <div key={item.skill}><span>{item.skill}</span><ProgressBar value={item.students/(data.total_students||1)*100} color="coral" /><strong>{item.students}</strong></div>)}</div></Panel><Panel title="Project participation" subtitle="Real project applications across student profiles"><div className="participation-number"><BriefcaseBusiness size={20} /><strong>{data.project_participation}</strong><span>applications across the platform</span></div></Panel></div></>}</LoadState>
}

function IndustryAnalyticsForInstitution() {
  return <InstitutionAnalyticsDashboard />
}

function InstitutionMentorManagementPage() {
  const load = useCallback(() => institutionService.mentors(), [])
  const { data, loading, error, refresh } = useLoad<InstitutionMentorDirectory>(load)
  const [query, setQuery] = useState('')
  const [availability, setAvailability] = useState('All availability')
  const [associationEmail, setAssociationEmail] = useState('')
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [expertise, setExpertise] = useState('')
  const [experience, setExperience] = useState(0)
  const [password, setPassword] = useState('')
  const [createAvailability, setCreateAvailability] = useState<InstitutionMentor['availability']>('AVAILABLE')
  const [selectedEdit, setSelectedEdit] = useState<number | null>(null)
  const [expandedMentorId, setExpandedMentorId] = useState<number | null>(null)
  const [editExpertise, setEditExpertise] = useState('')
  const [editExperience, setEditExperience] = useState(0)
  const [editAvailability, setEditAvailability] = useState<InstitutionMentor['availability']>('AVAILABLE')
  const [studentAssignments, setStudentAssignments] = useState<Record<number, number | null>>({})
  const [studentStatuses, setStudentStatuses] = useState<Record<number, 'ASSIGNED' | 'IN_PROGRESS'>>({})
  const [studentReasons, setStudentReasons] = useState<Record<number, string>>({})
  const [studentNotes, setStudentNotes] = useState<Record<number, string>>({})
  const [studentFollowUps, setStudentFollowUps] = useState<Record<number, string>>({})
  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} retry={() => void refresh()} />
  if (!data) return <Empty title="Mentor directory unavailable" body="No mentor directory data was returned." />
  const directory = data
  const mentors = data.mentors.filter((mentor) =>
    `${mentor.name} ${mentor.expertise} ${mentor.skills.join(' ')}`.toLowerCase().includes(query.toLowerCase()) &&
    (availability === 'All availability' || mentor.availability === availability),
  )
  async function createMentor(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await institutionService.createMentor({ name, email, expertise, experience, password, availability: createAvailability })
      setName(''); setEmail(''); setExpertise(''); setExperience(0); setPassword(''); setCreateAvailability('AVAILABLE'); setShowCreate(false)
      setMessage('Mentor account created and associated with this institution.'); await refresh()
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  async function associateMentor(event: FormEvent) {
    event.preventDefault(); setAdding(true); setMessage('')
    try { await institutionService.associateMentor(associationEmail); setAssociationEmail(''); setMessage('Existing mentor associated with this institution.'); await refresh() }
    catch (reason) { setMessage(messageFromError(reason)) } finally { setAdding(false) }
  }
  function beginEdit(mentor: InstitutionMentor) {
    setSelectedEdit(mentor.mentor_id); setEditExpertise(mentor.expertise); setEditExperience(mentor.experience); setEditAvailability(mentor.availability)
  }
  async function saveEdit(mentor: InstitutionMentor, active = mentor.active) {
    setBusy(true); setMessage('')
    const payload: InstitutionMentorUpdateInput = { expertise: editExpertise, experience: editExperience, availability: editAvailability, active }
    try { await institutionService.updateMentor(mentor.mentor_id, payload); setSelectedEdit(null); setStudentAssignments({}); setMessage(active ? 'Mentor details updated.' : 'Mentor deactivated; active student assignments were unassigned.'); await refresh() }
    catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  async function setMentorActive(mentor: InstitutionMentor, active: boolean) {
    setBusy(true); setMessage('')
    try {
      await institutionService.updateMentor(mentor.mentor_id, {
        expertise: mentor.expertise, experience: mentor.experience,
        availability: mentor.availability, active,
      })
      setStudentAssignments({})
      setMessage(active ? 'Mentor reactivated.' : 'Mentor deactivated; active student assignments were unassigned.')
      await refresh()
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  async function assignStudent(studentId: number) {
    const currentMentorId = directory.students.find((student) => student.id === studentId)?.assigned_mentor_id ?? null
    const mentorId = Object.prototype.hasOwnProperty.call(studentAssignments, studentId) ? studentAssignments[studentId] : currentMentorId
    const status = mentorId == null ? 'NOT_ASSIGNED' : studentStatuses[studentId] ?? 'ASSIGNED'
    const student = directory.students.find((item) => item.id === studentId)
    setBusy(true); setMessage('')
    try {
      await institutionService.updateMentorship(studentId, {
        mentor_id: mentorId, status,
        reason: Object.prototype.hasOwnProperty.call(studentReasons, studentId) ? studentReasons[studentId] : student?.mentorship_reason ?? '',
        notes: Object.prototype.hasOwnProperty.call(studentNotes, studentId) ? studentNotes[studentId] : student?.mentorship_notes ?? '',
        follow_up_date: Object.prototype.hasOwnProperty.call(studentFollowUps, studentId) ? studentFollowUps[studentId] || null : student?.follow_up_date ?? null,
      })
      setStudentAssignments((current) => { const next = { ...current }; delete next[studentId]; return next })
      setMessage(mentorId == null ? 'Mentor assignment removed.' : 'Student assigned to mentor.'); await refresh()
    } catch (reason) { setMessage(messageFromError(reason)) } finally { setBusy(false) }
  }
  return <><PageHeading eyebrow="INSTITUTION WORKSPACE" title="Mentor Management" description="Manage institution-associated mentors and assign students using your saved student records." action={<button className="button button-primary button-small" onClick={() => setShowCreate((value) => !value)}><Plus size={15} /> Add Mentor</button>} />
    <div className="metric-grid">
      <Metric label="Total mentors" value={data.summary.total_mentors} note="Associated with this institution" icon={Users} tone="blue" />
      <Metric label="Active mentors" value={data.summary.active_mentors} note="Eligible for new assignments" icon={CheckCircle2} tone="green" />
      <Metric label="Assigned students" value={data.summary.assigned_students} note="Current active mentorships" icon={GraduationCap} tone="purple" />
      <Metric label="Students without a mentor" value={data.summary.students_without_mentor} note="Institution-affiliated students" icon={UserRound} tone="amber" />
    </div>
    {message && <div className="notice-banner" role="status"><span>{message}</span></div>}
    {showCreate &&     <Panel title="Create mentor account" subtitle="The institution sets the initial password and shares it securely with the mentor. It is hashed and never displayed after submission; email invitations are not supported.">
      <form className="institution-filters" onSubmit={(event) => void createMentor(event)}>
        <label>Name<input required minLength={2} maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Expertise / skills<input required maxLength={255} value={expertise} onChange={(event) => setExpertise(event.target.value)} placeholder="Data analytics, SQL" /></label>
        <label>Years of experience<input required type="number" min={0} max={60} value={experience} onChange={(event) => setExperience(Number(event.target.value))} /></label>
        <label>Availability<select value={createAvailability} onChange={(event) => setCreateAvailability(event.target.value as InstitutionMentor['availability'])}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></select></label>
        <label>Initial password<input required type="password" minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></label>
        <button className="button button-primary button-small" disabled={busy}>{busy ? 'Creating…' : 'Create mentor account'}</button>
      </form>
    </Panel>}
    <Panel title="Associate an existing mentor" subtitle="Only an existing mentor account can be associated; duplicate accounts are not created.">
      <form className="institution-filters" onSubmit={(event) => void associateMentor(event)}>
        <label>Mentor account email<input required type="email" value={associationEmail} onChange={(event) => setAssociationEmail(event.target.value)} placeholder="mentor@example.com" /></label>
        <button className="button button-outline button-small" disabled={adding}>{adding ? 'Associating…' : 'Associate mentor'}</button>
      </form>
    </Panel>
    <Panel title="Mentor directory" subtitle="Only mentors associated with your institution are listed.">
      <div className="institution-filters">
        <label><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, expertise, or skills" aria-label="Search mentors" /></label>
        <select value={availability} onChange={(event) => setAvailability(event.target.value)}><option>All availability</option><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></select>
      </div>
      {mentors.length ? <div className="institution-student-list">{mentors.map((mentor) => <article className="institution-student-card" key={mentor.id}>
        <div className="institution-student-main"><div className="institution-avatar">{mentor.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</div><div className="institution-student-identity">
          <div className="institution-student-title"><strong>{mentor.name}</strong><Badge tone={mentor.active ? 'green' : 'amber'}>{mentor.active ? 'Active' : 'Inactive'}</Badge></div>
          <span>{mentor.email} · {mentor.experience} years experience</span><span>{mentor.expertise || 'Expertise not specified'}</span>
          <div className="institution-student-facts"><span>{mentor.availability.replace('_', ' ').toLowerCase()} availability</span><span>{mentor.assigned_student_count} assigned students</span></div>
          {expandedMentorId === mentor.mentor_id && <div className="institution-skill-chips"><span>{mentor.company ? `Organization: ${mentor.company}` : 'Organization not provided'}</span>{mentor.assigned_students.length ? mentor.assigned_students.map((student) => <Badge key={student.id}>{student.name} · {student.department || 'Department not provided'} · {student.status.replace(/_/g, ' ')}</Badge>) : <span>No current student assignments</span>}</div>}
          {selectedEdit === mentor.mentor_id && <div className="institution-filters"><label>Expertise<input value={editExpertise} onChange={(event) => setEditExpertise(event.target.value)} /></label><label>Experience<input type="number" min={0} max={60} value={editExperience} onChange={(event) => setEditExperience(Number(event.target.value))} /></label><label>Availability<select value={editAvailability} onChange={(event) => setEditAvailability(event.target.value as InstitutionMentor['availability'])}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></select></label><button className="button button-primary button-small" disabled={busy} onClick={() => void saveEdit(mentor)}>Save</button><button className="button button-outline button-small" onClick={() => setSelectedEdit(null)}>Cancel</button></div>}
          {selectedEdit !== mentor.mentor_id && <div className="institution-card-actions"><button className="button button-outline button-small" aria-expanded={expandedMentorId === mentor.mentor_id} onClick={() => setExpandedMentorId(expandedMentorId === mentor.mentor_id ? null : mentor.mentor_id)}>{expandedMentorId === mentor.mentor_id ? 'Hide details' : 'View details'}</button><button className="button button-outline button-small" onClick={() => beginEdit(mentor)}>Edit</button>{mentor.active ? <button className="button button-outline button-small" disabled={busy} onClick={() => void saveEdit(mentor, false)}>Deactivate</button> : <button className="button button-outline button-small" disabled={busy} onClick={() => void setMentorActive(mentor, true)}>Reactivate</button>}</div>}
        </div></div></article>)}</div> : <Empty title="No associated mentors" body={query ? 'No mentors match your search.' : 'Associate an existing mentor account or create a managed account to start.'} />}
    </Panel>
    <Panel title="Assign students to mentors" subtitle="Students and skill gaps below come from this institution's authorized records.">
      {data.students.length ? <div className="institution-student-list">{data.students.map((student) => {
        const current = Object.prototype.hasOwnProperty.call(studentAssignments, student.id) ? studentAssignments[student.id] : student.assigned_mentor_id
        const terms = [...student.skill_gaps, ...student.career_goal.split(/\s+/)].map((term) => term.trim().toLowerCase()).filter((term) => term.length > 2)
        const activeMentors = data.mentors.filter((mentor) => mentor.active).map((mentor) => ({
          mentor,
          score: terms.filter((term) => mentor.expertise.toLowerCase().includes(term)).length,
        })).sort((left, right) => right.score - left.score || left.mentor.name.localeCompare(right.mentor.name))
        return <div className="institution-mentorship-row" key={student.id}><div><strong>{student.name}</strong><span>{student.department || 'Department not provided'} · {student.career_goal || 'Career goal not set'}{student.skill_gaps.length ? ` · Gaps: ${student.skill_gaps.join(', ')}` : ''}</span><div className="institution-filters"><label>Mentorship reason<input value={Object.prototype.hasOwnProperty.call(studentReasons, student.id) ? studentReasons[student.id] : student.mentorship_reason} maxLength={1000} onChange={(event) => setStudentReasons({ ...studentReasons, [student.id]: event.target.value })} /></label><label>Follow-up date<input type="date" value={Object.prototype.hasOwnProperty.call(studentFollowUps, student.id) ? studentFollowUps[student.id] : student.follow_up_date ?? ''} onChange={(event) => setStudentFollowUps({ ...studentFollowUps, [student.id]: event.target.value })} /></label><label>Mentorship notes<textarea rows={2} value={Object.prototype.hasOwnProperty.call(studentNotes, student.id) ? studentNotes[student.id] : student.mentorship_notes} maxLength={5000} onChange={(event) => setStudentNotes({ ...studentNotes, [student.id]: event.target.value })} /></label></div></div><div className="institution-card-actions"><select aria-label={`Assign mentor to ${student.name}`} value={current ?? ''} onChange={(event) => setStudentAssignments({ ...studentAssignments, [student.id]: event.target.value ? Number(event.target.value) : null })}><option value="">Not assigned</option>{activeMentors.map(({ mentor, score }) => <option key={mentor.mentor_id} value={mentor.mentor_id}>{score > 0 ? 'Suggested · ' : ''}{mentor.name} — {mentor.expertise}</option>)}</select><select aria-label={`Mentorship status for ${student.name}`} value={studentStatuses[student.id] ?? (student.mentorship_status === 'IN_PROGRESS' ? 'IN_PROGRESS' : 'ASSIGNED')} disabled={current == null} onChange={(event) => setStudentStatuses({ ...studentStatuses, [student.id]: event.target.value as 'ASSIGNED' | 'IN_PROGRESS' })}><option value="ASSIGNED">Assigned</option><option value="IN_PROGRESS">In progress</option></select><button className="button button-primary button-small" disabled={busy} onClick={() => void assignStudent(student.id)}>Save</button></div></div>
      })}</div> : <Empty title="No affiliated students" body="Students matched to your institution will appear here." />}
    </Panel>
  </>
}

function InstitutionDashboard() {
  const { data, loading, error, refresh } = useLoad<InstitutionAnalytics>(institutionService.analytics)
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('All departments')
  const [year, setYear] = useState('All years')
  const [completion, setCompletion] = useState('All completion')
  const [gapStatus, setGapStatus] = useState('All skill status')
  const [mentorship, setMentorship] = useState('All mentorship')
  const [courseFilter, setCourseFilter] = useState('All courses')
  const [assessmentFrom, setAssessmentFrom] = useState('')
  const [assessmentTo, setAssessmentTo] = useState('')
  const students = data?.students ?? []
  const departments = [...new Set(students.map((student) => student.department || 'Not specified'))].sort()
  const years = [...new Set(students.map((student) => student.year))].sort((a, b) => a - b)
  const visible = students.filter((student) =>
    student.name.toLowerCase().includes(search.toLowerCase()) &&
    (department === 'All departments' || (student.department || 'Not specified') === department) &&
    (year === 'All years' || String(student.year) === year) &&
    (completion === 'All completion' || (completion === 'No courses assigned' ? !student.course_data_available : completion === 'Complete' ? student.assigned_courses > 0 && student.completed_courses === student.assigned_courses : student.completed_courses < student.assigned_courses)) &&
    (gapStatus === 'All skill status' || student.skill_gap_status === gapStatus) &&
    (mentorship === 'All mentorship' || (mentorship === 'Needs mentorship' ? student.needs_mentorship : student.mentorship_status !== 'NOT_ASSIGNED')) &&
    (courseFilter === 'All courses' || student.assigned_course_ids.includes(Number(courseFilter))) &&
    (!assessmentFrom || Boolean(student.last_assessment_at && student.last_assessment_at.slice(0, 10) >= assessmentFrom)) &&
    (!assessmentTo || Boolean(student.last_assessment_at && student.last_assessment_at.slice(0, 10) <= assessmentTo)),
  )
  function exportCsv() {
    if (!data) return
    const rows = [
      ['Student', 'Email', 'Department', 'Year', 'Career goal', 'Assigned courses', 'Completed courses', 'In progress', 'Pending', 'Completion percent', 'Skill gap status', 'Mentorship status'],
      ...visible.map((student) => [student.name, student.email, student.department, String(student.year), student.career_goal, String(student.assigned_courses), String(student.completed_courses), String(student.courses_in_progress), String(student.pending_courses), student.course_completion_percent == null ? '' : String(student.course_completion_percent), student.skill_gap_status, student.mentorship_status]),
    ]
    const csv = rows.map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(',')).join('\r\n')
    const href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = href
    link.download = 'institution-student-progress.csv'
    link.click()
    URL.revokeObjectURL(href)
  }
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <>
    <PageHeading eyebrow="INSTITUTIONAL STUDENT SUCCESS" title={data.institution_name} description="Monitor students whose saved college affiliation matches your institution. Course completion reflects assigned course records; older untracked history is not inferred." action={<button className="button button-outline button-small" onClick={exportCsv}>Export filtered CSV <FileText size={14} /></button>} />
    <div className="metric-grid">
      <Metric label="Total students" value={data.total_students} note="Students affiliated with your institution" icon={GraduationCap} />
      <Metric label="Completed all courses" value={data.students_completed_all_courses} note="All assigned courses completed" icon={CheckCircle2} tone="green" />
      <Metric label="Currently learning" value={data.students_learning} note="Has an in-progress assigned course" icon={BookOpen} tone="teal" />
      <Metric label="Pending courses" value={data.students_with_pending_courses} note="Has a pending assigned course" icon={ClipboardCheck} tone="purple" />
      <Metric label="Identified skill gaps" value={data.students_with_skill_gaps} note="Assessed gaps against selected role" icon={Activity} tone="amber" />
      <Metric label="Needs mentorship" value={data.students_requiring_mentorship} note="Significant gaps or incomplete assigned courses" icon={Users} tone="coral" />
    </div>
    <div className="institution-chart-grid">
      <Panel title="Course completion distribution" subtitle={`${data.course_status_counts.completed} completed · ${data.course_status_counts.in_progress} in progress · ${data.course_status_counts.pending} pending`}>
        {data.course_status_counts.completed + data.course_status_counts.in_progress + data.course_status_counts.pending
          ? <div className="demand-bars">{[['Completed', data.course_status_counts.completed, 'green'], ['In progress', data.course_status_counts.in_progress, 'blue'], ['Pending', data.course_status_counts.pending, 'amber']].map(([label, value, color]) => <div key={String(label)}><span>{label}</span><ProgressBar value={Number(value) * 100 / Math.max(1, data.course_status_counts.completed + data.course_status_counts.in_progress + data.course_status_counts.pending)} color={String(color)} /><strong>{value}</strong></div>)}</div>
          : <Empty title="No course assignments recorded" body="Assign courses from the existing catalog to track completion." />}
      </Panel>
      <Panel title="Most common assessed skill gaps" subtitle="Unassessed skills are not counted as confirmed gaps">
        {data.common_skill_gaps.length ? <div className="demand-bars">{data.common_skill_gaps.map((item) => <div key={item.skill}><span>{item.skill}</span><ProgressBar value={item.students / Math.max(1, data.total_students) * 100} color="coral" /><strong>{item.students}</strong></div>)}</div> : <Empty title="No assessed skill gaps" body="A gap is shown only when completed assessment evidence is available." />}
      </Panel>
    </div>
    <div className="institution-chart-grid">
      <Panel title="Department-wise learning progress" subtitle="Completion is calculated only from institution-assigned courses">
        {data.department_progress.length ? <div className="demand-bars">{data.department_progress.map((item) => <div key={item.department}><span>{item.department}</span><ProgressBar value={item.completion_percent ?? 0} color="blue" /><strong>{item.completion_percent == null ? 'No courses' : `${item.completion_percent}%`}</strong></div>)}</div> : <Empty title="No department records" body="Department progress will appear for affiliated students." />}
      </Panel>
      <Panel title="Assessment progress over time" subtitle="Historical completed assessment records in this institution">
        {data.assessment_progress_over_time.length ? data.assessment_progress_over_time.map((item) => <div className="institution-record-row" key={item.month}><span>{item.month}</span><span>{item.assessments} assessments · average score {item.average_score}</span></div>) : <Empty title="No assessment history available" body="Completed assessment records will appear here by month." />}
      </Panel>
    </div>
    <Panel title="All Students" subtitle={`${visible.length} of ${students.length} institution students`} action={<span className="institution-record-note">Only records authorized for this institution</span>}>
      <div className="institution-filters">
        <label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search student name" aria-label="Search students" /></label>
        <select value={department} onChange={(event) => setDepartment(event.target.value)}><option>All departments</option>{departments.map((item) => <option key={item}>{item}</option>)}</select>
        <select value={year} onChange={(event) => setYear(event.target.value)}><option>All years</option>{years.map((item) => <option key={item} value={item}>Year {item}</option>)}</select>
        <select value={completion} onChange={(event) => setCompletion(event.target.value)}><option>All completion</option><option>Complete</option><option>Incomplete</option><option>No courses assigned</option></select>
        <select value={gapStatus} onChange={(event) => setGapStatus(event.target.value)}><option>All skill status</option><option value="SKILLS_ALIGNED">Skills Aligned</option><option value="MINOR_GAPS">Minor Skill Gaps</option><option value="SIGNIFICANT_GAPS">Significant Skill Gaps</option><option value="ASSESSMENT_PENDING">Assessment Pending</option></select>
        <select value={mentorship} onChange={(event) => setMentorship(event.target.value)}><option>All mentorship</option><option>Needs mentorship</option><option>Assigned</option></select>
        <select value={courseFilter} onChange={(event) => setCourseFilter(event.target.value)}><option>All courses</option>{data.course_catalog.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select>
        <label className="institution-date-filter"><span>Assessment from</span><input type="date" value={assessmentFrom} onChange={(event) => setAssessmentFrom(event.target.value)} /></label>
        <label className="institution-date-filter"><span>Assessment to</span><input type="date" value={assessmentTo} onChange={(event) => setAssessmentTo(event.target.value)} /></label>
      </div>
      {visible.length ? <div className="institution-student-list">{visible.map((student) => <InstitutionStudentCard key={student.id} student={student} catalog={data.course_catalog} onChanged={refresh} />)}</div> : <Empty title="No matching students" body="Change the search or filters to see other institution records." />}
    </Panel>
    <Panel title="Students Requiring Mentorship" subtitle="Flagged for significant assessed gaps or incomplete assigned courses">
      {students.some((student) => student.needs_mentorship)
        ? <div className="institution-student-list">{students.filter((student) => student.needs_mentorship).map((student) => <div className="institution-mentorship-row" key={student.id}><div><strong>{student.name}</strong><span>{student.mentorship_reason}</span></div><Link className="button button-outline button-small" to={`/institution/students/${student.id}`}>Review & support <ArrowRight size={14} /></Link></div>)}</div>
        : <Empty title="No mentorship flags at this time" body="Students with insufficient assessment data remain marked Assessment Pending." />}
    </Panel>
  </>}</LoadState>
}

function InstitutionStudentCard({ student, catalog, onChanged }: { student: InstitutionStudent; catalog: InstitutionAnalytics['course_catalog']; onChanged: () => void }) {
  const [courseId, setCourseId] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function assignCourse() {
    if (!courseId) return
    setBusy(true); setMessage('')
    try { await institutionService.assignCourse(student.id, Number(courseId)); setMessage('Course assigned.'); setCourseId(''); onChanged() }
    catch (error) { setMessage(messageFromError(error)) }
    finally { setBusy(false) }
  }
  const tone = student.skill_gap_status === 'SIGNIFICANT_GAPS' ? 'coral' : student.skill_gap_status === 'MINOR_GAPS' ? 'amber' : student.skill_gap_status === 'SKILLS_ALIGNED' ? 'green' : 'blue'
  return <article className="institution-student-card">
    <div className="institution-student-main">
      <div className="institution-avatar">{student.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</div>
      <div className="institution-student-identity">
        <div className="institution-student-title"><strong>{student.name}</strong><Badge tone={tone}>{student.skill_gap_status.replace(/_/g, ' ')}</Badge></div>
        <span>{student.department || 'Department not provided'} · Year {student.year} · Student ID {student.id}</span><span>{student.email}</span>
        <div className="institution-student-facts"><span>{student.assigned_courses ? `${student.completed_courses}/${student.assigned_courses} courses completed` : 'No courses assigned'}</span><span>{student.mentorship_status.replace(/_/g, ' ')}{student.mentor_name ? ` · ${student.mentor_name}` : ''}</span></div>
        {student.course_completion_percent != null && <div className="institution-progress"><ProgressBar value={student.course_completion_percent} /><strong>{student.course_completion_percent}%</strong></div>}
        {student.skill_gaps.length > 0 && <div className="institution-skill-chips">{student.skill_gaps.map((gap) => <Badge key={gap.skill} tone={gap.status === 'NEEDS_IMPROVEMENT' ? 'coral' : gap.status === 'MEETS_REQUIREMENT' ? 'green' : 'blue'}>{gap.skill}: {gap.status === 'INSUFFICIENT_EVIDENCE' ? 'assessment pending' : gap.status === 'MEETS_REQUIREMENT' ? 'aligned' : 'improve'}</Badge>)}</div>}
        <div className="institution-profile-links">{student.linkedin_url && <a href={student.linkedin_url} target="_blank" rel="noopener noreferrer"><Linkedin size={14} /> LinkedIn</a>}{student.github_url && <a href={student.github_url} target="_blank" rel="noopener noreferrer"><Github size={14} /> GitHub</a>}</div>
      </div>
      <div className="institution-student-actions"><Link className="button button-primary button-small" to={`/institution/students/${student.id}`}>View Full Profile <ArrowRight size={14} /></Link>
        <div className="institution-assign-course"><select value={courseId} onChange={(event) => setCourseId(event.target.value)} aria-label={`Select course for ${student.name}`}><option value="">Assign catalog course</option>{catalog.filter((course) => !student.assigned_course_ids.includes(course.id)).map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select><button className="button button-outline button-small" disabled={!courseId || busy} onClick={() => void assignCourse()}>{busy ? 'Assigning…' : 'Assign'} <Plus size={14} /></button></div>
        {message && <div className={message === 'Course assigned.' ? 'success-note' : 'inline-error'}>{message}</div>}
      </div>
    </div>
  </article>
}

function InstitutionStudentDetailPage() {
  const { id } = useParams()
  const studentId = Number(id)
  const { data, loading, error, refresh } = useLoad<InstitutionStudentDetail>(() => institutionService.student(studentId))
  const [tab, setTab] = useState('Overview')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [mentorId, setMentorId] = useState('')
  const [status, setStatus] = useState<'NOT_ASSIGNED' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED'>('NOT_ASSIGNED')
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [followUp, setFollowUp] = useState('')
  useEffect(() => {
    if (!data) return
    setMentorId(data.mentor_id == null ? '' : String(data.mentor_id))
    setStatus(data.mentorship_status)
    setReason(data.mentorship_reason)
    setNotes(data.mentorship_notes)
    setFollowUp(data.follow_up_date ?? '')
  }, [data])
  async function saveMentorship(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try { await institutionService.updateMentorship(studentId, { mentor_id: mentorId ? Number(mentorId) : null, status, reason, notes, follow_up_date: followUp || null }); setMessage('Mentorship record saved.'); await refresh() }
    catch (cause) { setMessage(messageFromError(cause)) }
    finally { setBusy(false) }
  }
  async function updateCourse(enrollmentId: number, courseStatus: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED', score: number | null) {
    setBusy(true); setMessage('')
    try { await institutionService.updateCourse(enrollmentId, courseStatus, score); setMessage('Course progress updated.'); await refresh() }
    catch (cause) { setMessage(messageFromError(cause)) }
    finally { setBusy(false) }
  }
  const tabs = ['Overview', 'Course Progress', 'Skill Assessment', 'Skill Gap Analysis', 'Learning Roadmap', 'Industry Projects', 'Mentorship History']
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <>
    <PageHeading eyebrow="AUTHORIZED STUDENT RECORD" title={data.name} description={`${data.department || 'Department not provided'} · Year ${data.year} · ${data.career_goal || 'No career role selected'}`} action={<Link className="button button-outline button-small" to="/institution/dashboard">Back to All Students</Link>} />
    <div className="institution-detail-tabs" role="tablist">{tabs.map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</div>
    {message && <div className={message.includes('saved') || message.includes('updated') ? 'success-note' : 'inline-error'}>{message}</div>}
    {tab === 'Overview' && <div className="institution-detail-grid"><Panel title="Student overview" subtitle={`Student ID ${data.id}`}><div className="institution-detail-facts"><span><strong>Email</strong>{data.email}</span><span><strong>Career role</strong>{data.career_goal || 'Not selected'}</span><span><strong>Course completion</strong>{data.course_completion_percent == null ? 'No courses assigned' : `${data.course_completion_percent}% (${data.completed_courses}/${data.assigned_courses})`}</span><span><strong>Skill status</strong>{data.skill_gap_status.replace(/_/g, ' ')}</span><span><strong>Last assessment</strong>{data.last_assessment_at ? new Date(data.last_assessment_at).toLocaleDateString() : 'Assessment Pending'}</span><span><strong>Mentorship</strong>{data.mentorship_status.replace(/_/g, ' ')}{data.mentor_name ? ` · ${data.mentor_name}` : ''}</span></div></Panel><Panel title="Assessed skill snapshot" subtitle="Only completed assessment evidence is listed">{data.assessed_skills.length ? data.assessed_skills.map((skill) => <div className="institution-record-row" key={skill.skill_id}><span>{skill.skill}</span><Badge tone="green">Level {skill.proficiency}/5</Badge><small>{new Date(skill.assessed_at).toLocaleDateString()}</small></div>) : <Empty title="Assessment Pending" body="No completed assessment results are recorded." />}</Panel></div>}
    {tab === 'Course Progress' && <Panel title="Assigned courses" subtitle={data.course_records.length ? `${data.completed_courses} completed · ${data.courses_in_progress} in progress · ${data.pending_courses} pending` : 'No courses assigned.'}>{data.course_records.map((course) => <div className="institution-record-row" key={course.id}><div><strong>{course.course_name}</strong><small>Assigned {new Date(course.assigned_at).toLocaleDateString()}{course.completed_at ? ` · Completed ${new Date(course.completed_at).toLocaleDateString()}` : ''}{course.score != null ? ` · Score ${course.score}` : ''}</small></div><select aria-label={`Update ${course.course_name} status`} value={course.status} disabled={busy} onChange={(event) => void updateCourse(course.id, event.target.value as 'PENDING' | 'IN_PROGRESS' | 'COMPLETED', course.score)}><option value="PENDING">Pending</option><option value="IN_PROGRESS">In progress</option><option value="COMPLETED">Completed</option></select></div>)}</Panel>}
    {tab === 'Skill Assessment' && <Panel title="Completed assessments" subtitle={data.last_assessment_at ? `Latest skill evidence: ${new Date(data.last_assessment_at).toLocaleDateString()}` : 'Assessment Pending'}>{data.assessed_skills.length ? data.assessed_skills.map((skill) => <div className="institution-record-row" key={skill.skill_id}><span>{skill.skill}</span><span>Proficiency {skill.proficiency}/5 · score {skill.score}</span><small>{new Date(skill.assessed_at).toLocaleString()}</small></div>) : <Empty title="No assessed skills" body="No completed assessment results are recorded." />}</Panel>}
    {tab === 'Skill Gap Analysis' && <Panel title={data.career_goal ? `Requirements for ${data.career_goal}` : 'No configured career role'} subtitle="Unassessed requirements are insufficient evidence, not confirmed gaps">{data.skill_gaps.length ? data.skill_gaps.map((gap) => <div className="institution-record-row institution-gap-row" key={gap.skill}><div><strong>{gap.skill}</strong><small>Required {gap.required}/5 · current {gap.current == null ? 'unassessed' : `${gap.current}/5`}</small>{gap.recommended_courses.map((course) => <small key={course.id}>Recommended course: {course.title}</small>)}</div><Badge tone={gap.status === 'NEEDS_IMPROVEMENT' ? 'coral' : gap.status === 'MEETS_REQUIREMENT' ? 'green' : 'blue'}>{gap.status.replace(/_/g, ' ')}</Badge></div>) : <Empty title="Assessment Pending" body="No configured role requirements are available for comparison." />}</Panel>}
    {tab === 'Learning Roadmap' && <Panel title="Saved learning roadmap" subtitle="Tasks come from existing student roadmap records">{data.roadmap.length ? data.roadmap.map((item, index) => <div className="institution-record-row" key={`${item.title}-${index}`}><div><strong>{item.title}</strong><small>{item.skill || 'General learning task'}</small></div><Badge tone={item.status === 'COMPLETED' ? 'green' : 'blue'}>{item.status.replace(/_/g, ' ')}</Badge></div>) : <Empty title="No learning roadmap recorded" body="Saved roadmap tasks appear here when available." />}</Panel>}
    {tab === 'Industry Projects' && <><div className="institution-detail-grid"><Panel title="Project applications" subtitle="Existing project participation records">{data.industry_projects.length ? data.industry_projects.map((item, index) => <div className="institution-record-row" key={`${item.title}-${index}`}><span>{item.title}</span><Badge>{item.status}</Badge></div>) : <Empty title="No industry project applications" body="Project applications appear here when recorded." />}</Panel><Panel title="Project submissions" subtitle="Submitted work and review state">{data.project_submissions.length ? data.project_submissions.map((item, index) => <div className="institution-record-row" key={`${item.project}-${index}`}><div><strong>{item.project}</strong><small>{item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : 'Date unavailable'}{item.score != null ? ` · Score ${item.score}` : ''}{item.feedback ? ` · Feedback: ${item.feedback}` : ''}</small></div><Badge>{item.status}</Badge></div>) : <Empty title="No project submissions" body="No industry project submissions are recorded." />}</Panel></div><Panel title="Job and internship preparation" subtitle="Submitted applications and their current saved status">{data.job_applications.length ? data.job_applications.map((item, index) => <div className="institution-record-row" key={`${item.job}-${index}`}><div><strong>{item.job}</strong><small>{item.company}{item.applied_at ? ` · Applied ${new Date(item.applied_at).toLocaleDateString()}` : ''}</small></div><Badge>{item.status}</Badge></div>) : <Empty title="No job applications recorded" body="Student job applications appear here when submitted." />}</Panel></>}
    {tab === 'Mentorship History' && <Panel title="Mentorship and follow-up" subtitle={data.mentorship_reason || 'Add an evidence-based mentorship plan'}>
      <form className="institution-mentorship-form" onSubmit={(event) => void saveMentorship(event)}>
        <label>Mentor<select value={mentorId} onChange={(event) => setMentorId(event.target.value)}><option value="">No mentor assigned</option>{data.mentors.map((mentor) => <option key={mentor.id} value={mentor.id}>{mentor.name} · {mentor.expertise}</option>)}</select></label>
        <label>Status<select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="NOT_ASSIGNED">Not assigned</option><option value="ASSIGNED">Assigned</option><option value="IN_PROGRESS">In progress</option><option value="COMPLETED">Completed</option></select></label>
        <label>Reason<input maxLength={1000} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Document the reason" /></label>
        <label>Follow-up date<input type="date" value={followUp} onChange={(event) => setFollowUp(event.target.value)} /></label>
        <label className="field-full">Mentorship notes<textarea rows={4} maxLength={5000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record institution mentorship notes…" /></label>
        <button className="button button-primary button-small" disabled={busy}>{busy ? 'Saving…' : 'Save mentorship record'} <Check size={14} /></button>
      </form>
      {data.mentorship_history.map((item) => <div className="institution-record-row" key={item.created_at}><div><strong>{item.mentor || 'Mentor not assigned'} · {new Date(item.created_at).toLocaleDateString()}</strong><small>{item.reason}</small><small>{item.notes}</small><small>{item.follow_up_date ? `Follow up ${item.follow_up_date}` : ''}</small></div><Badge>{item.status.replace(/_/g, ' ')}</Badge></div>)}
    </Panel>}
  </>}</LoadState>
}

function RoleRoutes({ role }: { role: keyof typeof navigation }) {
  let content: ReactNode
  if (role === 'student') content = <Routes>
    <Route path="dashboard" element={<StudentDashboard />} /><Route path="career" element={<CareerPage />} /><Route path="profile" element={<ProfilePage />} />
    <Route path="learning-profile" element={<LearningProfilePage />} /><Route path="learning-analysis" element={<LearningAnalysisPage />} />
    <Route path="assessment" element={<AssessmentPage />} /><Route path="skill-gap" element={<SkillGapPage />} /><Route path="roadmap" element={<RoadmapPage />} />
    <Route path="projects" element={<StudentProjectsPage />} /><Route path="projects/:id" element={<StudentProjectDetail />} />
    <Route path="jobs" element={<StudentJobsPage />} /><Route path="applications" element={<StudentApplicationsPage />} />
    <Route path="profile-sharing" element={<StudentProfileSharingPage />} /><Route path="feedback" element={<StudentFeedbackPage />} />
    <Route path="notifications" element={<PortalNotificationsPage role="student" />} />
    <Route path="opportunities" element={<OpportunitiesPage />} /><Route path="skills" element={<SkillPassportPage />} /><Route path="progress" element={<ProgressPage />} />
    <Route path="*" element={<Navigate to="/student/dashboard" replace />} />
  </Routes>
  else if (role === 'industry') content = <Routes>
    <Route path="dashboard" element={<IndustryDashboard />} /><Route path="companies" element={<IndustryCompanyDirectoryPage />} /><Route path="profile" element={<IndustryProfilePage />} /><Route path="skills" element={<IndustrySkillsPage />} />
    <Route path="analyzer" element={<IndustryAnalyzerPage />} /><Route path="projects" element={<IndustryProjectsPage />} /><Route path="projects/new" element={<IndustryProjectsPage />} />
    <Route path="jobs" element={<IndustryVacanciesPage />} /><Route path="applications" element={<IndustryApplicationsPage />} />
    <Route path="talent" element={<IndustryTalentPage />} /><Route path="candidates" element={<IndustryCandidateAnalysisPage />} />
    <Route path="submissions" element={<IndustrySubmissionsPage />} /><Route path="notifications" element={<PortalNotificationsPage role="industry" />} />
    <Route path="analytics" element={<IndustryAnalyticsPage />} /><Route path="*" element={<Navigate to="/industry/dashboard" replace />} />
  </Routes>
  else if (role === 'mentor') content = <Routes>
    <Route path="dashboard" element={<MentorDashboard />} /><Route path="projects" element={<MentorSubmissionsPage />} /><Route path="evaluations" element={<MentorSubmissionsPage />} /><Route path="*" element={<Navigate to="/mentor/dashboard" replace />} />
  </Routes>
  else content = <Routes>
    <Route path="dashboard" element={<InstitutionDashboard />} /><Route path="mentors" element={<InstitutionMentorManagementPage />} /><Route path="students/:id" element={<InstitutionStudentDetailPage />} /><Route path="analytics" element={<IndustryAnalyticsForInstitution />} /><Route path="*" element={<Navigate to="/institution/dashboard" replace />} />
  </Routes>
  return <WorkspaceLayout role={role}>{content}</WorkspaceLayout>
}

function StudentProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const load = useCallback(() => projectService.get(Number(id)), [id])
  const { data, loading, error, refresh } = useLoad(load)
  return <LoadState loading={loading} error={error} retry={refresh}>{data && <><PageHeading eyebrow="INDUSTRY PROJECT" title={data.title} description={data.description} action={<button className="button button-outline button-small" onClick={() => navigate('/student/projects')}>Back to projects</button>} /><div className="panel project-detail-panel"><div className="project-skills">{data.required_skills.map((skill) => <Badge tone="blue" key={skill}>{skill}</Badge>)}</div><h2>Expected outcome</h2><p>{data.expected_outcome || 'Apply the listed skills to a practical industry challenge.'}</p><h2>Acceptance criteria</h2><p>{data.evaluation_criteria || 'Quality of implementation, problem solving, communication and evidence.'}</p>{data.instructions && <><h2>Project instructions</h2><p>{data.instructions}</p></>}{data.deliverables?.length ? <><h2>Required deliverables</h2><ul>{data.deliverables.map((item) => <li key={item}>{item}</li>)}</ul></> : null}<p>{data.participation || 'Individual'} participation{data.participation === 'Team' ? ` · team size ${data.team_size_min}–${data.team_size_max}` : ''}{data.duration_weeks ? ` · ${data.duration_weeks} weeks` : ''}</p>{data.references?.map((url) => <p key={url}><a href={url} target="_blank" rel="noreferrer">{url}</a></p>)}<ProjectCard project={data} onChanged={() => void refresh()} /></div></>}</LoadState>
}

function App() {
  const { loading } = useAuth()
  if (loading) return <LoadingState />
  return <Routes>
    <Route path="/" element={<Landing />} /><Route path="/login" element={<Login />} /><Route path="/register" element={<Login register />} />
    <Route path="/student/*" element={<Protected role="student"><RoleRoutes role="student" /></Protected>} />
    <Route path="/industry/*" element={<Protected role="industry"><RoleRoutes role="industry" /></Protected>} />
    <Route path="/mentor/*" element={<Protected role="mentor"><RoleRoutes role="mentor" /></Protected>} />
    <Route path="/institution/*" element={<Protected role="institution"><RoleRoutes role="institution" /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}

export default App
