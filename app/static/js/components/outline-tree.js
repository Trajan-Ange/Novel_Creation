/** Outline tree view and editor */
let outlineStreamingClient = null;

async function renderOutlineTree() {
  const project = AppState.currentProject;

  $content.innerHTML = `
    <div class="section-header">
      <h2>大纲管理</h2>
    </div>
    <div style="display:flex;gap:16px">
      <div style="width:280px;flex-shrink:0" id="outline-tree-container"></div>
      <div style="flex:1" id="outline-detail"></div>
    </div>
  `;

  await loadOutlineTree(project);
}

async function loadOutlineTree(project) {
  const container = document.getElementById('outline-tree-container');
  try {
    const [bookData, volsData] = await Promise.all([
      API.outline.book(project),
      API.outline.volumes(project),
    ]);

    let html = '<ul class="outline-tree">';
    html += `<li><div class="outline-item" data-otype="book" onclick="viewOutline('book')">
      <span class="icon">📖</span> 全书大纲
    </div></li>`;

    const volumes = volsData.volumes || [];
    for (const vol of volumes) {
      const chaps = await API.outline.chapterList(project, vol);
      html += `<li><div class="outline-item" data-otype="volume" data-vol="${vol}" onclick="viewOutline('volume', ${vol})">
        <span class="icon">📑</span> 第${vol}卷
      </div><ul style="padding-left:20px">`;
      const chapters = chaps.chapters || [];
      for (const ch of chapters) {
        html += `<li><div class="outline-item" data-otype="chapter" data-vol="${vol}" data-ch="${ch}" onclick="viewOutline('chapter', ${vol}, ${ch})">
          <span class="icon">📄</span> 第${ch}章
        </div></li>`;
      }
      html += '</ul></li>';
    }
    html += `<li><div class="outline-item" data-otype="new-volume" onclick="createNewVolume()" style="color:#27ae60;font-weight:600">
      <span class="icon">＋</span> 新建卷大纲
    </div></li>`;
    html += '</ul>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div class="error-message">加载大纲失败</div>';
  }
}

async function createNewVolume() {
  const vStr = await Dialog.prompt('请输入新卷号：');
  const vol = parseInt(vStr);
  if (!vol || vol < 1) return;
  viewOutline('volume', vol);
}

async function viewOutline(type, vol, ch) {
  const project = AppState.currentProject;
  const detail = document.getElementById('outline-detail');
  detail.innerHTML = '<div class="loading">加载中...</div>';

  let content = '';
  let title = '';

  try {
    switch (type) {
      case 'book':
        const book = await API.outline.book(project);
        content = book.content;
        title = '全书大纲';
        break;
      case 'volume':
        const v = await API.outline.volume(project, vol);
        content = v.content;
        title = `第${vol}卷大纲`;
        break;
      case 'chapter':
        const chData = await API.outline.chapter(project, vol, ch);
        content = chData.content;
        title = `第${vol}卷第${ch}章大纲`;
        break;
    }

    detail.innerHTML = `
      <h3>${title}</h3>
      <div class="settings-toolbar">
        <button class="btn btn-primary btn-sm" onclick="openOutlineChat('${type}_outline', ${vol || 0}, ${ch || 0})">AI 对话创建</button>
        <button class="btn btn-secondary btn-sm" onclick="editOutlineManual('${type}', ${vol || 0}, ${ch || 0})">手动编辑</button>
      </div>
      <div id="outline-display" class="markdown-content">${content ? marked.parse(content) : '<p>暂无内容</p>'}</div>
      <div id="outline-editor" style="display:none"></div>
      <div id="outline-stream" style="display:none"></div>
    `;

    // Highlight in tree
    document.querySelectorAll('.outline-item').forEach(el => el.classList.remove('active'));
    const selector = type === 'book' ? `[data-otype="book"]` :
      type === 'volume' ? `[data-otype="volume"][data-vol="${vol}"]` :
      `[data-otype="chapter"][data-vol="${vol}"][data-ch="${ch}"]`;
    const node = document.querySelector(`.outline-item${selector}`);
    if (node) node.classList.add('active');
  } catch (e) {
    detail.innerHTML = `<div class="error-message">加载失败：${e.message}</div>`;
  }
}

