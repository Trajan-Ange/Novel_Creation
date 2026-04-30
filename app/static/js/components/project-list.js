/** Project list and creation */
let wizardSSEClient = null;

function openProjectModal() {
  document.getElementById('project-modal').style.display = 'flex';
  document.getElementById('lore-source-group').style.display = 'none';
  document.getElementById('proj-type').value = '原创';

  // Toggle lore source visibility
  document.getElementById('proj-type').onchange = function() {
    document.getElementById('lore-source-group').style.display =
      this.value === '二创' ? 'block' : 'none';
  };
}

function closeProjectModal() {
  document.getElementById('project-modal').style.display = 'none';
}

async function createProject() {
  const name = document.getElementById('proj-name').value.trim();
  const description = document.getElementById('proj-desc').value.trim();
  const type = document.getElementById('proj-type').value;

  if (!name) { await Dialog.alert('请输入项目名称'); return; }

  // Create project — pass type and source to backend
  const result = await API.projects.create(name, description, type, type === '二创' ? (document.getElementById('lore-source').value.trim() || '') : '');
  if (!result.success) { await Dialog.alert('创建失败：' + result.error); return; }

  // If fan-fiction, extract lore first
  if (type === '二创') {
    const source = document.getElementById('lore-source').value.trim();
    if (source) {
      $content.innerHTML = `<div class="loading">正在采集《${escapeHtml(source)}》的世界观设定...</div>`;
      closeProjectModal();

      const loreResult = await API.sync.loreExtract(name, source, [], description);
      if (loreResult.success) {
        // Save all extracted sections directly to project files
        const data = loreResult.data || loreResult.result || {};
        await API.sync.loreApply(
          name,
          data.world_setting || '',
          data.character_settings || [],
          data.timeline || '',
        );
        setProject(name);
        $content.innerHTML = `<div class="loading">世界观采集完成！正在初始化项目设定...</div>`;
        openCreationWizard(name, description);
        return;
      }
    }
  }

  closeProjectModal();
  setProject(name);
  openCreationWizard(name, description);
}

async function deleteProject(name) {
  if (!await Dialog.confirm(`确定要删除项目「${name}」吗？此操作无法撤销，所有相关文件将被永久删除。`)) return;
  try {
    const result = await API.projects.delete(name);
    if (result.success) {
      if (AppState.currentProject === name) {
        AppState.currentProject = null;
        document.getElementById('sidebar-project-nav').style.display = 'none';
        document.getElementById('project-indicator').textContent = '未选择项目';
      }
      updateSidebarProjects();
      navigate('projects');
    } else {
      await Dialog.alert('删除失败：' + (result.error || '未知错误'));
    }
  } catch (e) {
    await Dialog.alert('删除出错：' + e.message);
  }
}

function updateSidebarProjects() {
  const nav = document.getElementById('nav-projects');
  API.projects.list().then(projects => {
    nav.innerHTML = projects.map(p => `
      <li data-project="${escapeHtml(p.name)}">${escapeHtml(p.name)}
        <span style="float:right;font-size:11px;color:var(--color-sidebar-muted)">${escapeHtml(p.stage || '')}</span>
      </li>
    `).join('') + `<li class="nav-create">+ 创建新项目</li>`;
    if (projects.length === 0) {
      nav.innerHTML = `<li class="nav-create">+ 创建新项目</li>`;
    }
  }).catch(() => {
    nav.innerHTML = `<li class="nav-create">+ 创建新项目</li>`;
  });
}

// ── Interactive Creation Wizard ────────────────────
let wizardState = {
  project: '',
  description: '',
  currentStep: 0,
  steps: [
    { key: 'world', label: '世界设定', icon: '🌍' },
    { key: 'characters', label: '人物设定', icon: '👤' },
    { key: 'timeline', label: '背景时间线', icon: '⏰' },
    { key: 'relationship', label: '人物关系', icon: '🔗' },
    { key: 'outline', label: '全书大纲', icon: '📖' },
    { key: 'style', label: '风格指南', icon: '🎨' },
  ],
  results: {},
};

