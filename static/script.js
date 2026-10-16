/* ============================================================
   JOBBRIDGE - FRONTEND APPLICATION JAVASCRIPT (v2.0)
   Full REST API Integration | Real Server-Side Sessions
   ============================================================ */

// Global State
let currentUser = null;
let currentAuthRole = 'candidate';
let isRegisterMode = false;
let onboardingSkills = [];
let profileSkillsList = [];
let candidateJobsCache = [];
let jobFilterDebounceTimer = null;

// ============================================================
// API HELPER
// ============================================================
async function apiFetch(endpoint, options = {}) {
  options.headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(endpoint, options);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const errMsg = data.message || `Request failed (${res.status})`;
      return { ok: false, status: res.status, error: errMsg, data };
    }
    return { ok: true, status: res.status, data };
  } catch (err) {
    console.error('API Network Error:', err);
    return { ok: false, status: 0, error: 'Network error or backend is not reachable.', data: null };
  }
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toast');
  if (!container) return;

  const item = document.createElement('div');
  item.className = `toast-item ${type}`;
  item.textContent = message;
  container.appendChild(item);

  setTimeout(() => {
    item.style.opacity = '0';
    item.style.transform = 'translateX(100%)';
    item.style.transition = 'all 0.3s ease';
    setTimeout(() => item.remove(), 300);
  }, 4000);
}

// ============================================================
// INITIALIZATION & SESSION CHECK
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  loadOccupationsDatalist();

  // Check existing session
  const res = await apiFetch('/api/auth/me');
  if (res.ok && res.data.authenticated && res.data.user) {
    currentUser = res.data.user;
    routeUserByRole(currentUser);
  } else {
    currentUser = null;
    showAuthPage();
  }
}

async function loadOccupationsDatalist() {
  const res = await apiFetch('/api/occupations');
  if (res.ok && res.data.occupations) {
    const datalist = document.getElementById('occupationsList');
    if (datalist) {
      datalist.innerHTML = res.data.occupations
        .slice(0, 100)
        .map(o => `<option value="${escapeHtml(o)}">`)
        .join('');
    }
  }
}

function routeUserByRole(user) {
  hideAllPages();

  if (user.role === 'candidate') {
    if (user.onboarding_status === 'pending') {
      showCandidateOnboarding(user.onboarding_step || 1);
    } else {
      showCandidatePortal();
    }
  } else if (user.role === 'recruiter') {
    showRecruiterPortal();
  } else if (user.role === 'admin') {
    showAdminPortal();
  }
}

function hideAllPages() {
  document.getElementById('authPage').classList.add('hidden');
  document.getElementById('candidateOnboardingPage').classList.add('hidden');
  document.getElementById('candidatePortal').classList.add('hidden');
  document.getElementById('recruiterPortal').classList.add('hidden');
  document.getElementById('adminPortal').classList.add('hidden');
}

// ============================================================
// AUTHENTICATION LOGIC
// ============================================================
function showAuthPage() {
  hideAllPages();
  document.getElementById('authPage').classList.remove('hidden');
  setAuthRole(currentAuthRole);
}

function setAuthRole(role) {
  currentAuthRole = role;

  ['Candidate', 'Recruiter', 'Admin'].forEach(r => {
    const btn = document.getElementById(`roleBtn${r}`);
    if (btn) btn.classList.toggle('active', r.toLowerCase() === role);
  });

  const switchContainer = document.getElementById('switchContainer');
  const nameGroup = document.getElementById('authNameGroup');
  const submitBtn = document.getElementById('authSubmitBtn');

  if (role === 'admin') {
    isRegisterMode = false;
    if (switchContainer) switchContainer.classList.add('hidden');
    if (nameGroup) nameGroup.classList.add('hidden');
    submitBtn.textContent = 'Sign In as Platform Admin';
  } else {
    if (switchContainer) switchContainer.classList.remove('hidden');
    updateAuthModeUI();
  }
}

function toggleAuthMode() {
  if (currentAuthRole === 'admin') return;
  isRegisterMode = !isRegisterMode;
  updateAuthModeUI();
}

function updateAuthModeUI() {
  const nameGroup = document.getElementById('authNameGroup');
  const submitBtn = document.getElementById('authSubmitBtn');
  const switchQuestion = document.getElementById('switchQuestion');
  const switchBtn = document.getElementById('switchButton');
  const roleName = currentAuthRole.charAt(0).toUpperCase() + currentAuthRole.slice(1);

  if (isRegisterMode) {
    nameGroup.classList.remove('hidden');
    submitBtn.textContent = `Register as ${roleName}`;
    switchQuestion.textContent = 'Already have an account?';
    switchBtn.textContent = `Sign in as ${roleName}`;
  } else {
    nameGroup.classList.add('hidden');
    submitBtn.textContent = `Sign In as ${roleName}`;
    switchQuestion.textContent = "Don't have an account?";
    switchBtn.textContent = `Register as ${roleName}`;
  }
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value;
  const name = document.getElementById('authName').value.trim();

  if (!email || !password) {
    showToast('Email and password are required.', 'error');
    return;
  }

  let endpoint = isRegisterMode ? '/api/auth/register' : '/api/auth/login';
  let payload = { email, password, role: currentAuthRole };
  if (isRegisterMode) payload.name = name;

  const res = await apiFetch(endpoint, {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    showToast(res.error, 'error');
    return;
  }

  showToast(res.data.message || 'Login successful!', 'success');
  currentUser = res.data.user;
  routeUserByRole(currentUser);
}

async function handleLogout() {
  await apiFetch('/api/auth/logout', { method: 'POST' });
  currentUser = null;
  showToast('You have been signed out.', 'info');
  showAuthPage();
}

// ============================================================
// CANDIDATE ONBOARDING WIZARD
// ============================================================
function showCandidateOnboarding(step = 1) {
  hideAllPages();
  document.getElementById('candidateOnboardingPage').classList.remove('hidden');
  goToOnboardingStep(step);
}

function goToOnboardingStep(step) {
  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById(`onboardingStep${i}`);
    const node = document.getElementById(`nodeStep${i}`);
    const line = document.getElementById(`line${i}`);

    if (el) el.classList.toggle('hidden', i !== step);
    if (node) {
      node.classList.toggle('active', i === step);
      node.classList.toggle('completed', i < step);
    }
    if (line) line.classList.toggle('active', i < step);
  }

  // Pre-fill user data if available
  if (currentUser) {
    if (step === 1) {
      document.getElementById('onbName').value = currentUser.name || '';
      document.getElementById('onbPhone').value = currentUser.phone || '';
      document.getElementById('onbLocation').value = currentUser.location || '';
    } else if (step === 2) {
      document.getElementById('onbEducation').value = currentUser.education || '';
    } else if (step === 3) {
      document.getElementById('onbOccupation').value = currentUser.current_occupation !== 'Not specified' ? (currentUser.current_occupation || '') : '';
      document.getElementById('onbExperience').value = currentUser.experience || 0;
    } else if (step === 4) {
      document.getElementById('onbTargetRole').value = currentUser.career_interest || '';
      document.getElementById('onbHeadline').value = currentUser.headline || '';
      document.getElementById('onbBio').value = currentUser.bio || '';
    } else if (step === 5) {
      if (currentUser.skills && onboardingSkills.length === 0) {
        onboardingSkills = currentUser.skills.map(s => typeof s === 'string' ? { skill: s, proficiency: 'Intermediate' } : s);
      }
      renderOnboardingSkillsCloud();
    }
  }
}

