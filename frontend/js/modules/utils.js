/**
 * AI RESEARCH WORKBENCH - UTILITIES MODULE
 * Sanitization, safe URL handling, formatting, and UI helpers
 */

/**
 * XSS Sanitization helper with DOMPurify and offline regex fallback.
 */
export function sanitizeHTML(html) {
  if (!html) return '';
  if (typeof window !== 'undefined' && typeof window.DOMPurify !== 'undefined' && window.DOMPurify.sanitize) {
    return window.DOMPurify.sanitize(html, {
      ADD_TAGS: ['claim', 'math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac'],
      ADD_ATTR: ['data-claim-id', 'data-ref-id', 'data-conf', 'data-page', 'data-fig', 'data-tier', 'data-caveat']
    });
  }
  // Offline / CDN-failure resilient fallback sanitizer
  return String(html)
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi, '')
    .replace(/<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi, '')
    .replace(/<form\b[^<]*(?:(?!<\/form>)<[^<]*)*<\/form>/gi, '')
    .replace(/\son\w+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)/gi, '')
    .replace(/href\s*=\s*(?:'javascript:[^']*'|"javascript:[^"]*"|javascript:[^\s>]+)/gi, 'href="#"');
}

/**
 * Basic character escaping for untrusted user inputs.
 */
export function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Safe URL sanitizer (prevents javascript: protocol injection in hrefs).
 */
export function safeURL(url) {
  if (!url || typeof url !== 'string') return '#';
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith('#') || trimmed.startsWith('/')) {
    return encodeURI(trimmed);
  }
  return '#';
}

/**
 * Safe innerHTML setter: sanitizes rich HTML content via DOMPurify before DOM insertion.
 */
export function safeSetHTML(element, html) {
  if (!element) return;
  element.innerHTML = sanitizeHTML(html);
}

/**
 * Toast notification banner.
 */
export function showToast(msg, toastElement = null) {
  const el = toastElement || document.getElementById('toast-notification');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2600);
}

/**
 * Formats prompt, completion, and total tokens into a readable badge label.
 */
export function formatTokenBreakdown(tot, p, c) {
  if (!tot && !p && !c) return '0 tokens';
  tot = tot || 0;
  p = p || 0;
  c = c || 0;
  if (p > 0 || c > 0) {
    return `${tot.toLocaleString()} tokens (Prompt: ${p.toLocaleString()} | Completion: ${c.toLocaleString()})`;
  }
  return `${tot.toLocaleString()} tokens`;
}

/**
 * Live character counter helper.
 */
export function updateQueryCharCounter(inputEl, counterEl) {
  if (!inputEl || !counterEl) return;
  const len = inputEl.value.length;
  counterEl.textContent = `${len.toLocaleString()} / 1,000`;
  counterEl.classList.remove('counter-warning', 'counter-danger');
  if (len > 1000) {
    counterEl.classList.add('counter-danger');
  } else if (len >= 900) {
    counterEl.classList.add('counter-warning');
  }
}

/**
 * Dynamic auto-growing textarea helper.
 */
export function autoResizeQueryTextarea(textarea) {
  if (!textarea) return;
  textarea.style.height = 'auto';
  const maxHeight = 120; // Auto-grow up to ~5 lines
  const newHeight = Math.min(textarea.scrollHeight, maxHeight);
  textarea.style.height = `${newHeight}px`;
  textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
}

/**
 * Standard debounce utility.
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