function openCreationWizard(name, description) {
  if (!AppState.apiConfigured) {
    $content.innerHTML = `
      <h2>项目已创建：《${escapeHtml(name)}》</h2>
      <div class="card" style="margin-top:16px">
        <h3>AI 生成设定需要配置 API</h3>
        <p style="color:var(--color-warning);margin:10px 0">尚未配置 API 密钥，无法自动生成世界设定、人物等创作依据。</p>
        <p>你可以：</p>
        <ul style="margin:8px 0;padding-left:20px">
          <li>点击右上角齿轮图标配置 API，然后回来继续</li>
          <li>先在项目中手动编写设定文件</li>
        </ul>
        <div style="margin-top:14px">
          <button class="btn btn-primary" onclick="openConfig()">前往配置 API</button>
          <button class="btn btn-secondary" onclick="navigate('dashboard')" style="margin-left:8px">进入项目</button>
        </div>
      </div>
    `;
    updateSidebarProjects();
    return;
  }

  wizardState.project = name;
  wizardState.description = description;
  wizardState.currentStep = 0;
  wizardState.results = {};
  wizardState.steps.forEach(s => { s.done = false; s.skipped = false; });

  renderWizardFrame();
  renderWizardStep(0);
}

function renderWizardFrame() {
  const steps = wizardState.steps;
  let stepsHtml = steps.map((s, i) => {
    let cls = 'wizard-pip';
    if (s.done) cls += ' wizard-pip-done';
    else if (s.skipped) cls += ' wizard-pip-skipped';
    else if (i === wizardState.currentStep) cls += ' wizard-pip-active';
    return `<div class="${cls}" title="${s.label}">${s.done ? '✓' : s.skipped ? '−' : s.icon}</div>`;
  }).join('');

  $content.innerHTML = `
    <div class="section-header">
      <h2>项目创建向导：《${wizardState.project}》</h2>
      <span style="font-size:13px;color:var(--color-text-subtle)">步骤 ${wizardState.currentStep + 1}/${steps.length}</span>
    </div>
    <div class="wizard-progress">${stepsHtml}</div>
    <div id="wizard-step-content"></div>
  `;
}

function renderWizardStep(stepIndex) {
  wizardState.currentStep = stepIndex;
  const step = wizardState.steps[stepIndex];
  const container = document.getElementById('wizard-step-content');
  if (!container) return;

  // Update progress pips
  document.querySelectorAll('.wizard-pip').forEach((pip, i) => {
    pip.classList.remove('wizard-pip-active');
    if (i === stepIndex) pip.classList.add('wizard-pip-active');
  });

  const headerSpan = document.querySelector('.section-header span');
  if (headerSpan) headerSpan.textContent = `步骤 ${stepIndex + 1}/${wizardState.steps.length}`;

  container.innerHTML = `
    <div class="card wizard-step-card">
      <h3>${step.icon} ${step.label}</h3>
      <p style="color:var(--color-text-muted);margin-bottom:12px">为你的小说设定${step.label}。输入具体指令（可选），或直接点击自动生成。</p>
      <div class="form-group">
        <label>AI 指令（可选，留空则由AI自由发挥）</label>
        <textarea id="wizard-instruction" rows="3" placeholder="例如：东方仙侠世界、五行灵气体系、上古神魔大战背景..."></textarea>
      </div>
      <div class="wizard-step-actions">
        <button class="btn btn-primary" onclick="runWizardStep()" id="wizard-generate-btn">自动生成</button>
        <button class="btn btn-secondary" onclick="handleWizardSkip()">跳过此步骤</button>
      </div>
      <div id="wizard-result" style="margin-top:16px;display:none"></div>
    </div>
  `;
}

