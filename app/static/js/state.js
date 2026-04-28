/** Global application state — loaded first so all components can access it */
const AppState = {
  currentProject: null,
  currentSection: 'projects',
  apiConfigured: false,
};
const $content = document.getElementById('content');

function navigate(section) {
  // Disconnect active SSE clients before destroying DOM
  if (typeof chapterSSE !== 'undefined' && chapterSSE) { chapterSSE.disconnect(); chapterSSE = null; }
  if (typeof outlineStreamingClient !== 'undefined' && outlineStreamingClient) { outlineStreamingClient.disconnect(); outlineStreamingClient = null; }
  if (typeof settingsChatClient !== 'undefined' && settingsChatClient) { settingsChatClient.disconnect(); settingsChatClient = null; }

  AppState.currentSection = section;
  document.querySelectorAll('#sidebar li[data-section]').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });
  // Keep the selected project highlighted when navigating within a project
  if (section !== 'projects') {
    document.querySelectorAll('#nav-projects li[data-project]').forEach(el => {
      el.classList.toggle('active', el.dataset.project === AppState.currentProject);
    });
  }
  renderContent(section);
}

function setProject(name) {
  AppState.currentProject = name;
  const indicator = document.getElementById('project-indicator');
  if (indicator) indicator.textContent = name ? '当前项目：' + name : '未选择项目';
  if (indicator) indicator.style.cursor = name ? 'pointer' : 'default';
  if (indicator) indicator.title = name ? '点击返回项目列表' : '';
  const nav = document.getElementById('sidebar-project-nav');
  if (nav) nav.style.display = name ? 'block' : 'none';

  // Highlight selected project in sidebar
  document.querySelectorAll('#nav-projects li[data-project]').forEach(el => {
    el.classList.toggle('active', el.dataset.project === name);
  });

  if (name) {
    navigate('dashboard');
  } else {
    navigate('projects');
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
    case 'chapters': if (typeof renderChapterManager === 'function') renderChapterManager(); break;
    case 'foreshadowing': if (typeof renderForeshadowing === 'function') renderForeshadowing(); break;
    case 'query': if (typeof renderQuerySection === 'function') renderQuerySection(); break;
    default: $content.innerHTML = '<div class="empty-state"><h3>未知页面</h3></div>';
  }
}
