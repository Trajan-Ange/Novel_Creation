/** Central namespace for the Novel Creation app.
 *
 * All public component functions are also accessible via window.NovelApp.*,
 * reducing the risk of 109 global identifiers colliding with browser built-ins
 * or third-party scripts. Components still define their functions globally
 * for internal cross-references; the namespace is a façade for external use.
 */
window.NovelApp = {
  // State management (state.js)
  State: window.AppState,
  navigate: (section) => { if (typeof navigate === 'function') navigate(section); },
  setProject: (name) => { if (typeof setProject === 'function') setProject(name); },

  // API (api.js)
  API: window.API,
  safeApiCall: (fn, errorMsg, onError) => {
    if (typeof safeApiCall === 'function') return safeApiCall(fn, errorMsg, onError);
    return fn();
  },

  // SSE utilities (utils/sse.js)
  SSEClient: window.SSEClient,
  createSSEConnection: (url, body, handlers) => {
    if (typeof createSSEConnection === 'function') return createSSEConnection(url, body, handlers);
    return null;
  },

  // Component functions — populated as each component loads
  // config-panel.js:  openConfig, closeConfig, saveConfig, testConnection
  // project-list.js: openProjectModal, closeProjectModal, createProject, deleteProject
  // settings-editor.js / settings-chat.js / outline-tree.js
  // chapter-writer.js / chapter-manager.js / foreshadowing.js
};
