/** Foreshadowing management and memory query */
async function renderForeshadowing() {
  const project = AppState.currentProject;
  $content.innerHTML = `
    <div class="section-header"><h2>伏笔管理</h2></div>
    <div id="fb-content">加载中...</div>
  `;

  try {
    const data = await API.chapters.foreshadowing(project);
    document.getElementById('fb-content').innerHTML = `
      <div class="markdown-content">${data.content ? marked.parse(data.content) : '<div class="empty-state"><p>暂无伏笔记录</p></div>'}</div>
    `;
  } catch (e) {
    document.getElementById('fb-content').innerHTML = '<div class="error-message">加载失败</div>';
  }
}

/** Render memory query section */
async function renderQuerySection() {
  $content.innerHTML = `
    <div class="section-header"><h2>智能查询</h2></div>
    <div class="query-input-area">
      <input type="text" id="query-input" placeholder="输入你想查询的问题，例如：主角在第5章是什么状态？修仙世界的修炼等级有哪些？">
      <button class="btn btn-primary" onclick="submitQuery()">查询</button>
    </div>
    <div id="query-result"></div>
  `;

  document.getElementById('query-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitQuery();
  });
}

async function submitQuery() {
  const input = document.getElementById('query-input');
  const query = input.value.trim();
  if (!query) return;

  const resultEl = document.getElementById('query-result');
  resultEl.innerHTML = '<div class="loading">正在查询...</div>';

  try {
    const result = await API.chapters.query(AppState.currentProject, query);
    if (result.success) {
      resultEl.innerHTML = `
        <div class="query-result">
          <div class="markdown-content">${marked.parse(result.content || '无结果')}</div>
          ${result.sources ? `<div class="sources">来源文件：${result.sources.join(', ')}</div>` : ''}
        </div>
      `;
    } else {
      resultEl.innerHTML = `<div class="error-message">查询失败：${result.error}</div>`;
    }
  } catch (e) {
    resultEl.innerHTML = `<div class="error-message">查询出错</div>`;
  }
}

/** Render dashboard */
async function renderDashboard() {
  const project = AppState.currentProject;

  $content.innerHTML = '<div class="loading">加载项目概览...</div>';

  try {
    const data = await API.settings.all(project);
    const state = data.state || {};
    const settings = data.settings || [];

    let html = `
      <div class="section-header"><h2>项目概览：${project}</h2></div>
      <div class="dashboard-grid">
        <div class="dashboard-card">
          <h4>创作进度</h4>
          <div class="value">第${state.当前进度?.当前卷 || 1}卷 第${state.当前进度?.当前章 || 0}章</div>
          <div class="sub">阶段：${state.阶段 || ''} | 模式：${state.创作模式 || ''}</div>
        </div>
        <div class="dashboard-card">
          <h4>创作类型</h4>
          <div class="value">${state.创作类型 || '原创'}</div>
          <div class="sub">${state.源作品信息 ? '源作品：' + state.源作品信息 : ''}</div>
        </div>
        <div class="dashboard-card">
          <h4>人物数量</h4>
          <div class="value">${settings.filter(s => s.title.startsWith('人物设定')).length}</div>
          <div class="sub">世界设定 / 时间线 / 关系图谱 / 风格指南</div>
        </div>
        <div class="dashboard-card">
          <h4>待回收伏笔</h4>
          <div class="value">${(state.待回收伏笔 || []).length}</div>
          <div class="sub">${(state.待回收伏笔 || []).join(', ') || '无'}</div>
        </div>
        <div class="dashboard-card">
          <h4>最近更新</h4>
          <div class="value" style="font-size:14px">${state.最近更新时间 ? new Date(state.最近更新时间).toLocaleString('zh-CN') : '-'}</div>
        </div>
        <div class="dashboard-card">
          <h4>创作依据版本</h4>
          <div class="sub">${Object.entries(state.创作依据版本 || {}).map(([k,v]) => k+':'+v).join(' / ')}</div>
        </div>
      </div>
    `;

    // Add a quick-actions section
    html += `
      <div style="margin-top:24px">
        <h3 style="margin-bottom:12px">快捷操作</h3>
        <button class="btn btn-primary" onclick="navigate('writing')" style="margin-right:8px">写下一章</button>
        <button class="btn btn-success" onclick="navigateManualWriter()" style="margin-right:8px">手动创作</button>
        <button class="btn btn-secondary" onclick="navigate('settings')" style="margin-right:8px">管理设定</button>
        <button class="btn btn-secondary" onclick="navigate('outline')" style="margin-right:8px">查看大纲</button>
        <button class="btn btn-secondary" onclick="navigate('foreshadowing')">伏笔管理</button>
      </div>
    `;

    $content.innerHTML = html;
  } catch (e) {
    $content.innerHTML = `<div class="error-message">加载失败：${e.message}</div>`;
  }
}
