/**
 * AI RESEARCH WORKBENCH - NETWORKING & STREAMING MODULE
 * Secure Server-Sent Events (SSE) streaming client using HTTP POST
 */

export const MOCK_SCENARIOS = {};

/**
 * SEC-01: Secure SSE streaming client using HTTP POST.
 * Transmits API keys and parameters in the POST body,
 * completely preventing credential leakage into URLs or browser history.
 */
export async function fetchSSE(url, payload, eventHandlers, abortSignal) {
  const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    credentials: 'same-origin',
    body: JSON.stringify(payload),
    signal: abortSignal
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let currentEvent = 'message';
  let currentData = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const rawLine of lines) {
      const line = rawLine.replace(/\r$/, '');
      if (line === '') {
        if (currentData) {
          if (eventHandlers[currentEvent]) {
            try {
              eventHandlers[currentEvent]({ data: currentData });
            } catch (err) {
              console.error('SSE handler error for event', currentEvent, err);
            }
          }
          currentEvent = 'message';
          currentData = '';
        }
      } else if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const d = line.slice(5).trim();
        currentData = currentData ? currentData + '\n' + d : d;
      }
    }
  }

  if (buffer) {
    const line = buffer.replace(/\r$/, '');
    if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      const d = line.slice(5).trim();
      currentData = currentData ? currentData + '\n' + d : d;
    }
  }

  if (currentData && eventHandlers[currentEvent]) {
    try {
      eventHandlers[currentEvent]({ data: currentData });
    } catch (err) {
      console.error('SSE handler flush error', err);
    }
  }
}
