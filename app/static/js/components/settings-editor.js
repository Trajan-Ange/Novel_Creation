/** Settings editor — tabbed panel for world, characters, timeline, relationships */
let currentSettingsTab = 'world';

async function renderSettingsEditor() {
  $content.innerHTML = `
    <div class="section-header">
      <h2>创作依据管理</h2>
      <button class="btn btn-secondary btn-sm" onclick="showVersionHistory()">版本历史</button>
    </div>
    <div class="settings-tabs">
      <div class="settings-tab" data-stab="world">世界设定</div>
      <div class="settings-tab" data-stab="characters">人物设定</div>
      <div class="settings-tab" data-stab="timeline">时间线</div>
      <div class="settings-tab" data-stab="relationship">人物关系</div>
      <div class="settings-tab" data-stab="style">风格指南</div>
    </div>
    <div id="settings-content"></div>
  `;

  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      currentSettingsTab = tab.dataset.stab;
      document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadSettingsTab(currentSettingsTab);
    });
  });

  // Activate first tab
  document.querySelector(`.settings-tab[data-stab="${currentSettingsTab}"]`).classList.add('active');
  loadSettingsTab(currentSettingsTab);
}

async function showVersionHistory() {
  const project = AppState.currentProject;
  try {
    const resp = await fetch(`/api/settings/${encodeURIComponent(project)}/snapshots`);
    const data = await resp.json();
    if (!data.success) {
      await Dialog.alert('加载版本历史失败：' + data.error);
      return;
    }
    const snapshots = data.snapshots;
    if (!snapshots || snapshots.length === 0) {
      await Dialog.alert('暂无版本历史记录。每次知识同步后会自动保存版本快照。');
      return;
    }
    let html = '<div class="snapshot-list">';
    snapshots.forEach(s => {
      html += `<div class="snapshot-item">
        <span>${s.id}</span>
        <span>${s.reason || '—'}</span>
        <span>${s.file_count} 个文件</span>
        <button class="btn btn-sm btn-warning" onclick="restoreSnapshot('${s.id}')">恢复此版本</button>
      </div>`;
    });
    html += '</div>';
    await Dialog.alertHtml(html);
  } catch (e) {
    await Dialog.alert('加载版本历史失败：' + e.message);
  }
}

