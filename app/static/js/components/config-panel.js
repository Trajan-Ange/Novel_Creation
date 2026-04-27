/** API Configuration panel */
async function openConfig() {
  const modal = document.getElementById('config-modal');
  const statusEl = document.getElementById('cfg-status');
  try {
    const cfg = await API.config.get();
    document.getElementById('cfg-api-key').value = '';
    document.getElementById('cfg-api-key').placeholder = cfg.api_key || 'sk-...';
    document.getElementById('cfg-base-url').value = cfg.base_url || 'https://api.openai.com/v1';
    document.getElementById('cfg-model').value = cfg.model || 'gpt-4o';
    document.getElementById('cfg-temperature').value = cfg.temperature || 0.7;
    document.getElementById('cfg-max-tokens').value = cfg.max_tokens || 4096;
    if (cfg.is_configured) {
      statusEl.innerHTML = '<span style="color:#27ae60">已配置（密钥已保存，输入框留空则不清除）</span>';
    } else {
      statusEl.innerHTML = '<span style="color:#e67e22">未配置 API 密钥</span>';
    }
  } catch (e) {
    statusEl.innerHTML = '<span style="color:#e74c3c">无法加载配置</span>';
  }
  modal.style.display = 'flex';
}

function closeConfig() {
  document.getElementById('config-modal').style.display = 'none';
}

async function saveConfig() {
  const apiKey = document.getElementById('cfg-api-key').value.trim();
  const statusEl = document.getElementById('cfg-status');
  const saveBtn = document.getElementById('cfg-save-btn');

  // If no new key entered but already configured, keep existing
  const cfg = {
    api_key: apiKey,
    base_url: document.getElementById('cfg-base-url').value.trim() || 'https://api.openai.com/v1',
    model: document.getElementById('cfg-model').value.trim() || 'gpt-4o',
    temperature: parseFloat(document.getElementById('cfg-temperature').value) || 0.7,
    max_tokens: parseInt(document.getElementById('cfg-max-tokens').value) || 4096,
  };

  // If no new key, we need to check if one exists already
  if (!apiKey) {
    try {
      const existing = await API.config.get();
      if (existing.api_key && existing.api_key.includes('****')) {
        // User didn't change the key, keep the existing one
        cfg.api_key = '';  // Backend will keep old key if new one is empty
      }
    } catch (e) {}
  }

  saveBtn.disabled = true;
  saveBtn.textContent = '保存中...';
  statusEl.innerHTML = '<span style="color:#999">正在保存...</span>';

  try {
    const result = await API.config.save(cfg);
    if (result.success) {
      AppState.apiConfigured = true;
      statusEl.innerHTML = '<span style="color:#27ae60">配置已保存</span>';
      document.getElementById('cfg-api-key').value = '';
      document.getElementById('cfg-api-key').placeholder = '密钥已保存（已隐藏）';
      saveBtn.textContent = '保存配置';
      saveBtn.disabled = false;
    } else {
      throw new Error(result.error || '保存失败');
    }
  } catch (e) {
    statusEl.innerHTML = '<span style="color:#e74c3c">保存失败：' + (e.message || '网络错误') + '</span>';
    saveBtn.textContent = '保存配置';
    saveBtn.disabled = false;
  }
}

async function testConnection() {
  const statusEl = document.getElementById('cfg-status');
  const testBtn = document.getElementById('cfg-test-btn');

  testBtn.disabled = true;
  testBtn.textContent = '测试中...';
  statusEl.innerHTML = '<span style="color:#999">正在测试连接...</span>';

  // Save config first if there's a new key
  const apiKey = document.getElementById('cfg-api-key').value.trim();
  if (apiKey) {
    await saveConfig();
  }

  try {
    const result = await API.config.test();
    if (result.success) {
      statusEl.innerHTML = '<span style="color:#27ae60">连接成功！模型响应：' + (result.message || 'OK') + '</span>';
    } else {
      statusEl.innerHTML = '<span style="color:#e74c3c">连接失败：' + (result.error || '未知错误') + '</span>';
    }
  } catch (e) {
    statusEl.innerHTML = '<span style="color:#e74c3c">测试请求失败：' + (e.message || '网络错误') + '</span>';
  }

  testBtn.disabled = false;
  testBtn.textContent = '测试连接';
}
