/** Global application state — loaded first so all components can access it */
const AppState = {
  currentProject: null,
  currentSection: 'projects',
  apiConfigured: false,
};
const $content = document.getElementById('content');

// Theme management
const THEMES = ['light', 'dark', 'warm', 'forest'];
const THEME_LABELS = { light: '亮色', dark: '暗色', warm: '暖色', forest: '森林' };

function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('novel-theme', theme);
}

function cycleTheme() {
  const current = getCurrentTheme();
  const idx = THEMES.indexOf(current);
  const next = THEMES[(idx + 1) % THEMES.length];
  setTheme(next);
  return next;
}

function setDensity(density) {
  document.documentElement.setAttribute('data-density', density);
  localStorage.setItem('novel-density', density);
}

function getDensity() {
  return document.documentElement.getAttribute('data-density') || 'default';
}

function setFontScale(scale) {
  document.documentElement.setAttribute('data-font-scale', scale);
  localStorage.setItem('novel-font-scale', scale);
}

function getFontScale() {
  return document.documentElement.getAttribute('data-font-scale') || 'default';
}

const _SSE_VARS = ['chapterSSE', 'outlineStreamingClient', 'settingsChatClient', 'wizardSSEClient'];

function hasActiveSSE() {
  return _SSE_VARS.some(name => {
    try {
      const client = window[name];
      if (!client) return false;
      if (typeof client._abortController === 'undefined') return false;
      return client._abortController && !client._abortController.signal.aborted;
    } catch (e) { return false; }
  });
}

function disconnectAllSSE() {
  _SSE_VARS.forEach(name => {
    try {
      const client = window[name];
      if (client) { client.disconnect(); window[name] = null; }
    } catch (e) { /* ignore */ }
  });
}

async function navigate(section, skipSseCheck) {
  if (!skipSseCheck && hasActiveSSE()) {
    const proceed = await Dialog.confirm('当前有正在进行的 AI 生成任务，确定要离开吗？');
    if (!proceed) return;
  }

  disconnectAllSSE();

  AppState.currentSection = section;
  document.querySelectorAll('#sidebar li[data-section]').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });
  if (section !== 'projects') {
    document.querySelectorAll('#nav-projects li[data-project]').forEach(el => {
      el.classList.toggle('active', el.dataset.project === AppState.currentProject);
    });
  }

  // Update browser history
  const url = AppState.currentProject
    ? `#/${encodeURIComponent(AppState.currentProject)}/${section}`
    : `#/${section}`;
  const state = { project: AppState.currentProject, section };
  if (skipSseCheck) {
    history.replaceState(state, '', url);
  } else {
    history.pushState(state, '', url);
  }

  renderContent(section);
}

function setProject(name) {
  if (name && AppState.currentProject && name !== AppState.currentProject && hasActiveSSE()) {
    Dialog.confirm('当前有正在进行的 AI 生成任务，确定要切换项目吗？').then(proceed => {
      if (proceed) doSetProject(name);
    });
    return;
  }
  doSetProject(name);
}

function doSetProject(name) {
  AppState.currentProject = name;
  const indicator = document.getElementById('project-indicator');
  if (indicator) indicator.textContent = name ? '当前项目：' + name : '未选择项目';
  if (indicator) indicator.style.cursor = name ? 'pointer' : 'default';
  if (indicator) indicator.title = name ? '点击返回项目列表' : '';
  const nav = document.getElementById('sidebar-project-nav');
  if (nav) nav.style.display = name ? 'block' : 'none';

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

// ── Browser history support ──────────────────────────────────

function restoreFromHash() {
  const hash = window.location.hash.slice(1); // Remove leading #
  if (!hash) return false;
  const parts = hash.split('/').filter(Boolean);
  if (parts.length === 0) return false;

  // Check if first part is a project name or a section name
  const sections = ['projects', 'dashboard', 'settings', 'outline', 'writing', 'chapters', 'foreshadowing', 'query'];
  if (sections.includes(parts[0])) {
    navigate(parts[0], true);
    return true;
  }

  // First part might be a project name
  const project = decodeURIComponent(parts[0]);
  const section = parts[1] || 'dashboard';
  if (sections.includes(section)) {
    doSetProject(project);
    navigate(section, true);
    return true;
  }

  navigate('projects', true);
  return true;
}

window.addEventListener('popstate', (event) => {
  if (event.state && event.state.section) {
    if (event.state.project) {
      doSetProject(event.state.project);
    }
    navigate(event.state.section, true);
  }
});

window.addEventListener('beforeunload', (event) => {
  if (hasActiveSSE()) {
    event.preventDefault();
    event.returnValue = '';
  }
});
