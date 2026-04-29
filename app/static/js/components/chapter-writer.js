/** Chapter writing component — chat-like interactive interface with SSE streaming */
let chapterSSE = null;
let writeState = { phase: 'idle', volume: 1, chapter: 1 };

async function renderChapterWriter() {
  const project = AppState.currentProject;

  $content.innerHTML = `
    <div class="section-header">
      <h2>章节写作</h2>
    </div>
    <div class="write-controls">
      <label>卷：<input type="number" id="write-vol" value="${writeState.volume}" min="1" style="width:60px"></label>
      <label>章：<input type="number" id="write-ch" value="${writeState.chapter}" min="1" style="width:60px"></label>
      <button class="btn btn-primary btn-sm" onclick="startChapterWrite()">AI 写作</button>
      <button class="btn btn-secondary btn-sm" onclick="renderManualWriter()">手动创作</button>
      <button class="btn btn-secondary btn-sm" onclick="viewWrittenChapter()">查看已写章节</button>
    </div>
    <div id="chapter-chat" class="chat-container">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-message system">
          <div class="content">准备开始章节创作。请先设置卷号和章节号，然后点击「开始写作」。</div>
        </div>
      </div>
    </div>
  `;
}

function addChatMessage(type, html) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = `chat-message ${type}`;
  div.innerHTML = `<div class="content">${html}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

async function startChapterWrite() {
  const project = AppState.currentProject;
  const vol = parseInt(document.getElementById('write-vol').value) || 1;
  const ch = parseInt(document.getElementById('write-ch').value) || 1;
  writeState = { phase: 'outline', volume: vol, chapter: ch };

  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML = '';

  addChatMessage('system', `<div class="content">开始创作第${vol}卷第${ch}章...</div>`);

  // Pre-check: validate that book and volume outlines exist
  try {
    const [bookOutline, volOutline] = await Promise.all([
      API.outline.book(project),
      API.outline.volume(project, vol),
    ]);

    if (!bookOutline.content) {
      addChatMessage('system', `
        <div class="error-message">
          <strong>无法开始写作：尚未创建全书大纲</strong><br>
          章节写作需要全书大纲和卷大纲作为结构指导。<br>
          <button class="btn btn-primary btn-sm" onclick="navigate('outline')" style="margin-top:8px">前往大纲管理</button>
        </div>
      `);
      return;
    }

    if (!volOutline.content) {
      addChatMessage('system', `
        <div class="error-message">
          <strong>无法开始写作：尚未创建第${vol}卷大纲</strong><br>
          请先生成第${vol}卷大纲，再进行章节写作。<br>
          <button class="btn btn-primary btn-sm" onclick="navigate('outline')" style="margin-top:8px">前往大纲管理</button>
        </div>
      `);
      return;
    }
  } catch (e) {
    addChatMessage('system', `<div class="error-message">大纲验证失败：${e.message}</div>`);
    return;
  }

  // Connect SSE
  chapterSSE = new SSEClient();
  chapterSSE.onEvent = (event) => handleChapterEvent(event, project, vol, ch);
  chapterSSE.onError = (err) => {
    addChatMessage('system', `<div class="content error-message">连接出错：${err.message}</div>`);
  };

  const instruction = (await Dialog.prompt('请输入特别要求（可选）：')) || '';

  await chapterSSE.connect('/api/chapters/generate', {
    body: {
      project, volume: vol, chapter: ch,
      instruction, mode: 'interactive',
    },
  });
}

function handleChapterEvent(event, project, vol, ch) {
  const msgs = document.getElementById('chat-messages');

  switch (event.type) {
    case 'status':
      addChatMessage('system', `<div class="content">${event.message}</div>`);
      break;

    case 'outline_chunk':
      if (writeState.phase !== 'outline') {
        writeState.phase = 'outline';
        writeState.outlineText = '';
        addChatMessage('outline', '<div class="label">章节大纲</div><div class="markdown-content streaming-cursor" id="streaming-outline"></div>');
      }
      writeState.outlineText = (writeState.outlineText || '') + event.text;
      const outlineStreamEl = document.getElementById('streaming-outline');
      if (outlineStreamEl) {
        outlineStreamEl.innerHTML = marked.parse(writeState.outlineText);
      }
      msgs.scrollTop = msgs.scrollHeight;
      break;

    case 'outline':
      writeState.phase = 'review';
      // Replace streaming outline with final version
      const outlineFinalEl = document.getElementById('streaming-outline');
      if (outlineFinalEl) {
        outlineFinalEl.classList.remove('streaming-cursor');
        outlineFinalEl.innerHTML = marked.parse(event.markdown || '');
      } else {
        addChatMessage('outline', `
          <div class="label">章节大纲</div>
          <div class="markdown-content">${marked.parse(event.markdown || '')}</div>
        `);
      }

      if (event.adjusted) {
        addChatMessage('system', '<div class="content">大纲已根据你的反馈调整。是否满意？<br>输入修改意见或回复「确认」开始生成正文。</div>');
      } else {
        addChatMessage('system', `
          <div class="content">
            <strong>请确认大纲</strong><br>
            输入修改意见进行调整，或回复「<strong>确认</strong>」开始生成正文。
          </div>
        `);
      }
      addChatInput('请输入修改意见或「确认」', (value) => {
        handleOutlineFeedback(value, project, vol, ch);
      });
      break;

    case 'awaiting_confirmation':
      addChatMessage('system', '<div class="content">大纲已生成，请确认。输入修改意见或「确认」。</div>');
      break;

    case 'text_chunk':
      if (writeState.phase !== 'streaming') {
        writeState.phase = 'streaming';
        writeState.fullText = '';
        addChatMessage('text-chunk', '<div class="label">正文</div><div class="markdown-content streaming-cursor" id="streaming-text"></div>');
      }
      writeState.fullText = (writeState.fullText || '') + event.text;
      const streamingEl = document.getElementById('streaming-text');
      if (streamingEl) {
        streamingEl.innerHTML = marked.parse(writeState.fullText);
        streamingEl.classList.add('streaming-cursor');
      }
      msgs.scrollTop = msgs.scrollHeight;
      break;

    case 'text_complete':
      writeState.phase = 'syncing';
      const el = document.getElementById('streaming-text');
      if (el) {
        el.classList.remove('streaming-cursor');
      }
      addChatMessage('system', '<div class="content">正文生成完成！正在更新创作依据...</div>');
      break;

    case 'sync_summary':
      writeState.phase = 'done';
      addChatMessage('summary', `
        <div class="label">更新摘要</div>
        <div class="markdown-content">${marked.parse(event.data?.summary || '无更新')}</div>
      `);
      addChatMessage('system', `
        <div class="content">
          第${vol}卷第${ch}章 创作完成！
          <div class="chat-actions">
            <button class="btn btn-primary btn-sm" onclick="startNextChapter(${vol}, ${ch})">继续下一章</button>
            <button class="btn btn-secondary btn-sm" onclick="viewWrittenChapter()">查看已写章节</button>
          </div>
        </div>
      `);
      break;

    case 'done':
      addChatMessage('system', `<div class="content">${event.message}</div>`);
      break;

    case 'error':
      let errorHtml = event.message;
      if (event.code === 'MISSING_BOOK_OUTLINE' || event.code === 'MISSING_VOLUME_OUTLINE') {
        errorHtml = `
          <strong>${event.message}</strong><br>
          <button class="btn btn-primary btn-sm" onclick="navigate('outline')" style="margin-top:8px">前往大纲管理</button>
        `;
      }
      addChatMessage('system', `<div class="error-message">${errorHtml}</div>`);
      break;
  }
}

function addChatInput(placeholder, onSubmit) {
  // Remove any existing input to prevent duplicates
  const existing = document.getElementById('chat-input-msg');
  if (existing) existing.remove();

  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-message system';
  div.id = 'chat-input-msg';
  div.innerHTML = `
    <div class="content" style="display:flex;gap:8px;align-items:center">
      <input type="text" id="chat-feedback-input" placeholder="${placeholder}"
        style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:20px;font-size:14px"
        onkeydown="if(event.key==='Enter')document.getElementById('chat-submit-btn').click()">
      <button class="btn btn-primary btn-sm" id="chat-submit-btn">发送</button>
    </div>
  `;
  msgs.appendChild(div);

  document.getElementById('chat-submit-btn').addEventListener('click', () => {
    const input = document.getElementById('chat-feedback-input');
    const value = input.value.trim();
    if (value) {
      div.remove();
      addChatMessage('system', `<div class="content"><em>你的回复：</em>${value}</div>`);
      onSubmit(value);
    }
  });

  setTimeout(() => {
    const input = document.getElementById('chat-feedback-input');
    if (input) input.focus();
  }, 100);

  msgs.scrollTop = msgs.scrollHeight;
}

async function handleOutlineFeedback(feedback, project, vol, ch) {
  if (chapterSSE) chapterSSE.disconnect();

  const trimmed = feedback.trim();
  const isConfirm = trimmed === '确认' || trimmed === '确认。' || trimmed.toLowerCase() === 'ok' || trimmed === '可以';

  chapterSSE = new SSEClient();
  chapterSSE.onEvent = (event) => handleChapterEvent(event, project, vol, ch);
  chapterSSE.onError = (err) => {
    addChatMessage('system', `<div class="content error-message">连接出错：${err.message}</div>`);
  };

  await chapterSSE.connect('/api/chapters/feedback', {
    body: {
      project,
      volume: vol,
      chapter: ch,
      action: isConfirm ? 'confirm' : 'modify',
      feedback: isConfirm ? '' : feedback,
    },
  });
}

function startNextChapter(vol, ch) {
  document.getElementById('write-vol').value = vol;
  document.getElementById('write-ch').value = ch + 1;
  startChapterWrite();
}

async function viewWrittenChapter() {
  const project = AppState.currentProject;
  const vol = parseInt(document.getElementById('write-vol').value) || 1;
  const ch = parseInt(document.getElementById('write-ch').value) || 1;

  try {
    const data = await API.chapters.get(project, vol, ch);
    const msgs = document.getElementById('chat-messages');
    if (data.content) {
      addChatMessage('system', '<div class="content">已加载第' + vol + '卷第' + ch + '章：</div>');
      addChatMessage('text-chunk', `<div class="label">第${vol}卷第${ch}章</div><div class="markdown-content">${marked.parse(data.content)}</div>`);
    } else {
      addChatMessage('system', '<div class="content">该章节暂无内容</div>');
    }
  } catch (e) {
    addChatMessage('system', `<div class="content error-message">加载失败</div>`);
  }
}


function navigateManualWriter() {
  navigate('writing');
  renderManualWriter();
}


// ══════════════════════════════════════════════════════════════
// Manual Chapter Writing
// ══════════════════════════════════════════════════════════════

let manualState = { phase: 'outline', vol: 1, ch: 1 };

function renderManualWriter(presetVol, presetCh) {
  const vol = presetVol || parseInt(document.getElementById('write-vol').value) || 1;
  const ch = presetCh || parseInt(document.getElementById('write-ch').value) || 1;
  manualState = { phase: 'outline', vol, ch };

  // Show loading state immediately
  $content.innerHTML = `<div class="loading">正在加载手动创作界面...</div>`;

  function renderManualUI(existingOutline, existingText) {
    $content.innerHTML = `
      <div class="section-header">
        <h2>手动创作 — 第${vol}卷第${ch}章</h2>
        <div style="display:flex;gap:8px">
          <button class="btn btn-sm btn-secondary" onclick="renderChapterWriter()">← 返回</button>
        </div>
      </div>

      <div id="manual-writer">
        <div class="manual-phase-tabs" style="margin-bottom:16px">
          <button id="tab-outline-btn" class="btn btn-primary btn-sm" onclick="switchManualPhase('outline')">阶段 1：大纲</button>
          <button id="tab-text-btn" class="btn btn-sm btn-secondary" onclick="switchManualPhase('text')">阶段 2：正文</button>
        </div>

        <div id="manual-outline-section">
          <label style="font-weight:600;display:block;margin-bottom:8px">章节大纲</label>
          <textarea id="manual-outline-editor" class="manual-editor-textarea"
            placeholder="在此编写章节大纲...&#10;&#10;## 本章定位&#10;- &#10;&#10;## 核心事件&#10;1. &#10;2. &#10;&#10;## 人物目标&#10;- &#10;&#10;输入部分内容后，可点击「AI 接管」让 AI 帮你补全。"
            style="width:100%;min-height:300px;font-family:inherit;font-size:14px;padding:12px;border:1px solid #ddd;border-radius:8px;resize:vertical"
          >${existingOutline}</textarea>
          <div style="margin-top:12px;display:flex;gap:8px">
            <button class="btn btn-primary btn-sm" onclick="aiTakeoverOutline()">AI 接管大纲</button>
            <button class="btn btn-success btn-sm" onclick="saveManualOutline()">保存大纲</button>
          </div>
          <div id="manual-outline-status" style="margin-top:8px;font-size:13px;color:#666"></div>
        </div>

        <div id="manual-text-section" style="display:none">
          <label style="font-weight:600;display:block;margin-bottom:8px">章节正文</label>
          <textarea id="manual-text-editor" class="manual-editor-textarea"
            placeholder="在此编写章节正文...&#10;&#10;输入部分内容后，可点击「AI 接管」让 AI 从断点处续写。"
            style="width:100%;min-height:400px;font-family:inherit;font-size:14px;padding:12px;border:1px solid #ddd;border-radius:8px;resize:vertical"
          >${existingText}</textarea>
          <div style="margin-top:12px;display:flex;gap:8px">
            <button class="btn btn-primary btn-sm" onclick="aiTakeoverText()">AI 接管正文</button>
            <button class="btn btn-success btn-sm" onclick="saveManualText()">保存并更新</button>
          </div>
          <div id="manual-text-status" style="margin-top:8px;font-size:13px;color:#666"></div>
        </div>
      </div>
    `;
  }

  // Load existing content if any, but always render the UI (even if loading fails)
  Promise.all([
    API.outline.chapter(AppState.currentProject, vol, ch).catch(() => ({ content: '' })),
    API.chapters.get(AppState.currentProject, vol, ch).catch(() => ({ content: '' })),
  ]).then(([outlineData, chapterData]) => {
    renderManualUI(outlineData.content || '', chapterData.content || '');
  }).catch(() => {
    renderManualUI('', '');
  });
}

function switchManualPhase(phase) {
  manualState.phase = phase;
  document.getElementById('manual-outline-section').style.display = phase === 'outline' ? 'block' : 'none';
  document.getElementById('manual-text-section').style.display = phase === 'text' ? 'block' : 'none';
  document.getElementById('tab-outline-btn').className = 'btn btn-sm ' + (phase === 'outline' ? 'btn-primary' : 'btn-secondary');
  document.getElementById('tab-text-btn').className = 'btn btn-sm ' + (phase === 'text' ? 'btn-primary' : 'btn-secondary');
}

async function saveManualOutline() {
  const project = AppState.currentProject;
  const content = document.getElementById('manual-outline-editor').value;
  const statusEl = document.getElementById('manual-outline-status');

  try {
    await API.outline.saveChapter(project, manualState.vol, manualState.ch, content);
    statusEl.innerHTML = '<span style="color:#27ae60">大纲已保存 ✓</span>';
    // Switch to text phase
    switchManualPhase('text');
  } catch (e) {
    statusEl.innerHTML = `<span style="color:#e74c3c">保存失败：${e.message}</span>`;
  }
}

async function saveManualText() {
  const project = AppState.currentProject;
  const content = document.getElementById('manual-text-editor').value;
  const statusEl = document.getElementById('manual-text-status');

  try {
    await API.chapters.save(project, manualState.vol, manualState.ch, content, '');
    statusEl.innerHTML = '<span style="color:#27ae60">正文已保存 ✓ 正在触发知识同步...</span>';

    // Trigger sync
    try {
      const result = await API.sync.trigger(project, manualState.vol, manualState.ch);
      if (result.success) {
        statusEl.innerHTML = '<span style="color:#27ae60">正文已保存，创作依据已更新 ✓</span>';
      } else {
        statusEl.innerHTML = `<span style="color:#e67e22">正文已保存，但同步可能未完成：${result.error || ''}</span>`;
      }
    } catch (e) {
      statusEl.innerHTML = `<span style="color:#e67e22">正文已保存，但同步请求失败：${e.message}</span>`;
    }
  } catch (e) {
    statusEl.innerHTML = `<span style="color:#e74c3c">保存失败：${e.message}</span>`;
  }
}

function aiTakeoverOutline() {
  const project = AppState.currentProject;
  const vol = manualState.vol;
  const ch = manualState.ch;
  const partialContent = document.getElementById('manual-outline-editor').value || '';

  const statusEl = document.getElementById('manual-outline-status');
  statusEl.innerHTML = '<span style="color:#3498db">AI 正在补全大纲...</span>';

  chapterSSE = new SSEClient();
  chapterSSE.onEvent = (event) => {
    switch (event.type) {
      case 'status':
        statusEl.innerHTML = `<span style="color:#3498db">${event.message}</span>`;
        break;
      case 'outline_chunk':
        const editor = document.getElementById('manual-outline-editor');
        editor.value += event.text;
        editor.scrollTop = editor.scrollHeight;
        break;
      case 'outline':
        const ed = document.getElementById('manual-outline-editor');
        // Only replace if AI generated something new beyond the partial
        if (event.markdown && event.markdown.length > partialContent.length) {
          ed.value = event.markdown;
          ed.scrollTop = ed.scrollHeight;
        }
        break;
      case 'done':
        statusEl.innerHTML = '<span style="color:#27ae60">AI 接管完成 ✓ 请检查并保存。</span>';
        break;
      case 'error':
        statusEl.innerHTML = `<span style="color:#e74c3c">AI 接管失败：${event.message}</span>`;
        break;
    }
  };
  chapterSSE.onError = (err) => {
    statusEl.innerHTML = `<span style="color:#e74c3c">连接出错：${err.message}</span>`;
  };

  chapterSSE.connect('/api/chapters/generate', {
    body: {
      project, volume: vol, chapter: ch,
      mode: 'continue_outline',
      partial_content: partialContent,
      instruction: '',
    },
  });
}

function aiTakeoverText() {
  const project = AppState.currentProject;
  const vol = manualState.vol;
  const ch = manualState.ch;
  const partialContent = document.getElementById('manual-text-editor').value || '';

  const statusEl = document.getElementById('manual-text-status');
  statusEl.innerHTML = '<span style="color:#3498db">AI 正在续写正文...</span>';

  chapterSSE = new SSEClient();
  chapterSSE.onEvent = (event) => {
    switch (event.type) {
      case 'status':
        statusEl.innerHTML = `<span style="color:#3498db">${event.message}</span>`;
        break;
      case 'text_chunk':
        const editor = document.getElementById('manual-text-editor');
        editor.value += event.text;
        editor.scrollTop = editor.scrollHeight;
        break;
      case 'text_complete':
        statusEl.innerHTML = '<span style="color:#27ae60">AI 续写完成 ✓ 请检查后保存。</span>';
        break;
      case 'done':
        statusEl.innerHTML = '<span style="color:#27ae60">AI 续写完成 ✓ 请检查后保存。</span>';
        break;
      case 'error':
        statusEl.innerHTML = `<span style="color:#e74c3c">AI 续写失败：${event.message}</span>`;
        break;
    }
  };
  chapterSSE.onError = (err) => {
    statusEl.innerHTML = `<span style="color:#e74c3c">连接出错：${err.message}</span>`;
  };

  chapterSSE.connect('/api/chapters/generate', {
    body: {
      project, volume: vol, chapter: ch,
      mode: 'continue_text',
      partial_content: partialContent,
      instruction: '',
    },
  });
}
