//! Native macOS menu bar. Navigation items emit `kiko://navigate` with an in-app route;
//! the UI performs the navigation. Standard Edit items are required for text editing
//! shortcuts (copy, paste, undo) to work inside the WebView on macOS.

use tauri::menu::{AboutMetadata, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Emitter, Manager, Runtime};

pub const NAVIGATE_EVENT: &str = "kiko://navigate";
pub const COMMAND_EVENT: &str = "kiko://command";

/// (menu id, label, accelerator, route)
pub const GO_ITEMS: &[(&str, &str, &str, &str)] = &[
    ("go.home", "Início", "CmdOrCtrl+1", "/dashboard/"),
    ("go.kiko", "Conversas", "CmdOrCtrl+2", "/dashboard/kiko/"),
    (
        "go.commands",
        "Comandos",
        "CmdOrCtrl+3",
        "/dashboard/commands/",
    ),
    ("go.tasks", "Tarefas", "CmdOrCtrl+4", "/dashboard/tasks/"),
    (
        "go.projects",
        "Projetos",
        "CmdOrCtrl+5",
        "/dashboard/projects/",
    ),
    (
        "go.approvals",
        "Aprovações",
        "CmdOrCtrl+6",
        "/dashboard/approvals/",
    ),
    ("go.crm", "CRM", "CmdOrCtrl+7", "/dashboard/crm/"),
    (
        "go.notifications",
        "Notificações",
        "CmdOrCtrl+8",
        "/dashboard/notifications/",
    ),
    ("go.knowledge", "Conhecimento", "", "/dashboard/knowledge/"),
    ("go.marketing", "Marketing", "", "/dashboard/marketing/"),
    (
        "go.automations",
        "Automatizações",
        "",
        "/dashboard/automations/",
    ),
    (
        "go.integrations",
        "Integrações",
        "",
        "/dashboard/integrations/",
    ),
    ("go.analytics", "Relatórios", "", "/dashboard/analytics/"),
    ("go.agents", "Agentes", "", "/dashboard/agents/"),
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
        comments: Some("Sistema operativo de IA da Pixart".into()),
        ..Default::default()
    };
    let app_menu = Submenu::with_items(
        app,
        "Kiko",
        true,
        &[
            &PredefinedMenuItem::about(app, Some("Acerca do Kiko"), Some(about))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(
                app,
                "app.settings",
                "Definições…",
                true,
                Some("CmdOrCtrl+,"),
            )?,
            &MenuItem::with_id(
                app,
                "app.connection",
                "Ligação ao servidor…",
                true,
                None::<&str>,
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::hide(app, Some("Ocultar Kiko"))?,
            &PredefinedMenuItem::hide_others(app, Some("Ocultar outras"))?,
            &PredefinedMenuItem::show_all(app, Some("Mostrar todas"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::quit(app, Some("Sair do Kiko"))?,
        ],
    )?;
    let file_menu = Submenu::with_items(
        app,
        "Ficheiro",
        true,
        &[
            &MenuItem::with_id(
                app,
                "file.new_command",
                "Novo comando",
                true,
                Some("CmdOrCtrl+N"),
            )?,
            &MenuItem::with_id(
                app,
                "file.palette",
                "Pesquisar no Kiko…",
                true,
                Some("CmdOrCtrl+K"),
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::close_window(app, Some("Fechar janela"))?,
        ],
    )?;
    let edit_menu = Submenu::with_items(
        app,
        "Editar",
        true,
        &[
            &PredefinedMenuItem::undo(app, Some("Desfazer"))?,
            &PredefinedMenuItem::redo(app, Some("Refazer"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::cut(app, Some("Cortar"))?,
            &PredefinedMenuItem::copy(app, Some("Copiar"))?,
            &PredefinedMenuItem::paste(app, Some("Colar"))?,
            &PredefinedMenuItem::select_all(app, Some("Selecionar tudo"))?,
        ],
    )?;
    let view_menu = Submenu::with_items(
        app,
        "Ver",
        true,
        &[
            &MenuItem::with_id(app, "view.back", "Recuar", true, Some("CmdOrCtrl+["))?,
            &MenuItem::with_id(app, "view.forward", "Avançar", true, Some("CmdOrCtrl+]"))?,
            &MenuItem::with_id(app, "view.reload", "Recarregar", true, Some("CmdOrCtrl+R"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::fullscreen(app, Some("Entrar em ecrã inteiro"))?,
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
    let go_menu = Submenu::with_items(app, "Ir", true, &go_refs)?;
    let window_menu = Submenu::with_items(
        app,
        "Janela",
        true,
        &[
            &PredefinedMenuItem::minimize(app, Some("Minimizar"))?,
            &PredefinedMenuItem::maximize(app, Some("Ampliar"))?,
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
