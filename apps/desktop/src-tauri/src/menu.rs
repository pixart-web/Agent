//! Native macOS menu bar. Navigation items emit `kiko://navigate` with an in-app route;
//! the UI performs the navigation. Standard Edit items are required for text editing
//! shortcuts (copy, paste, undo) to work inside the WebView on macOS.

use tauri::menu::{AboutMetadata, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Emitter, Manager, Runtime};

pub const NAVIGATE_EVENT: &str = "kiko://navigate";
pub const COMMAND_EVENT: &str = "kiko://command";

/// (menu id, label, accelerator, route)
pub const GO_ITEMS: &[(&str, &str, &str, &str)] = &[
    ("go.home", "Home", "CmdOrCtrl+1", "/dashboard/"),
    ("go.kiko", "Kiko AI", "CmdOrCtrl+2", "/dashboard/kiko/"),
    (
        "go.commands",
        "Commands",
        "CmdOrCtrl+3",
        "/dashboard/commands/",
    ),
    ("go.tasks", "Tasks", "CmdOrCtrl+4", "/dashboard/tasks/"),
    (
        "go.projects",
        "Projects",
        "CmdOrCtrl+5",
        "/dashboard/projects/",
    ),
    (
        "go.approvals",
        "Approvals",
        "CmdOrCtrl+6",
        "/dashboard/approvals/",
    ),
    ("go.crm", "CRM", "CmdOrCtrl+7", "/dashboard/crm/"),
    (
        "go.notifications",
        "Notifications",
        "CmdOrCtrl+8",
        "/dashboard/notifications/",
    ),
    ("go.knowledge", "Knowledge", "", "/dashboard/knowledge/"),
    ("go.marketing", "Marketing", "", "/dashboard/marketing/"),
    (
        "go.automations",
        "Automations",
        "",
        "/dashboard/automations/",
    ),
    (
        "go.integrations",
        "Integrations",
        "",
        "/dashboard/integrations/",
    ),
    ("go.analytics", "Analytics", "", "/dashboard/analytics/"),
    ("go.agents", "Agents", "", "/dashboard/agents/"),
];

pub fn route_for_menu_id(id: &str) -> Option<&'static str> {
    match id {
        "app.settings" => Some("/dashboard/settings/"),
        "file.new_command" => Some("/dashboard/commands/new/"),
        "app.connection" => Some("/desktop/connection/"),
        _ => GO_ITEMS
            .iter()
            .find(|(item_id, ..)| *item_id == id)
            .map(|(.., route)| *route),
    }
}

pub fn build<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let version = app.package_info().version.to_string();
    let about = AboutMetadata {
        name: Some("Kiko".into()),
        version: Some(version),
        copyright: Some("© Pixart".into()),
        comments: Some("Pixart AI Operating System".into()),
        ..Default::default()
    };
    let app_menu = Submenu::with_items(
        app,
        "Kiko",
        true,
        &[
            &PredefinedMenuItem::about(app, Some("About Kiko"), Some(about))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "app.settings", "Settings…", true, Some("CmdOrCtrl+,"))?,
            &MenuItem::with_id(
                app,
                "app.connection",
                "Server Connection…",
                true,
                None::<&str>,
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::hide(app, None)?,
            &PredefinedMenuItem::hide_others(app, None)?,
            &PredefinedMenuItem::show_all(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::quit(app, Some("Quit Kiko"))?,
        ],
    )?;
    let file_menu = Submenu::with_items(
        app,
        "File",
        true,
        &[
            &MenuItem::with_id(
                app,
                "file.new_command",
                "New Command",
                true,
                Some("CmdOrCtrl+N"),
            )?,
            &MenuItem::with_id(
                app,
                "file.palette",
                "Command Palette…",
                true,
                Some("CmdOrCtrl+K"),
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::close_window(app, None)?,
        ],
    )?;
    let edit_menu = Submenu::with_items(
        app,
        "Edit",
        true,
        &[
            &PredefinedMenuItem::undo(app, None)?,
            &PredefinedMenuItem::redo(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::cut(app, None)?,
            &PredefinedMenuItem::copy(app, None)?,
            &PredefinedMenuItem::paste(app, None)?,
            &PredefinedMenuItem::select_all(app, None)?,
        ],
    )?;
    let view_menu = Submenu::with_items(
        app,
        "View",
        true,
        &[
            &MenuItem::with_id(app, "view.back", "Back", true, Some("CmdOrCtrl+["))?,
            &MenuItem::with_id(app, "view.forward", "Forward", true, Some("CmdOrCtrl+]"))?,
            &MenuItem::with_id(app, "view.reload", "Reload", true, Some("CmdOrCtrl+R"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::fullscreen(app, None)?,
        ],
    )?;
    let go_items: Vec<MenuItem<R>> = GO_ITEMS
        .iter()
        .map(|(id, label, accel, _)| {
            MenuItem::with_id(
                app,
                *id,
                *label,
                true,
                (!accel.is_empty()).then_some(*accel),
            )
        })
        .collect::<tauri::Result<_>>()?;
    let go_refs: Vec<&dyn tauri::menu::IsMenuItem<R>> = go_items
        .iter()
        .map(|item| item as &dyn tauri::menu::IsMenuItem<R>)
        .collect();
    let go_menu = Submenu::with_items(app, "Go", true, &go_refs)?;
    let window_menu = Submenu::with_items(
        app,
        "Window",
        true,
        &[
            &PredefinedMenuItem::minimize(app, None)?,
            &PredefinedMenuItem::maximize(app, Some("Zoom"))?,
        ],
    )?;
    Menu::with_items(
        app,
        &[
            &app_menu,
            &file_menu,
            &edit_menu,
            &view_menu,
            &go_menu,
            &window_menu,
        ],
    )
}

pub fn handle_event<R: Runtime>(app: &AppHandle<R>, id: &str) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    if let Some(route) = route_for_menu_id(id) {
        let _ = window.emit(NAVIGATE_EVENT, route);
        return;
    }
    let command = match id {
        "view.back" => "back",
        "view.forward" => "forward",
        "view.reload" => "reload",
        "file.palette" => "palette",
        _ => return,
    };
    let _ = window.emit(COMMAND_EVENT, command);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn menu_routes_are_internal_dashboard_paths() {
        for (id, ..) in GO_ITEMS {
            let route = route_for_menu_id(id).unwrap();
            assert!(route.starts_with("/dashboard/") && route.ends_with('/'));
        }
        assert_eq!(route_for_menu_id("unknown"), None);
    }
}
