// --- State ---
const state = {
  lessons: [],
  projects: [],
  currentLevel: null,
  currentTier: 1,
  currentProject: null,
  currentStep: 0,
  accumulatedCode: '',
  stepCompleted: false,
  progress: {},  // { projectId: { stepsCompleted: Set } }
};

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
  loadProgressFromStorage();
  await loadLessons();
  renderSidebar();
  showWelcome();
});

// --- Data Loading ---
async function loadLessons() {
  try {
    state.lessons = await api.getLessons();
  } catch (e) {
    console.error('Failed to load lessons:', e);
  }
}

async function loadProjects(levelId, tier) {
  try {
    state.projects = await api.getProjects(levelId, tier);
  } catch (e) {
    console.error('Failed to load projects:', e);
    state.projects = [];
  }
}

async function loadProject(projectId) {
  try {
    state.currentProject = await api.getProject(projectId);
    state.currentStep = findFirstIncompleteStep();
    state.accumulatedCode = buildAccumulatedCode();
    state.stepCompleted = false;
    renderProject();
  } catch (e) {
    console.error('Failed to load project:', e);
  }
}

// --- Sidebar ---
function renderSidebar() {
  const sidebar = document.getElementById('sidebar-levels');
  sidebar.innerHTML = '';

  state.lessons.forEach(lesson => {
    const item = document.createElement('div');
    item.className = 'level-item' + (state.currentLevel === lesson.id ? ' active' : '');
    item.innerHTML = `<span class="level-num">${String(lesson.id).padStart(2, '0')}</span>${lesson.name}`;
    item.addEventListener('click', () => selectLevel(lesson.id));
    sidebar.appendChild(item);
  });
}

async function selectLevel(levelId) {
  state.currentLevel = levelId;
  renderSidebar();
  await loadProjects(levelId, null);
  renderProjectList();
}

function renderTiers() {
  const container = document.getElementById('tier-selector');
  container.innerHTML = '';

  const tierNames = { 1: 'Basic', 2: 'Intermediate', 3: 'Capstone' };

  [1, 2, 3].forEach(tier => {
    const btn = document.createElement('button');
    btn.className = 'tier-btn' + (state.currentTier === tier ? ' active' : '');
    btn.textContent = tierNames[tier];

    const unlocked = isTierUnlocked(state.currentLevel, tier);
    if (!unlocked) btn.classList.add('locked');

    btn.addEventListener('click', async () => {
      if (!unlocked) return;
      state.currentTier = tier;
      await loadProjects(state.currentLevel, tier);
      renderTiers();
      renderProjectList();
    });

    container.appendChild(btn);
  });
}

function renderProjectList() {
  const container = document.getElementById('project-list');
  container.innerHTML = '';

  if (!state.projects.length) {
    container.innerHTML = '<div class="project-item" style="color: var(--text-dim)">No projects yet</div>';
    return;
  }

  const tierNames = { 1: 'Basic', 2: 'Intermediate', 3: 'Capstone' };
  let lastTier = null;

  state.projects.forEach(p => {
    if (p.tier !== lastTier) {
      lastTier = p.tier;
      const label = document.createElement('div');
      label.className = 'sidebar-section';
      label.innerHTML = `<div class="sidebar-label">${tierNames[p.tier] || 'Tier ' + p.tier}</div>`;
      container.appendChild(label);
    }

    const item = document.createElement('div');
    const isActive = state.currentProject && state.currentProject.id === p.id;
    const isComplete = isProjectComplete(p.id);
    item.className = 'project-item' + (isActive ? ' active' : '');
    item.innerHTML = `
      ${isComplete ? '<span style="color: var(--success)">✓</span> ' : ''}${p.name}
      <div class="project-meta">${p.total_lines} lines · ~${p.estimated_minutes}min</div>
    `;
    item.addEventListener('click', () => loadProject(p.id));
    container.appendChild(item);
  });

  // Generate button
  if (state.currentLevel) {
    const genDiv = document.createElement('div');
    genDiv.style.padding = '12px 16px';
    genDiv.innerHTML = `
      <button class="btn btn-run" id="btn-generate" onclick="showGenerateDialog()" style="width:100%; font-size:10px;">
        + Generate Project
      </button>
    `;
    container.appendChild(genDiv);
  }
}

