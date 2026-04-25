// yolo.js — YOLO model and dataset management page
// Uses simple string concatenation for HTML.

import * as api from '../shared/config-api.js';

function e(s) {
  if (s === null || s === undefined) return '';
  var d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

export async function load(c) {
  c.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';
  try {
    var state = window.ShellApi ? window.ShellApi.getState() : null;
    var yolo = (state && state._raw) ? (state._raw.yolo_model || {}) : {};

    var available = yolo.available ? 'AVAILABLE' : 'NOT LOADED';
    var availCls = yolo.available ? 'ok' : 'error';
    var modelName = yolo.model_name || yolo.active_model || '—';
    var modelPath = yolo.model_path || '—';
    var quality = yolo.quality_score ? yolo.quality_score.toFixed(1) : '—';
    var warning = yolo.warning || yolo.error || '—';
    var dsReady = yolo.dataset_ready ? 'READY' : 'NOT READY';
    var dsReadyCls = yolo.dataset_ready ? 'ok' : 'warning';
    var capClass = yolo.capture_class || '—';
    var capCount = yolo.capture_count || 0;
    var capturing = yolo.capturing;
    var capBtnCls = capturing ? 'btn-danger' : 'btn-primary';
    var capBtnTxt = capturing ? 'Stop Capture' : 'Start Capture';

    var opts = '';
    var classes = yolo.available_classes || [];
    for (var i = 0; i < classes.length; i++) {
      opts += '<option value="' + classes[i] + '">' + classes[i] + '</option>';
    }

    var html = '<div class="settings-page">';

    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Model Status</h2></div><div class="section-card">';
    html += '<div class="metric-row"><span class="metric-label">Status</span><span class="health-badge health-' + availCls + '">' + available + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Active Model</span><span class="metric-value font-mono">' + e(modelName) + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Model Path</span><span class="metric-value font-mono text-xs">' + e(modelPath) + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Quality Score</span><span class="metric-value font-mono">' + quality + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Warning</span><span class="metric-value text-warning">' + e(warning) + '</span></div>';
    html += '</div></div>';

    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Dataset</h2></div><div class="section-card">';
    html += '<div class="metric-row"><span class="metric-label">Readiness</span><span class="health-badge health-' + dsReadyCls + '">' + dsReady + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Capture Class</span><span class="metric-value font-mono">' + e(capClass) + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Capture Count</span><span class="metric-value font-mono">' + capCount + '</span></div>';
    html += '</div></div>';

    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Actions</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Capture Class</span><p class="setting-desc">Select which object class to capture for training data</p></div>';
    html += '<select class="select select-sm" id="yolo-capture-class" onchange="if(window.__yoloPage)window.__yoloPage.setCaptureClass(this.value)"><option value="">\u2014 Select \u2014</option>' + opts + '</select></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Dataset Capture</span><p class="setting-desc">' + (capturing ? 'Capturing frames...' : 'Start capturing training images') + '</p></div>';
    html += '<button class="btn btn-sm ' + capBtnCls + '" id="yolo-capture-btn" onclick="if(window.__yoloPage)window.__yoloPage.toggleCapture()">' + capBtnTxt + '</button></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">List Models</span><p class="setting-desc">Show all available YOLO models</p></div>';
    html += '<button class="btn btn-sm btn-secondary" onclick="if(window.__yoloPage)window.__yoloPage.listModels()">List Models</button></div>';
    html += '</div></div>';

    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Available Models</h2></div><div class="section-card" id="yolo-models-list">';
    html += '<p class="text-sm text-muted">Click "List Models" to see available models.</p></div></div>';

    html += '</div>';
    c.innerHTML = html;

    window.__yoloPage = {
      toggleCapture: function() {
        var yoloState = (window.ShellApi && window.ShellApi.getState() && window.ShellApi.getState()._raw) ? window.ShellApi.getState()._raw.yolo_model || {} : {};
        var isCap = yoloState.capturing;
        if (isCap) {
          api.sendYoloCommand('yolo_capture_stop', {}).then(function(res) {
            if (res && res.status === 'ok') {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Capture stopped');
              load(c);
            } else {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Capture failed: ' + (res && res.message || 'unknown'));
            }
          });
        } else {
          var clsEl = document.getElementById('yolo-capture-class');
          var cls = clsEl ? clsEl.value : '';
          api.sendYoloCommand('yolo_capture_start', { class_name: cls }).then(function(res) {
            if (res && res.status === 'ok') {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Capture started' + (cls ? ' (' + cls + ')' : ''));
              load(c);
            } else {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Capture failed: ' + (res && res.message || 'unknown'));
            }
          });
        }
      },
      setCaptureClass: function(cls) {
        // Store in local UI state only — no backend action needed.
        // The class will be sent with yolo_capture_start.
        var clsEl = document.getElementById('yolo-capture-class');
        if (clsEl) clsEl.value = cls;
        if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Capture class set to: ' + cls);
      },
      listModels: function() {
        api.sendYoloCommand('yolo_model_list', {}).then(function(res) {
          if (res && res.status === 'ok' && res.models) {
            var list = document.getElementById('yolo-models-list');
            var activeModel = (window.ShellApi && window.ShellApi.getState() && window.ShellApi.getState()._raw && window.ShellApi.getState()._raw.yolo_model) ?
              (window.ShellApi.getState()._raw.yolo_model.active_model || window.ShellApi.getState()._raw.yolo_model.model_name) : null;
            var mhtml = '';
            for (var j = 0; j < res.models.length; j++) {
              var m = res.models[j];
              var mName = m.name || m;
              var isActive = mName === activeModel;
              mhtml += '<div class="model-item"><div><span class="font-mono text-sm">' + e(mName) + '</span>';
              if (isActive) mhtml += '<span class="health-badge health-ok" style="margin-left:8px">ACTIVE</span>';
              mhtml += '</div><button class="btn btn-xs btn-secondary" onclick="if(window.__yoloPage)window.__yoloPage.activateModel(\'' + mName + '\')">Activate</button></div>';
            }
            list.innerHTML = mhtml || '<p class="text-sm text-muted">No models found.</p>';
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to list models');
          }
        });
      },
      activateModel: function(modelName) {
        api.sendYoloCommand('yolo_activate_model', { model_name: modelName }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Model activated: ' + modelName);
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to activate model: ' + (res && res.message || 'unknown'));
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load YOLO page: ' + e(err.message) + '</p></div>';
  }
}
