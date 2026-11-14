//! `kiko://` deep links. Links only ever navigate inside the app; they never perform an
//! action by themselves. Unknown or malformed links are ignored.
//!
//! Supported forms:
//! - `kiko://open/<dashboard path>` → `/dashboard/<path>/`
//! - `kiko://verify-email?token=<token>` → `/verify-email/?token=<token>`
//! - `kiko://reset-password?token=<token>` → `/reset-password/?token=<token>`
//! - `kiko://invite?token=<token>` → `/invite/?token=<token>`

use std::sync::Mutex;

use url::Url;

const MAX_LINK_LEN: usize = 2048;
const MAX_TOKEN_LEN: usize = 512;

fn safe_segment(segment: &str) -> bool {
    !segment.is_empty()
        && segment.len() <= 128
        && segment
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_'))
}

fn safe_token(token: &str) -> bool {
    !token.is_empty()
        && token.len() <= MAX_TOKEN_LEN
        && token
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | '~'))
}

/// Translate a deep link into an in-app route, or `None` if it is not allowed.
pub fn route_for(link: &str) -> Option<String> {
    if link.len() > MAX_LINK_LEN {
        return None;
    }
    // Reject traversal before URL parsing normalises it away.
    let lower = link.to_ascii_lowercase();
    if lower.contains("..") || lower.contains("%2e") || lower.contains('\\') {
        return None;
    }
    let url = Url::parse(link).ok()?;
    if url.scheme() != "kiko" || !url.username().is_empty() || url.password().is_some() {
        return None;
    }
    let host = url.host_str()?;
    let token = || {
        url.query_pairs()
            .find(|(key, _)| key == "token")
            .map(|(_, value)| value.into_owned())
            .filter(|value| safe_token(value))
    };
    match host {
        "open" => {
            let segments: Vec<&str> = url.path().split('/').filter(|s| !s.is_empty()).collect();
            if segments.len() > 6 || !segments.iter().all(|s| safe_segment(s)) {
                return None;
            }
            if segments.is_empty() {
                return Some("/dashboard/".into());
            }
            Some(format!("/dashboard/{}/", segments.join("/")))
        }
        "verify-email" | "reset-password" | "invite" => {
            Some(format!("/{host}/?token={}", token()?))
        }
        _ => None,
    }
}

/// Holds a deep link that arrived before the UI could listen for navigation events
/// (cold start: the link is delivered while the window is still loading, so an emitted
/// event would be lost). Once the UI has taken the pending route, links are emitted live.
#[derive(Default)]
pub struct PendingRoute(Mutex<PendingState>);

#[derive(Default)]
struct PendingState {
    route: Option<String>,
    ui_ready: bool,
}

impl PendingRoute {
    /// Offer a route. Returns it back when the UI is listening (emit it now); otherwise it
    /// is kept (latest wins) until the UI calls [`PendingRoute::take`].
    pub fn offer(&self, route: String) -> Option<String> {
        let mut state = self.0.lock().unwrap_or_else(|e| e.into_inner());
        if state.ui_ready {
            Some(route)
        } else {
            state.route = Some(route);
            None
        }
    }

    /// Mark the UI as listening and hand over the route that arrived before, if any.
    pub fn take(&self) -> Option<String> {
        let mut state = self.0.lock().unwrap_or_else(|e| e.into_inner());
        state.ui_ready = true;
        state.route.take()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pending_route_is_kept_until_the_ui_listens() {
        let pending = PendingRoute::default();
        assert_eq!(pending.offer("/verify-email/?token=a".into()), None);
        assert_eq!(pending.offer("/verify-email/?token=b".into()), None);
        assert_eq!(pending.take().as_deref(), Some("/verify-email/?token=b"));
        assert_eq!(pending.take(), None);
        assert_eq!(
            pending.offer("/dashboard/tasks/".into()).as_deref(),
            Some("/dashboard/tasks/")
        );
        assert_eq!(pending.take(), None);
    }

    #[test]
    fn maps_supported_links() {
        assert_eq!(
            route_for("kiko://open/tasks/abc-123").as_deref(),
            Some("/dashboard/tasks/abc-123/")
        );
        assert_eq!(route_for("kiko://open").as_deref(), Some("/dashboard/"));
        assert_eq!(
            route_for("kiko://verify-email?token=AbC_123-x").as_deref(),
            Some("/verify-email/?token=AbC_123-x")
        );
        assert_eq!(
            route_for("kiko://invite?token=t0k").as_deref(),
            Some("/invite/?token=t0k")
        );
    }

    #[test]
    fn rejects_unsafe_links() {
        for link in [
            "https://open/tasks",
            "kiko://open/../../etc",
            "kiko://open/tasks/%2e%2e",
            "kiko://open/tasks/<script>",
            "kiko://settings/delete",
            "kiko://verify-email",
            "kiko://verify-email?token=",
            "kiko://verify-email?token=a%20b",
            "kiko://user:pw@open/tasks",
            "javascript:alert(1)",
        ] {
            assert_eq!(route_for(link), None, "{link} should be rejected");
        }
        assert_eq!(
            route_for(&format!("kiko://invite?token={}", "a".repeat(600))),
            None
        );
    }
}
