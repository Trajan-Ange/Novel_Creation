/** In-page dialog system — replaces browser prompt/confirm/alert */
const Dialog = {
  _resolve: null,
  _overlay: null,

  _createOverlay() {
    if (this._overlay) return this._overlay;
    const overlay = document.createElement('div');
    overlay.className = 'novel-dialog-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this._close(false);
    });
    document.body.appendChild(overlay);
    this._overlay = overlay;
    return overlay;
  },

  _close(value) {
    if (this._resolve) {
      this._resolve(value);
      this._resolve = null;
    }
    if (this._overlay) {
      this._overlay.remove();
      this._overlay = null;
    }
  },

  /** Show a message with an OK button. Returns Promise<void>. */
  alert(message) {
    return new Promise((resolve) => {
      this._resolve = resolve;
      const overlay = this._createOverlay();
      overlay.innerHTML = `
        <div class="novel-dialog">
          <div class="novel-dialog-body">${escapeHtml(message)}</div>
          <div class="novel-dialog-footer">
            <button class="btn btn-primary btn-sm novel-dialog-ok">确定</button>
          </div>
        </div>
      `;
      overlay.querySelector('.novel-dialog-ok').addEventListener('click', () => this._close());
      overlay.querySelector('.novel-dialog-ok').focus();
      this._bindKeyboard(true, false);
    });
  },

  /** Show HTML content with an OK button. Only use with trusted (non-user) markup. */
  alertHtml(html) {
    return new Promise((resolve) => {
      this._resolve = resolve;
      const overlay = this._createOverlay();
      overlay.innerHTML = `
        <div class="novel-dialog">
          <div class="novel-dialog-body">${html}</div>
          <div class="novel-dialog-footer">
            <button class="btn btn-primary btn-sm novel-dialog-ok">确定</button>
          </div>
        </div>
      `;
      overlay.querySelector('.novel-dialog-ok').addEventListener('click', () => this._close());
      overlay.querySelector('.novel-dialog-ok').focus();
      this._bindKeyboard(true, false);
    });
  },

  /** Show a message with OK/Cancel. Returns Promise<boolean>. */
  confirm(message) {
    return new Promise((resolve) => {
      this._resolve = resolve;
      const overlay = this._createOverlay();
      overlay.innerHTML = `
        <div class="novel-dialog">
          <div class="novel-dialog-body">${escapeHtml(message)}</div>
          <div class="novel-dialog-footer">
            <button class="btn btn-secondary btn-sm novel-dialog-cancel">取消</button>
            <button class="btn btn-primary btn-sm novel-dialog-ok">确定</button>
          </div>
        </div>
      `;
      overlay.querySelector('.novel-dialog-ok').addEventListener('click', () => this._close(true));
      overlay.querySelector('.novel-dialog-cancel').addEventListener('click', () => this._close(false));
      overlay.querySelector('.novel-dialog-ok').focus();
      this._bindKeyboard(true, false);
    });
  },

  /** Show a prompt with text input. Returns Promise<string|null>. */
  prompt(message, defaultValue) {
    return new Promise((resolve) => {
      this._resolve = resolve;
      const overlay = this._createOverlay();
      overlay.innerHTML = `
        <div class="novel-dialog">
          <div class="novel-dialog-body">
            <label class="novel-dialog-label">${escapeHtml(message)}</label>
            <input type="text" class="novel-dialog-input" value="${escapeHtml(defaultValue || '')}" maxlength="100">
          </div>
          <div class="novel-dialog-footer">
            <button class="btn btn-secondary btn-sm novel-dialog-cancel">取消</button>
            <button class="btn btn-primary btn-sm novel-dialog-ok">确定</button>
          </div>
        </div>
      `;
      const input = overlay.querySelector('.novel-dialog-input');
      overlay.querySelector('.novel-dialog-ok').addEventListener('click', () => this._close(input.value));
      overlay.querySelector('.novel-dialog-cancel').addEventListener('click', () => this._close(null));
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this._close(input.value);
        if (e.key === 'Escape') this._close(null);
      });
      setTimeout(() => { input.focus(); input.select(); }, 50);
      this._bindKeyboard(true, true);
    });
  },

  _bindKeyboard(enterOk, escapeCancel) {
    const handler = (e) => {
      if (e.key === 'Escape' && escapeCancel) { this._close(null); }
      if (e.key === 'Enter' && enterOk && !this._overlay?.querySelector('input')) {
        this._close(true);
      }
    };
    document.addEventListener('keydown', handler, { once: true });
  }
};
