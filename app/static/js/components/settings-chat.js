/** Interactive chat-based creation component — works for settings & outlines */

let settingsChatClient = null;
let settingsChatHistory = [];
let settingsChatType = '';
let settingsChatReady = false;
let settingsChatStreaming = false;
let settingsChatVolume = 1;
let settingsChatChapter = 1;
let settingsChatOnClose = null;  // called when user clicks "back"

const SETTING_LABELS = {
  world: '世界设定',
  character: '人物设定',
  timeline: '时间线',
  relationship: '人物关系',
  style: '风格指南',
  book_outline: '全书大纲',
  volume_outline: '卷大纲',
  chapter_outline: '章节大纲',
};

function openSettingsChat(type) {
  settingsChatOnClose = () => { loadSettingsTab(currentSettingsTab); };
  settingsChatVolume = 1;
  settingsChatChapter = 1;
  _initChatUI(
    'settings-content',
    type,
    'calc(100vh - 220px)',
    settingsChatOnClose
  );
}

function openOutlineChat(type, vol, ch) {
  settingsChatOnClose = () => {
    loadOutlineTree(AppState.currentProject);
    if (type === 'book_outline') viewOutline('book');
    else if (type === 'volume_outline') viewOutline('volume', vol);
    else viewOutline('chapter', vol, ch);
  };
  settingsChatVolume = vol || 1;
  settingsChatChapter = ch || 1;
  _initChatUI(
    'outline-detail',
    type,
    'calc(100vh - 280px)',
    settingsChatOnClose
  );
}

function _initChatUI(containerId, type, height, onClose) {
  const project = AppState.currentProject;
  if (!project) return;

  settingsChatType = type;
  settingsChatHistory = [];
  settingsChatReady = false;
  settingsChatStreaming = false;

  if (settingsChatClient) {
    settingsChatClient.disconnect();
    settingsChatClient = null;
  }

  const container = document.getElementById(containerId);
  const label = SETTING_LABELS[type] || type;
  container.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div>
        <button class="btn btn-secondary btn-sm" onclick="closeChatAndReturn()">返回</button>
        <span style="margin-left:12px;font-weight:600;font-size:15px">AI 对话创建：${label}</span>
      </div>
      <div>
        <button class="btn btn-sm" id="btn-chat-restart" style="display:none;background:#e0e0e0" onclick="restartChat()">重新开始</button>
        <button class="btn btn-success btn-sm" id="btn-chat-generate" style="display:none" onclick="generateFromChat()">生成${label}</button>
      </div>
    </div>
    <div class="chat-container" style="height:${height}">
      <div id="chat-msgs" class="chat-messages"></div>
      <div class="chat-input-area" id="chat-input-area" style="display:none">
        <input type="text" id="chat-input" placeholder="输入你的回答..."
          style="flex:1;padding:10px 16px;border:1px solid #ddd;border-radius:20px;font-size:14px;outline:none"
          onkeydown="if(event.key==='Enter')sendChatMessage()">
        <button class="btn btn-primary btn-sm" id="btn-chat-send" onclick="sendChatMessage()">发送</button>
      </div>
    </div>
  `;

  startChat();
}

function closeChatAndReturn() {
  if (settingsChatClient) {
    settingsChatClient.disconnect();
    settingsChatClient = null;
  }
  if (settingsChatOnClose) settingsChatOnClose();
}

function restartChat() {
  settingsChatHistory = [];
  settingsChatReady = false;
  const msgs = document.getElementById('chat-msgs');
  if (msgs) msgs.innerHTML = '';
  document.getElementById('btn-chat-generate').style.display = 'none';
  document.getElementById('btn-chat-restart').style.display = 'none';
  startChat();
}

async function startChat() {
  const project = AppState.currentProject;
  const type = settingsChatType;

  addChatMsg('system', '正在连接 AI 顾问...');

  settingsChatClient = new SSEClient();
  settingsChatClient.onEvent = (event) => handleChatEvent(event);
  settingsChatClient.onError = (err) => {
    addChatMsg('error', '连接出错：' + err.message);
    settingsChatStreaming = false;
  };

  try {
    await settingsChatClient.connect('/api/settings/chat-generate', {
      body: {
        project: project,
        setting_type: type,
        action: 'start',
        volume: settingsChatVolume,
        chapter: settingsChatChapter,
      },
    });
  } catch (e) {
    addChatMsg('error', '请求失败：' + e.message);
    settingsChatStreaming = false;
  }
}

function handleChatEvent(event) {
  switch (event.type) {
    case 'status':
      updateLastSystemMsg(event.message);
      break;

    case 'text_chunk':
      appendToStreaming(event.text);
      break;

    case 'complete':
      finishStreaming();

      if (event.phase === 'interview') {
        if (event.history) {
          settingsChatHistory = event.history;
        }
        if (event.ready) {
          settingsChatReady = true;
          document.getElementById('btn-chat-generate').style.display = 'inline-flex';
          document.getElementById('btn-chat-restart').style.display = 'inline-flex';
          addChatMsg('system',
            'AI 顾问觉得信息已经足够，点击「<b>生成' + SETTING_LABELS[settingsChatType] + '</b>」按钮开始生成。你也可以继续对话补充更多细节。');
        }
        showChatInput();
      } else if (event.phase === 'generation') {
        settingsChatStreaming = false;
        addChatMsg('system', '<b>已生成并保存。</b>');
        const msgs = document.getElementById('chat-msgs');
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'chat-message system';
        actionsDiv.innerHTML = `
          <div class="content" style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <button class="btn btn-success btn-sm" onclick="closeChatAndReturn()">接受并返回</button>
            <button class="btn btn-secondary btn-sm" onclick="restartChat()">重新对话</button>
          </div>`;
        msgs.appendChild(actionsDiv);
        msgs.scrollTop = msgs.scrollHeight;
        hideChatInput();
      }
      break;

    case 'error':
      settingsChatStreaming = false;
      addChatMsg('error', '出错了：' + event.message);
      showChatInput();
      break;
  }
}

function showChatInput() {
  const area = document.getElementById('chat-input-area');
  const input = document.getElementById('chat-input');
  if (area) area.style.display = 'flex';
  if (input) { input.value = ''; setTimeout(() => input.focus(), 100); }
}

function hideChatInput() {
  const area = document.getElementById('chat-input-area');
  if (area) area.style.display = 'none';
}

function addChatMsg(type, html) {
  const msgs = document.getElementById('chat-msgs');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = `chat-message ${type}`;
  div.innerHTML = `<div class="content">${html}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  if (type !== 'system') {
    const systems = msgs.querySelectorAll('.chat-message.system');
    systems.forEach(s => {
      if (s.textContent.includes('正在') || s.textContent.includes('连接')) s.remove();
    });
  }
}

