// toast.js — Premium toast notification system (Phase 13-06)

class ToastManager {
  constructor() {
    this.container = null;
    this.maxVisible = 3;
    this.init();
  }

  init() {
    if (!this.container) {
      this.container = document.getElementById('toast-container');
    }
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  }

  show(message, options = {}) {
    var type = options.type || 'info';
    var duration = options.duration !== undefined ? options.duration : 3000;
    var action = options.action || null;

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    var icons = {
      success: '\u2713',
      error: '\u2717',
      warning: '\u26A0',
      info: '\u24D8',
    };

    var html = '<span class="toast-icon">' + icons[type] + '</span>';
    html += '<span class="toast-message">' + this.escapeHtml(String(message)) + '</span>';
    if (action) {
      html += '<button class="toast-action">' + this.escapeHtml(String(action.label)) + '</button>';
    }
    html += '<button class="toast-close" aria-label="Dismiss">\u00D7</button>';
    toast.innerHTML = html;

    // Action handler
    if (action && action.onClick) {
      var actionBtn = toast.querySelector('.toast-action');
      if (actionBtn) actionBtn.addEventListener('click', (function() {
        action.onClick();
        this.dismiss(toast);
      }).bind(this));
    }

    // Close handler
    var closeBtn = toast.querySelector('.toast-close');
    if (closeBtn) closeBtn.addEventListener('click', this.dismiss.bind(this, toast));

    // Enter animation
    var self = this;
    requestAnimationFrame(function() {
      toast.classList.add('toast-visible');
    });

    // Cap visible toasts
    var visible = this.container.querySelectorAll('.toast-visible');
    if (visible.length >= this.maxVisible) {
      this.dismiss(visible[0]);
    }

    this.container.appendChild(toast);

    // Auto dismiss
    var timer = setTimeout(function() { self.dismiss(toast); }, duration);
    toast._dismissTimer = timer;

    return toast;
  }

  dismiss(toast) {
    if (!toast || !toast.parentNode) return;
    clearTimeout(toast._dismissTimer);
    toast.classList.remove('toast-visible');
    toast.classList.add('toast-exit');
    var self = this;
    setTimeout(function() {
      if (toast.parentNode) toast.remove();
    }, 200);
  }

  success(msg, opts) { opts = opts || {}; opts.type = 'success'; return this.show(msg, opts); }
  error(msg, opts) { opts = opts || {}; opts.type = 'error'; opts.duration = (opts.duration !== undefined ? opts.duration : 5000); return this.show(msg, opts); }
  warning(msg, opts) { opts = opts || {}; opts.type = 'warning'; opts.duration = (opts.duration !== undefined ? opts.duration : 4000); return this.show(msg, opts); }
  info(msg, opts) { opts = opts || {}; opts.type = 'info'; return this.show(msg, opts); }

  escapeHtml(str) {
    if (str === null || str === undefined) return '';
    var div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }
}

// Singleton
var Toast = new ToastManager();
export default Toast;

// Also expose as window.ToastApi for Tauri/Rust calls
window.ToastApi = {
  success: function(msg, opts) { Toast.success(msg, opts); },
  error: function(msg, opts) { Toast.error(msg, opts); },
  warning: function(msg, opts) { Toast.warning(msg, opts); },
  info: function(msg, opts) { Toast.info(msg, opts); },
};
