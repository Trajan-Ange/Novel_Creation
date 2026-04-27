/** Global application state — loaded first so all components can access it */
const AppState = {
  currentProject: null,
  currentSection: 'projects',
  apiConfigured: false,
};
const $content = document.getElementById('content');

function navigate(section) {
  AppState.currentSection = section;
  document.querySelectorAll('#sidebar li[data-section]').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });
  document.querySelectorAll('#nav-projects li').forEach(el => {
    el.classList.toggle('active', false);
  });
  renderContent(section);
}

function setProject(name) {
  AppState.currentProject = name;
  const indicator = document.getElementById('project-indicator');
  if (indicator) indicator.textContent = name ? '当前项目：' + name : '未选择项目';
  const nav = document.getElementById('sidebar-project-nav');
  if (nav) nav.style.display = name ? 'block' : 'none';
  if (name) {
    navigate('dashboard');
  }
}

function renderContent(section) {
  if (!AppState.currentProject && section !== 'projects') {
    $content.innerHTML = '<div class="empty-state"><h3>请先选择或创建项目</h3><p>在左侧边栏选择一个项目，或创建新项目</p></div>';
    return;
  }

  switch (section) {
    case 'projects': if (typeof renderProjectList === 'function') renderProjectList(); break;
    case 'dashboard': if (typeof renderDashboard === 'function') renderDashboard(); break;
    case 'settings': if (typeof renderSettingsEditor === 'function') renderSettingsEditor(); break;
    case 'outline': if (typeof renderOutlineTree === 'function') renderOutlineTree(); break;
    case 'writing': if (typeof renderChapterWriter === 'function') renderChapterWriter(); break;
    case 'foreshadowing': if (typeof renderForeshadowing === 'function') renderForeshadowing(); break;
    case 'query': if (typeof renderQuerySection === 'function') renderQuerySection(); break;
    default: $content.innerHTML = '<div class="empty-state"><h3>未知页面</h3></div>';
  }
}