async function restoreSnapshot(snapshotId) {
  const project = AppState.currentProject;
  const confirmed = await Dialog.confirm(`确定要恢复到版本 ${snapshotId} 吗？当前设定将被覆盖。`);
  if (!confirmed) return;
  try {
    const resp = await fetch(`/api/settings/${encodeURIComponent(project)}/snapshots/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ snapshot_id: snapshotId }),
    });
    const data = await resp.json();
    if (data.success) {
      await Dialog.alert('版本快照恢复成功！');
      loadSettingsTab(currentSettingsTab);
    } else {
      await Dialog.alert('恢复失败：' + data.error);
    }
  } catch (e) {
    await Dialog.alert('恢复失败：' + e.message);
  }
}

async function loadSettingsTab(tab) {
  const container = document.getElementById('settings-content');
  const project = AppState.currentProject;
  container.innerHTML = '<div class="loading">加载中...</div>';

  try {
    switch (tab) {
      case 'world': await renderWorldSettings(container, project); break;
      case 'characters': await renderCharacterSettings(container, project); break;
      case 'timeline': await renderTimelineSettings(container, project); break;
      case 'relationship': await renderRelationshipSettings(container, project); break;
      case 'style': await renderStyleSettings(container, project); break;
    }
  } catch (e) {
    container.innerHTML = `<div class="error-message">加载失败：${e.message}</div>`;
  }
}

async function renderWorldSettings(container, project) {
  const data = await API.settings.world(project);
  container.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-primary btn-sm" onclick="openSettingsChat('world')">AI 对话创建</button>
      <button class="btn btn-secondary btn-sm" onclick="editSetting('world', 'edit')">手动编辑</button>
    </div>
    <div id="world-display" class="markdown-content">
      ${data.content ? marked.parse(data.content) : '<div class="empty-state"><p>暂无世界设定，点击上方按钮创建</p></div>'}
    </div>
    <div id="world-editor" style="display:none"></div>
  `;
}

async function renderCharacterSettings(container, project) {
  const data = await API.settings.characters(project);
  const chars = data.characters || [];

  container.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-primary btn-sm" onclick="openSettingsChat('character')">AI 对话创建角色</button>
      <button class="btn btn-secondary btn-sm" onclick="createCharacterManual()">手动创建角色</button>
    </div>
    <div id="char-list">
      ${chars.length === 0 ? '<div class="empty-state"><p>暂无人物设定</p></div>' : ''}
      ${chars.map(c => `
        <div class="card char-card" style="cursor:pointer" data-char-name="${escapeHtml(c)}">
          <h3>${escapeHtml(c)}</h3>
        </div>
      `).join('')}
    </div>
    <div id="char-detail" style="display:none"></div>
    <div id="char-editor" style="display:none"></div>
  `;
  // Use event delegation for character card clicks (avoids onclick escaping issues)
  document.getElementById('char-list').addEventListener('click', (e) => {
    const card = e.target.closest('.char-card');
    if (card) viewCharacter(card.dataset.charName);
  });
}

async function viewCharacter(name) {
  const project = AppState.currentProject;
  const data = await API.settings.character(project, name);
  const detail = document.getElementById('char-detail');
  detail.style.display = 'block';
  document.getElementById('char-list').style.display = 'none';
  const safeName = escapeOnclick(name);
  detail.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-secondary btn-sm" onclick="document.getElementById('char-list').style.display='block';document.getElementById('char-detail').style.display='none'">返回列表</button>
      <button class="btn btn-secondary btn-sm" onclick="editCharacterManual('${safeName}')">手动编辑</button>
      <button class="btn btn-danger btn-sm" onclick="deleteCharacter('${safeName}')">删除</button>
    </div>
    <div class="markdown-content">${marked.parse(data.content || '无内容')}</div>
  `;
}

async function deleteCharacter(name) {
  const ok = await Dialog.confirm(`确定删除角色「${name}」？`);
  if (!ok) return;
  await API.settings.deleteCharacter(AppState.currentProject, name);
  renderSettingsEditor();
}

async function createCharacterManual() {
  const name = await Dialog.prompt('请输入新角色名称：');
  if (!name || !name.trim()) return;
  const trimmedName = name.trim();
  if (/[\/\\]/.test(trimmedName) || trimmedName.includes('..')) {
    await Dialog.alert('角色名包含非法字符，请使用其他名称。');
    return;
  }
  const existing = document.querySelectorAll('#char-list .card h3');
  for (const el of existing) {
    if (el.textContent === trimmedName) {
      const ok = await Dialog.confirm(`角色「${trimmedName}」已存在，是否编辑？`);
      if (ok) editCharacterManual(trimmedName);
      return;
    }
  }
  editCharacterManual(trimmedName);
}

async function renderTimelineSettings(container, project) {
  const data = await API.settings.timeline(project);
  container.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-primary btn-sm" onclick="openSettingsChat('timeline')">AI 对话创建</button>
      <button class="btn btn-secondary btn-sm" onclick="editSetting('timeline', 'edit')">手动编辑</button>
    </div>
    <div id="timeline-display">
      <details open><summary style="font-weight:600;cursor:pointer;margin-bottom:8px">背景时间线</summary>
        <div class="markdown-content">${data.background ? marked.parse(data.background) : '<p>暂无</p>'}</div>
      </details>
      <details open><summary style="font-weight:600;cursor:pointer;margin-bottom:8px;margin-top:16px">故事时间线</summary>
        <div class="markdown-content">${data.story ? marked.parse(data.story) : '<p>暂无</p>'}</div>
      </details>
    </div>
  `;
}

async function renderRelationshipSettings(container, project) {
  const data = await API.settings.relationship(project);
  container.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-primary btn-sm" onclick="openSettingsChat('relationship')">AI 对话创建</button>
      <button class="btn btn-secondary btn-sm" onclick="editSetting('relationship', 'edit')">手动编辑</button>
    </div>
    <div id="relationship-display" class="markdown-content">${data.content ? marked.parse(data.content) : '<div class="empty-state"><p>暂无关系图谱</p></div>'}</div>
  `;
}

async function renderStyleSettings(container, project) {
  const data = await API.settings.styleGuide(project);
  container.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-primary btn-sm" onclick="openSettingsChat('style')">AI 对话创建</button>
      <button class="btn btn-secondary btn-sm" onclick="editSetting('style', 'edit')">手动编辑</button>
    </div>
    <div id="style-display" class="markdown-content">${data.content ? marked.parse(data.content) : '<div class="empty-state"><p>暂无风格指南</p></div>'}</div>
  `;
}

async function editSetting(type, action) {
  const project = AppState.currentProject;

  if (action === 'edit') {
    openManualEditor(type);
    return;
  }

  // AI generation flow
  const msg = action === 'create' ? '请输入角色创建指令：' : '请输入AI生成/更新指令（可选，留空则AI自动生成）：';
  const instruction = await Dialog.prompt(msg);
  if (action === 'create' && !instruction) return;

  // Show loading state
  const container = document.getElementById('settings-content');
  const existingLoading = document.getElementById('gen-loading');
  if (existingLoading) existingLoading.remove();
  container.insertAdjacentHTML('afterbegin',
    '<div id="gen-loading" class="loading">AI 正在生成中，请稍候（约10-30秒）...</div>');

  try {
    let result;
    switch (type) {
      case 'world':
        result = await API.settings.generateWorld(project, instruction || '');
        break;
      case 'character':
        result = await API.settings.generateCharacter(project, instruction);
        break;
      case 'timeline':
        result = await API.settings.generateTimeline(project, instruction || '');
        break;
      case 'relationship':
        result = await API.settings.generateRelationship(project, instruction || '');
        break;
      case 'style':
        result = await API.settings.generateStyleGuide(project, instruction || '');
        break;
    }

    const loadingEl = document.getElementById('gen-loading');
    if (loadingEl) loadingEl.remove();

    if (result && result.success) {
      loadSettingsTab(currentSettingsTab);
    } else {
      await Dialog.alert('操作失败：' + (result?.error || '未知错误，请检查API配置'));
    }
  } catch (err) {
    const loadingEl = document.getElementById('gen-loading');
    if (loadingEl) loadingEl.remove();
    await Dialog.alert('请求出错：' + (err.message || '网络错误'));
  }
}

async function openManualEditor(type) {
  const project = AppState.currentProject;
  const container = document.getElementById('settings-content');

  try {
    let editorHtml = '';
    let displayId = '';

    switch (type) {
      case 'world': {
        const data = await API.settings.world(project);
        displayId = 'world-display';
        editorHtml = buildEditorHtml('world', data.content || '', '保存世界设定', displayId);
        break;
      }
      case 'timeline': {
        const data = await API.settings.timeline(project);
        displayId = 'timeline-display';
        editorHtml = `
          <div class="manual-editor">
            <label style="font-weight:600;margin-bottom:4px;display:block">背景时间线</label>
            <textarea id="manual-edit-bg" class="manual-edit-textarea" style="min-height:180px">${escapeHtml(data.background || '')}</textarea>
            <label style="font-weight:600;margin:12px 0 4px;display:block">故事时间线</label>
            <textarea id="manual-edit-story" class="manual-edit-textarea" style="min-height:180px">${escapeHtml(data.story || '')}</textarea>
            <div class="manual-editor-actions">
              <button class="btn btn-primary btn-sm" onclick="saveManualEdit('timeline')">保存时间线</button>
              <button class="btn btn-secondary btn-sm" onclick="cancelManualEdit('${displayId}')">取消</button>
            </div>
          </div>
        `;
        break;
      }
      case 'relationship': {
        const data = await API.settings.relationship(project);
        displayId = 'relationship-display';
        editorHtml = buildEditorHtml('relationship', data.content || '', '保存人物关系', displayId);
        break;
      }
      case 'style': {
        const data = await API.settings.styleGuide(project);
        displayId = 'style-display';
        editorHtml = buildEditorHtml('style', data.content || '', '保存风格指南', displayId);
        break;
      }
    }

    // Hide display, show editor
    const displayDiv = document.getElementById(displayId);
    if (displayDiv) displayDiv.style.display = 'none';

    let editorDiv = document.getElementById('manual-editor-container');
    if (!editorDiv) {
      editorDiv = document.createElement('div');
      editorDiv.id = 'manual-editor-container';
      container.appendChild(editorDiv);
    }
    editorDiv.innerHTML = editorHtml;
    editorDiv.style.display = 'block';
  } catch (e) {
    await Dialog.alert('加载内容失败：' + e.message);
  }
}

function buildEditorHtml(type, content, saveLabel, displayId) {
  return `
    <div class="manual-editor">
      <textarea id="manual-edit-textarea" class="manual-edit-textarea">${escapeHtml(content)}</textarea>
      <div class="manual-editor-actions">
        <button class="btn btn-primary btn-sm" onclick="saveManualEdit('${type}')">${saveLabel}</button>
        <button class="btn btn-secondary btn-sm" onclick="cancelManualEdit('${displayId}')">取消</button>
      </div>
    </div>
  `;
}

async function saveManualEdit(type) {
  const project = AppState.currentProject;

  try {
    let result;
    switch (type) {
      case 'world': {
        const ta = document.getElementById('manual-edit-textarea');
        if (!ta) return;
        result = await API.settings.saveWorld(project, ta.value);
        break;
      }
      case 'timeline': {
        const bgTa = document.getElementById('manual-edit-bg');
        const storyTa = document.getElementById('manual-edit-story');
        result = await API.settings.saveTimeline(project, bgTa?.value || '', storyTa?.value || '');
        break;
      }
      case 'relationship': {
        const ta = document.getElementById('manual-edit-textarea');
        if (!ta) return;
        result = await API.settings.saveRelationship(project, ta.value);
        break;
      }
      case 'style': {
        const ta = document.getElementById('manual-edit-textarea');
        if (!ta) return;
        result = await API.settings.saveStyleGuide(project, ta.value);
        break;
      }
    }
    if (result && result.success) {
      // Remove editor and reload
      const editorDiv = document.getElementById('manual-editor-container');
      if (editorDiv) editorDiv.remove();
      loadSettingsTab(currentSettingsTab);
    } else {
      await Dialog.alert('保存失败：' + (result?.error || '未知错误'));
    }
  } catch (e) {
    await Dialog.alert('保存出错：' + e.message);
  }
}

function cancelManualEdit(displayId) {
  const editorDiv = document.getElementById('manual-editor-container');
  if (editorDiv) editorDiv.remove();
  const displayDiv = document.getElementById(displayId);
  if (displayDiv) displayDiv.style.display = 'block';
}

async function editCharacterManual(name) {
  const project = AppState.currentProject;
  const data = await API.settings.character(project, name);
  const detail = document.getElementById('char-detail');
  detail.style.display = 'block';
  document.getElementById('char-list').style.display = 'none';
  const safeName = escapeOnclick(name);

  detail.innerHTML = `
    <div class="settings-toolbar">
      <button class="btn btn-secondary btn-sm" onclick="viewCharacter('${safeName}')">返回</button>
    </div>
    <div class="manual-editor">
      <textarea id="char-manual-edit-textarea" class="manual-edit-textarea">${escapeHtml(data.content || '')}</textarea>
      <div class="manual-editor-actions">
        <button class="btn btn-primary btn-sm" onclick="saveCharacterManualEdit('${safeName}')">保存角色设定</button>
        <button class="btn btn-secondary btn-sm" onclick="viewCharacter('${safeName}')">取消</button>
      </div>
    </div>
  `;
}

async function saveCharacterManualEdit(name) {
  const project = AppState.currentProject;
  const textarea = document.getElementById('char-manual-edit-textarea');
  if (!textarea) return;
  try {
    const result = await API.settings.saveCharacter(project, name, textarea.value);
    if (result && result.success) {
      viewCharacter(name);
    } else {
      await Dialog.alert('保存失败：' + (result?.error || '未知错误'));
    }
  } catch (e) {
    await Dialog.alert('保存出错：' + e.message);
  }
}