async function generateOutlineStream(level, vol, ch) {
  const project = AppState.currentProject;
  const detail = document.getElementById('outline-detail');

  if (outlineStreamingClient) {
    outlineStreamingClient.disconnect();
    outlineStreamingClient = null;
  }

  let settingType, instruction;
  if (level === 'book') {
    settingType = 'book_outline';
    instruction = '';
  } else if (level === 'volume') {
    const vStr = vol || await Dialog.prompt('请输入卷号：');
    const v = parseInt(vStr);
    if (!v) return;
    vol = v;
    settingType = 'volume_outline';
    instruction = '';
  } else if (level === 'chapter') {
    const promptInst = await Dialog.prompt('请输入特别要求（可选）：');
    if (promptInst === null) return;
    instruction = promptInst || '';
    settingType = 'chapter_outline';
  }

  // Show stream container
  const displayDiv = document.getElementById('outline-display');
  const streamDiv = document.getElementById('outline-stream');
  const editorDiv = document.getElementById('outline-editor');
  if (displayDiv) displayDiv.style.display = 'none';
  if (editorDiv) editorDiv.style.display = 'none';
  if (streamDiv) {
    streamDiv.style.display = 'block';
    streamDiv.innerHTML = `
      <div class="wizard-result-content">
        <h4>AI 正在生成<span class="streaming-cursor" style="display:inline-block;vertical-align:middle"></span></h4>
        <div id="outline-stream-text" class="markdown-content" style="max-height:500px;overflow-y:auto;border:1px solid #eee;padding:12px;border-radius:6px;background:#fff;min-height:60px"></div>
        <div id="outline-stream-actions" style="margin-top:12px;display:none;gap:8px">
          <button class="btn btn-success btn-sm" onclick="acceptOutlineStream('${level}', ${vol || 0}, ${ch || 0})">接受</button>
          <button class="btn btn-secondary btn-sm" onclick="generateOutlineStream('${level}', ${vol || 0}, ${ch || 0})">重新生成</button>
        </div>
      </div>
    `;
  }

  const streamTextEl = document.getElementById('outline-stream-text');
  let fullText = '';

  outlineStreamingClient = new SSEClient();
  outlineStreamingClient.onEvent = (event) => {
    switch (event.type) {
      case 'status':
        const h4 = streamDiv?.querySelector('h4');
        if (h4) h4.innerHTML = event.message + '<span class="streaming-cursor" style="display:inline-block;vertical-align:middle"></span>';
        break;
      case 'text_chunk':
        fullText += event.text;
        if (streamTextEl) {
          streamTextEl.innerHTML = marked.parse(fullText);
          streamTextEl.scrollTop = streamTextEl.scrollHeight;
        }
        break;
      case 'complete':
        if (streamTextEl) {
          streamTextEl.innerHTML = marked.parse(event.content || fullText);
        }
        const h4c = streamDiv?.querySelector('h4');
        if (h4c) h4c.textContent = '生成完成';
        const actions = document.getElementById('outline-stream-actions');
        if (actions) actions.style.display = 'flex';
        break;
      case 'error':
        if (streamTextEl) {
          streamTextEl.innerHTML = '<div class="error-message">生成失败：' + event.message + '</div>';
        }
        const h4e = streamDiv?.querySelector('h4');
        if (h4e) h4e.textContent = '';
        const actEl = document.getElementById('outline-stream-actions');
        if (actEl) {
          actEl.style.display = 'flex';
          actEl.innerHTML = `
            <button class="btn btn-primary btn-sm" onclick="generateOutlineStream('${level}', ${vol || 0}, ${ch || 0})">重试</button>
          `;
        }
        break;
    }
  };
  outlineStreamingClient.onError = (err) => {
    if (streamTextEl) {
      streamTextEl.innerHTML = '<div class="error-message">连接出错：' + err.message + '</div>';
    }
  };

  await outlineStreamingClient.connect('/api/settings/stream-generate', {
    body: {
      project: project,
      setting_type: settingType,
      instruction: instruction,
      volume: vol || 1,
      chapter: ch || 1,
    },
  });
}

async function acceptOutlineStream(level, vol, ch) {
  // Content is already saved by the backend, just refresh the view
  await loadOutlineTree(AppState.currentProject);
  if (level === 'book') {
    viewOutline('book');
  } else if (level === 'volume') {
    viewOutline('volume', vol);
  } else {
    viewOutline('chapter', vol, ch);
  }
}

async function editOutlineManual(level, vol, ch) {
  const project = AppState.currentProject;
  const displayDiv = document.getElementById('outline-display');
  const streamDiv = document.getElementById('outline-stream');
  const editorDiv = document.getElementById('outline-editor');

  let currentContent = '';
  try {
    if (level === 'book') {
      const data = await API.outline.book(project);
      currentContent = data.content || '';
    } else if (level === 'volume') {
      const data = await API.outline.volume(project, vol);
      currentContent = data.content || '';
    } else {
      const data = await API.outline.chapter(project, vol, ch);
      currentContent = data.content || '';
    }
  } catch (e) { /* ignore */ }

  if (displayDiv) displayDiv.style.display = 'none';
  if (streamDiv) streamDiv.style.display = 'none';
  if (editorDiv) {
    editorDiv.style.display = 'block';
    editorDiv.innerHTML = `
      <div class="manual-editor">
        <textarea id="outline-edit-textarea" class="manual-edit-textarea">${escapeHtml(currentContent)}</textarea>
        <div class="manual-editor-actions">
          <button class="btn btn-primary btn-sm" onclick="saveOutlineEdit('${level}', ${vol || 0}, ${ch || 0})">保存大纲</button>
          <button class="btn btn-secondary btn-sm" onclick="cancelOutlineEdit('${level}', ${vol || 0}, ${ch || 0})">取消</button>
        </div>
      </div>
    `;
  }
}

async function saveOutlineEdit(level, vol, ch) {
  const project = AppState.currentProject;
  const ta = document.getElementById('outline-edit-textarea');
  if (!ta) return;

  try {
    let result;
    if (level === 'book') {
      result = await API.outline.saveBook(project, ta.value);
    } else if (level === 'volume') {
      result = await API.outline.saveVolume(project, vol, ta.value);
    } else {
      result = await API.outline.saveChapter(project, vol, ch, ta.value);
    }
    if (result && result.success) {
      await loadOutlineTree(project);
      if (level === 'book') viewOutline('book');
      else if (level === 'volume') viewOutline('volume', vol);
      else viewOutline('chapter', vol, ch);
    } else {
      await Dialog.alert('保存失败：' + (result?.error || '未知错误'));
    }
  } catch (e) {
    await Dialog.alert('保存出错：' + e.message);
  }
}

function cancelOutlineEdit(level, vol, ch) {
  if (level === 'book') viewOutline('book');
  else if (level === 'volume') viewOutline('volume', vol);
  else viewOutline('chapter', vol, ch);
}