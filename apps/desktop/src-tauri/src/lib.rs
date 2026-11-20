//! Kiko desktop shell (Tauri 2).
//!
//! The UI is the Kiko web product compiled as a static export and served from the
//! bundle through the `kikoui://` protocol. All business logic stays on the Kiko API;
//! this crate only provides transport, secure session storage and native integrations.

pub mod api;
pub mod commands;
pub mod config;
pub mod deep_link;
pub mod keychain;
pub mod menu;
pub mod protocol;
#[cfg(debug_assertions)]
pub mod smoke;

use tauri::http::{header, Response, StatusCode};
use tauri::utils::config::BackgroundThrottlingPolicy;
use tauri::{Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_deep_link::DeepLinkExt;

use crate::api::ApiClient;
use crate::keychain::{KeychainStore, MemoryStore, TokenStore};

pub const UI_SCHEME: &str = "kikoui";

/// Content Security Policy for every bundled document. Only bundled code runs; the UI can
/// reach nothing but the IPC bridge (all network traffic goes through `api_request`).
/// Inline scripts are needed by the Next.js runtime bootstrap.
pub const CSP: &str = "default-src 'self'; script-src 'self' 'unsafe-inline'; \
style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; \
connect-src 'self' ipc: http://ipc.localhost; object-src 'none'; base-uri 'self'; \
form-action 'self'; frame-src 'none'; frame-ancestors 'none'";

/// Exact asset lookup. `AssetResolver::get` falls back to `index.html` for unknown paths
/// (SPA behaviour), so existence is checked against the embedded asset list first; `get`
/// is then used because it returns decompressed bytes.
fn exact_asset<R: tauri::Runtime>(
    resolver: &tauri::AssetResolver<R>,
    key: &str,
) -> Option<Vec<u8>> {
    let wanted = format!("/{key}");
    let exists = resolver
        .iter()
        .any(|(name, _)| name == wanted.as_str() || name == key);
    if !exists {
        return None;
    }
    resolver.get(wanted).map(|asset| asset.bytes)
}

fn serve_asset<R: tauri::Runtime>(app: &tauri::AppHandle<R>, path: &str) -> Response<Vec<u8>> {
    let resolver = app.asset_resolver();
    for key in protocol::candidates(path) {
        if let Some(bytes) = exact_asset(&resolver, &key) {
            return Response::builder()
                .status(StatusCode::OK)
                .header(header::CONTENT_TYPE, protocol::mime_for(&key))
                .header("Content-Security-Policy", CSP)
                .header("X-Content-Type-Options", "nosniff")
                .header(header::CACHE_CONTROL, "no-cache")
                .body(bytes)
                .expect("valid response");
        }
    }
    let not_found = exact_asset(&resolver, "404.html").unwrap_or_else(|| b"Not found".to_vec());
    Response::builder()
        .status(StatusCode::NOT_FOUND)
        .header(header::CONTENT_TYPE, "text/html; charset=utf-8")
        .header("Content-Security-Policy", CSP)
        .body(not_found)
        .expect("valid response")
}

fn focus_main<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn handle_deep_links<R: tauri::Runtime>(app: &tauri::AppHandle<R>, urls: &[url::Url]) {
    for link in urls {
        if let Some(route) = deep_link::route_for(link.as_str()) {
            focus_main(app);
            let live = app.state::<deep_link::PendingRoute>().offer(route);
            if let (Some(route), Some(window)) = (live, app.get_webview_window("main")) {
                let _ = window.emit(menu::NAVIGATE_EVENT, route);
            }
        } else {
            log::warn!("ignored unsupported deep link");
        }
    }
}

fn token_store() -> Box<dyn TokenStore> {
    // Smoke tests can opt out of the Keychain so they never touch the user's login keychain.
    if std::env::var("KIKO_DESKTOP_EPHEMERAL_SESSION").as_deref() == Ok("1") {
        Box::new(MemoryStore::default())
    } else {
        Box::new(KeychainStore)
    }
}

#[cfg(not(debug_assertions))]
fn invoke_handler() -> impl Fn(tauri::ipc::Invoke<tauri::Wry>) -> bool + Send + Sync + 'static {
    tauri::generate_handler![
        commands::api_request,
        commands::app_info,
        commands::clear_session,
        commands::set_server_url,
        commands::open_external,
        commands::save_file,
        commands::notify,
        commands::confirm_action,
        commands::take_pending_route,
    ]
}

/// Debug builds add the smoke-test reporter (see `smoke.rs`).
#[cfg(debug_assertions)]
fn invoke_handler() -> impl Fn(tauri::ipc::Invoke<tauri::Wry>) -> bool + Send + Sync + 'static {
    tauri::generate_handler![
        commands::api_request,
        commands::app_info,
        commands::clear_session,
        commands::set_server_url,
        commands::open_external,
        commands::save_file,
        commands::notify,
        commands::confirm_action,
        commands::take_pending_route,
        smoke::smoke_report,
    ]
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            focus_main(app)
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_opener::init())
        .register_asynchronous_uri_scheme_protocol(UI_SCHEME, |ctx, request, responder| {
            let app = ctx.app_handle().clone();
            let path = request.uri().path().to_owned();
            #[cfg(debug_assertions)]
            eprintln!("[kikoui] {path}");
            std::thread::spawn(move || responder.respond(serve_asset(&app, &path)));
        })
        .invoke_handler(invoke_handler())
        .setup(|app| {
            let config_dir = app.path().app_config_dir().ok();
            let base = config::resolve_api_url(config_dir.as_deref());
            let version = app.package_info().version.to_string();
            let client = ApiClient::new(base, token_store(), &version)
                .map_err(|e| Box::<dyn std::error::Error>::from(e.to_string()))?;
            app.manage(client);
            app.manage(deep_link::PendingRoute::default());

            let handle = app.handle().clone();
            app.set_menu(menu::build(&handle)?)?;
            app.on_menu_event(|app, event| menu::handle_event(app, event.id().as_ref()));

            let start = url::Url::parse(&format!("{UI_SCHEME}://localhost/desktop/"))?;
            WebviewWindowBuilder::new(app, "main", WebviewUrl::CustomProtocol(start))
                .title("Kiko")
                .inner_size(1360.0, 860.0)
                .min_inner_size(960.0, 640.0)
                .hidden_title(true)
                .title_bar_style(tauri::TitleBarStyle::Overlay)
                .disable_drag_drop_handler()
                // WebKit suspends a hidden window's page by default (macOS 27.2.1 does so after
                // a few seconds): the notification poller stopped and a plan being generated
                // was never shown while Kiko was behind other windows. Throttle, don't suspend.
                .background_throttling(BackgroundThrottlingPolicy::Throttle)
                .on_navigation(|url| url.scheme() == UI_SCHEME)
                .on_page_load(|_webview, _payload| {
                    #[cfg(debug_assertions)]
                    eprintln!("[page-load] {:?} {}", _payload.event(), _payload.url());
                    #[cfg(debug_assertions)]
                    if matches!(_payload.event(), tauri::webview::PageLoadEvent::Finished) {
                        if let Some(source) = smoke::script() {
                            smoke::inject_once(&_webview, &source);
                        }
                    }
                })
                .build()?;

            let deep_link_handle = handle.clone();
            app.deep_link().on_open_url(move |event| {
                handle_deep_links(&deep_link_handle, &event.urls());
            });
            if let Ok(Some(urls)) = app.deep_link().get_current() {
                handle_deep_links(&handle, &urls);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Kiko");
}
