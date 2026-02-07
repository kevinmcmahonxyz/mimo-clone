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

  deleteProject(id) {
    return fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' }).then(res => {
      if (!res.ok) throw new Error(`DELETE /projects/${id}: ${res.status}`);
      return res.json();
    });
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
  async generateProject(levelId, tier, theme = null, onStatus = null) {
    const res = await fetch(`${API_BASE}/generate/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level_id: levelId, tier, theme }),
    });

    if (!res.ok) {
      let detail = `POST /generate/project: ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch (_) {}
      throw new Error(detail);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let projectData = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split on double newline (SSE event boundary)
      const parts = buffer.split('\n\n');
      // Last part may be incomplete — keep it in the buffer
      buffer = parts.pop();

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed.startsWith('data: ')) continue;

        const jsonStr = trimmed.slice(6); // strip "data: "
        let event;
        try {
          event = JSON.parse(jsonStr);
        } catch (_) {
          continue;
        }

        if (event.status === 'done') {
          projectData = event.project;
        } else if (event.status === 'error') {
          throw new Error(event.message);
        } else if (onStatus) {
          onStatus(event);
        }
      }
    }

    // Process any remaining buffer
    if (buffer.trim().startsWith('data: ')) {
      try {
        const event = JSON.parse(buffer.trim().slice(6));
        if (event.status === 'done') {
          projectData = event.project;
        } else if (event.status === 'error') {
          throw new Error(event.message);
        }
      } catch (_) {}
    }

    if (!projectData) {
      throw new Error('No project data received from stream');
    }

    return projectData;
  },

  getHint(instruction, code, error = null) {
    return this.post('/generate/hint', {
      instruction,
      code,
      error,
    });
  },
};
