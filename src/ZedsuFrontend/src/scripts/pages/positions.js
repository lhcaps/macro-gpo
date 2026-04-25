// positions.js — Combat Positions management page (Phase 13-05 enhanced)
// Uses simple string concatenation for HTML.

import * as api from '../shared/config-api.js';

var POSITION_NAMES = ['melee', 'skill_1', 'skill_2', 'skill_3', 'ultimate', 'dash', 'block', 'aim_center', 'return_lobby'];

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
    var positions = (state && state._raw && state._raw.positions) ? state._raw.positions : await api.getPositions().catch(function() { return []; });

    var posMap = {};
    for (var i = 0; i < positions.length; i++) {
      posMap[positions[i].name] = positions[i];
    }

    var cards = '';
    for (var j = 0; j < POSITION_NAMES.length; j++) {
      var name = POSITION_NAMES[j];
      var pos = posMap[name];
      var hasPos = pos && (pos.x !== undefined || pos.y !== undefined);
      var disabled = hasPos ? '' : 'disabled';
      var btnCls = hasPos ? '' : 'btn-primary';
      var coords = hasPos ? ('x:' + Math.round(pos.x || 0) + ' y:' + Math.round(pos.y || 0)) : '';
      var enabled = pos && pos.enabled !== false ? 'checked ' : '';

      cards += '<div class="position-card" data-position="' + name + '">';
      cards += '<div class="position-card-header">';
      cards += '<span class="position-name font-mono">' + name + '</span>';
      cards += '<label class="toggle toggle-xs"><input type="checkbox" id="pos-enabled-' + name + '" ' + enabled + 'onchange="if(window.__positionsPage)window.__positionsPage.toggleEnabled(\'' + name + '\',this.checked)" /><span class="toggle-track"></span></label>';
      cards += '</div>';
      cards += '<div class="position-card-body">';
      if (hasPos) {
        cards += '<div class="position-coords font-mono text-xs text-muted" id="pos-coords-' + name + '">' + coords + '</div>';
      } else {
        cards += '<p class="text-xs text-muted">Not configured</p>';
      }
      cards += '</div>';
      cards += '<div class="position-test-result" id="test-result-' + name + '" style="display:none;"></div>';
      cards += '<div class="position-card-actions">';
      cards += '<button class="btn btn-xs ' + btnCls + '" onclick="if(window.__positionsPage)window.__positionsPage.pickPosition(\'' + name + '\')">' + (hasPos ? 'Repick' : 'Pick') + '</button>';
      cards += '<button class="btn btn-xs" onclick="if(window.__positionsPage)window.__positionsPage.testPosition(\'' + name + '\',event)" ' + disabled + '>Test</button>';
      cards += '<button class="btn btn-xs" onclick="if(window.__positionsPage)window.__positionsPage.editPosition(\'' + name + '\')" ' + (hasPos ? '' : 'disabled ') + '>Edit</button>';
      cards += '<button class="btn btn-xs btn-danger-text" onclick="if(window.__positionsPage)window.__positionsPage.deletePosition(\'' + name + '\')" ' + disabled + '>Delete</button>';
      cards += '</div></div>';
    }

    var html = '<div class="settings-page">';
    html += '<div class="settings-section"><div class="section-header">';
    html += '<h2 class="section-title">Combat Positions</h2>';
    html += '<p class="section-desc">Define and manage combat action positions on screen. Pick each position by clicking its location in the game window.</p>';
    html += '</div><div class="position-grid">' + cards + '</div></div>';

    html += '<div class="settings-section"><div class="section-header">';
    html += '<h2 class="section-title">Import / Export</h2>';
    html += '</div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Export Positions</span><p class="setting-desc">Download all positions as JSON</p></div>';
    html += '<button class="btn btn-sm" onclick="if(window.__positionsPage)window.__positionsPage.exportPositions()">Export JSON</button></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Import Positions</span><p class="setting-desc">Load positions from JSON file</p></div>';
    html += '<input type="file" accept=".json" id="import-positions-file" style="display:none" onchange="if(window.__positionsPage)window.__positionsPage.importPositions(this)" />';
    html += '<button class="btn btn-sm" onclick="document.getElementById(\'import-positions-file\').click()">Import JSON</button></div>';
    html += '</div></div>';
    html += '</div>';
    c.innerHTML = html;

    window.__positionsPage = {
      toggleEnabled: function(name, enabled) {
        api.getPositions().catch(function() { return []; }).then(function(positions) {
          for (var i = 0; i < positions.length; i++) {
            if (positions[i].name === name) {
              positions[i].enabled = enabled;
              api.setPosition(name, positions[i]);
              break;
            }
          }
        });
      },
      pickPosition: function(name) {
        if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Starting position picker for: ' + name);
        api.sendYoloCommand('pick_position', { name: name }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ' position set');
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Position selection cancelled or failed');
          }
        });
      },
      testPosition: function(name, evt) {
        var btn = evt && evt.target;
        if (btn) { btn.disabled = true; btn.textContent = 'Testing...'; }
        var el = document.getElementById('test-result-' + name);
        if (el) { el.innerHTML = '<span style="color:var(--color-warning)">Testing...</span>'; el.style.display = 'block'; el.className = 'position-test-result testing'; }
        api.resolvePosition(name)
          .then(function(res) {
            if (res && res.status === 'ok') {
              var pos = res.position || res;
              var x = pos.x !== undefined ? pos.x : (pos[0] !== undefined ? pos[0] : 0);
              var y = pos.y !== undefined ? pos.y : (pos[1] !== undefined ? pos[1] : 0);
              if (el) { el.innerHTML = '<span style="color:var(--color-running)">&#x2713; Clicked at (' + Math.round(x) + ', ' + Math.round(y) + ')</span>'; el.className = 'position-test-result'; }
            } else {
              if (el) { el.innerHTML = '<span style="color:var(--color-error)">&#x2717; ' + (res && res.message || 'Failed') + '</span>'; el.className = 'position-test-result'; }
            }
          })
          .catch(function(err) {
            if (el) { el.innerHTML = '<span style="color:var(--color-error)">&#x2717; ' + (err.message || 'Test failed') + '</span>'; el.className = 'position-test-result'; }
          })
          .then(function() {
            if (btn) { btn.disabled = false; btn.textContent = 'Test'; }
          });
      },
      editPosition: function(name) {
        var card = document.querySelector('[data-position="' + name + '"]');
        if (!card) return;
        var existing = card.querySelector('.position-edit-form');
        if (existing) { existing.remove(); return; }
        api.getPositions().then(function(positions) {
          var pos = null;
          for (var i = 0; i < positions.length; i++) {
            if (positions[i].name === name) { pos = positions[i]; break; }
          }
          var form = document.createElement('div');
          form.className = 'position-edit-form';
          form.innerHTML = '<div class="coord-inputs">' +
            '<label>X <input type="number" id="edit-px" value="' + Math.round(pos && pos.x !== undefined ? pos.x : 0) + '" step="1" style="width:100%" /></label>' +
            '<label>Y <input type="number" id="edit-py" value="' + Math.round(pos && pos.y !== undefined ? pos.y : 0) + '" step="1" style="width:100%" /></label>' +
            '</div>' +
            '<div class="form-actions">' +
            '<button class="btn btn-xs" onclick="if(window.__positionsPage)window.__positionsPage.saveEditPosition(\'' + name + '\')">Save</button>' +
            '<button class="btn btn-xs" onclick="this.closest(\'.position-edit-form\').remove()">Cancel</button>' +
            '</div>';
          card.appendChild(form);
        });
      },
      saveEditPosition: function(name) {
        var x = parseInt((document.getElementById('edit-px') || {}).value) || 0;
        var y = parseInt((document.getElementById('edit-py') || {}).value) || 0;
        api.getPositions().then(function(positions) {
          var pos = null;
          for (var i = 0; i < positions.length; i++) {
            if (positions[i].name === name) { pos = positions[i]; break; }
          }
          api.setPosition(name, {
            x: x,
            y: y,
            enabled: pos && pos.enabled !== false,
          }).then(function(res) {
            if (res && res.status === 'ok') {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ' position updated');
              load(c);
            } else {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to update position');
            }
          });
        });
      },
      deletePosition: function(name) {
        if (!confirm('Delete position "' + name + '"?')) return;
        api.deletePosition(name).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ' deleted');
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to delete position');
          }
        });
      },
      exportPositions: function() {
        api.getPositions().catch(function() { return []; }).then(function(positions) {
          var json = JSON.stringify(positions, null, 2);
          var blob = new Blob([json], { type: 'application/json' });
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url;
          a.download = 'zedsu-positions-' + Date.now() + '.json';
          a.click();
          URL.revokeObjectURL(url);
          if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Positions exported');
        });
      },
      importPositions: function(fileInput) {
        var file = fileInput.files[0];
        if (!file) return;
        file.text().then(function(text) {
          try {
            var parsed = JSON.parse(text);
            if (!Array.isArray(parsed)) throw new Error('Expected an array');
            var validPositions = [];
            for (var k = 0; k < parsed.length; k++) {
              if (parsed[k] && parsed[k].name && typeof parsed[k].name === 'string' &&
                  (parsed[k].x !== undefined || parsed[k].y !== undefined)) {
                if (typeof parsed[k].x !== 'number' || typeof parsed[k].y !== 'number') {
                  throw new Error('Position "' + parsed[k].name + '" has non-numeric coordinates');
                }
                validPositions.push(parsed[k]);
              }
            }
            if (validPositions.length === 0) {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.warning('No valid positions found in file');
              return;
            }
            Promise.all(validPositions.map(function(p) {
              return api.setPosition(p.name, p);
            })).then(function(results) {
              var saved = results.filter(function(r) { return r && r.status === 'ok'; }).length;
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Imported ' + saved + ' positions');
              load(c);
            }).catch(function() {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Import failed');
            });
          } catch (e) {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Invalid JSON: ' + e.message);
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load Positions page: ' + e(err.message) + '</p></div>';
  }
}
