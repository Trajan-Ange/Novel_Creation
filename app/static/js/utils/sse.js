/** Server-Sent Events handler */
class SSEClient {
  constructor() {
    this.abortController = null;
    this.onEvent = null;
    this.onError = null;
  }

  async connect(url, options = {}) {
    this.disconnect();
    this.abortController = new AbortController();

    const { method = 'POST', body, headers = {} } = options;

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
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError' && this.onError) {
        this.onError(err);
      }
    }
  }

  disconnect() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}