// --- Project Rendering ---
function showWelcome() {
  const main = document.getElementById('main-content');
  main.innerHTML = `
    <div class="welcome-screen">
      <div class="ascii-art">
 _____ _____ _____ _____
|     |     |     |     |
| M   | I   | M   | O   |
|_____|_____|_____|_____|
      </div>
      <p>Python Learning Companion</p>
      <p style="color: var(--text-dim); font-size: 11px;">Select a level from the sidebar to begin your journey.<br>
      Work through projects step by step, building real programs.</p>
    </div>
  `;
}

function renderProject() {
  const proj = state.currentProject;
  if (!proj) return;

  const step = proj.steps[state.currentStep];
  const main = document.getElementById('main-content');

  main.innerHTML = `
    <div class="instruction-panel">
      <div class="project-title">${proj.name}</div>
      <div class="project-desc">${proj.description}</div>
      <div class="step-header">
        <span class="step-badge">STEP ${step.step_num}</span>
        <span class="step-progress">${step.step_num} / ${proj.steps.length}</span>
        <div class="step-dots" id="step-dots"></div>
      </div>
      <div class="step-instruction">${step.instruction}</div>
      <button class="hint-toggle" onclick="toggleHint()">▸ Show hint</button>
      <div class="hint-text" id="hint-text">${step.hint}</div>
      <button class="hint-toggle" onclick="toggleSolution()">▸ Show solution</button>
      <div class="hint-text" id="solution-text"><code>${escapeHtml(step.solution)}</code></div>
    </div>
    <div class="editor-area">
      <div class="accumulated-code" id="accumulated-code">${state.accumulatedCode ? `<span class="accumulated-label">completed code ↓</span>\n${escapeHtml(state.accumulatedCode)}` : ''}</div>
      <div class="code-input-wrapper">
        <textarea class="code-input" id="code-input"
          placeholder="Type your Python code here..."
          spellcheck="false"
          rows="${Math.max(step.expected_lines + 1, 4)}"
        ></textarea>
      </div>
    </div>
    <div class="output-panel">
      <div class="output-header">
        <span class="output-title">Output</span>
        <div class="action-buttons">
          <button class="btn btn-reset" onclick="resetStep()">Clear</button>
          <button class="btn btn-run" id="btn-run" onclick="runCode()">▶ Run</button>
          <button class="btn btn-next" id="btn-next" onclick="nextStep()">Next →</button>
        </div>
      </div>
      <div class="output-content" id="output-content">
        <span style="color: var(--text-dim)">Output will appear here after you run your code...</span>
      </div>
      <div class="feedback" id="feedback" style="display:none"></div>
    </div>
    <div class="project-complete" id="project-complete">
      <div class="complete-card">
        <h2>Project Complete!</h2>
        <p>You've finished "${proj.name}"</p>
        <button class="btn btn-run" onclick="closeComplete()">Continue</button>
      </div>
    </div>
  `;

  renderStepDots();
  setupCodeInput();
}

function renderStepDots() {
  const container = document.getElementById('step-dots');
  if (!container || !state.currentProject) return;

  container.innerHTML = '';
  state.currentProject.steps.forEach((s, i) => {
    const dot = document.createElement('div');
    dot.className = 'step-dot';
    if (isStepCompleted(state.currentProject.id, s.step_num)) dot.classList.add('completed');
    if (i === state.currentStep) dot.classList.add('current');
    container.appendChild(dot);
  });
}

function setupCodeInput() {
  const input = document.getElementById('code-input');
  if (!input) return;

  // Tab key support
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = input.selectionStart;
      const end = input.selectionEnd;
      input.value = input.value.substring(0, start) + '    ' + input.value.substring(end);
      input.selectionStart = input.selectionEnd = start + 4;
    }
    // Ctrl/Cmd+Enter to run
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      runCode();
    }
  });

  input.focus();
}

// --- Code Execution ---
async function runCode() {
  const btn = document.getElementById('btn-run');
  const output = document.getElementById('output-content');
  const feedback = document.getElementById('feedback');
  const code = document.getElementById('code-input').value;

  if (!code.trim()) {
    output.textContent = '';
    output.className = 'output-content error';
    feedback.textContent = 'Write some code first!';
    feedback.className = 'feedback mismatch';
    feedback.style.display = 'block';
    return;
  }

  btn.classList.add('loading');
  btn.textContent = '⟳ Running...';

  try {
    const step = state.currentProject.steps[state.currentStep];
    const result = await api.execute(
      state.currentProject.id,
      step.step_num,
      code,
      state.accumulatedCode
    );

    output.textContent = result.output || '(no output)';
    output.className = 'output-content' + (result.success ? '' : ' error');

    if (result.error) {
      output.textContent = result.output ? result.output + '\n\n' + result.error : result.error;
    }

    feedback.textContent = result.feedback;
    feedback.className = 'feedback ' + (result.match ? 'match' : 'mismatch');
    feedback.style.display = 'block';

    if (result.match) {
      state.stepCompleted = true;
      markStepComplete(state.currentProject.id, step.step_num, code);
      document.getElementById('btn-next').classList.add('visible');

      // Auto-advance if last step
      if (state.currentStep >= state.currentProject.steps.length - 1) {
        showProjectComplete();
      }
    }
  } catch (e) {
    output.textContent = 'Failed to execute: ' + e.message;
    output.className = 'output-content error';
    feedback.style.display = 'none';
  } finally {
    btn.classList.remove('loading');
    btn.textContent = '▶ Run';
  }
}

