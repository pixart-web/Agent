//! Desktop smoke-test harness. Compiled into **debug builds only** (`cfg(debug_assertions)`)
//! and inert unless `KIKO_DESKTOP_SMOKE_SCRIPT` names a script file. Release bundles contain
//! none of this code.
//!
//! The script runs inside the real WebView of the real app bundle and drives the UI through
//! the DOM; it reports progress with `invoke('smoke_report', { line })`. A line starting
//! with `DONE` or `FAIL` ends the run and sets the exit code.

use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{AppHandle, Runtime, WebviewWindow};

static INJECTED: AtomicBool = AtomicBool::new(false);

pub fn script() -> Option<String> {
    let path = std::env::var("KIKO_DESKTOP_SMOKE_SCRIPT").ok()?;
    std::fs::read_to_string(path).ok()
}

/// Inject the smoke script once, after the first document finishes loading.
pub fn inject_once<R: Runtime>(webview: &WebviewWindow<R>, source: &str) {
    if INJECTED.swap(true, Ordering::SeqCst) {
        return;
    }
    eprintln!("SMOKE injecting script ({} bytes)", source.len());
    if let Err(error) = webview.eval(source) {
        eprintln!("SMOKE FAIL could not inject script: {error}");
    }
}

#[tauri::command]
pub fn smoke_report(app: AppHandle, line: String) {
    println!("SMOKE {line}");
    if line.starts_with("DONE") {
        app.exit(0);
    } else if line.starts_with("FAIL") {
        app.exit(1);
    }
}
