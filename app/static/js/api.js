/** API client — all backend fetch calls */

/**
 * Wraps an async API call with standardized error handling.
 * Eliminates 28+ repetitive try/catch blocks across component files.
 *
 * @param {Function} fn - async function that performs the API call
 * @param {string} errorMsg - human-readable error prefix
 * @param {Function} [onError] - optional callback receiving the error message
 * @returns {Promise<{success:boolean, data?:any, error?:string}>}
 */
async function safeApiCall(fn, errorMsg, onError) {
  try {
    const result = await fn();
    if (result && result.success === false) {
      const msg = `${errorMsg}: ${result.error}`;
      if (onError) onError(msg);
      return { success: false, error: result.error };
    }
    return { success: true, data: result };
  } catch (e) {
    const msg = `${errorMsg}: ${e.message || e}`;
    if (onError) onError(msg);
    return { success: false, error: msg };
  }
}

const API = {
  async _request(method, url, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
    } else {
      delete opts.headers;
    }
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const errBody = data?.detail || data;
      return { success: false, error: errBody?.error || `HTTP ${res.status}` };
    }
    return data;
  },

  async get(url) {
    return this._request('GET', url);
  },

  async post(url, body = {}) {
    return this._request('POST', url, body);
  },

  async put(url, body = {}) {
    return this._request('PUT', url, body);
  },

  async del(url) {
    return this._request('DELETE', url);
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
    save: (project, vol, ch, content, outline) =>
      API.put(`/api/chapters/${encodeURIComponent(project)}/volume/${vol}/chapter/${ch}`, { project, content, outline }),
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
    loreApply: (project, worldSetting, characters, timeline) =>
      API.post(`/api/sync/${encodeURIComponent(project)}/lore-apply`, { project, world_setting: worldSetting, characters, timeline }),
  },
};
