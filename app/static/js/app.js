/** App initialization — loaded last after all components */
document.getElementById('sidebar').addEventListener('click', (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  if (li.dataset.section) {
    navigate(li.dataset.section);
  } else if (li.dataset.project) {
    setProject(li.dataset.project);
  } else if (li.classList.contains('nav-create')) {
    if (typeof openProjectModal === 'function') openProjectModal();
  }
});

document.getElementById('btn-config').addEventListener('click', () => {
  if (typeof openConfig === 'function') openConfig();
});

(async function init() {
  try {
    const cfg = await API.config.get();
    AppState.apiConfigured = cfg.is_configured;
  } catch (e) { /* ignore */ }
  navigate('projects');
})();
