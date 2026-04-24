//! ZedsuFrontend — Tier 3: Rust/Tauri process supervisor + IPC client.
//!
//! Per D-09f: Bottom-up migration — this scaffold is Wave 3, after Tier 1 + Tier 2.
//! Per D-09d: Overlay GUI (glassmorphism HUD) deferred to Phase 10.
//!
//! ## Architecture
//!
//! - BackendManager: spawns ZedsuBackend.exe, health-checks every 3s, respawns on crash
//! - IPC: reqwest HTTP client to port 9761
//! - Tauri commands: get_backend_state, get_hud_state, send_action, restart_backend, stop_backend
//! - Health watch thread: every 3s checks if backend responds
//! - Global shortcuts: F1=emergency_stop, F2=toggle_HUD, F3=toggle_start_stop, F4=show_settings
//! - HUD overlay window: 300x80px transparent overlay at top-right (created in setup)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{Manager, State};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

// ============================================================================
// Constants
// ============================================================================

const BACKEND_EXE: &str = "ZedsuBackend.exe";
const BACKEND_PORT: u16 = 9761;
const BACKEND_HOST: &str = "127.0.0.1";
const HEALTH_INTERVAL_SECS: u64 = 3;
const MAX_RESTART_ATTEMPTS: usize = 3;
const HTTP_TIMEOUT_SECS: u64 = 10;

// ============================================================================
// Types
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendState {
    #[serde(rename = "running")]
    pub running: bool,
    #[serde(rename = "status")]
    pub status: String,
    #[serde(rename = "status_color")]
    pub status_color: String,
    #[serde(rename = "logs")]
    pub logs: Vec<serde_json::Value>,
    #[serde(rename = "combat")]
    pub combat: HashMap<String, serde_json::Value>,
    #[serde(rename = "vision")]
    pub vision: HashMap<String, serde_json::Value>,
    #[serde(rename = "stats")]
    pub stats: HashMap<String, serde_json::Value>,
    #[serde(rename = "config")]
    pub config: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    #[serde(rename = "status")]
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandRequest {
    #[serde(rename = "action")]
    pub action: String,
    #[serde(rename = "payload")]
    pub payload: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandResponse {
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

/// HUD-specific state format optimized for frontend display
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HudState {
    #[serde(rename = "combat_state")]
    pub combat_state: String,
    #[serde(rename = "stats")]
    pub stats: HudStats,
    #[serde(rename = "status_color")]
    pub status_color: String,
    #[serde(rename = "running")]
    pub running: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HudStats {
    #[serde(rename = "kills")]
    pub kills: i32,
    #[serde(rename = "detection_ms")]
    pub detection_ms: i32,
    #[serde(rename = "elapsed")]
    pub elapsed: i64,
}

// ============================================================================
// Application State (HUD visibility)
// ============================================================================

/// Shared application state for HUD visibility and other UI state
pub struct AppState {
    pub hud_visible: Arc<Mutex<bool>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            hud_visible: Arc::new(Mutex::new(true)),
        }
    }
}

// ============================================================================
// Backend Process Manager
// ============================================================================

pub struct BackendManager {
    process: Option<std::process::Child>,
    restart_count: usize,
    running: Arc<Mutex<bool>>,
}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            process: None,
            restart_count: 0,
            running: Arc::new(Mutex::new(false)),
        }
    }

    /// Find the backend executable.
    /// Checks: 1) same dir as frontend, 2) parent dir, 3) src/ subdir
    fn find_backend_exe() -> std::path::PathBuf {
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_default();

        let candidates = vec![
            exe_dir.join(BACKEND_EXE),
            exe_dir.join("src").join(BACKEND_EXE),
            exe_dir
                .parent()
                .map(|p| p.join(BACKEND_EXE))
                .unwrap_or_default(),
        ];

        candidates
            .into_iter()
            .find(|p| p.exists())
            .unwrap_or_else(|| exe_dir.join(BACKEND_EXE))
    }

    /// Spawn ZedsuBackend.exe process.
    pub fn start(&mut self) -> Result<bool, String> {
        self.stop();

        let backend_path = Self::find_backend_exe();
        eprintln!(
            "[ZEDSU] Spawning backend: {}",
            backend_path.display()
        );

        let child = Command::new(&backend_path)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn {}: {}", backend_path.display(), e))?;

        *self.running.lock().unwrap() = true;
        self.process = Some(child);
        self.restart_count = 0;
        Ok(true)
    }

    /// Stop the backend process.
    pub fn stop(&mut self) {
        if let Some(mut child) = self.process.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        *self.running.lock().unwrap() = false;
    }

    /// Check if backend is still alive (process running).
    pub fn is_alive(&mut self) -> bool {
        if let Some(ref mut child) = self.process {
            child.try_wait().ok().flatten().is_none()
        } else {
            false
        }
    }

    /// Attempt to respawn the backend (max MAX_RESTART_ATTEMPTS times).
    pub fn respawn(&mut self) -> Result<(), String> {
        if self.restart_count >= MAX_RESTART_ATTEMPTS {
            return Err(format!(
                "Max restart attempts reached ({})",
                MAX_RESTART_ATTEMPTS
            ));
        }
        self.stop();
        self.restart_count += 1;
        self.start()?;
        Ok(())
    }

    pub fn get_restart_count(&self) -> usize {
        self.restart_count
    }

    // --- HTTP communication ---

    fn http_url(&self, path: &str) -> String {
        format!("http://{}:{}{}", BACKEND_HOST, BACKEND_PORT, path)
    }

    /// GET /health — returns true if backend is responding.
    pub fn health_check(&self) -> bool {
        let url = self.http_url("/health");
        let client = match reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
        {
            Ok(c) => c,
            Err(_) => return false,
        };
        client
            .get(&url)
            .send()
            .ok()
            .map(|r| r.status().is_success())
            .unwrap_or(false)
    }

    /// GET /state — fetch full hierarchical state snapshot.
    pub fn get_state(&self) -> Result<BackendState, String> {
        let url = self.http_url("/state");
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(HTTP_TIMEOUT_SECS))
            .build()
            .map_err(|e| e.to_string())?;

        let resp = client
            .get(&url)
            .send()
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Backend returned HTTP {}", resp.status()));
        }

        resp.json::<BackendState>()
            .map_err(|e| format!("Failed to parse state: {}", e))
    }

    /// POST /command — send action to backend.
    pub fn send_command(
        &self,
        action: &str,
        payload: Option<&serde_json::Value>,
    ) -> Result<CommandResponse, String> {
        let url = self.http_url("/command");
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(HTTP_TIMEOUT_SECS))
            .build()
            .map_err(|e| e.to_string())?;

        let body = serde_json::json!({
            "action": action,
            "payload": payload,
        });

        let resp = client
            .post(&url)
            .json(&body)
            .send()
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Backend returned HTTP {}", resp.status()));
        }

        resp.json::<CommandResponse>()
            .map_err(|e| format!("Failed to parse response: {}", e))
    }
}

