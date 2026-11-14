//! Refresh-token storage. Production uses the macOS Keychain (login keychain, generic
//! password items). The account name is the API origin, so different servers never share
//! credentials.

use std::collections::HashMap;
use std::sync::Mutex;

use crate::api::ApiError;

pub const KEYCHAIN_SERVICE: &str = "pt.pixart.kiko.session";

pub trait TokenStore: Send + Sync {
    fn load(&self, account: &str) -> Result<Option<String>, ApiError>;
    fn store(&self, account: &str, token: &str) -> Result<(), ApiError>;
    fn delete(&self, account: &str) -> Result<(), ApiError>;
}

pub struct KeychainStore;

impl KeychainStore {
    fn entry(account: &str) -> Result<keyring::Entry, ApiError> {
        keyring::Entry::new(KEYCHAIN_SERVICE, account).map_err(|e| ApiError::Storage(e.to_string()))
    }
}

impl TokenStore for KeychainStore {
    fn load(&self, account: &str) -> Result<Option<String>, ApiError> {
        match Self::entry(account)?.get_password() {
            Ok(token) => Ok(Some(token)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(error) => Err(ApiError::Storage(error.to_string())),
        }
    }

    fn store(&self, account: &str, token: &str) -> Result<(), ApiError> {
        Self::entry(account)?
            .set_password(token)
            .map_err(|e| ApiError::Storage(e.to_string()))
    }

    fn delete(&self, account: &str) -> Result<(), ApiError> {
        match Self::entry(account)?.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(error) => Err(ApiError::Storage(error.to_string())),
        }
    }
}

/// In-memory store used by tests and by `KIKO_DESKTOP_EPHEMERAL_SESSION=1` smoke runs.
#[derive(Default)]
pub struct MemoryStore(Mutex<HashMap<String, String>>);

impl TokenStore for MemoryStore {
    fn load(&self, account: &str) -> Result<Option<String>, ApiError> {
        Ok(self
            .0
            .lock()
            .expect("token store poisoned")
            .get(account)
            .cloned())
    }

    fn store(&self, account: &str, token: &str) -> Result<(), ApiError> {
        self.0
            .lock()
            .expect("token store poisoned")
            .insert(account.to_owned(), token.to_owned());
        Ok(())
    }

    fn delete(&self, account: &str) -> Result<(), ApiError> {
        self.0.lock().expect("token store poisoned").remove(account);
        Ok(())
    }
}