function nextStep() {
  if (state.currentStep >= state.currentProject.steps.length - 1) {
    showProjectComplete();
    return;
  }

  // Add current code to accumulated
  const code = document.getElementById('code-input').value;
  state.accumulatedCode = state.accumulatedCode
    ? state.accumulatedCode + '\n' + code
    : code;

  state.currentStep++;
  state.stepCompleted = false;
  renderProject();
}

function resetStep() {
  const input = document.getElementById('code-input');
  if (input) input.value = '';
  const output = document.getElementById('output-content');
  output.textContent = '';
  output.className = 'output-content';
  const feedback = document.getElementById('feedback');
  feedback.style.display = 'none';
  document.getElementById('btn-next').classList.remove('visible');
  state.stepCompleted = false;
}

// --- Hints & Solution ---
function toggleHint() {
  const hint = document.getElementById('hint-text');
  const btns = document.querySelectorAll('.hint-toggle');
  hint.classList.toggle('visible');
  btns[0].textContent = hint.classList.contains('visible') ? '▾ Hide hint' : '▸ Show hint';
}

function toggleSolution() {
  const sol = document.getElementById('solution-text');
  const btns = document.querySelectorAll('.hint-toggle');
  sol.classList.toggle('visible');
  btns[1].textContent = sol.classList.contains('visible') ? '▾ Hide solution' : '▸ Show solution';
}

// --- Progress ---
function loadProgressFromStorage() {
  try {
    const saved = localStorage.getItem('mimo_progress');
    if (saved) {
      const data = JSON.parse(saved);
      // Convert arrays back to Sets
      for (const [pid, info] of Object.entries(data)) {
        state.progress[pid] = { stepsCompleted: new Set(info.stepsCompleted) };
      }
    }
  } catch (e) {
    console.error('Failed to load progress:', e);
  }
}

function saveProgressToStorage() {
  const data = {};
  for (const [pid, info] of Object.entries(state.progress)) {
    data[pid] = { stepsCompleted: Array.from(info.stepsCompleted) };
  }
  localStorage.setItem('mimo_progress', JSON.stringify(data));
}

function markStepComplete(projectId, stepNum, code) {
  if (!state.progress[projectId]) {
    state.progress[projectId] = { stepsCompleted: new Set() };
  }
  state.progress[projectId].stepsCompleted.add(stepNum);
  saveProgressToStorage();

  // Also save to backend
  api.markComplete(projectId, stepNum, code).catch(e =>
    console.error('Failed to save progress to server:', e)
  );

  renderStepDots();
  renderProjectList();
}

function isStepCompleted(projectId, stepNum) {
  return state.progress[projectId]?.stepsCompleted?.has(stepNum) || false;
}

function isProjectComplete(projectId) {
  const proj = state.projects.find(p => p.id === projectId);
  if (!proj || !state.progress[projectId]) return false;
  // We only know total_lines from list, not step count. Check what we have.
  return state.progress[projectId].stepsCompleted.size >= (proj.steps?.length || 5);
}

function findFirstIncompleteStep() {
  if (!state.currentProject) return 0;
  for (let i = 0; i < state.currentProject.steps.length; i++) {
    if (!isStepCompleted(state.currentProject.id, state.currentProject.steps[i].step_num)) {
      return i;
    }
  }
  return 0;
}

function buildAccumulatedCode() {
  if (!state.currentProject) return '';

  const lines = [];
  for (let i = 0; i < state.currentStep; i++) {
    const step = state.currentProject.steps[i];
    if (isStepCompleted(state.currentProject.id, step.step_num)) {
      lines.push(step.solution);
    }
  }
  return lines.join('\n');
}

