//! `kiko://` protocol: serves the bundled UI (a Next.js static export).
//!
//! Dynamic routes are exported once with the placeholder segment `__kiko__`. A request
//! for `/dashboard/tasks/<id>/` is served from `/dashboard/tasks/__kiko__/index.html`
//! (and likewise for the matching `.txt` RSC payloads). The URL the page sees keeps the
//! real identifier, which `lib/route-params.ts` reads on the client.

use percent_encoding::percent_decode_str;

pub const PLACEHOLDER: &str = "__kiko__";

/// Normalise a request path into a relative asset key. Returns `None` for traversal or
/// malformed input.
pub fn normalise(path: &str) -> Option<String> {
    let raw = path.split(['?', '#']).next().unwrap_or_default();
    let decoded = percent_decode_str(raw).decode_utf8().ok()?;
    let mut parts = Vec::new();
    for segment in decoded.split('/') {
        match segment {
            "" | "." => continue,
            ".." => return None,
            s if s.contains('\\') || s.chars().any(char::is_control) => return None,
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// Candidate asset keys for a request, most specific first.
pub fn candidates(path: &str) -> Vec<String> {
    let Some(key) = normalise(path) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    let mut push_variants = |base: &str| {
        if base.is_empty() {
            out.push("index.html".to_owned());
            return;
        }
        out.push(base.to_owned());
        out.push(format!("{base}/index.html"));
        out.push(format!("{base}.html"));
    };
    push_variants(&key);
    if key.starts_with("_next/") {
        return out;
    }
    let segments: Vec<&str> = key.split('/').collect();
    // Replace one segment (right to left) with the placeholder. Static segments never
    // equal the placeholder, so only exported dynamic routes can match.
    for index in (1..segments.len()).rev() {
        if segments[index] == PLACEHOLDER {
            continue;
        }
        let mut replaced = segments.clone();
        replaced[index] = PLACEHOLDER;
        push_variants(&replaced.join("/"));
    }
    out
}

pub fn mime_for(key: &str) -> &'static str {
    match key.rsplit('.').next().unwrap_or_default() {
        "html" => "text/html; charset=utf-8",
        "js" | "mjs" => "text/javascript; charset=utf-8",
        "css" => "text/css; charset=utf-8",
        "json" => "application/json",
        "txt" => "text/x-component; charset=utf-8",
        "svg" => "image/svg+xml",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "webp" => "image/webp",
        "ico" => "image/x-icon",
        "woff2" => "font/woff2",
        "woff" => "font/woff",
        _ => "application/octet-stream",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn root_and_static_pages() {
        assert_eq!(candidates("/")[0], "index.html");
        assert!(candidates("/dashboard/").contains(&"dashboard/index.html".to_owned()));
    }

    #[test]
    fn dynamic_routes_map_to_placeholder() {
        let c = candidates("/dashboard/tasks/abc-123/");
        assert!(c.contains(&"dashboard/tasks/__kiko__/index.html".to_owned()));
        let rsc = candidates("/dashboard/tasks/abc-123/index.txt");
        assert!(rsc.contains(&"dashboard/tasks/__kiko__/index.txt".to_owned()));
        let crm = candidates("/dashboard/crm/clients/7f3e/");
        assert!(crm.contains(&"dashboard/crm/clients/__kiko__/index.html".to_owned()));
    }

    #[test]
    fn static_chunks_are_not_rewritten_and_are_decoded() {
        let c = candidates("/_next/static/chunks/app/dashboard/tasks/%5Bid%5D/page-1.js");
        assert_eq!(
            c[0],
            "_next/static/chunks/app/dashboard/tasks/[id]/page-1.js"
        );
        assert!(c.iter().all(|k| !k.contains(PLACEHOLDER)));
    }

    #[test]
    fn traversal_is_rejected() {
        assert!(candidates("/../../etc/passwd").is_empty());
        assert!(candidates("/dashboard/%2e%2e/%2e%2e/secret").is_empty());
        assert!(candidates("/a\\b").is_empty());
    }

    #[test]
    fn mime_types() {
        assert!(mime_for("index.html").starts_with("text/html"));
        assert!(mime_for("x.js").starts_with("text/javascript"));
        assert_eq!(mime_for("blob"), "application/octet-stream");
    }
}
