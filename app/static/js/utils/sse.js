/** Server-Sent Events handler */
class SSEClient {
  constructor(options = {}) {
    this.abortController = null;
    this.onEvent = null;
    this.onError = null;
    this.timeout = options.timeout || 300000; // 5 min default
    this._timeoutId = null;
  }

  async connect(url, options = {}) {
    this.disconnect();
    this.abortController = new AbortController();

    const { method = 'POST', body, headers = {} } = options;

    // Set up timeout
    this._timeoutId = setTimeout(() => {
      this.abortController.abort();
      if (this.onError) this.onError(new Error('SSE 连接超时'));
    }, this.timeout);

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
        if (done) break;

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
    } catch (err) {
      if (err.name !== 'AbortError' && this.onError) {
        this.onError(err);
      }
    } finally {
      clearTimeout(this._timeoutId);
      this._timeoutId = null;
    }
  }

  disconnect() {
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
