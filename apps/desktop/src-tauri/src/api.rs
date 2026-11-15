//! Authenticated proxy between the WebView and the Kiko API.
//!
//! The WebView never sees credentials. The access token lives only in this process's
//! memory and the refresh token only in the macOS Keychain. Every request from the UI is
//! validated (method, path, headers, size) before it leaves the machine.

use std::time::Duration;

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use reqwest::header::{HeaderMap, HeaderName, HeaderValue, AUTHORIZATION, COOKIE, SET_COOKIE};
use serde::{Deserialize, Serialize};
use tokio::sync::{Mutex, RwLock};
use url::Url;

use crate::keychain::TokenStore;

pub const REFRESH_COOKIE_NAME: &str = "agent_refresh_token";
pub const MAX_BODY_BYTES: usize = 25 * 1024 * 1024;
const MAX_PATH_LEN: usize = 2048;
const REQUEST_TIMEOUT: Duration = Duration::from_secs(30);
/// Local-AI generation (Supervisor plans, specialist agent runs) runs on the user's own
/// hardware and can take minutes; the backend bounds it with AI_REQUEST_TIMEOUT_SECONDS.
const AI_REQUEST_TIMEOUT: Duration = Duration::from_secs(600);
const AI_ROUTE_SUFFIXES: [&str; 4] = [
    "/generate-plan",
    "/regenerate-plan",
    "/run-agent",
    "/rerun-agent",
];

/// Timeout for one request: long only for the AI generation endpoints.
pub fn request_timeout(method: &reqwest::Method, route: &str) -> Duration {
    if method == reqwest::Method::POST
        && route.starts_with("/api/v1/")
        && AI_ROUTE_SUFFIXES
            .iter()
            .any(|suffix| route.ends_with(suffix))
    {
        AI_REQUEST_TIMEOUT
    } else {
        REQUEST_TIMEOUT
    }
}
/// Below common server keep-alive limits (uvicorn 5 s) so a connection the server is about
/// to close is not reused for the next request.
const POOL_IDLE_TIMEOUT: Duration = Duration::from_secs(4);
/// Replaces the real access token in JSON bodies handed to the WebView.
pub const DESKTOP_TOKEN_SENTINEL: &str = "desktop-managed";

const ALLOWED_METHODS: &[&str] = &["GET", "POST", "PUT", "PATCH", "DELETE"];
const ALLOWED_REQUEST_HEADERS: &[&str] = &["accept", "content-type", "idempotency-key"];
const FORWARDED_RESPONSE_HEADERS: &[&str] = &[
    "content-type",
    "content-disposition",
    "retry-after",
    "x-request-id",
    "location",
];

