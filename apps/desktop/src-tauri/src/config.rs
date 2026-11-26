//! Backend connection settings.
//!
//! Resolution order: `KIKO_API_URL` environment variable (development and smoke tests),
//! then `server.json` in the app config directory (set from the in-app Connection screen),
//! then the URL baked in at build time (`KIKO_DEFAULT_API_URL`), then local development.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use url::Url;

pub const DEV_API_URL: &str = "http://localhost:8000";
const SERVER_FILE: &str = "server.json";

#[derive(Debug, Serialize, Deserialize)]
struct ServerFile {
    api_base_url: String,
}

/// Accept only an origin (no path, query, credentials). HTTPS is mandatory except for
/// loopback development servers.
pub fn validate_api_url(raw: &str) -> Result<Url, String> {
    let url = Url::parse(raw.trim()).map_err(|_| {
        "Indica um endereço completo, por exemplo https://kiko.example.com.".to_owned()
    })?;
    if !url.username().is_empty() || url.password().is_some() {
        return Err("O endereço do servidor não pode conter credenciais.".into());
    }
    if url.query().is_some()
        || url.fragment().is_some()
        || !(url.path() == "/" || url.path().is_empty())
    {
        return Err("Usa só a origem do servidor, sem caminho.".into());
    }
    let host = url
        .host_str()
        .ok_or("O endereço do servidor precisa de um anfitrião.")?;
    let loopback = matches!(host, "localhost" | "127.0.0.1" | "[::1]" | "::1");
    match url.scheme() {
        "https" => {}
        "http" if loopback => {}
        "http" => return Err("Os servidores remotos têm de usar HTTPS.".into()),
        _ => return Err("Só são suportados servidores HTTPS.".into()),
    }
    Ok(Url::parse(&url.origin().ascii_serialization()).expect("origin is a valid URL"))
}

pub fn server_file(config_dir: &Path) -> PathBuf {
    config_dir.join(SERVER_FILE)
}

pub fn resolve_api_url(config_dir: Option<&Path>) -> Url {
    if let Ok(value) = std::env::var("KIKO_API_URL") {
        if let Ok(url) = validate_api_url(&value) {
            return url;
        }
    }
    if let Some(dir) = config_dir {
        if let Ok(text) = std::fs::read_to_string(server_file(dir)) {
            if let Ok(file) = serde_json::from_str::<ServerFile>(&text) {
                if let Ok(url) = validate_api_url(&file.api_base_url) {
                    return url;
                }
            }
        }
    }
    if let Some(baked) = option_env!("KIKO_DEFAULT_API_URL") {
        if let Ok(url) = validate_api_url(baked) {
            return url;
        }
    }
    validate_api_url(DEV_API_URL).expect("development URL is valid")
}

pub fn save_api_url(config_dir: &Path, url: &Url) -> std::io::Result<()> {
    std::fs::create_dir_all(config_dir)?;
    let body = serde_json::to_vec_pretty(&ServerFile {
        api_base_url: url.origin().ascii_serialization(),
    })?;
    std::fs::write(server_file(config_dir), body)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_https_and_loopback_http() {
        assert_eq!(
            validate_api_url("https://kiko.example.com")
                .unwrap()
                .as_str(),
            "https://kiko.example.com/"
        );
        assert!(validate_api_url("https://kiko.example.com/").is_ok());
        assert!(validate_api_url("http://localhost:8000").is_ok());
        assert!(validate_api_url("http://127.0.0.1:8000").is_ok());
    }

    #[test]
    fn rejects_unsafe_urls() {
        for raw in [
            "http://kiko.example.com",
            "ftp://kiko.example.com",
            "https://user:pass@kiko.example.com",
            "https://kiko.example.com/api",
            "https://kiko.example.com?x=1",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "not a url",
        ] {
            assert!(validate_api_url(raw).is_err(), "{raw} should be rejected");
        }
    }

    #[test]
    fn round_trips_server_file() {
        let dir = std::env::temp_dir().join(format!("kiko-config-test-{}", std::process::id()));
        let url = validate_api_url("https://kiko.example.com").unwrap();
        save_api_url(&dir, &url).unwrap();
        std::env::remove_var("KIKO_API_URL");
        assert_eq!(resolve_api_url(Some(&dir)), url);
        std::fs::remove_dir_all(dir).ok();
    }
}
