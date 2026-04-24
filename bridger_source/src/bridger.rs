// bridger.rs — Bridger Tauri Frontend (Reconstructed from binary analysis)
//
// Architecture:
//   - Rust/Tauri 2.x application
//   - Spawns BridgerBackend.exe (Python/HTTP server) as a managed child process
//   - Health-checks the backend every 3 seconds; respawns on crash
//   - Communicates with the backend via HTTP POST /command on port 9760
//   - Manages transparent overlay windows (status + monitor display)
//   - Exposes IPC commands to the web-based GUI (HTML/CSS/JS)
//   - Detects and kills conflicting RobloxPlayerBeta.exe processes
//
// Build:  cargo build --release
//         (Produces bridger.exe)
// Run:    ./bridger.exe
//
// Dependencies:
//   - tauri 2.x
//   - serde, serde_json
//   - reqwest (HTTP client)
//   - tokio (async runtime)
//   - sysinfo (process management)
//   - windows (DPI awareness, window management)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Manager, State};

// ============================================================================
// Types
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    terms_accepted: bool,
    subscribed: bool,
    settings: HashMap<String, serde_json::Value>,
    global_gui_settings: HashMap<String, serde_json::Value>,
    hotkeys: HashMap<String, String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        let mut settings = HashMap::new();
        settings.insert("terms_accepted".to_string(), serde_json::json!(false));
        settings.insert("subscribed".to_string(), serde_json::json!(false));

        let mut gui_settings = HashMap::new();
        gui_settings.insert("Always On Top".to_string(), serde_json::json!(true));
        gui_settings.insert("Auto Minimize GUI".to_string(), serde_json::json!(true));
        gui_settings.insert("Auto Focus Roblox".to_string(), serde_json::json!(true));
        gui_settings.insert("Show Status Overlay".to_string(), serde_json::json!(true));
        gui_settings.insert("Show Audio Monitor".to_string(), serde_json::json!(false));

        let mut hotkeys = HashMap::new();
        hotkeys.insert("start_stop".to_string(), "f3".to_string());
        hotkeys.insert("exit".to_string(), "f2".to_string());
        hotkeys.insert("select_region".to_string(), "f1".to_string());

        Self {
            terms_accepted: false,
            subscribed: false,
            settings,
            global_gui_settings: gui_settings,
            hotkeys,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandPayload {
    action: String,
    #[serde(rename = "payload")]
    data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandResponse {
    status: Option<String>,
    error: Option<String>,
    #[serde(flatten)]
    extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendState {
    running: bool,
    status: String,
    audio: HashMap<String, serde_json::Value>,
    monitors: Vec<serde_json::Value>,
    config: AppConfig,
    logs: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    status: String,
}

// ============================================================================
// Backend process management
// ============================================================================

const BACKEND_EXE: &str = "BridgerBackend.exe";
const BACKEND_PORT: u16 = 9760;
const BACKEND_HOST: &str = "127.0.0.1";
const HEALTH_INTERVAL_SECS: u64 = 3;
const MAX_RESTART_ATTEMPTS: usize = 3;

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

    /// Spawn the Python backend process (BridgerBackend.exe).
    /// Returns true if spawned successfully.
    pub fn start(&mut self) -> Result<bool, String> {
        // Kill any existing instance
        self.stop();

        let exe_path = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .map(|p| p.join(BACKEND_EXE))
            .ok_or("Could not determine exe directory")?;

        // Spawn as detached process
        let child = Command::new(&exe_path)
            .args(["--headless"])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to spawn {}: {}", exe_path.display(), e))?;

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

    /// Check if the backend process is still alive.
    pub fn is_alive(&self) -> bool {
        if let Some(ref child) = self.process {
            child.try_wait().ok().flatten().is_none()
        } else {
            false
        }
    }

    /// Attempt to respawn the backend.
    pub fn respawn(&mut self) -> Result<(), String> {
        if self.restart_count >= MAX_RESTART_ATTEMPTS {
            return Err("Max restart attempts reached".to_string());
        }
        self.stop();
        self.restart_count += 1;
        self.start()?;
        Ok(())
    }

    pub fn get_restart_count(&self) -> usize {
        self.restart_count
    }
}

// ============================================================================
// HTTP communication with backend
// ============================================================================

const HTTP_TIMEOUT_SECS: u64 = 10;

impl BackendManager {
    /// Send a command to the backend HTTP server.
    pub fn send_command(&self, action: &str, payload: Option<&serde_json::Value>) -> Result<CommandResponse, String> {
        let url = format!("http://{}:{}/command", BACKEND_HOST, BACKEND_PORT);

        let body = serde_json::json!({
            "action": action,
            "payload": payload,
        });

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(HTTP_TIMEOUT_SECS))
            .build()
            .map_err(|e| e.to_string())?;

        let resp = client
            .post(&url)
            .json(&body)
            .send()
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Backend returned HTTP {}", resp.status()));
        }

        let data: CommandResponse = resp
            .json()
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        Ok(data)
    }

    /// Poll /health endpoint.
    pub fn health_check(&self) -> bool {
        let url = format!("http://{}:{}/health", BACKEND_HOST, BACKEND_PORT);
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .ok();

        if let Some(client) = client {
            client.get(&url).send().ok()
                .map(|r| r.status().is_success())
                .unwrap_or(false)
        } else {
            false
        }
    }

    /// Fetch /state from the backend.
    pub fn get_state(&self) -> Result<BackendState, String> {
        let url = format!("http://{}:{}/state", BACKEND_HOST, BACKEND_PORT);
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(HTTP_TIMEOUT_SECS))
            .build()
            .map_err(|e| e.to_string())?;

        let resp = client
            .get(&url)
            .send()
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        let state: BackendState = resp
            .json()
            .map_err(|e| format!("Failed to parse state: {}", e))?;

        Ok(state)
    }
}