#[derive(Debug, thiserror::Error, Serialize)]
#[serde(tag = "kind", content = "message", rename_all = "snake_case")]
pub enum ApiError {
    #[error("invalid request: {0}")]
    InvalidRequest(String),
    #[error("the Kiko server could not be reached")]
    Offline(String),
    #[error("the Kiko server did not answer in time")]
    Timeout(String),
    #[error("secure storage is unavailable: {0}")]
    Storage(String),
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ApiRequest {
    pub method: String,
    pub path: String,
    #[serde(default)]
    pub headers: Vec<(String, String)>,
    #[serde(default)]
    pub body_base64: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApiResponse {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body_base64: String,
}

/// Validate a request path coming from the UI. Only relative Kiko API paths are allowed.
pub fn validate_path(path: &str) -> Result<(), ApiError> {
    let invalid = |reason: &str| Err(ApiError::InvalidRequest(reason.to_owned()));
    if path.len() > MAX_PATH_LEN {
        return invalid("path too long");
    }
    let (route, _query) = path.split_once('?').unwrap_or((path, ""));
    if !(route.starts_with("/api/v1/") || route == "/health") {
        return invalid("path outside the Kiko API");
    }
    if route.contains("//") || route.contains('\\') || route.contains('#') {
        return invalid("malformed path");
    }
    let decoded = percent_encoding::percent_decode_str(route).decode_utf8_lossy();
    if decoded
        .split('/')
        .any(|segment| segment == ".." || segment == ".")
    {
        return invalid("path traversal");
    }
    if path.chars().any(|c| c.is_control() || c.is_whitespace()) {
        return invalid("control characters in path");
    }
    Ok(())
}

pub fn validate_method(method: &str) -> Result<reqwest::Method, ApiError> {
    let upper = method.to_ascii_uppercase();
    if !ALLOWED_METHODS.contains(&upper.as_str()) {
        return Err(ApiError::InvalidRequest(format!(
            "method {method} not allowed"
        )));
    }
    reqwest::Method::from_bytes(upper.as_bytes())
        .map_err(|_| ApiError::InvalidRequest("invalid method".into()))
}

fn filtered_request_headers(headers: &[(String, String)]) -> Result<HeaderMap, ApiError> {
    let mut map = HeaderMap::new();
    for (name, value) in headers {
        let lower = name.to_ascii_lowercase();
        if !ALLOWED_REQUEST_HEADERS.contains(&lower.as_str()) {
            continue; // Authorization, Cookie, Origin, Host… are never accepted from the UI.
        }
        let header_name = HeaderName::from_bytes(lower.as_bytes())
            .map_err(|_| ApiError::InvalidRequest("invalid header name".into()))?;
        let header_value = HeaderValue::from_str(value)
            .map_err(|_| ApiError::InvalidRequest("invalid header value".into()))?;
        map.insert(header_name, header_value);
    }
    Ok(map)
}

/// Outcome of a `Set-Cookie` header for the refresh cookie.
#[derive(Debug, PartialEq, Eq)]
pub enum RefreshCookie {
    Set(String),
    Cleared,
}

/// Parse a single `Set-Cookie` header value for the Kiko refresh cookie.
pub fn parse_refresh_cookie(set_cookie: &str) -> Option<RefreshCookie> {
    let mut parts = set_cookie.split(';');
    let (name, value) = parts.next()?.trim().split_once('=')?;
    if name.trim() != REFRESH_COOKIE_NAME {
        return None;
    }
    let value = value.trim().trim_matches('"');
    let expired = parts.any(|attr| {
        let attr = attr.trim().to_ascii_lowercase();
        attr == "max-age=0"
            || attr.starts_with("max-age=-")
            || attr.contains("expires=thu, 01 jan 1970")
    });
    if value.is_empty() || expired {
        Some(RefreshCookie::Cleared)
    } else {
        Some(RefreshCookie::Set(value.to_owned()))
    }
}

/// Remove `access_token` from a JSON object body, returning the token if one was present.
pub fn extract_access_token(body: &[u8]) -> Option<(String, Vec<u8>)> {
    let mut value: serde_json::Value = serde_json::from_slice(body).ok()?;
    let object = value.as_object_mut()?;
    let token = object.get("access_token")?.as_str()?.to_owned();
    object.insert(
        "access_token".into(),
        serde_json::Value::String(DESKTOP_TOKEN_SENTINEL.into()),
    );
    Some((token, serde_json::to_vec(&value).ok()?))
}

/// Methods that can be retried without risk of repeating a business write.
pub fn is_retry_safe(method: &reqwest::Method) -> bool {
    matches!(*method, reqwest::Method::GET | reqwest::Method::HEAD)
}

fn is_auth_session_path(route: &str) -> bool {
    matches!(route, "/api/v1/auth/refresh" | "/api/v1/auth/logout")
}

pub struct ApiClient {
    http: reqwest::Client,
    base: RwLock<Url>,
    access_token: RwLock<Option<String>>,
    refresh_lock: Mutex<()>,
    tokens: Box<dyn TokenStore>,
    user_agent: String,
}

struct RawResponse {
    status: u16,
    headers: HeaderMap,
    body: Vec<u8>,
}

impl ApiClient {
    pub fn new(base: Url, tokens: Box<dyn TokenStore>, version: &str) -> Result<Self, ApiError> {
        let http = reqwest::Client::builder()
            .timeout(REQUEST_TIMEOUT)
            .connect_timeout(Duration::from_secs(10))
            .pool_idle_timeout(POOL_IDLE_TIMEOUT)
            // Redirects could leak the bearer token to another origin.
            .redirect(reqwest::redirect::Policy::none())
            // Plain HTTP is only reachable for loopback hosts (see config::validate_api_url).
            .build()
            .map_err(|e| ApiError::InvalidRequest(e.to_string()))?;
        Ok(Self {
            http,
            base: RwLock::new(base),
            access_token: RwLock::new(None),
            refresh_lock: Mutex::new(()),
            tokens,
            user_agent: format!("Kiko-Desktop/{version} (macOS)"),
        })
    }

    pub async fn base_url(&self) -> Url {
        self.base.read().await.clone()
    }

    /// Point the client at another server. Callers must clear the session first.
    pub async fn set_base_url(&self, base: Url) {
        *self.access_token.write().await = None;
        *self.base.write().await = base;
    }

    fn account_key(base: &Url) -> String {
        base.origin().ascii_serialization()
    }

    pub async fn has_session(&self) -> Result<bool, ApiError> {
        let base = self.base_url().await;
        Ok(self.tokens.load(&Self::account_key(&base))?.is_some())
    }

    /// Forget all credentials for the current server (local sign-out).
    pub async fn clear_session(&self) -> Result<(), ApiError> {
        *self.access_token.write().await = None;
        let base = self.base_url().await;
        self.tokens.delete(&Self::account_key(&base))
    }

    pub async fn request(&self, request: ApiRequest) -> Result<ApiResponse, ApiError> {
        validate_path(&request.path)?;
        let method = validate_method(&request.method)?;
        let headers = filtered_request_headers(&request.headers)?;
        let body = match request.body_base64 {
            Some(encoded) => {
                if encoded.len() > MAX_BODY_BYTES * 4 / 3 + 4 {
                    return Err(ApiError::InvalidRequest("body too large".into()));
                }
                let bytes = B64
                    .decode(encoded)
                    .map_err(|_| ApiError::InvalidRequest("body is not base64".into()))?;
                Some(bytes)
            }
            None => None,
        };
        let route = request
            .path
            .split('?')
            .next()
            .unwrap_or_default()
            .to_owned();
        #[cfg(debug_assertions)]
        eprintln!("[api] {} {}", method, route);

        let mut response = self
            .send(&method, &request.path, &headers, body.as_deref())
            .await?;
        let retry_after_refresh =
            response.status == 401 && !route.starts_with("/api/v1/auth/") && self.refresh().await?;
        if retry_after_refresh {
            response = self
                .send(&method, &request.path, &headers, body.as_deref())
                .await?;
        }

        let mut body = response.body;
        if route == "/api/v1/auth/login" || route == "/api/v1/auth/refresh" {
            if let Some((token, stripped)) = extract_access_token(&body) {
                *self.access_token.write().await = Some(token);
                body = stripped;
            }
        }
        if route == "/api/v1/auth/logout"
            || (route == "/api/v1/auth/refresh" && response.status == 401)
        {
            *self.access_token.write().await = None;
        }

        let headers = response
            .headers
            .iter()
            .filter(|(name, _)| FORWARDED_RESPONSE_HEADERS.contains(&name.as_str()))
            .filter_map(|(name, value)| {
                value
                    .to_str()
                    .ok()
                    .map(|v| (name.as_str().to_owned(), v.to_owned()))
            })
            .collect();
        Ok(ApiResponse {
            status: response.status,
            headers,
            body_base64: B64.encode(body),
        })
    }

    /// Rotate the refresh token. Returns `true` when a new access token is available.
    pub async fn refresh(&self) -> Result<bool, ApiError> {
        let observed = self.access_token.read().await.clone();
        let _guard = self.refresh_lock.lock().await;
        // Another caller refreshed while we waited for the lock.
        let current = self.access_token.read().await.clone();
        if current.is_some() && current != observed {
            return Ok(true);
        }
        let base = self.base_url().await;
        if self.tokens.load(&Self::account_key(&base))?.is_none() {
            return Ok(false);
        }
        let response = self
            .send(
                &reqwest::Method::POST,
                "/api/v1/auth/refresh",
                &HeaderMap::new(),
                None,
            )
            .await?;
        if response.status != 200 {
            *self.access_token.write().await = None;
            return Ok(false);
        }
        match extract_access_token(&response.body) {
            Some((token, _)) => {
                *self.access_token.write().await = Some(token);
                Ok(true)
            }
            None => Ok(false),
        }
    }

    async fn send(
        &self,
        method: &reqwest::Method,
        path: &str,
        headers: &HeaderMap,
        body: Option<&[u8]>,
    ) -> Result<RawResponse, ApiError> {
        let base = self.base_url().await;
        let url = base
            .join(path)
            .map_err(|_| ApiError::InvalidRequest("invalid path".into()))?;
        if url.origin() != base.origin() {
            return Err(ApiError::InvalidRequest("cross-origin request".into()));
        }
        let account = Self::account_key(&base);
        let route = path.split('?').next().unwrap_or_default();

        let build = |token: Option<&String>, refresh: Option<&String>| {
            let mut builder = self
                .http
                .request(method.clone(), url.clone())
                .headers(headers.clone())
                .header(reqwest::header::USER_AGENT, &self.user_agent)
                .header("X-Kiko-Client", "desktop-macos")
                .timeout(request_timeout(method, route));
            if let Some(token) = token {
                builder = builder.header(AUTHORIZATION, format!("Bearer {token}"));
            }
            if let Some(refresh) = refresh {
                builder = builder.header(COOKIE, format!("{REFRESH_COOKIE_NAME}={refresh}"));
            }
            if let Some(bytes) = body {
                builder = builder.body(bytes.to_vec());
            }
            builder
        };
        let token = self.access_token.read().await.clone();
        let refresh = if is_auth_session_path(route) {
            self.tokens.load(&account)?
        } else {
            None
        };

        let mut attempt = 0;
        let response = loop {
            attempt += 1;
            match build(token.as_ref(), refresh.as_ref()).send().await {
                Ok(response) => break response,
                // Only safe methods are retried, and only for connection-level failures
                // (e.g. a pooled keep-alive connection closed by the server). Writes are
                // never repeated automatically.
                Err(error)
                    if attempt == 1
                        && is_retry_safe(method)
                        && (error.is_connect() || error.is_request())
                        && !error.is_timeout() => {}
                Err(error) if error.is_timeout() => {
                    return Err(ApiError::Timeout(error.to_string()))
                }
                Err(error) => return Err(ApiError::Offline(error.to_string())),
            }
        };
        let status = response.status().as_u16();
        let response_headers = response.headers().clone();
        for value in response_headers.get_all(SET_COOKIE) {
            match value.to_str().ok().and_then(parse_refresh_cookie) {
                Some(RefreshCookie::Set(token)) => self.tokens.store(&account, &token)?,
                Some(RefreshCookie::Cleared) => self.tokens.delete(&account)?,
                None => {}
            }
        }
        if route == "/api/v1/auth/refresh" && status == 401 {
            self.tokens.delete(&account)?;
        }
        let body = response
            .bytes()
            .await
            .map_err(|e| ApiError::Offline(e.to_string()))?;
        if body.len() > MAX_BODY_BYTES * 4 {
            return Err(ApiError::InvalidRequest("response too large".into()));
        }
        Ok(RawResponse {
            status,
            headers: response_headers,
            body: body.to_vec(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_api_paths() {
        assert!(validate_path("/api/v1/tasks").is_ok());
        assert!(validate_path("/api/v1/tasks/abc?status=open&page=2").is_ok());
        assert!(validate_path("/health").is_ok());
    }

    #[test]
    fn rejects_paths_outside_the_api() {
        for path in [
            "/metrics",
            "https://evil.example/api/v1/x",
            "//evil.example/api/v1/x",
            "/api/v2/x",
            "api/v1/tasks",
            "/api/v1/../metrics",
            "/api/v1/%2e%2e/metrics",
            "/api/v1/tasks\\x",
            "/api/v1/tasks#frag",
            "/api/v1/tasks\n",
            "/api/v1/ta sks",
        ] {
            assert!(validate_path(path).is_err(), "{path} should be rejected");
        }
        assert!(validate_path(&format!("/api/v1/{}", "a".repeat(3000))).is_err());
    }

    #[test]
    fn only_safe_methods_are_retried() {
        assert!(is_retry_safe(&reqwest::Method::GET));
        assert_eq!(
            request_timeout(&reqwest::Method::POST, "/api/v1/commands/abc/generate-plan"),
            AI_REQUEST_TIMEOUT
        );
        assert_eq!(
            request_timeout(&reqwest::Method::POST, "/api/v1/tasks/abc/run-agent"),
            AI_REQUEST_TIMEOUT
        );
        assert_eq!(
            request_timeout(&reqwest::Method::GET, "/api/v1/commands/abc/generate-plan"),
            REQUEST_TIMEOUT
        );
        assert_eq!(
            request_timeout(&reqwest::Method::POST, "/api/v1/auth/login"),
            REQUEST_TIMEOUT
        );
        for method in [
            reqwest::Method::POST,
            reqwest::Method::PUT,
            reqwest::Method::PATCH,
            reqwest::Method::DELETE,
        ] {
            assert!(!is_retry_safe(&method));
        }
    }

    #[test]
    fn method_allowlist() {
        assert!(validate_method("get").is_ok());
        assert!(validate_method("PATCH").is_ok());
        assert!(validate_method("TRACE").is_err());
        assert!(validate_method("CONNECT").is_err());
    }

    #[test]
    fn drops_sensitive_request_headers() {
        let headers = filtered_request_headers(&[
            ("Authorization".into(), "Bearer stolen".into()),
            ("Cookie".into(), "a=b".into()),
            ("Origin".into(), "https://evil.example".into()),
            ("Content-Type".into(), "application/json".into()),
            ("Idempotency-Key".into(), "k1".into()),
        ])
        .unwrap();
        assert_eq!(headers.len(), 2);
        assert!(headers.get("authorization").is_none());
        assert!(headers.get("cookie").is_none());
        assert_eq!(headers.get("content-type").unwrap(), "application/json");
    }

    #[test]
    fn parses_refresh_cookie() {
        assert_eq!(
            parse_refresh_cookie(
                "agent_refresh_token=abc123; HttpOnly; Path=/api/v1/auth; Max-Age=2592000"
            ),
            Some(RefreshCookie::Set("abc123".into()))
        );
        assert_eq!(
            parse_refresh_cookie("agent_refresh_token=\"\"; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/api/v1/auth"),
            Some(RefreshCookie::Cleared)
        );
        assert_eq!(parse_refresh_cookie("other=abc; Path=/"), None);
    }

    #[test]
    fn strips_access_token_from_bodies() {
        let (token, body) =
            extract_access_token(br#"{"access_token":"secret.jwt","user":{"id":"u"}}"#).unwrap();
        assert_eq!(token, "secret.jwt");
        let text = String::from_utf8(body).unwrap();
        assert!(!text.contains("secret.jwt"));
        assert!(text.contains(DESKTOP_TOKEN_SENTINEL));
        assert!(extract_access_token(b"{\"message\":\"ok\"}").is_none());
        assert!(extract_access_token(b"not json").is_none());
    }
}
