// confirm.js — Confirm dialog overlay for dangerous actions (Phase 13-06)

class ConfirmDialog {
  constructor() {
    this.overlay = null;
    this.resolvePromise = null;
    this.init();
  }

  init() {
    this.overlay = document.getElementById('confirm-overlay');
    if (!this.overlay) return;

    var self = this;
    var cancelBtn = document.getElementById('confirm-cancel');
    var okBtn = document.getElementById('confirm-ok');

    if (cancelBtn) cancelBtn.addEventListener('click', function() { self.resolve(false); });
    if (okBtn) okBtn.addEventListener('click', function() { self.resolve(true); });

    // Close on overlay click (not dialog box click)
    this.overlay.addEventListener('click', function(e) {
      if (e.target === self.overlay) self.resolve(false);
    });

    // Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && self.overlay.style.display !== 'none') {
        self.resolve(false);
      }
    });
  }

  show(options) {
    options = options || {};
    var title = options.title || 'Confirm';
    var message = options.message || 'Are you sure?';
    var confirmLabel = options.confirmLabel || 'Confirm';
    var cancelLabel = options.cancelLabel || 'Cancel';
    var danger = options.danger || false;

    var titleEl = document.getElementById('confirm-title');
    var messageEl = document.getElementById('confirm-message');
    var okBtn = document.getElementById('confirm-ok');
    var cancelBtnEl = document.getElementById('confirm-cancel');

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = String(message);
    if (okBtn) {
      okBtn.textContent = confirmLabel;
      okBtn.className = danger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm';
    }
    if (cancelBtnEl) cancelBtnEl.textContent = cancelLabel;

    this.overlay.style.display = 'flex';

    var self = this;
    return new Promise(function(resolve) {
      self.resolvePromise = resolve;
    });
  }

  resolve(value) {
    this.overlay.style.display = 'none';
    if (this.resolvePromise) {
      this.resolvePromise(value);
      this.resolvePromise = null;
    }
  }
}

var Confirm = new ConfirmDialog();
export default Confirm;

// Global convenience — replaces window.confirm with a styled version
// but falls back to native confirm if overlay not found
window.confirm = function(message, options) {
  options = options || {};
  options.message = message;
  return Confirm.show(options);
};

// Also expose as ConfirmApi
window.ConfirmApi = {
  show: function(opts) { return Confirm.show(opts); },
};