async function runWizardStep() {
  const step = wizardState.steps[wizardState.currentStep];
  const instruction = document.getElementById('wizard-instruction')?.value.trim() || wizardState.description;
  const resultDiv = document.getElementById('wizard-result');
  const genBtn = document.getElementById('wizard-generate-btn');

  resultDiv.style.display = 'block';
  resultDiv.innerHTML = `
    <div class="wizard-result-content">
      <h4>AI 正在生成<span class="streaming-cursor" style="display:inline-block;vertical-align:middle"></span></h4>
      <div id="wizard-stream-content" class="markdown-content" style="max-height:400px;overflow-y:auto;border:1px solid var(--border-color-light);padding:12px;border-radius:6px;background:var(--color-surface);min-height:60px"></div>
      <div id="wizard-actions" style="margin-top:12px;display:none;gap:8px">
        <button class="btn btn-success" onclick="handleWizardAccept()">接受，继续下一步</button>
        <button class="btn btn-secondary" onclick="handleWizardRedo()">重新生成</button>
      </div>
    </div>
  `;
  if (genBtn) genBtn.disabled = true;

  const streamEl = document.getElementById('wizard-stream-content');
  let fullText = '';

  // Map wizard step key to SSE setting_type
  const settingType = step.key === 'outline' ? 'book_outline' : step.key;

  if (wizardSSEClient) wizardSSEClient.disconnect();
  wizardSSEClient = new SSEClient();
  wizardSSEClient.onEvent = (event) => {
    switch (event.type) {
      case 'status':
        // Update the header
        const h4 = resultDiv.querySelector('h4');
        if (h4) h4.innerHTML = event.message + '<span class="streaming-cursor" style="display:inline-block;vertical-align:middle"></span>';
        break;
      case 'text_chunk':
        fullText += event.text;
        if (streamEl) {
          streamEl.innerHTML = marked.parse(fullText);
          streamEl.scrollTop = streamEl.scrollHeight;
        }
        break;
      case 'complete':
        wizardState.results[step.key] = event.content || fullText;
        if (streamEl) {
          streamEl.innerHTML = marked.parse(event.content || fullText);
          streamEl.style.maxHeight = '400px';
        }
        const h4c = resultDiv.querySelector('h4');
        if (h4c) h4c.textContent = '生成结果预览';
        const actions = document.getElementById('wizard-actions');
        if (actions) actions.style.display = 'flex';
        if (genBtn) genBtn.disabled = false;
        break;
      case 'error':
        if (streamEl) {
          streamEl.innerHTML = '<div class="error-message">生成失败：' + event.message + '</div>';
        }
        const h4e = resultDiv.querySelector('h4');
        if (h4e) h4e.textContent = '';
        const actEl = document.getElementById('wizard-actions');
        if (actEl) {
          actEl.style.display = 'flex';
          actEl.innerHTML = `
            <button class="btn btn-primary btn-sm" onclick="runWizardStep()">重试</button>
            <button class="btn btn-secondary btn-sm" onclick="handleWizardSkip()">跳过此步骤</button>
          `;
        }
        if (genBtn) genBtn.disabled = false;
        break;
    }
  };
  wizardSSEClient.onError = (err) => {
    if (streamEl) {
      streamEl.innerHTML = '<div class="error-message">连接出错：' + err.message + '</div>';
    }
    if (genBtn) genBtn.disabled = false;
  };

  await wizardSSEClient.connect('/api/settings/stream-generate', {
    body: {
      project: wizardState.project,
      setting_type: settingType,
      instruction: instruction,
      volume: 1,
    },
  });
}

function handleWizardAccept() {
  const step = wizardState.steps[wizardState.currentStep];
  step.done = true;
  step.skipped = false;
  advanceWizardStep();
}

function handleWizardSkip() {
  const step = wizardState.steps[wizardState.currentStep];
  step.done = false;
  step.skipped = true;
  advanceWizardStep();
}

function handleWizardRedo() {
  const resultDiv = document.getElementById('wizard-result');
  if (resultDiv) {
    resultDiv.innerHTML = '';
    resultDiv.style.display = 'none';
  }
  const genBtn = document.getElementById('wizard-generate-btn');
  if (genBtn) genBtn.disabled = false;
  runWizardStep();
}

function advanceWizardStep() {
  const nextIndex = wizardState.currentStep + 1;
  if (nextIndex >= wizardState.steps.length) {
    finishWizard();
    return;
  }
  renderWizardFrame();
  renderWizardStep(nextIndex);
}