function addSkillFromInput() {
  const input = document.getElementById('skillNameInput');
  const profSelect = document.getElementById('skillProfInput');
  const skillName = input.value.trim();
  if (!skillName) return;

  if (!onboardingSkills.some(s => s.skill.toLowerCase() === skillName.toLowerCase())) {
    onboardingSkills.push({ skill: skillName, proficiency: profSelect.value, years_experience: 1.0 });
    renderOnboardingSkillsCloud();
  }
  input.value = '';
}

function removeOnboardingSkill(index) {
  onboardingSkills.splice(index, 1);
  renderOnboardingSkillsCloud();
}

function renderOnboardingSkillsCloud() {
  const container = document.getElementById('onboardingSkillsPills');
  if (!container) return;
  container.innerHTML = onboardingSkills.map((s, idx) => `
    <span class="skill-pill">
      ${escapeHtml(s.skill)} <small>(${s.proficiency})</small>
      <span class="remove-x" onclick="removeOnboardingSkill(${idx})">✕</span>
    </span>
  `).join('');
}

async function handleResumeFileSelected(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('resume', file);

  const statusEl = document.getElementById('onbResumeStatus');
  statusEl.classList.remove('hidden');
  statusEl.textContent = `Uploading ${file.name}...`;

  const res = await apiFetch('/api/candidate/resume/upload', {
    method: 'POST',
    body: formData
  });

  if (res.ok) {
    statusEl.textContent = `✓ Uploaded: ${file.name}`;
    showToast('Resume uploaded and verified.', 'success');
  } else {
    statusEl.textContent = `❌ ${res.error}`;
    showToast(res.error, 'error');
  }
}

async function submitOnboardingStep(step) {
  let payload = { step };

  if (step === 1) {
    payload.name = document.getElementById('onbName').value.trim();
    payload.phone = document.getElementById('onbPhone').value.trim();
    payload.location = document.getElementById('onbLocation').value.trim();
    if (!payload.name || !payload.location) {
      showToast('Please fill in your name and location.', 'error');
      return;
    }
  } else if (step === 2) {
    payload.education = document.getElementById('onbEducation').value.trim();
    if (!payload.education) {
      showToast('Please specify your education background.', 'error');
      return;
    }
  } else if (step === 3) {
    payload.current_occupation = document.getElementById('onbOccupation').value.trim();
    payload.experience = parseInt(document.getElementById('onbExperience').value || 0, 10);
    if (!payload.current_occupation) {
      showToast('Please enter your current occupation.', 'error');
      return;
    }
  } else if (step === 4) {
    payload.career_interest = document.getElementById('onbTargetRole').value.trim();
    payload.headline = document.getElementById('onbHeadline').value.trim();
    payload.bio = document.getElementById('onbBio').value.trim();
    if (!payload.career_interest) {
      showToast('Please enter your target role.', 'error');
      return;
    }
  } else if (step === 5) {
    payload.skills = onboardingSkills;
  } else if (step === 6) {
    // Finish onboarding
  }

  const res = await apiFetch('/api/candidate/onboarding/step', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    showToast(res.error, 'error');
    return;
  }

  currentUser = res.data.user;

  if (step < 6) {
    goToOnboardingStep(step + 1);
  } else {
    showToast('Profile completed! Welcome to JobBridge.', 'success');
    showCandidatePortal();
  }
}

// ============================================================
// CANDIDATE PORTAL TABS & DATA
// ============================================================
function showCandidatePortal() {
  hideAllPages();
  document.getElementById('candidatePortal').classList.remove('hidden');

  // Update profile headers
  document.getElementById('candSidebarName').textContent = currentUser.name || 'Candidate';
  document.getElementById('candTopName').textContent = currentUser.name || 'Candidate';
  const initials = getInitials(currentUser.name || 'Candidate');
  document.getElementById('candAvatar').textContent = initials;
  document.getElementById('candTopAvatar').textContent = initials;

  showCandidateTab('dashboard');
  loadNotifications();
}