function isTierUnlocked(levelId, tier) {
  if (levelId === 1 && tier === 1) return true;
  // Simplified: check localStorage progress
  // In production, this would call the backend
  if (tier === 1) {
    // Need previous level complete
    return isAnyProjectComplete(levelId - 1);
  }
  // Need previous tier at same level complete
  return isAnyTierComplete(levelId, tier - 1);
}

function isAnyProjectComplete(levelId) {
  for (const [pid, info] of Object.entries(state.progress)) {
    if (pid.startsWith(`level${levelId}_`) && info.stepsCompleted.size >= 3) {
      return true;
    }
  }
  return false;
}

function isAnyTierComplete(levelId, tier) {
  const tierNames = { 1: 'basic', 2: 'intermediate', 3: 'capstone' };
  const prefix = `level${levelId}_${tierNames[tier]}`;
  for (const [pid, info] of Object.entries(state.progress)) {
    if (pid.startsWith(prefix) && info.stepsCompleted.size >= 3) {
      return true;
    }
  }
  return false;
}

// --- Project Complete ---
function showProjectComplete() {
  const overlay = document.getElementById('project-complete');
  if (overlay) overlay.classList.add('visible');
}

function closeComplete() {
  const overlay = document.getElementById('project-complete');
  if (overlay) overlay.classList.remove('visible');
}

// --- Project Generation ---
function showGenerateDialog() {
  // Remove existing dialog if any
  const existing = document.getElementById('generate-dialog');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'generate-dialog';
  overlay.className = 'project-complete visible';
  overlay.innerHTML = `
    <div class="complete-card" style="text-align:left; min-width:350px;">
      <h2 style="margin-bottom:16px;">Generate New Project</h2>
      <div style="margin-bottom:12px;">
        <label style="font-size:11px; color:var(--text-dim); display:block; margin-bottom:4px;">LEVEL</label>
        <div style="font-size:13px; color:var(--accent);">
          Level ${state.currentLevel} — ${state.lessons.find(l => l.id === state.currentLevel)?.name || ''}
        </div>
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:11px; color:var(--text-dim); display:block; margin-bottom:4px;">TIER</label>
        <select id="gen-tier" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border); padding:6px 10px; font-family:inherit; font-size:12px; width:100%;">
          <option value="1">Basic (15-20 lines, 4-6 steps)</option>
          <option value="2">Intermediate (20-30 lines, 6-8 steps)</option>
          <option value="3">Capstone (30-70 lines, 8-15 steps)</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <label style="font-size:11px; color:var(--text-dim); display:block; margin-bottom:4px;">THEME (optional)</label>
        <input id="gen-theme" type="text" placeholder="e.g. space exploration, cooking, sports..."
          style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border); padding:6px 10px; font-family:inherit; font-size:12px; width:100%; box-sizing:border-box;">
      </div>
      <div style="display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn btn-reset" onclick="document.getElementById('generate-dialog').remove()">Cancel</button>
        <button class="btn btn-run" id="btn-do-generate" onclick="doGenerate()">Generate</button>
      </div>
      <div id="gen-status" style="margin-top:12px; font-size:11px; color:var(--text-dim); display:none;"></div>
    </div>
  `;
  document.body.appendChild(overlay);
}

async function doGenerate() {
  const tier = parseInt(document.getElementById('gen-tier').value);
  const theme = document.getElementById('gen-theme').value.trim() || null;
  const btn = document.getElementById('btn-do-generate');
  const status = document.getElementById('gen-status');

  btn.classList.add('loading');
  btn.textContent = 'Generating...';
  status.style.display = 'block';
  status.textContent = 'Asking Claude to create a project... this may take a moment.';

  try {
    const project = await api.generateProject(state.currentLevel, tier, theme);
    status.style.color = 'var(--success)';
    status.textContent = `Created: ${project.name}`;

    // Reload project list and open the new project
    await loadProjects(state.currentLevel, null);
    renderProjectList();

    // Close dialog after a beat
    setTimeout(() => {
      document.getElementById('generate-dialog')?.remove();
      loadProject(project.id);
    }, 800);
  } catch (e) {
    // Try to get detail from response body
    let msg = e.message;
    try {
      const errData = await e.response?.json?.();
      if (errData?.detail) msg = errData.detail;
    } catch (_) {}

    const isCodeError = msg.includes('invalid code');
    status.style.color = 'var(--error)';
    status.textContent = isCodeError
      ? 'Generated code had syntax errors. Click Generate to try again.'
      : `Failed: ${msg}`;
    btn.classList.remove('loading');
    btn.textContent = isCodeError ? 'Retry' : 'Generate';
  }
}

// --- Utilities ---
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
