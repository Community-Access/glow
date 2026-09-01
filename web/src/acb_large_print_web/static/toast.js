/**
 * GLOW Toast Notification System
 *
 * Exposes window.GLOW.toast(message, type) where type is one of:
 *   'success' | 'error' | 'info' (default)
 *
 * Also wires up [data-copy-target] buttons globally for clipboard copy.
 */
(function () {
  'use strict';

  function createToast(msg, type) {
    var container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'false');
      document.body.appendChild(container);
    }
    var toast = document.createElement('div');
    toast.className = 'toast toast--' + (type || 'info');
    toast.setAttribute('role', 'status');
    toast.textContent = msg;
    container.appendChild(toast);
    // Force reflow so transition plays
    void toast.offsetWidth;
    toast.classList.add('toast--visible');
    setTimeout(function () {
      toast.classList.remove('toast--visible');
      toast.addEventListener('transitionend', function () {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, { once: true });
    }, 3500);
  }

  // Expose globally
  window.GLOW = window.GLOW || {};
  window.GLOW.toast = createToast;

  // NOTE: [data-copy-target] clicks are handled by static/inline-handlers.js,
  // which is the single documented owner of that behavior. A duplicate copy
  // listener used to live here, causing every copy to fire twice and announce
  // two or three times. Do not re-add it here.
}());
