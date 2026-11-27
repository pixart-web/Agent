//! Cold-start measurements for the packaged app.
//!
//! The shell marks when `run()` starts, when the main window exists and when the first page
//! finishes loading; the UI reports when the first usable screen is on display (sign-in or
//! dashboard, no longer a loading placeholder). One JSON line per launch is appended to
//! `startup.jsonl` in the app log directory (the last 200 launches are kept), so cold-start
//! regressions can be measured on real installs (`scripts/local/kiko-local.sh startup`).
//! Nothing leaves the Mac.

use std::io::Write;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Mutex, OnceLock};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Manager, State};

const LOG_FILE: &str = "startup.jsonl";
const KEEP_LINES: usize = 200;

static PROCESS_START: OnceLock<Instant> = OnceLock::new();

/// Call first thing in `run()`.
pub fn mark_process_start() {
    let _ = PROCESS_START.get_or_init(Instant::now);
}

fn elapsed_ms() -> u64 {
    PROCESS_START
        .get()
        .map(|start| start.elapsed().as_millis() as u64)
        .unwrap_or(0)
}

#[derive(Default)]
pub struct StartupTimes {
    window_ms: Mutex<Option<u64>>,
    page_loaded_ms: Mutex<Option<u64>>,
    reported: AtomicBool,
}

impl StartupTimes {
    pub fn mark_window(&self) {
        let mut slot = self.window_ms.lock().expect("startup lock");
        slot.get_or_insert_with(elapsed_ms);
    }

    pub fn mark_page_loaded(&self) {
        let mut slot = self.page_loaded_ms.lock().expect("startup lock");
        slot.get_or_insert_with(elapsed_ms);
    }
}

#[derive(Debug, Serialize, PartialEq)]
pub struct StartupReport {
    pub version: String,
    pub started_at: u64,
    pub window_ms: Option<u64>,
    pub page_loaded_ms: Option<u64>,
    pub ui_ready_ms: u64,
    pub screen: String,
}

/// Keep only a route's first segment pair (`/dashboard/tasks/…` → `/dashboard/tasks`), so no
/// record id or token ever lands in the log.
pub fn screen_name(route: &str) -> String {
    let path = route.split(['?', '#']).next().unwrap_or_default();
    let segments: Vec<&str> = path.split('/').filter(|s| !s.is_empty()).take(2).collect();
    let safe = segments.iter().all(|s| {
        s.chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    });
    if !safe || segments.is_empty() {
        return "/".into();
    }
    format!("/{}", segments.join("/"))
}

/// Append one line and keep the file bounded.
pub fn append_report(dir: &Path, report: &StartupReport) -> std::io::Result<()> {
    std::fs::create_dir_all(dir)?;
    let path = dir.join(LOG_FILE);
    let mut lines: Vec<String> = std::fs::read_to_string(&path)
        .unwrap_or_default()
        .lines()
        .map(str::to_owned)
        .collect();
    lines.push(serde_json::to_string(report).map_err(std::io::Error::other)?);
    let start = lines.len().saturating_sub(KEEP_LINES);
    let mut file = std::fs::File::create(&path)?;
    for line in &lines[start..] {
        writeln!(file, "{line}")?;
    }
    Ok(())
}

/// Called once by the UI when the first usable screen is displayed. Later calls (navigation,
/// reloads) are ignored, so only the cold start is recorded.
#[tauri::command]
pub fn report_startup(
    app: AppHandle,
    times: State<'_, StartupTimes>,
    route: String,
) -> Result<Option<u64>, String> {
    if times.reported.swap(true, Ordering::SeqCst) {
        return Ok(None);
    }
    let ui_ready_ms = elapsed_ms();
    let started_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|now| now.as_secs().saturating_sub(ui_ready_ms / 1000))
        .unwrap_or(0);
    let report = StartupReport {
        version: app.package_info().version.to_string(),
        started_at,
        window_ms: *times.window_ms.lock().expect("startup lock"),
        page_loaded_ms: *times.page_loaded_ms.lock().expect("startup lock"),
        ui_ready_ms,
        screen: screen_name(&route),
    };
    let dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
    append_report(&dir, &report).map_err(|e| e.to_string())?;
    Ok(Some(ui_ready_ms))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn screen_names_drop_ids_and_queries() {
        assert_eq!(
            screen_name("/dashboard/tasks/abc-123/?x=1"),
            "/dashboard/tasks"
        );
        assert_eq!(screen_name("/login/"), "/login");
        assert_eq!(
            screen_name("/reset-password/?token=secret"),
            "/reset-password"
        );
        assert_eq!(screen_name("/"), "/");
        assert_eq!(screen_name("/a b/c"), "/");
    }

    #[test]
    fn report_file_is_bounded() {
        let dir = std::env::temp_dir().join(format!("kiko-startup-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        let report = StartupReport {
            version: "0.0.0".into(),
            started_at: 1,
            window_ms: Some(10),
            page_loaded_ms: Some(20),
            ui_ready_ms: 30,
            screen: "/login".into(),
        };
        for _ in 0..(KEEP_LINES + 5) {
            append_report(&dir, &report).unwrap();
        }
        let text = std::fs::read_to_string(dir.join(LOG_FILE)).unwrap();
        assert_eq!(text.lines().count(), KEEP_LINES);
        assert!(text.lines().all(|line| line.contains("\"ui_ready_ms\":30")));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn first_mark_wins() {
        let times = StartupTimes::default();
        mark_process_start();
        times.mark_window();
        let first = *times.window_ms.lock().unwrap();
        std::thread::sleep(std::time::Duration::from_millis(5));
        times.mark_window();
        assert_eq!(*times.window_ms.lock().unwrap(), first);
    }
}