function updateLastSystemMsg(text) {
  const msgs = document.getElementById('chat-msgs');
  if (!msgs) return;
  const systems = msgs.querySelectorAll('.chat-message.system');
  if (systems.length > 0) {
    const last = systems[systems.length - 1];
    const content = last.querySelector('.content');
    if (content) content.textContent = text;
  } else {
    addChatMsg('system', text);
  }
}

function appendToStreaming(text) {
  const msgs = document.getElementById('chat-msgs');
  if (!msgs) return;
  let streamDiv = document.getElementById('streaming-msg');
  if (!streamDiv) {
    const div = document.createElement('div');
    div.className = 'chat-message ai';
    div.id = 'streaming-msg';
    div.innerHTML = '<div class="content"><span class="streaming-cursor"></span></div>';
    msgs.appendChild(div);
    streamDiv = div;
    settingsChatStreaming = true;
  }
  const content = streamDiv.querySelector('.content');
  const cursor = content.querySelector('.streaming-cursor');
  const textNode = document.createTextNode(text);
  if (cursor) content.insertBefore(textNode, cursor);
  else content.appendChild(textNode);
  msgs.scrollTop = msgs.scrollHeight;
}

function finishStreaming() {
  const streamDiv = document.getElementById('streaming-msg');
  if (streamDiv) {
    const cursor = streamDiv.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();
    streamDiv.removeAttribute('id');
  }
  settingsChatStreaming = false;
}

async function sendChatMessage() {
  if (settingsChatStreaming) return;
  const input = document.getElementById('chat-input');
  if (!input) return;
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  input.disabled = true;
  document.getElementById('btn-chat-send').disabled = true;

  const genKeywords = ['开始生成', '可以了', '好了', '生成吧', '开始', '生成'];
  const wantsGenerate = genKeywords.some(kw => message.includes(kw));

  addChatMsg('user-message', `<b>你：</b>${escapeHtml(message)}`);
  settingsChatHistory.push({ role: 'user', content: message });

  if (wantsGenerate && settingsChatHistory.length >= 2) {
    await generateFromChat();
    return;
  }

  const project = AppState.currentProject;
  const type = settingsChatType;

  settingsChatClient = new SSEClient();
  settingsChatClient.onEvent = (event) => handleChatEvent(event);
  settingsChatClient.onError = (err) => {
    addChatMsg('error', '连接出错：' + err.message);
    settingsChatStreaming = false;
    input.disabled = false;
    document.getElementById('btn-chat-send').disabled = false;
  };

  try {
    await settingsChatClient.connect('/api/settings/chat-generate', {
      body: {
        project: project,
        setting_type: type,
        action: 'chat',
        message: message,
        history: settingsChatHistory.slice(0, -1),
        volume: settingsChatVolume,
        chapter: settingsChatChapter,
      },
    });
  } catch (e) {
    addChatMsg('error', '请求失败：' + e.message);
    settingsChatStreaming = false;
  }

  input.disabled = false;
  document.getElementById('btn-chat-send').disabled = false;
  input.focus();
}

async function generateFromChat() {
  if (settingsChatStreaming) return;

  const project = AppState.currentProject;
  const type = settingsChatType;

  hideChatInput();
  document.getElementById('btn-chat-generate').style.display = 'none';
  document.getElementById('btn-chat-restart').style.display = 'none';
  addChatMsg('system', '正在根据对话内容生成文档...');

  settingsChatClient = new SSEClient();
  settingsChatClient.onEvent = (event) => handleChatEvent(event);
  settingsChatClient.onError = (err) => {
    addChatMsg('error', '生成出错：' + err.message);
    settingsChatStreaming = false;
    showChatInput();
  };

  try {
    await settingsChatClient.connect('/api/settings/chat-generate', {
      body: {
        project: project,
        setting_type: type,
        action: 'generate',
        history: settingsChatHistory,
        volume: settingsChatVolume,
        chapter: settingsChatChapter,
      },
    });
  } catch (e) {
    addChatMsg('error', '生成失败：' + e.message);
    settingsChatStreaming = false;
    showChatInput();
  }
}
