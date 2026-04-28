/** App initialization — loaded last after all components */

// Sidebar click delegation
document.getElementById('sidebar').addEventListener('click', (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  if (li.classList.contains('nav-back')) {
    setProject(null);
    return;
  }
  if (li.dataset.section) {
    navigate(li.dataset.section);
  } else if (li.dataset.project) {
    setProject(li.dataset.project);
  } else if (li.classList.contains('nav-create')) {
    if (typeof openProjectModal === 'function') openProjectModal();
  }
});

// Right-click context menu on sidebar projects
document.getElementById('sidebar').addEventListener('contextmenu', (e) => {
  const li = e.target.closest('li[data-project]');
  if (!li) return;
  e.preventDefault();
  const menu = document.getElementById('context-menu');
  menu.style.display = 'block';
  menu.style.left = e.pageX + 'px';
  menu.style.top = e.pageY + 'px';
  menu.dataset.projectName = li.dataset.project;
});

// Close context menu on click elsewhere
document.addEventListener('click', (e) => {
  const menu = document.getElementById('context-menu');
  if (!e.target.closest('#context-menu')) {
    menu.style.display = 'none';
  }
});

// Context menu action: delete project
document.getElementById('context-menu').addEventListener('click', (e) => {
  const item = e.target.closest('.context-menu-item');
  if (!item) return;
  const menu = document.getElementById('context-menu');
  const projectName = menu.dataset.projectName;
  menu.style.display = 'none';
  if (item.dataset.action === 'delete-project' && projectName) {
    if (confirm(`确定要删除项目「${projectName}」吗？此操作不可撤销。`)) {
      if (typeof deleteProject === 'function') deleteProject(projectName);
    }
  }
});

// Click project indicator to return to project list
document.getElementById('project-indicator').addEventListener('click', () => {
  if (AppState.currentProject) {
    setProject(null);
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
