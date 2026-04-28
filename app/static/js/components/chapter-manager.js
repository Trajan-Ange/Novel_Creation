/** Chapter management — browse and view completed chapters by volume-chapter hierarchy */
let chapterMgrState = { volume: 1 };

async function renderChapterManager() {
  const project = AppState.currentProject;

  $content.innerHTML = `
    <div class="section-header">
      <h2>章节管理</h2>
    </div>
    <div class="cm-layout">
      <div class="cm-sidebar" id="cm-sidebar">
        <div class="cm-vol-selector" id="cm-vol-selector">加载中...</div>
        <div class="cm-chapter-list" id="cm-chapter-list"></div>
      </div>
      <div class="cm-viewer" id="cm-viewer">
        <div class="empty-state">
          <h3>选择一个章节</h3>
          <p>从左侧列表选择章节查看正文内容</p>
        </div>
      </div>
    </div>
  `;

  await loadVolumeTabs(project);
}

async function loadVolumeTabs(project) {
  const selector = document.getElementById('cm-vol-selector');
  try {
    const data = await API.outline.volumes(project);
    const vols = data.volumes || [];
    if (!vols.length) {
      selector.innerHTML = '<div class="empty-state" style="padding:20px"><p>暂无卷大纲，请先生成大纲</p></div>';
      document.getElementById('cm-chapter-list').innerHTML = '';
      return;
    }

    selector.innerHTML = vols.map(v => `
      <button class="cm-vol-tab${v === chapterMgrState.volume ? ' active' : ''}"
              onclick="selectVolume(${v})">第${v}卷</button>
    `).join('');

    if (!vols.includes(chapterMgrState.volume)) {
      chapterMgrState.volume = vols[0];
      selector.querySelectorAll('.cm-vol-tab').forEach((b, i) => {
        b.classList.toggle('active', i === 0);
      });
    }

    await loadChapterList(project, chapterMgrState.volume);
  } catch (e) {
    selector.innerHTML = '<div class="error-message">加载卷列表失败</div>';
  }
}

async function selectVolume(vol) {
  const project = AppState.currentProject;
  chapterMgrState.volume = vol;
  document.querySelectorAll('.cm-vol-tab').forEach(b => {
    b.classList.toggle('active', parseInt(b.textContent.match(/\d+/)[0]) === vol);
  });
  await loadChapterList(project, vol);
}

async function loadChapterList(project, vol) {
  const listEl = document.getElementById('cm-chapter-list');
  listEl.innerHTML = '<div class="loading" style="padding:20px;font-size:13px">加载中...</div>';

  try {
    const [chaptersData, outlineData] = await Promise.all([
      API.chapters.list(project, vol),
      API.outline.chapterList(project, vol),
    ]);

    const writtenChaps = chaptersData.chapters || [];
    const outlinedChaps = outlineData.chapters || [];
    const allChaps = [...new Set([...writtenChaps, ...outlinedChaps])].sort((a, b) => a - b);

    if (!allChaps.length) {
      listEl.innerHTML = '<div class="empty-state" style="padding:20px"><p>该卷暂无章节</p></div>';
      return;
    }

    const maxChap = Math.max(...allChaps, 1);
    const html = [];
    for (let ch = 1; ch <= maxChap; ch++) {
      const hasContent = writtenChaps.includes(ch);
      const hasOutline = outlinedChaps.includes(ch);
      let statusClass = 'cm-no-content';
      let statusText = '无内容';
      if (hasContent) {
        statusClass = 'cm-has-content';
        statusText = '已写作';
      } else if (hasOutline) {
        statusClass = 'cm-has-outline';
        statusText = '有大纲';
      }
      const activeClass = chapterMgrState.chapter === ch ? ' active' : '';
      html.push(`
        <div class="cm-chapter-item ${statusClass}${activeClass}" onclick="viewChapter(${vol}, ${ch})" id="cm-item-${ch}">
          <span class="cm-ch-num">第${ch}章</span>
          <span class="cm-ch-status">${statusText}</span>
        </div>
      `);
    }
    listEl.innerHTML = html.join('');
  } catch (e) {
    listEl.innerHTML = '<div class="error-message">加载章节列表失败</div>';
  }
}

async function viewChapter(vol, ch) {
  const project = AppState.currentProject;
  chapterMgrState.chapter = ch;
  chapterMgrState.volume = vol;

  // Highlight active item
  document.querySelectorAll('.cm-chapter-item').forEach(el => el.classList.remove('active'));
  const item = document.getElementById(`cm-item-${ch}`);
  if (item) item.classList.add('active');

  const viewer = document.getElementById('cm-viewer');
  viewer.innerHTML = '<div class="loading" style="padding:40px">加载章节内容...</div>';

  try {
    const [chapterData, outlineData] = await Promise.all([
      API.chapters.get(project, vol, ch),
      API.outline.chapter(project, vol, ch),
    ]);

    const content = chapterData.content || '';
    const outline = outlineData.content || '';

    // Word count
    const wordCount = content.replace(/\s/g, '').length;

    viewer.innerHTML = `
      <div class="cm-toolbar">
        <h3>第${vol}卷 第${ch}章</h3>
        <div class="cm-toolbar-actions">
          <span class="cm-word-count">约 ${wordCount.toLocaleString()} 字</span>
          ${content ? '<button class="btn btn-sm btn-primary" onclick="jumpToWrite(' + vol + ',' + ch + ')">编辑/重写</button>' : ''}
        </div>
      </div>
      <div class="cm-tabs">
        <button class="cm-tab active" onclick="switchChapterTab('content')" id="cm-tab-content-btn">正文</button>
        <button class="cm-tab" onclick="switchChapterTab('outline')" id="cm-tab-outline-btn">大纲</button>
      </div>
      <div class="cm-tab-content" id="cm-tab-content-panel">
        ${content ? `<div class="markdown-content">${marked.parse(content)}</div>` : '<div class="empty-state"><p>该章节尚未生成正文</p></div>'}
      </div>
      <div class="cm-tab-content" id="cm-tab-outline-panel" style="display:none">
        ${outline ? `<div class="markdown-content">${marked.parse(outline)}</div>` : '<div class="empty-state"><p>该章节暂无大纲</p></div>'}
      </div>
    `;
  } catch (e) {
    viewer.innerHTML = '<div class="error-message">加载章节失败：' + escapeHtml(String(e.message || e)) + '</div>';
  }
}

function switchChapterTab(tab) {
  document.querySelectorAll('.cm-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`cm-tab-${tab}-btn`).classList.add('active');
  document.getElementById('cm-tab-content-panel').style.display = tab === 'content' ? 'block' : 'none';
  document.getElementById('cm-tab-outline-panel').style.display = tab === 'outline' ? 'block' : 'none';
}

function jumpToWrite(vol, ch) {
  if (typeof writeState !== 'undefined') {
    writeState.volume = vol;
    writeState.chapter = ch;
    writeState.phase = 'idle';
  }
  navigate('writing');
}