function showCandidateTab(tabName, btn) {
  const tabs = ['dashboard', 'transitions', 'readiness', 'learning', 'jobs', 'applications', 'saved', 'profile', 'assistant'];
  tabs.forEach(t => {
    const el = document.getElementById(`candTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.classList.toggle('hidden', t !== tabName);
  });

  document.querySelectorAll('#candidatePortal .nav-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const titles = {
    dashboard: ['Career Dashboard', 'Track your profile, readiness, learning pathways, and active job matches.'],
    transitions: ['Career Transitions & Skill-Gap Analysis', 'Standardized ESCO/NCO occupational overlaps and gap breakdowns.'],
    readiness: ['Career-Readiness Score (v1.0)', 'Transparent breakdown of profile readiness against target roles.'],
    learning: ['Personalized Learning Pathways', 'Curated verified free courses and skill progress tracking.'],
    jobs: ['Verified Job Opportunities', 'Opportunities ranked with explainable candidate compatibility scores.'],
    applications: ['Application Pipeline', 'Track your submitted applications and status transitions.'],
    saved: ['Bookmarked Jobs', 'Opportunities you saved for later.'],
    profile: ['Profile & Resume Center', 'Manage your contact details, skills, and secure resume document.'],
    assistant: ['AI Career Assistant', 'Contextual guidance grounded in your profile and industry benchmarks.']
  };

  if (titles[tabName]) {
    document.getElementById('candPageTitle').textContent = titles[tabName][0];
    document.getElementById('candPageSubtitle').textContent = titles[tabName][1];
  }

  if (tabName === 'dashboard') loadCandidateDashboard();
  if (tabName === 'transitions') loadCareerTransitions();
  if (tabName === 'readiness') recalculateReadiness();
  if (tabName === 'learning') loadLearningPathways();
  if (tabName === 'jobs') loadCandidateJobs();
  if (tabName === 'applications') loadCandidateApplications();
  if (tabName === 'saved') loadCandidateSavedJobs();
  if (tabName === 'profile') loadCandidateProfileTab();
}

// 1. Candidate Dashboard
async function loadCandidateDashboard() {
  const res = await apiFetch('/api/candidate/dashboard');
  if (!res.ok) return;

  const data = res.data;
  document.getElementById('dashProfileStrength').textContent = `${data.profile_strength}%`;
  document.getElementById('dashAppCount').textContent = data.active_applications;
  document.getElementById('dashSavedCount').textContent = data.saved_jobs_count;
  document.getElementById('candAppBadge').textContent = data.active_applications;
  document.getElementById('candSavedBadge').textContent = data.saved_jobs_count;

  if (data.career_readiness) {
    const r = data.career_readiness;
    document.getElementById('dashReadinessScore').textContent = `${r.readiness_score}%`;
    document.getElementById('dashReadinessBand').textContent = r.readiness_band;
    document.getElementById('dashTargetRoleHeading').textContent = `Ready for: ${r.target_role}`;
    document.getElementById('dashMeterPercent').textContent = `${Math.round(r.readiness_score)}%`;
  }

  renderJobCards(data.recommended_jobs, 'dashRecommendedJobs');
}

// 2. Career Transitions & Skill Gap
async function loadCareerTransitions() {
  const occInput = document.getElementById('transitionOccInput');
  const occ = occInput ? occInput.value.trim() : '';

  const res = await apiFetch('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ occupation: occ || currentUser.current_occupation })
  });

  const container = document.getElementById('transitionResults');
  if (!container) return;

  if (!res.ok || !res.data.recommendations || res.data.recommendations.length === 0) {
    container.innerHTML = `<div class="card"><p>No transitions found for this occupation. Please try a standard title from the database.</p></div>`;
    return;
  }

  container.innerHTML = res.data.recommendations.map(t => `
    <div class="transition-card">
      <div class="transition-head">
        <div>
          <span class="eyebrow">TRANSITION TARGET</span>
          <div class="transition-target">${escapeHtml(t.target_occupation)}</div>
          <small class="text-muted">Current: ${escapeHtml(t.current_occupation)}</small>
        </div>
        <div class="transition-scores">
          <span class="score-pill">Match: ${t.match_score}%</span>
          <span class="score-pill">Skill Overlap: ${t.skill_similarity}%</span>
        </div>
      </div>
      <p style="margin: 10px 0; font-size: 0.9rem;">${escapeHtml(t.explanation)}</p>

      <div class="field-row" style="margin-top: 14px;">
        <div>
          <strong style="font-size:0.85rem; color:#065f46;">✓ Matched Skills (${t.common_skills ? t.common_skills.length : 0})</strong>
          <div class="skills-tag-cloud small">
            ${(t.common_skills || []).map(s => `<span class="skill-tag matched">${escapeHtml(s)}</span>`).join('') || '<small>None in common</small>'}
          </div>
        </div>
        <div>
          <strong style="font-size:0.85rem; color:#b87409;">○ Skills to Develop (${t.missing_skills ? t.missing_skills.length : t.missing_skill_count})</strong>
          <div class="skills-tag-cloud small">
            ${(t.missing_skills || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') || '<small>Fully matched</small>'}
          </div>
        </div>
      </div>

      <div class="transition-plan-box">
        <strong>Suggested Learning Plan:</strong> ${escapeHtml(t.learning_plan)}
      </div>
    </div>
  `).join('');
}

// 3. Career Readiness Score
async function recalculateReadiness() {
  const roleInput = document.getElementById('readinessRoleInput');
  const roleName = roleInput && roleInput.value.trim() ? roleInput.value.trim() : (currentUser.career_interest || 'Data Analyst');
  if (roleInput) roleInput.value = roleName;

  const res = await apiFetch(`/api/career-readiness?target_role=${encodeURIComponent(roleName)}`);
  if (!res.ok) return;

  const r = res.data.readiness;
  document.getElementById('readinessFactorEssential').textContent = `${r.factors.essential_skill_coverage.score} / ${r.factors.essential_skill_coverage.max}`;
  document.getElementById('readinessFactorProf').textContent = `${r.factors.proficiency_depth.score} / ${r.factors.proficiency_depth.max}`;
  document.getElementById('readinessFactorExp').textContent = `${r.factors.experience_alignment.score} / ${r.factors.experience_alignment.max}`;
  document.getElementById('readinessFactorLearning').textContent = `${r.factors.learning_progress.score} / ${r.factors.learning_progress.max}`;

  const matchedCloud = document.getElementById('readinessMatchedSkills');
  if (matchedCloud) {
    matchedCloud.innerHTML = r.factors.essential_skill_coverage.matched_skills
      .map(s => `<span class="skill-tag matched">✓ ${escapeHtml(s)}</span>`)
      .join('') + r.factors.essential_skill_coverage.missing_skills
      .map(s => `<span class="skill-tag">○ ${escapeHtml(s)}</span>`)
      .join('');
  }

  const actionList = document.getElementById('readinessActionList');
  if (actionList) {
    actionList.innerHTML = r.actionable_next_steps.map(step => `<li>${escapeHtml(step)}</li>`).join('');
  }
  document.getElementById('readinessDisclaimer').textContent = r.disclaimer;
}

// 4. Learning Pathways & Courses
async function loadLearningPathways() {
  const res = await apiFetch('/api/candidate/learning-paths');
  if (!res.ok) return;

  const courses = res.data.verified_courses || [];
  const progress = res.data.user_progress || {};
  const container = document.getElementById('learningCoursesList');
  if (!container) return;

  container.innerHTML = courses.map(c => {
    const status = progress[c.skill_name.toLowerCase()] || 'Not Started';
    return `
      <div class="course-card">
        <div>
          <div class="course-prov">${escapeHtml(c.provider)}</div>
          <div class="course-title">${escapeHtml(c.title)}</div>
          <div style="font-size:0.85rem; margin:6px 0; color:var(--deep-navy);">Skill: <strong>${escapeHtml(c.skill_name)}</strong></div>
        </div>
        <div>
          <div class="course-meta">
            <span>⏱ ${c.duration_hours} hrs</span>
            <span>🏷 ${c.cost}</span>
            <span>⚡ ${c.difficulty}</span>
          </div>
          <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
            <a href="${c.url}" target="_blank" rel="noopener noreferrer" class="btn secondary" style="padding:6px 12px; font-size:0.8rem;">Open Course ↗</a>
            <select onchange="updateCourseProgress('${escapeHtml(c.skill_name)}', this.value)" style="padding:4px 8px; font-size:0.8rem; border-radius:6px; border:1px solid #cbd5e1;">
              <option value="Not Started" ${status === 'Not Started' ? 'selected' : ''}>Not Started</option>
              <option value="In Progress" ${status === 'In Progress' ? 'selected' : ''}>In Progress</option>
              <option value="Completed" ${status === 'Completed' ? 'selected' : ''}>Completed</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function updateCourseProgress(skill, status) {
  const res = await apiFetch('/api/candidate/learning-progress', {
    method: 'POST',
    body: JSON.stringify({ skill, status })
  });
  if (res.ok) {
    showToast(res.data.message, 'success');
  }
}

// 5. Jobs Explorer
async function loadCandidateJobs() {
  const query = document.getElementById('jobSearchQuery')?.value || '';
  const loc = document.getElementById('jobFilterLocation')?.value || 'all';
  const type = document.getElementById('jobFilterType')?.value || 'all';

  const res = await apiFetch(`/api/candidate/jobs?q=${encodeURIComponent(query)}&location=${encodeURIComponent(loc)}&type=${encodeURIComponent(type)}`);
  if (!res.ok) return;

  candidateJobsCache = res.data.jobs || [];
  renderJobCards(candidateJobsCache, 'jobsExplorerList');
}

function debounceJobFilter() {
  clearTimeout(jobFilterDebounceTimer);
  jobFilterDebounceTimer = setTimeout(loadCandidateJobs, 300);
}

function filterCandidateJobs() {
  loadCandidateJobs();
}

function renderJobCards(jobs, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!jobs || jobs.length === 0) {
    container.innerHTML = `<div class="card" style="grid-column: 1/-1;"><p>No jobs found matching your criteria.</p></div>`;
    return;
  }

  container.innerHTML = jobs.map(j => `
    <div class="job-card">
      <div class="job-head">
        <div>
          <div class="job-title">${escapeHtml(j.title)}</div>
          <div class="job-company">${escapeHtml(j.company_name || 'Independent Recruiter')}</div>
        </div>
        <div class="compat-badge ${j.compatibility_score < 70 ? 'amber' : ''}">
          ★ ${j.compatibility_score}% Compatibility
        </div>
      </div>
      <div class="job-meta">
        <span>📍 ${escapeHtml(j.location)}</span>
        <span>💼 ${escapeHtml(j.employment_type)}</span>
        <span>⏱ ${j.experience_years_min}+ yrs exp</span>
      </div>
      <div class="job-desc">${escapeHtml(j.description)}</div>
      <div class="job-skills-row">
        ${(j.required_skills || '').split(',').map(s => s.trim()).filter(Boolean).map(s => `
          <span class="skill-tag ${j.matched_skills && j.matched_skills.map(x=>x.toLowerCase()).includes(s.toLowerCase()) ? 'matched' : ''}">
            ${escapeHtml(s)}
          </span>
        `).join('')}
      </div>
      <div class="job-footer">
        <div class="job-salary">₹${(j.salary_min / 100000).toFixed(1)}–${(j.salary_max / 100000).toFixed(1)} LPA</div>
        <div class="job-actions">
          <button type="button" class="btn secondary" onclick="toggleSaveJob(${j.id}, ${j.is_saved})" title="${j.is_saved ? 'Unsave' : 'Save'}">
            ${j.is_saved ? '❤️ Saved' : '🤍 Save'}
          </button>
          ${j.applied_status ? `
            <span class="status-badge status-${j.applied_status.toLowerCase().replace(' ', '-')}">${j.applied_status}</span>
          ` : `
            <button type="button" class="btn primary" onclick="openApplyModal(${j.id}, '${escapeHtml(j.title)}', '${escapeHtml(j.company_name || '')}')">
              Apply Now →
            </button>
          `}
        </div>
      </div>
    </div>
  `).join('');
}

async function toggleSaveJob(jobId, isSaved) {
  const res = await apiFetch(`/api/candidate/jobs/${jobId}/save`, {
    method: isSaved ? 'DELETE' : 'POST'
  });
  if (res.ok) {
    showToast(res.data.message, 'success');
    loadCandidateJobs();
    loadCandidateDashboard();
  }
}

function openApplyModal(jobId, jobTitle, companyName) {
  document.getElementById('applyJobId').value = jobId;
  document.getElementById('applyModalTitle').textContent = `Apply for: ${jobTitle}`;
  document.getElementById('applyModalCompany').textContent = companyName;
  document.getElementById('applyCoverLetter').value = '';
  document.getElementById('modalApply').classList.remove('hidden');
}

async function submitJobApplication(event) {
  event.preventDefault();
  const jobId = document.getElementById('applyJobId').value;
  const coverLetter = document.getElementById('applyCoverLetter').value.trim();

  const res = await apiFetch(`/api/candidate/jobs/${jobId}/apply`, {
    method: 'POST',
    body: JSON.stringify({ cover_letter: coverLetter })
  });

  if (!res.ok) {
    showToast(res.error, 'error');
    return;
  }

  showToast('Application submitted successfully!', 'success');
  closeModal('modalApply');
  loadCandidateJobs();
  loadCandidateDashboard();
}

// 6. Candidate Applications
async function loadCandidateApplications() {
  const res = await apiFetch('/api/candidate/applications');
  if (!res.ok) return;

  const container = document.getElementById('myApplicationsList');
  if (!container) return;

  if (res.data.applications.length === 0) {
    container.innerHTML = `<div class="card"><p>You haven't submitted any applications yet. Explore recommended roles to apply.</p></div>`;
    return;
  }

  container.innerHTML = res.data.applications.map(a => `
    <div class="application-row-card">
      <div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--deep-navy);">${escapeHtml(a.job_title)}</div>
        <div style="font-size:0.9rem; color:var(--text-muted);">${escapeHtml(a.company_name || 'Independent Recruiter')} • ${escapeHtml(a.job_location)}</div>
        <div style="margin-top:8px; font-size:0.82rem; color:var(--text-muted);">
          Applied on ${new Date(a.applied_at).toLocaleDateString()} • Compatibility Match: <strong>${a.compatibility_score}%</strong>
        </div>
        ${a.status_history && a.status_history.length > 0 ? `
          <div style="margin-top:8px; font-size:0.8rem; background:var(--bg-slate); padding:6px 10px; border-radius:6px;">
            Latest activity: <em>${escapeHtml(a.status_history[a.status_history.length - 1].note || a.status)}</em>
          </div>
        ` : ''}
      </div>
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:10px;">
        <span class="status-badge status-${a.status.toLowerCase().replace(' ', '-')}">${a.status}</span>
        ${['Applied', 'Under Review'].includes(a.status) ? `
          <button type="button" class="btn secondary" style="padding:4px 10px; font-size:0.8rem;" onclick="withdrawCandidateApplication(${a.id})">
            Withdraw Application
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

async function withdrawCandidateApplication(appId) {
  if (!confirm('Are you sure you want to withdraw this application?')) return;
  const res = await apiFetch(`/api/candidate/applications/${appId}/withdraw`, { method: 'POST' });
  if (res.ok) {
    showToast('Application withdrawn.', 'info');
    loadCandidateApplications();
    loadCandidateDashboard();
  } else {
    showToast(res.error, 'error');
  }
}

// 7. Saved Jobs
async function loadCandidateSavedJobs() {
  const res = await apiFetch('/api/candidate/saved-jobs');
  if (!res.ok) return;
  renderJobCards(res.data.saved_jobs, 'mySavedJobsList');
}

// 8. Profile & Resume Tab
async function loadCandidateProfileTab() {
  const res = await apiFetch('/api/candidate/profile');
  if (!res.ok) return;

  const p = res.data.profile;
  document.getElementById('profName').value = p.name || '';
  document.getElementById('profEmail').value = p.email || '';
  document.getElementById('profPhone').value = p.phone || '';
  document.getElementById('profLocation').value = p.location || '';
  document.getElementById('profEducation').value = p.education || '';
  document.getElementById('profOccupation').value = p.current_occupation || '';
  document.getElementById('profExperience').value = p.experience || 0;
  document.getElementById('profInterest').value = p.career_interest || '';
  document.getElementById('profHeadline').value = p.headline || '';
  document.getElementById('profBio').value = p.bio || '';

  // Resume status
  const resumeInfo = document.getElementById('resumeActiveInfo');
  const dlBtn = document.getElementById('downloadResumeBtn');
  if (p.resume_filename) {
    resumeInfo.innerHTML = `📄 Active Resume: <strong>${escapeHtml(p.resume_filename)}</strong>`;
    dlBtn.classList.remove('hidden');
  } else {
    resumeInfo.textContent = 'No resume uploaded yet.';
    dlBtn.classList.add('hidden');
  }

  profileSkillsList = p.skills || [];
  renderProfileSkillsCloud();
}

function addProfileSkill() {
  const nameInput = document.getElementById('profSkillName');
  const profInput = document.getElementById('profSkillProf');
  const name = nameInput.value.trim();
  if (!name) return;

  if (!profileSkillsList.some(s => s.skill.toLowerCase() === name.toLowerCase())) {
    profileSkillsList.push({ skill: name, proficiency: profInput.value, years_experience: 1.0 });
    renderProfileSkillsCloud();
  }
  nameInput.value = '';
}

function removeProfileSkill(idx) {
  profileSkillsList.splice(idx, 1);
  renderProfileSkillsCloud();
}

function renderProfileSkillsCloud() {
  const container = document.getElementById('profSkillsCloud');
  if (!container) return;
  container.innerHTML = profileSkillsList.map((s, idx) => `
    <span class="skill-pill">
      ${escapeHtml(s.skill)} <small>(${s.proficiency})</small>
      <span class="remove-x" onclick="removeProfileSkill(${idx})">✕</span>
    </span>
  `).join('');
}

async function saveProfileChanges() {
  const payload = {
    name: document.getElementById('profName').value.trim(),
    phone: document.getElementById('profPhone').value.trim(),
    location: document.getElementById('profLocation').value.trim(),
    education: document.getElementById('profEducation').value.trim(),
    current_occupation: document.getElementById('profOccupation').value.trim(),
    experience: parseInt(document.getElementById('profExperience').value || 0, 10),
    career_interest: document.getElementById('profInterest').value.trim(),
    headline: document.getElementById('profHeadline').value.trim(),
    bio: document.getElementById('profBio').value.trim(),
    skills: profileSkillsList
  };

  const res = await apiFetch('/api/candidate/profile', {
    method: 'PUT',
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    showToast('Profile updated successfully!', 'success');
    currentUser = res.data.profile;
    document.getElementById('candSidebarName').textContent = currentUser.name;
    document.getElementById('candTopName').textContent = currentUser.name;
  } else {
    showToast(res.error, 'error');
  }
}

function downloadMyResume() {
  window.location.href = `/api/candidate/resume/download?user_id=${currentUser.id}`;
}

async function uploadProfileResume(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('resume', file);

  const res = await apiFetch('/api/candidate/resume/upload', {
    method: 'POST',
    body: formData
  });

  if (res.ok) {
    showToast('Resume uploaded and verified.', 'success');
    loadCandidateProfileTab();
  } else {
    showToast(res.error, 'error');
  }
}

// 9. AI Assistant Chat
async function sendAssistantMessage(event) {
  event.preventDefault();
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  const history = document.getElementById('chatHistory');
  history.innerHTML += `
    <div class="chat-msg user">
      <div class="chat-bubble">${escapeHtml(msg)}</div>
    </div>
  `;
  input.value = '';
  history.scrollTop = history.scrollHeight;

  const res = await apiFetch('/api/assistant/chat', {
    method: 'POST',
    body: JSON.stringify({ message: msg })
  });

  if (res.ok) {
    const formattedReply = escapeHtml(res.data.reply).replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    history.innerHTML += `
      <div class="chat-msg bot">
        <div class="chat-bubble">${formattedReply}</div>
      </div>
    `;
  } else {
    history.innerHTML += `
      <div class="chat-msg bot">
        <div class="chat-bubble" style="color:var(--danger)">Sorry, I encountered an issue. Please try again.</div>
      </div>
    `;
  }
  history.scrollTop = history.scrollHeight;
}

// Notifications
async function loadNotifications() {
  const res = await apiFetch('/api/notifications');
  if (!res.ok) return;

  const notifs = res.data.notifications || [];
  const unread = res.data.unread_count || 0;
  const badge = document.getElementById('notifBadge');
  if (badge) badge.classList.toggle('hidden', unread === 0);

  const list = document.getElementById('notifList');
  if (list) {
    list.innerHTML = notifs.length === 0 ? `<div style="padding:16px; font-size:0.85rem; color:var(--text-muted);">No new notifications.</div>` :
      notifs.map(n => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotificationRead(${n.id})">
          <strong>${escapeHtml(n.title)}</strong>
          <div>${escapeHtml(n.message)}</div>
          <small style="color:var(--text-muted);">${new Date(n.created_at).toLocaleTimeString()}</small>
        </div>
      `).join('');
  }
}

function toggleNotificationsMenu() {
  const dropdown = document.getElementById('notifDropdown');
  if (dropdown) dropdown.classList.toggle('hidden');
}

async function markNotificationRead(id) {
  await apiFetch(`/api/notifications/${id}/read`, { method: 'PATCH' });
  loadNotifications();
}

async function markAllNotificationsRead(event) {
  event.stopPropagation();
  await apiFetch('/api/notifications/read-all', { method: 'PATCH' });
  loadNotifications();
}

// ============================================================
// RECRUITER PORTAL TABS & DATA
// ============================================================
function showRecruiterPortal() {
  hideAllPages();
  document.getElementById('recruiterPortal').classList.remove('hidden');

  document.getElementById('recSidebarName').textContent = currentUser.name || 'Recruiter';
  document.getElementById('recSidebarCompany').textContent = currentUser.company ? currentUser.company.company_name : 'Company Setup Needed';
  document.getElementById('recAvatar').textContent = getInitials(currentUser.name || 'Recruiter');

  showRecruiterTab('dashboard');
}

function showRecruiterTab(tabName, btn) {
  ['dashboard', 'jobs', 'applicants', 'analytics'].forEach(t => {
    const el = document.getElementById(`recTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.classList.toggle('hidden', t !== tabName);
  });

  document.querySelectorAll('#recruiterPortal .nav-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const titles = {
    dashboard: ['Recruiter Overview', 'Manage company jobs, review qualified applicants, and make decisions.'],
    jobs: ['Job Postings', 'Publish, edit, pause, and close recruitment postings.'],
    applicants: ['Applicant Pipeline & Evaluation', 'Review candidate profiles, download resumes, and record decisions.'],
    analytics: ['Recruitment Analytics', 'Calculated metrics on applicant volume, conversion funnels, and compatibility.']
  };

  if (titles[tabName]) {
    document.getElementById('recPageTitle').textContent = titles[tabName][0];
    document.getElementById('recPageSubtitle').textContent = titles[tabName][1];
  }

  if (tabName === 'dashboard') loadRecruiterDashboard();
  if (tabName === 'jobs') loadRecruiterJobs();
  if (tabName === 'applicants') loadRecruiterApplicants();
  if (tabName === 'analytics') loadRecruiterAnalytics();
}

async function loadRecruiterDashboard() {
  const res = await apiFetch('/api/recruiter/dashboard');
  if (!res.ok) return;

  const m = res.data.metrics;
  document.getElementById('recMetricActiveJobs').textContent = m.active_jobs;
  document.getElementById('recMetricTotalApps').textContent = m.total_applications;
  document.getElementById('recMetricPendingApps').textContent = m.pending_review;
  document.getElementById('recMetricShortlisted').textContent = m.shortlisted;

  const tableContainer = document.getElementById('recRecentApplicantsTable');
  const recent = res.data.recent_applications || [];
  if (recent.length === 0) {
    tableContainer.innerHTML = `<div style="padding:20px;"><p>No applicants received yet.</p></div>`;
  } else {
    tableContainer.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Job Role</th>
            <th>Match</th>
            <th>Status</th>
            <th>Applied At</th>
          </tr>
        </thead>
        <tbody>
          ${recent.map(r => `
            <tr>
              <td><strong>${escapeHtml(r.candidate_name)}</strong><br><small>${escapeHtml(r.candidate_email)}</small></td>
              <td>${escapeHtml(r.job_title)}</td>
              <td><span class="compat-badge">★ ${r.compatibility_score}%</span></td>
              <td><span class="status-badge status-${r.status.toLowerCase().replace(' ', '-')}">${r.status}</span></td>
              <td>${new Date(r.applied_at).toLocaleDateString()}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }
}

async function loadRecruiterJobs() {
  const res = await apiFetch('/api/recruiter/jobs');
  if (!res.ok) return;

  const table = document.getElementById('recJobsTable');
  const jobs = res.data.jobs || [];

  table.innerHTML = jobs.length === 0 ? `<div style="padding:24px;"><p>No jobs published yet.</p></div>` : `
    <table class="data-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Location & Type</th>
          <th>Applicants</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${jobs.map(j => `
          <tr>
            <td><strong>${escapeHtml(j.title)}</strong><br><small>₹${(j.salary_min/100000).toFixed(1)}–${(j.salary_max/100000).toFixed(1)} LPA</small></td>
            <td>${escapeHtml(j.location)} • ${escapeHtml(j.employment_type)}</td>
            <td><strong>${j.application_count}</strong> total (${j.shortlist_count} shortlisted)</td>
            <td><span class="status-badge ${j.status === 'Open' ? 'status-shortlisted' : 'status-withdrawn'}">${j.status}</span></td>
            <td>
              <button type="button" class="btn secondary" style="padding:4px 8px; font-size:0.8rem;" onclick="toggleRecruiterJobStatus(${j.id}, '${j.status}')">
                ${j.status === 'Open' ? 'Close Job' : 'Reopen Job'}
              </button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  // Update applicant job filter dropdown
  const filterSelect = document.getElementById('recApplicantJobFilter');
  if (filterSelect) {
    filterSelect.innerHTML = `<option value="">All Jobs</option>` +
      jobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
  }
}

function openCreateJobModal() {
  document.getElementById('editJobId').value = '';
  document.getElementById('jobTitleInput').value = '';
  document.getElementById('jobLocationInput').value = 'Nagpur / Remote';
  document.getElementById('jobSkillsInput').value = '';
  document.getElementById('jobDescInput').value = '';
  document.getElementById('modalJob').classList.remove('hidden');
}

async function handleSaveJob(event) {
  event.preventDefault();
  const payload = {
    title: document.getElementById('jobTitleInput').value.trim(),
    location: document.getElementById('jobLocationInput').value.trim(),
    employment_type: document.getElementById('jobTypeInput').value,
    salary_min: parseFloat(document.getElementById('jobSalaryMin').value || 400000),
    salary_max: parseFloat(document.getElementById('jobSalaryMax').value || 800000),
    experience_years_min: parseInt(document.getElementById('jobExpMin').value || 0, 10),
    required_skills: document.getElementById('jobSkillsInput').value.trim(),
    description: document.getElementById('jobDescInput').value.trim()
  };

  const res = await apiFetch('/api/recruiter/jobs', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    showToast('Job posting published!', 'success');
    closeModal('modalJob');
    loadRecruiterJobs();
    loadRecruiterDashboard();
  } else {
    showToast(res.error, 'error');
  }
}

async function toggleRecruiterJobStatus(jobId, currentStatus) {
  const newStatus = currentStatus === 'Open' ? 'Closed' : 'Open';
  const res = await apiFetch(`/api/recruiter/jobs/${jobId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });

  if (res.ok) {
    showToast(res.data.message, 'success');
    loadRecruiterJobs();
  }
}

async function loadRecruiterApplicants() {
  const jobFilter = document.getElementById('recApplicantJobFilter')?.value || '';
  const statusFilter = document.getElementById('recApplicantStatusFilter')?.value || 'all';

  let url = '/api/recruiter/applications?status=' + encodeURIComponent(statusFilter);
  if (jobFilter) url += '&job_id=' + encodeURIComponent(jobFilter);

  const res = await apiFetch(url);
  if (!res.ok) return;

  const container = document.getElementById('recApplicantsList');
  if (!container) return;

  const apps = res.data.applications || [];
  if (apps.length === 0) {
    container.innerHTML = `<div class="card" style="grid-column: 1/-1;"><p>No applicants match the selected criteria.</p></div>`;
    return;
  }

  container.innerHTML = apps.map(a => `
    <div class="card" style="display:flex; flex-direction:column; justify-content:space-between; gap:14px;">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <strong style="font-size:1.15rem; color:var(--deep-navy);">${escapeHtml(a.candidate_name)}</strong>
            <div style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(a.candidate_email)} • ${escapeHtml(a.candidate_location || '')}</div>
          </div>
          <span class="compat-badge">★ ${a.compatibility_score}% Match</span>
        </div>
        <div style="margin: 10px 0; font-size: 0.88rem;">
          Applied for: <strong>${escapeHtml(a.job_title)}</strong><br>
          Experience: ${a.candidate_experience} yrs • Education: ${escapeHtml(a.candidate_education || 'N/A')}
        </div>
        <div class="skills-tag-cloud small">
          ${(a.candidate_skills || []).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}
        </div>
        ${a.cover_letter ? `
          <div style="margin-top:10px; font-size:0.82rem; background:var(--bg-slate); padding:8px 12px; border-radius:6px; font-style:italic;">
            "${escapeHtml(a.cover_letter)}"
          </div>
        ` : ''}
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-light); padding-top:12px;">
        <span class="status-badge status-${a.status.toLowerCase().replace(' ', '-')}">${a.status}</span>
        <div style="display:flex; gap:8px;">
          ${a.resume_filename ? `
            <a href="/api/candidate/resume/download?user_id=${a.candidate_id}" class="btn secondary" style="padding:4px 8px; font-size:0.8rem;">Resume 📄</a>
          ` : '<small style="color:var(--text-muted); padding:4px;">No resume</small>'}
          <button type="button" class="btn primary" style="padding:4px 10px; font-size:0.8rem;"
                  onclick="openApplicantDecisionModal(${a.id}, '${escapeHtml(a.candidate_name)}', '${escapeHtml(a.job_title)}', '${a.status}')">
            Review / Decide →
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

function openApplicantDecisionModal(appId, candName, jobTitle, currentStatus) {
  document.getElementById('decisionAppId').value = appId;
  document.getElementById('decisionCandidateName').textContent = candName;
  document.getElementById('decisionJobTitle').textContent = `Applied for: ${jobTitle} (Current: ${currentStatus})`;
  document.getElementById('decisionNewStatus').value = currentStatus === 'Applied' ? 'Under Review' : currentStatus;
  document.getElementById('decisionNote').value = '';
  document.getElementById('modalApplicantDecision').classList.remove('hidden');
}

async function handleApplicantDecision(event) {
  event.preventDefault();
  const appId = document.getElementById('decisionAppId').value;
  const newStatus = document.getElementById('decisionNewStatus').value;
  const note = document.getElementById('decisionNote').value.trim();

  const res = await apiFetch(`/api/recruiter/applications/${appId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus, note })
  });

  if (res.ok) {
    showToast(res.data.message, 'success');
    closeModal('modalApplicantDecision');
    loadRecruiterApplicants();
    loadRecruiterDashboard();
  } else {
    showToast(res.error, 'error');
  }
}

async function loadRecruiterAnalytics() {
  const res = await apiFetch('/api/recruiter/analytics');
  if (!res.ok) return;

  const data = res.data;
  const container = document.getElementById('recAnalyticsContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="card">
      <h3>Application Pipeline Distribution</h3>
      <div style="margin-top:16px; display:flex; flex-direction:column; gap:10px;">
        ${Object.entries(data.status_distribution || {}).map(([st, cnt]) => `
          <div>
            <div style="display:flex; justify-content:space-between; font-size:0.88rem; margin-bottom:4px;">
              <span>${st}</span>
              <strong>${cnt}</strong>
            </div>
            <div style="height:8px; background:var(--bg-slate); border-radius:4px; overflow:hidden;">
              <div style="height:100%; background:var(--primary-blue); width:${Math.min(100, cnt * 25)}%;"></div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="card">
      <h3>Role Performance & Match Averages</h3>
      <div style="margin-top:16px;">
        ${(data.jobs_summary || []).map(j => `
          <div style="margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #f1f5f9;">
            <div style="font-weight:700; color:var(--deep-navy);">${escapeHtml(j.title)}</div>
            <small style="color:var(--text-muted);">${j.applications_count} applicants • Average candidate match: <strong>${j.avg_compatibility}%</strong></small>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// ============================================================
// ADMINISTRATOR PORTAL TABS & DATA
// ============================================================
function showAdminPortal() {
  hideAllPages();
  document.getElementById('adminPortal').classList.remove('hidden');
  showAdminTab('overview');
}

function showAdminTab(tabName, btn) {
  ['overview', 'users', 'jobs', 'logs'].forEach(t => {
    const el = document.getElementById(`adminTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.classList.toggle('hidden', t !== tabName);
  });

  document.querySelectorAll('#adminPortal .nav-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  if (tabName === 'overview') loadAdminOverview();
  if (tabName === 'users') loadAdminUsers();
  if (tabName === 'jobs') loadAdminJobs();
  if (tabName === 'logs') loadAdminLogs();
}

async function loadAdminOverview() {
  const res = await apiFetch('/api/admin/metrics');
  if (!res.ok) return;

  const m = res.data.metrics;
  document.getElementById('adminMetricCandidates').textContent = m.total_candidates;
  document.getElementById('adminMetricRecruiters').textContent = m.total_recruiters;
  document.getElementById('adminMetricJobs').textContent = m.total_jobs;
  document.getElementById('adminMetricApps').textContent = m.total_applications;

  const dbRes = await apiFetch('/api/database-status');
  if (dbRes.ok) {
    document.getElementById('adminDbStatusSummary').innerHTML = `
      <div style="margin-top:12px; font-size:0.88rem; background:var(--bg-slate); padding:14px; border-radius:8px;">
        <div><strong>Database Path:</strong> <code>${escapeHtml(dbRes.data.database_path)}</code></div>
        <div><strong>Integrity Check:</strong> <span class="pill-green">${dbRes.data.integrity}</span></div>
        <div><strong>Active Tables:</strong> ${dbRes.data.table_count} tables validated</div>
      </div>
    `;
  }
}

async function loadAdminUsers() {
  const res = await apiFetch('/api/admin/users');
  if (!res.ok) return;

  const table = document.getElementById('adminUsersTable');
  table.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Name & Email</th>
          <th>Role</th>
          <th>Location</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        ${res.data.users.map(u => `
          <tr>
            <td><strong>${escapeHtml(u.name)}</strong><br><small>${escapeHtml(u.email)}</small></td>
            <td><span class="pill-green">${u.role}</span></td>
            <td>${escapeHtml(u.location || 'N/A')}</td>
            <td><span class="status-badge ${u.status === 'active' ? 'status-selected' : 'status-rejected'}">${u.status}</span></td>
            <td>
              ${u.role !== 'admin' ? `
                <button type="button" class="btn secondary" style="padding:4px 8px; font-size:0.8rem;" onclick="toggleUserStatus(${u.id}, '${u.status}')">
                  ${u.status === 'active' ? 'Suspend' : 'Activate'}
                </button>
              ` : '<small style="color:var(--text-muted);">Protected</small>'}
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function toggleUserStatus(userId, currentStatus) {
  const newStatus = currentStatus === 'active' ? 'suspended' : 'active';
  if (!confirm(`Are you sure you want to change user status to '${newStatus}'?`)) return;

  const res = await apiFetch(`/api/admin/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });

  if (res.ok) {
    showToast(res.data.message, 'success');
    loadAdminUsers();
  } else {
    showToast(res.error, 'error');
  }
}

async function loadAdminJobs() {
  const res = await apiFetch('/api/admin/jobs');
  if (!res.ok) return;

  const table = document.getElementById('adminJobsTable');
  table.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Title & Company</th>
          <th>Recruiter</th>
          <th>Applicants</th>
          <th>Status</th>
          <th>Moderate</th>
        </tr>
      </thead>
      <tbody>
        ${res.data.jobs.map(j => `
          <tr>
            <td><strong>${escapeHtml(j.title)}</strong><br><small>${escapeHtml(j.company_name || 'N/A')}</small></td>
            <td>${escapeHtml(j.recruiter_email || 'N/A')}</td>
            <td>${j.applications_count}</td>
            <td><span class="status-badge ${j.status === 'Open' ? 'status-selected' : 'status-rejected'}">${j.status}</span></td>
            <td>
              <button type="button" class="btn secondary" style="padding:4px 8px; font-size:0.8rem;" onclick="moderateAdminJob(${j.id}, '${j.status}')">
                ${j.status === 'Open' ? 'Close/Flag' : 'Reopen'}
              </button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function moderateAdminJob(jobId, currentStatus) {
  const newStatus = currentStatus === 'Open' ? 'Closed' : 'Open';
  const res = await apiFetch(`/api/admin/jobs/${jobId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });

  if (res.ok) {
    showToast(res.data.message, 'success');
    loadAdminJobs();
  }
}

async function loadAdminLogs() {
  const res = await apiFetch('/api/admin/audit-logs');
  if (!res.ok) return;

  const table = document.getElementById('adminLogsTable');
  const logs = res.data.logs || [];
  table.innerHTML = logs.length === 0 ? `<div style="padding:20px;"><p>No audit logs recorded yet.</p></div>` : `
    <table class="data-table">
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Action</th>
          <th>Actor</th>
          <th>Target</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        ${logs.map(l => `
          <tr>
            <td><small>${new Date(l.created_at).toLocaleString()}</small></td>
            <td><code>${escapeHtml(l.action)}</code></td>
            <td>${escapeHtml(l.actor_email || 'System')}</td>
            <td>${escapeHtml(l.target_type)} #${l.target_id || ''}</td>
            <td>${escapeHtml(l.details || '')}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// ============================================================
// UTILITIES
// ============================================================
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('hidden');
}

function getInitials(name) {
  if (!name) return 'JB';
  const parts = name.trim().split(' ');
  return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}