/** Server-Sent Events handler with optional automatic reconnection */
class SSEClient {
  constructor(options = {}) {
    this.abortController = null;
    this.onEvent = null;
    this.onError = null;
    this.timeout = options.timeout || 300000; // 5 min default
    this._timeoutId = null;

    // Reconnection settings
    this.reconnect = options.reconnect !== false; // default true
    this.maxReconnect = options.maxReconnect || 5;
    this.baseDelay = options.baseDelay || 1000;
    this.maxDelay = options.maxDelay || 30000;
    this.onReconnecting = options.onReconnecting || null;
    this.onComplete = options.onComplete || null;
    this._intentionalDisconnect = false;
    this._reconnectAttempt = 0;
    this._connectUrl = null;
    this._connectOptions = null;
  }

  async connect(url, options = {}) {
    this.disconnect();
    this._intentionalDisconnect = false;
    this.abortController = new AbortController();

    // Stash for retry
    this._connectUrl = url;
    this._connectOptions = options;

    const { method = 'POST', body, headers = {} } = options;

    this._timeoutId = setTimeout(() => {
      this.abortController.abort();
      if (this.onError) this.onError(new Error('SSE 连接超时'));
    }, this.timeout);

    let completed = false;

    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...headers },
        body: body ? JSON.stringify(body) : undefined,
        signal: this.abortController.signal,
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          completed = true;
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (this.onEvent) this.onEvent(data);
            } catch (e) {
              console.error('SSE parse error:', e, 'data:', line.slice(6).substring(0, 200));
            }
          }
        }
      }

      // Natural completion — reset reconnect counter
      this._reconnectAttempt = 0;
      if (this.onComplete) this.onComplete();

    } catch (err) {
      if (err.name === 'AbortError') {
        if (this._intentionalDisconnect) return;
      }

      // Attempt reconnection
      if (this.reconnect && !this._intentionalDisconnect && this._reconnectAttempt < this.maxReconnect) {
        this._reconnectAttempt++;
        const delay = Math.min(
          this.baseDelay * Math.pow(2, this._reconnectAttempt - 1) + Math.random() * 1000,
          this.maxDelay
        );
        if (this.onReconnecting) {
          this.onReconnecting({ attempt: this._reconnectAttempt, delay, error: err });
        }
        console.warn(`SSE reconnecting in ${Math.round(delay)}ms (attempt ${this._reconnectAttempt}/${this.maxReconnect})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        if (!this._intentionalDisconnect) {
          return this._retryConnect();
        }
      } else if (this.onError && !this._intentionalDisconnect) {
        this.onError(err);
      }
    } finally {
      clearTimeout(this._timeoutId);
      this._timeoutId = null;
    }
  }

  async _retryConnect() {
    return this.connect(this._connectUrl, this._connectOptions);
  }

  disconnect() {
    this._intentionalDisconnect = true;
    clearTimeout(this._timeoutId);
    this._timeoutId = null;
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}

/**
 * SSE connection factory. Eliminates 10+ repetitive SSEClient instantiation
 * patterns across chapter-writer.js, outline-tree.js, project-list.js,
 * and settings-chat.js.
 *
 * @param {string} url - SSE endpoint URL
 * @param {object} body - POST body (JSON)
 * @param {object} handlers - { onEvent(data), onError(err), timeout? }
 * @returns {SSEClient}
 */
function createSSEConnection(url, body, handlers = {}) {
  const sse = new SSEClient({ timeout: handlers.timeout || 300000 });
  sse.onEvent = handlers.onEvent || null;
  sse.onError = handlers.onError || null;
  sse.connect(url, { body });
  return sse;
}