function finishWizard() {
  const done = wizardState.steps.filter(s => s.done).length;
  const skipped = wizardState.steps.filter(s => s.skipped).length;
  const total = wizardState.steps.length;

  $content.innerHTML = `
    <h2>项目创建完成：《${wizardState.project}》</h2>
    <div class="card" style="margin-top:16px">
      <h3>创建摘要</h3>
      <div style="display:flex;gap:24px;margin:12px 0">
        <div><span style="color:var(--color-success);font-size:24px;font-weight:600">${done}</span><br>已完成</div>
        <div><span style="color:var(--color-warning);font-size:24px;font-weight:600">${skipped}</span><br>已跳过</div>
        <div><span style="color:var(--color-text-subtle);font-size:24px;font-weight:600">${total - done - skipped}</span><br>未完成</div>
      </div>
      <div style="margin-top:8px">
        ${wizardState.steps.map(s =>
          `<div style="padding:4px 0">
            ${s.done ? '✓' : s.skipped ? '−' : '✕'} ${s.label}
          </div>`
        ).join('')}
      </div>
      <div style="margin-top:16px">
        <button class="btn btn-primary" onclick="navigate('dashboard')">进入项目</button>
        <button class="btn btn-secondary" onclick="navigate('settings')" style="margin-left:8px">管理创作依据</button>
      </div>
    </div>
  `;
  updateSidebarProjects();
}

async function renderProjectList() {
  const nav = document.getElementById('nav-projects');
  try {
    const projects = await API.projects.list();
    nav.innerHTML = projects.map(p => `
      <li data-project="${p.name}">
        ${p.name}
        <span style="float:right;font-size:11px;color:var(--color-sidebar-muted)">${p.stage || ''}</span>
      </li>
    `).join('') + `<li class="nav-create">+ 创建新项目</li>`;

    if (projects.length === 0) {
      nav.innerHTML = `<li class="nav-create">+ 创建新项目</li>`;
    }
  } catch (e) {
    nav.innerHTML = `<li class="nav-create">+ 创建新项目</li>`;
  }

  // Render project list in content area
  $content.innerHTML = `
    <div class="section-header">
      <h2>项目列表</h2>
      <button class="btn btn-primary" onclick="openProjectModal()">+ 创建新项目</button>
    </div>
    <div id="project-list-content"></div>
  `;

  try {
    const projects = await API.projects.list();
    const listEl = document.getElementById('project-list-content');
    if (projects.length === 0) {
      listEl.innerHTML = `<div class="empty-state">
        <h3>还没有项目</h3>
        <p>点击上方按钮创建你的第一部小说</p>
      </div>`;
    } else {
      listEl.innerHTML = projects.map(p => `
        <div class="card project-card" style="cursor:pointer;position:relative" onclick="setProject('${p.name}')" data-project="${p.name}">
          <button class="btn btn-danger btn-sm" style="position:absolute;top:12px;right:12px;z-index:1" onclick="event.stopPropagation();deleteProject('${p.name}')">删除</button>
          <h3>${p.name}</h3>
          <div style="display:flex;gap:16px;font-size:13px;color:var(--color-text-subtle)">
            <span>类型：${p.type}</span>
            <span>进度：第${p.volume}卷 第${p.chapter}章</span>
            <span>阶段：${p.stage}</span>
            <span>更新：${new Date(p.updated).toLocaleString('zh-CN')}</span>
          </div>
        </div>
      `).join('');

      // Enable right-click context menu on project cards
      document.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('contextmenu', (e) => {
          e.preventDefault();
          e.stopPropagation();
          const menu = document.getElementById('context-menu');
          menu.style.display = 'block';
          menu.style.left = e.pageX + 'px';
          menu.style.top = e.pageY + 'px';
          menu.dataset.projectName = card.dataset.project;
        });
      });
    }
  } catch (e) {
    document.getElementById('project-list-content').innerHTML = `<div class="error-message">加载项目列表失败</div>`;
  }
}