// ============================================================================
// Tauri IPC Commands
// ============================================================================

#[tauri::command]
fn send_to_python(
    action: String,
    payload: Option<serde_json::Value>,
    backend: State<'_, Arc<Mutex<BackendManager>>>,
) -> Result<CommandResponse, String> {
    let manager = backend.lock().map_err(|e| e.to_string())?;
    manager.send_command(&action, payload.as_ref())
}

#[tauri::command]
fn create_status_overlay(app: AppHandle) -> Result<(), String> {
    // Creates a transparent frameless window that floats above the game.
    // The window shows current macro status (CASTING, WAITING FOR BITE, etc.)
    // and audio detection scores (correlation, RMS).
    //
    // In the Tauri implementation, this would:
    //   1. Create a WebviewWindow with transparent background
    //   2. Load an embedded HTML overlay page (from web resources)
    //   3. Set window to be always-on-top, transparent, borderless
    //   4. Position it at the top-right corner of the monitor

    // Reconstructed window creation (Tauri 2.x style):
    use tauri::webview::WebviewWindowBuilder;

    let window = WebviewWindowBuilder::new(
        &app,
        "status_overlay",  // unique label
        tauri::webview::WebviewUrl::App("overlay.html".into()),
    )
    .title("Bridger Status")
    .inner_size(360.0, 200.0)
    .resizable(false)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .skip_taskbar(true)
    .position(100.0, 100.0)  // will be repositioned by JS
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn create_monitor_overlay(
    monitor_index: usize,
    app: AppHandle,
) -> Result<(), String> {
    // Creates a per-monitor transparent overlay showing:
    //   - Current OCR region rectangle (green dashed border)
    //   - Cast position marker (blue dot)
    //   - Audio waveform / correlation bar (if Show Audio Monitor is enabled)
    //
    // The overlay is built from an embedded HTML page that receives
    // state updates via HTTP polling to /state.

    use tauri::webview::WebviewWindowBuilder;

    let label = format!("monitor_overlay_{}", monitor_index);

    WebviewWindowBuilder::new(
        &app,
        &label,
        tauri::webview::WebviewUrl::App("monitor.html".into()),
    )
    .title(format!("Monitor {} Overlay", monitor_index))
    .inner_size(1920.0, 1080.0)
    .resizable(false)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .skip_taskbar(true)
    .fullscreen(false)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn open_main_window(app: AppHandle) -> Result<(), String> {
    // Reveal/hide the main GUI window
    if let Some(window) = app.get_webview_window("main") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn open_browser(url: String) -> Result<(), String> {
    // Open a URL in the default web browser.
    // Used for: YouTube subscribe link, documentation links, etc.
    open::that(&url).map_err(|e| format!("Failed to open URL: {}", e))
}

#[tauri::command]
fn kill_bridger_backend(backend: State<'_, Arc<Mutex<BackendManager>>>) -> Result<(), String> {
    let mut manager = backend.lock().map_err(|e| e.to_string())?;
    manager.stop();
    Ok(())
}

#[tauri::command]
fn get_backend_state(backend: State<'_, Arc<Mutex<BackendManager>>>) -> Result<BackendState, String> {
    let manager = backend.lock().map_err(|e| e.to_string())?;
    manager.get_state()
}

#[tauri::command]
fn restart_backend(backend: State<'_, Arc<Mutex<BackendManager>>>) -> Result<bool, String> {
    let mut manager = backend.lock().map_err(|e| e.to_string())?;
    manager.respawn()
}

#[tauri::command]
fn kill_conflicting_processes() -> Result<(), String> {
    // Kill any running RobloxPlayerBeta.exe processes that might interfere
    // with the macro's audio capture and input simulation.
    //
    // Implementation uses sysinfo to iterate running processes:
    //
    // let sys = sysinfo::System::new_all();
    // for (pid, process) in sys.processes() {
    //     if process.name().to_string_lossy().contains("RobloxPlayerBeta") {
    //         process.kill();
    //     }
    // }

    let sys = sysinfo::System::new_all();
    let mut killed = 0;
    for (pid, process) in sys.processes() {
        let name = process.name().to_string_lossy();
        if name.contains("RobloxPlayerBeta") {
            let _ = process.kill();
            killed += 1;
        }
    }

    Ok(())
}

// ============================================================================
// Main entry point
// ============================================================================

// #[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_manager = Arc::new(Mutex::new(BackendManager::new()));

    // Attempt to start the backend
    {
        let mut mgr = backend_manager.lock().unwrap();
        if let Err(e) = mgr.start() {
            eprintln!("Warning: Failed to start backend on launch: {}", e);
        }
    }

    // Spawn background health-check thread
    let backend_for_health = Arc::clone(&backend_manager);
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(HEALTH_INTERVAL_SECS));

            let mut mgr = backend_for_health.lock().unwrap();
            if !mgr.is_alive() {
                eprintln!(
                    "[BRIDGER] Backend not responding (attempt {}/{}). Respawning...",
                    mgr.get_restart_count() + 1,
                    MAX_RESTART_ATTEMPTS
                );
                if let Err(e) = mgr.respawn() {
                    eprintln!("[BRIDGER] Backend respawn failed: {}", e);
                }
            }
        }
    });

    // Spawn crash-watch thread: monitors backend exit code
    let backend_for_watch = Arc::clone(&backend_manager);
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(1));

            let mgr = backend_for_watch.lock().unwrap();
            if let Some(ref mut child) = mgr.process {
                if let Ok(Some(status)) = child.try_wait() {
                    eprintln!(
                        "[BRIDGER] Backend exited with code {:?}. Restarting...",
                        status.code()
                    );
                    drop(mgr);
                    let mut mgr2 = backend_for_watch.lock().unwrap();
                    let _ = mgr2.respawn();
                    break;
                }
            }
        }
    });

    // Build and run Tauri application
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(backend_manager)
        .invoke_handler(tauri::generate_handler![
            send_to_python,
            create_status_overlay,
            create_monitor_overlay,
            open_main_window,
            open_browser,
            kill_bridger_backend,
            get_backend_state,
            restart_backend,
            kill_conflicting_processes,
        ])
        .setup(|app| {
            // Kill conflicting processes on startup
            let _ = kill_conflicting_processes();

            // Set DPI awareness for the window on Windows
            #[cfg(target_os = "windows")]
            unsafe {
                use windows::Win32::UI::HiDpi::SetProcessDpiAwareness;
                use windows::Win32::UI::HiDpi::PROCESS_PER_MONITOR_DPI_AWARE_V2;
                let _ = SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE_V2);
            }

            // Open main window
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Error building Tauri application");

    app.run(|_app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            // On exit, stop the backend
            let mgr = backend_manager.lock().unwrap();
            mgr.stop();
        }
    });
}
