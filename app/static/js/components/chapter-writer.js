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
      <label>卷：<input type="number" id="write-vol" value="1" min="1" style="width:60px"></label>
      <label>章：<input type="number" id="write-ch" value="1" min="1" style="width:60px"></label>
      <button class="btn btn-primary btn-sm" onclick="startChapterWrite()">开始写作</button>
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

  const instruction = prompt('请输入特别要求（可选）：') || '';

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

    case 'outline':
      writeState.phase = 'review';
      addChatMessage('outline', `
        <div class="label">章节大纲</div>
        <div class="markdown-content">${marked.parse(event.markdown || '')}</div>
      `);

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
      // Add input for feedback
      addChatInput('请输入修改意见或「确认」', (value) => {
        handleOutlineFeedback(value, project, vol, ch);
      });
      break;

    case 'awaiting_confirmation':
      addChatMessage('system', '<div class="content">大纲已生成，请确认。输入修改意见或「确认」。</div>');
      addChatInput('请输入修改意见或「确认」', (value) => {
        handleOutlineFeedback(value, project, vol, ch);
      });
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