// ============================================================================
// Tauri IPC Commands
// ============================================================================

#[tauri::command]
fn get_backend_state(
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<BackendState, String> {
    let manager = backend.lock().map_err(|e| e.to_string())?;
    manager.get_state()
}

/// Get HUD-specific state formatted for frontend display.
/// Returns combat state with emoji, stats, status color, and running status.
#[tauri::command]
fn get_hud_state(
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<HudState, String> {
    let manager = backend.lock().map_err(|e| e.to_string())?;
    let state = manager.get_state()?;

    // Extract combat state (default to IDLE if not present)
    let combat_state = state
        .combat
        .get("combat_state")
        .and_then(|v| v.as_str())
        .unwrap_or("IDLE")
        .to_string();

    // Extract stats
    let kills = state
        .stats
        .get("kills")
        .and_then(|v| v.as_i64())
        .unwrap_or(0) as i32;

    // Extract detection_ms from vision (if available)
    let detection_ms = state
        .vision
        .get("detection_ms")
        .and_then(|v| v.as_i64())
        .unwrap_or(0) as i32;

    // Extract elapsed from vision (if available)
    let elapsed = state
        .vision
        .get("elapsed")
        .and_then(|v| v.as_i64())
        .unwrap_or(0);

    Ok(HudState {
        combat_state,
        stats: HudStats {
            kills,
            detection_ms,
            elapsed,
        },
        status_color: state.status_color,
        running: state.running,
    })
}

#[tauri::command]
fn send_action(
    action: String,
    payload: Option<serde_json::Value>,
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<CommandResponse, String> {
    let manager = backend.lock().map_err(|e| e.to_string())?;
    manager.send_command(&action, payload.as_ref())
}

#[tauri::command]
fn restart_backend(
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<bool, String> {
    let mut manager = backend.lock().map_err(|e| e.to_string())?;
    manager.respawn()?;
    Ok(true)
}

#[tauri::command]
fn stop_backend(
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<(), String> {
    let mut manager = backend.lock().map_err(|e| e.to_string())?;
    manager.stop();
    Ok(())
}

// ============================================================================
// Global Shortcut Handler
// ============================================================================

/// Register F1-F4 global shortcuts and handle their actions.
fn register_hotkeys(
    app: &tauri::AppHandle,
    backend: Arc<Mutex<BackendManager>>,
    hud_visible: Arc<Mutex<bool>>,
) {
    let f1_shortcut = Shortcut::new(None, tauri_plugin_global_shortcut::Code::F1);
    let f2_shortcut = Shortcut::new(None, tauri_plugin_global_shortcut::Code::F2);
    let f3_shortcut = Shortcut::new(None, tauri_plugin_global_shortcut::Code::F3);
    let f4_shortcut = Shortcut::new(None, tauri_plugin_global_shortcut::Code::F4);

    // F1: emergency_stop -- each closure gets its own Arc clone
    let backend_f1 = Arc::clone(&backend);
    let _ = app.global_shortcut().on_shortcut(f1_shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            eprintln!("[ZEDSU] F1 pressed: emergency_stop");
            if let Ok(mgr) = backend_f1.lock() {
                let _ = mgr.send_command("emergency_stop", None);
            }
        }
    });

    // F2: toggle HUD
    let app_f2 = app.clone();
    let hud_visible_f2 = Arc::clone(&hud_visible);
    let _ = app.global_shortcut().on_shortcut(f2_shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            if let Some(hud) = app_f2.get_webview_window("hud") {
                let mut visible = hud_visible_f2.lock().unwrap();
                if *visible {
                    let _ = hud.hide();
                    eprintln!("[ZEDSU] HUD hidden (F2)");
                } else {
                    let _ = hud.show();
                    let _ = hud.set_focus();
                    eprintln!("[ZEDSU] HUD shown (F2)");
                }
                *visible = !*visible;
            }
        }
    });

    // F3: toggle start/stop
    let backend_f3 = Arc::clone(&backend);
    let _ = app.global_shortcut().on_shortcut(f3_shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            eprintln!("[ZEDSU] F3 pressed: toggle_start_stop");
            if let Ok(mgr) = backend_f3.lock() {
                let _ = mgr.send_command("toggle", None);
            }
        }
    });

    // F4: show main window
    let app_f4 = app.clone();
    let _ = app.global_shortcut().on_shortcut(f4_shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            eprintln!("[ZEDSU] F4 pressed: show_main_window");
            if let Some(main) = app_f4.get_webview_window("main") {
                let _ = main.show();
                let _ = main.set_focus();
                eprintln!("[ZEDSU] Main window shown (F4)");
            }
        }
    });

    eprintln!(
        "[ZEDSU] Hotkeys registered: F1=Stop, F2=HUD, F3=Start/Stop, F4=Settings"
    );
}

