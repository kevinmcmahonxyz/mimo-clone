const API_BASE = '/api/v1';

const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
  },

  async post(path, data) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      let detail = `POST ${path}: ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  },

  // Lessons
  getLessons() {
    return this.get('/lessons');
  },

  getLesson(id) {
    return this.get(`/lessons/${id}`);
  },

  // Projects
  getProjects(level, tier) {
    let query = '';
    const params = [];
    if (level) params.push(`level=${level}`);
    if (tier) params.push(`tier=${tier}`);
    if (params.length) query = '?' + params.join('&');
    return this.get(`/projects${query}`);
  },

  getProject(id) {
    return this.get(`/projects/${id}`);
  },

  // Execution
  execute(projectId, stepNum, code, accumulatedCode) {
    return this.post('/execute', {
      project_id: projectId,
      step_num: stepNum,
      code,
      accumulated_code: accumulatedCode,
    });
  },

  // Progress
  getProgress() {
    return this.get('/progress');
  },

  markComplete(projectId, stepNum, code) {
    return this.post('/progress/complete', {
      project_id: projectId,
      step_num: stepNum,
      code,
    });
  },

  // Generation
  generateProject(levelId, tier, theme = null) {
    return this.post('/generate/project', {
      level_id: levelId,
      tier,
      theme,
    });
  },

  getHint(instruction, code, error = null) {
    return this.post('/generate/hint', {
      instruction,
      code,
      error,
    });
  },
};
