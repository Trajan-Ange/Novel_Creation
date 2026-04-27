/** API client — all backend fetch calls */
const API = {
  async get(url) {
    const res = await fetch(url);
    return res.json();
  },

  async post(url, body = {}) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  async put(url, body = {}) {
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  async del(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return res.json();
  },

  // ── Config ──────────────────────────────────────
  config: {
    get: () => API.get('/api/config'),
    save: (cfg) => API.put('/api/config', cfg),
    test: () => API.post('/api/config/test'),
  },

  // ── Projects ────────────────────────────────────
  projects: {
    list: () => API.get('/api/projects'),
    create: (name, description, type, source) =>
      API.post('/api/projects', { name, description, type, source }),
    delete: (name) => API.del(`/api/projects/${encodeURIComponent(name)}`),
  },

  // ── Settings ────────────────────────────────────
  settings: {
    all: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/all`),
    world: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/world`),
    generateWorld: (project, instruction) =>
      API.post(`/api/settings/${encodeURIComponent(project)}/world/generate`, { project, instruction }),
    characters: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/characters`),
    character: (project, name) =>
      API.get(`/api/settings/${encodeURIComponent(project)}/characters/${encodeURIComponent(name)}`),
    generateCharacter: (project, instruction) =>
      API.post(`/api/settings/${encodeURIComponent(project)}/characters/generate`, { project, instruction }),
    deleteCharacter: (project, name) =>
      API.del(`/api/settings/${encodeURIComponent(project)}/characters/${encodeURIComponent(name)}`),
    timeline: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/timeline`),
    generateTimeline: (project, instruction) =>
      API.post(`/api/settings/${encodeURIComponent(project)}/timeline/generate`, { project, instruction }),
    relationship: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/relationship`),
    generateRelationship: (project, instruction) =>
      API.post(`/api/settings/${encodeURIComponent(project)}/relationship/generate`, { project, instruction }),
    styleGuide: (project) => API.get(`/api/settings/${encodeURIComponent(project)}/style-guide`),
    generateStyleGuide: (project, instruction) =>
      API.post(`/api/settings/${encodeURIComponent(project)}/style-guide/generate`, { project, instruction }),
    saveWorld: (project, content) =>
      API.put(`/api/settings/${encodeURIComponent(project)}/world`, { project, content }),
    saveTimeline: (project, background, story) =>
      API.put(`/api/settings/${encodeURIComponent(project)}/timeline`, { project, background, story }),
    saveCharacter: (project, name, content) =>
      API.put(`/api/settings/${encodeURIComponent(project)}/characters/${encodeURIComponent(name)}`, { project, content }),
    saveRelationship: (project, content) =>
      API.put(`/api/settings/${encodeURIComponent(project)}/relationship`, { project, content }),
    saveStyleGuide: (project, content) =>
      API.put(`/api/settings/${encodeURIComponent(project)}/style-guide`, { project, content }),
  },

  // ── Outline ─────────────────────────────────────
  outline: {
    book: (project) => API.get(`/api/outline/${encodeURIComponent(project)}/book`),
    saveBook: (project, content) => API.put(`/api/outline/${encodeURIComponent(project)}/book`, { project, content }),
    generateBook: (project, instruction = '') =>
      API.post(`/api/outline/${encodeURIComponent(project)}/book/generate`, { project, instruction }),
    volume: (project, vol) => API.get(`/api/outline/${encodeURIComponent(project)}/volume/${vol}`),
    saveVolume: (project, vol, content) => API.put(`/api/outline/${encodeURIComponent(project)}/volume/${vol}`, { project, content }),
    generateVolume: (project, vol, instruction = '') =>
      API.post(`/api/outline/${encodeURIComponent(project)}/volume/${vol}/generate`, { project, volume: vol, instruction }),
    chapter: (project, vol, ch) =>
      API.get(`/api/outline/${encodeURIComponent(project)}/volume/${vol}/chapter/${ch}`),
    saveChapter: (project, vol, ch, content) =>
      API.put(`/api/outline/${encodeURIComponent(project)}/volume/${vol}/chapter/${ch}`, { project, content }),
    generateChapter: (project, vol, ch, instruction = '') =>
      API.post(`/api/outline/${encodeURIComponent(project)}/volume/${vol}/chapter/${ch}/generate`, { project, volume: vol, chapter: ch, instruction }),
    volumes: (project) => API.get(`/api/outline/${encodeURIComponent(project)}/volumes`),
    chapterList: (project, vol) => API.get(`/api/outline/${encodeURIComponent(project)}/volume/${vol}/chapters`),
  },

  // ── Chapters ────────────────────────────────────
  chapters: {
    list: (project, vol) => API.get(`/api/chapters/${encodeURIComponent(project)}/volume/${vol}`),
    get: (project, vol, ch) =>
      API.get(`/api/chapters/${encodeURIComponent(project)}/volume/${vol}/chapter/${ch}`),
    foreshadowing: (project) => API.get(`/api/chapters/${encodeURIComponent(project)}/foreshadowing`),
    query: (project, query) =>
      API.post('/api/chapters/query', { project, query }),
  },

  // ── Sync ────────────────────────────────────────
  sync: {
    trigger: (project, volume, chapter) =>
      API.post(`/api/sync/${encodeURIComponent(project)}/trigger`, { project, volume, chapter }),
    loreExtract: (project, sourceName, scope = [], customRequirements = '') =>
      API.post(`/api/sync/${encodeURIComponent(project)}/lore-extract`, { project, source_name: sourceName, scope, custom_requirements: customRequirements }),
  },
};