// ============================================================================
// Main entry
// ============================================================================

pub fn run() {
    let backend_manager = Arc::new(Mutex::new(BackendManager::new()));
    let app_state = AppState::new();

    // Attempt to start the backend
    {
        let mut mgr = backend_manager.lock().unwrap();
        if let Err(e) = mgr.start() {
            eprintln!("[ZEDSU] Warning: Failed to start backend on launch: {}", e);
        }
    }

    // Spawn threads before moving backend_manager into the app.
    // Health check thread: every 3s, check if backend responds and respawn if dead.
    let backend_for_health = Arc::clone(&backend_manager);
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(HEALTH_INTERVAL_SECS));

            let mut mgr = backend_for_health.lock().unwrap();
            if !mgr.is_alive() {
                if !mgr.health_check() {
                    eprintln!(
                        "[ZEDSU] Backend not responding (attempt {}/{}). Respawning...",
                        mgr.get_restart_count() + 1,
                        MAX_RESTART_ATTEMPTS
                    );
                    if let Err(e) = mgr.respawn() {
                        eprintln!("[ZEDSU] Backend respawn failed: {}", e);
                    }
                }
            }
        }
    });

    let hud_visible = app_state.hud_visible.clone();
    let backend_for_setup = backend_manager.clone();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(backend_manager.clone())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            get_backend_state,
            get_hud_state,
            send_action,
            restart_backend,
            stop_backend,
        ])
        .setup(move |app| {
            eprintln!("[ZEDSU] Frontend ready");

            // Register F1-F4 global shortcuts
            register_hotkeys(app.handle(), backend_for_setup.clone(), hud_visible.clone());

            // HUD window is configured in tauri.conf.json (visible: true, 300x80, top-right)
            // No need to create it here -- Tauri creates it from config

            // Main window starts hidden (D-10a-01) -- don't show it on startup
            // User can reveal via F4 or system tray

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Error building Tauri application");

    let _backend = backend_manager;
    app.run(|_app_handle, _event| {});
}
