//! IPC commands exposed to the bundled UI. Each command validates its input; none of them
//! can run shell commands, read arbitrary files, or reach hosts other than the configured
//! Kiko server.

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use serde::Serialize;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_notification::NotificationExt;
use tauri_plugin_opener::OpenerExt;
use url::Url;

use crate::api::{ApiClient, ApiError, ApiRequest, ApiResponse, MAX_BODY_BYTES};
use crate::config;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AppInfo {
    version: String,
    platform: &'static str,
    api_base_url: String,
    has_session: bool,
}

#[tauri::command]
pub async fn api_request(
    client: State<'_, ApiClient>,
    request: ApiRequest,
) -> Result<ApiResponse, ApiError> {
    client.request(request).await
}

#[tauri::command]
pub async fn app_info(app: AppHandle, client: State<'_, ApiClient>) -> Result<AppInfo, ApiError> {
    Ok(AppInfo {
        version: app.package_info().version.to_string(),
        platform: "macos",
        api_base_url: client.base_url().await.origin().ascii_serialization(),
        has_session: client.has_session().await.unwrap_or(false),
    })
}

/// Forget local credentials (used after password change or a rejected session).
#[tauri::command]
pub async fn clear_session(client: State<'_, ApiClient>) -> Result<(), ApiError> {
    client.clear_session().await
}

/// Change the Kiko server. Clears the session for the previous server first.
#[tauri::command]
pub async fn set_server_url(
    app: AppHandle,
    client: State<'_, ApiClient>,
    url: String,
) -> Result<String, String> {
    let parsed = config::validate_api_url(&url)?;
    client.clear_session().await.map_err(|e| e.to_string())?;
    let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
    config::save_api_url(&dir, &parsed).map_err(|e| e.to_string())?;
    client.set_base_url(parsed.clone()).await;
    Ok(parsed.origin().ascii_serialization())
}

/// Allowed external destinations: HTTPS pages and mail links. Everything else is refused.
pub fn validate_external_url(raw: &str) -> Result<Url, String> {
    let url = Url::parse(raw).map_err(|_| "invalid URL".to_owned())?;
    match url.scheme() {
        "https" if url.host_str().is_some() && url.username().is_empty() => Ok(url),
        "mailto" => Ok(url),
        _ => Err("only https and mailto links can be opened".into()),
    }
}

#[tauri::command]
pub async fn open_external(app: AppHandle, url: String) -> Result<(), String> {
    let url = validate_external_url(&url)?;
    app.opener()
        .open_url(url.as_str(), None::<&str>)
        .map_err(|e| e.to_string())
}

/// Reduce a server-suggested file name to a safe base name.
pub fn sanitise_file_name(name: &str) -> String {
    let base = name.rsplit(['/', '\\']).next().unwrap_or_default();
    let cleaned: String = base
        .chars()
        .filter(|c| !c.is_control())
        .map(|c| {
            if matches!(c, ':' | '*' | '?' | '"' | '<' | '>' | '|') {
                '_'
            } else {
                c
            }
        })
        .collect();
    let trimmed = cleaned.trim().trim_start_matches('.');
    if trimmed.is_empty() {
        "kiko-export".into()
    } else {
        trimmed.chars().take(120).collect()
    }
}

/// Ask the user where to save a file, then write it there. Nothing is written without the
/// user choosing a destination in the native save panel.
#[tauri::command]
pub async fn save_file(
    app: AppHandle,
    file_name: String,
    body_base64: String,
) -> Result<Option<String>, String> {
    if body_base64.len() > MAX_BODY_BYTES * 4 / 3 + 4 {
        return Err("file too large".into());
    }
    let bytes = B64
        .decode(body_base64)
        .map_err(|_| "invalid file data".to_owned())?;
    let name = sanitise_file_name(&file_name);
    let Some(path) = app
        .dialog()
        .file()
        .set_file_name(&name)
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let path = path.into_path().map_err(|e| e.to_string())?;
    std::fs::write(&path, bytes).map_err(|e| e.to_string())?;
    Ok(Some(path.display().to_string()))
}

#[tauri::command]
pub async fn notify(app: AppHandle, title: String, body: String) -> Result<(), String> {
    let title: String = title.chars().take(120).collect();
    let body: String = body.chars().take(400).collect();
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn external_url_allowlist() {
        assert!(validate_external_url("https://accounts.google.com/o/oauth2").is_ok());
        assert!(validate_external_url("mailto:hello@pixart.pt").is_ok());
        for bad in [
            "http://example.com",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "kiko://open/tasks",
            "smb://server/share",
            "https://user@evil.example",
        ] {
            assert!(validate_external_url(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn file_names_are_sanitised() {
        assert_eq!(sanitise_file_name("../../etc/passwd"), "passwd");
        assert_eq!(sanitise_file_name("crm-contacts.csv"), "crm-contacts.csv");
        assert_eq!(sanitise_file_name(".hidden"), "hidden");
        assert_eq!(sanitise_file_name("a:b?.csv"), "a_b_.csv");
        assert_eq!(sanitise_file_name(""), "kiko-export");
    }
}
