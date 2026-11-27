// Desktop E2E helpers. Prepended to each phase script by run-journey.sh and executed inside
// the real Kiko WebView of a debug build (see src-tauri/src/smoke.rs). Drives the actual UI
// through the DOM; every API call goes through the production IPC bridge to a real backend.
const K = window.__KIKO_SMOKE__ || {};
const report = (line) =>
  window.__TAURI_INTERNALS__.invoke('smoke_report', { line });
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const pageText = () => document.body.innerText;

async function waitFor(predicate, label, timeout = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    try {
      const value = predicate();
      if (value) return value;
    } catch {
      // keep polling
    }
    await sleep(150);
  }
  throw new Error(
    `timeout waiting for ${label} at ${location.pathname}: ${pageText().slice(0, 240).replace(/\n/g, ' | ')}`,
  );
}

function labelControl(text) {
  const wanted = text.toLowerCase();
  const label = [...document.querySelectorAll('label')].find((item) =>
    item.textContent.trim().toLowerCase().startsWith(wanted),
  );
  return label
    ? label.control || label.querySelector('input,textarea,select')
    : null;
}

function setValue(element, value) {
  const proto =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : element instanceof HTMLSelectElement
        ? HTMLSelectElement.prototype
        : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(element, value);
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
}

async function fill(label, value) {
  setValue(await waitFor(() => labelControl(label), `field "${label}"`), value);
}

async function check(label) {
  const box = await waitFor(() => labelControl(label), `checkbox "${label}"`);
  if (!box.checked) box.click();
}

function actionByText(text) {
  const wanted = text.toLowerCase();
  return [...document.querySelectorAll('button, a')].find(
    (item) =>
      item.textContent.trim().toLowerCase().startsWith(wanted) &&
      !item.disabled &&
      item.offsetParent !== null,
  );
}

async function click(text) {
  (await waitFor(() => actionByText(text), `action "${text}"`)).click();
}

async function seeText(text, timeout) {
  await waitFor(() => pageText().includes(text), `text "${text}"`, timeout);
}

async function atPath(prefix, timeout) {
  await waitFor(
    () => location.pathname.startsWith(prefix),
    `path ${prefix}`,
    timeout,
  );
}

async function go(path) {
  const target = path.split('?')[0].replace(/\/$/, '');
  // The App Router can drop a push issued while a previous transition is still running;
  // retry instead of failing on a lost navigation.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    window.next.router.push(path);
    try {
      await atPath(target, 7000);
      return;
    } catch (error) {
      if (attempt === 2) throw error;
    }
  }
}

async function step(name, body) {
  await body();
  await report(`PASS ${name}`);
}

async function phase(name, body) {
  try {
    await body();
    await report(`DONE ${name}`);
  } catch (error) {
    await report(
      `FAIL ${name}: ${error && error.message ? error.message : String(error)}`,
    );
  }
}

// RFC 6238 TOTP (HMAC-SHA1, 30 s, 6 digits) in plain JS: `crypto.subtle` is not guaranteed
// on the app's custom kikoui:// scheme. Used only by the journey's two-factor steps.
function sha1(bytes) {
  const words = [];
  const length = bytes.length;
  const padded = new Uint8Array(((length + 9 + 63) >> 6) << 6);
  padded.set(bytes);
  padded[length] = 0x80;
  const bits = length * 8;
  padded[padded.length - 4] = (bits >>> 24) & 0xff;
  padded[padded.length - 3] = (bits >>> 16) & 0xff;
  padded[padded.length - 2] = (bits >>> 8) & 0xff;
  padded[padded.length - 1] = bits & 0xff;
  let [h0, h1, h2, h3, h4] = [
    0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0,
  ];
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i += 1) {
      const j = offset + i * 4;
      words[i] =
        (padded[j] << 24) |
        (padded[j + 1] << 16) |
        (padded[j + 2] << 8) |
        padded[j + 3];
    }
    for (let i = 16; i < 80; i += 1) {
      const value = words[i - 3] ^ words[i - 8] ^ words[i - 14] ^ words[i - 16];
      words[i] = (value << 1) | (value >>> 31);
    }
    let [a, b, c, d, e] = [h0, h1, h2, h3, h4];
    for (let i = 0; i < 80; i += 1) {
      const [f, k] =
        i < 20
          ? [(b & c) | (~b & d), 0x5a827999]
          : i < 40
            ? [b ^ c ^ d, 0x6ed9eba1]
            : i < 60
              ? [(b & c) | (b & d) | (c & d), 0x8f1bbcdc]
              : [b ^ c ^ d, 0xca62c1d6];
      const temp = (((a << 5) | (a >>> 27)) + f + e + k + words[i]) | 0;
      e = d;
      d = c;
      c = (b << 30) | (b >>> 2);
      b = a;
      a = temp;
    }
    h0 = (h0 + a) | 0;
    h1 = (h1 + b) | 0;
    h2 = (h2 + c) | 0;
    h3 = (h3 + d) | 0;
    h4 = (h4 + e) | 0;
  }
  const out = new Uint8Array(20);
  [h0, h1, h2, h3, h4].forEach((h, i) => {
    out[i * 4] = (h >>> 24) & 0xff;
    out[i * 4 + 1] = (h >>> 16) & 0xff;
    out[i * 4 + 2] = (h >>> 8) & 0xff;
    out[i * 4 + 3] = h & 0xff;
  });
  return out;
}

function hmacSha1(key, message) {
  let block = key.length > 64 ? sha1(key) : key;
  const padded = new Uint8Array(64);
  padded.set(block);
  const inner = new Uint8Array(64 + message.length);
  const outer = new Uint8Array(64 + 20);
  for (let i = 0; i < 64; i += 1) {
    inner[i] = padded[i] ^ 0x36;
    outer[i] = padded[i] ^ 0x5c;
  }
  inner.set(message, 64);
  outer.set(sha1(inner), 64);
  return sha1(outer);
}

function totp(secret, offsetSteps = 0) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of secret.replace(/=+$/, '').toUpperCase()) {
    bits += alphabet.indexOf(character).toString(2).padStart(5, '0');
  }
  const key = new Uint8Array(Math.floor(bits.length / 8));
  for (let i = 0; i < key.length; i += 1) {
    key[i] = parseInt(bits.slice(i * 8, i * 8 + 8), 2);
  }
  let counter = Math.floor(Date.now() / 30000) + offsetSteps;
  const message = new Uint8Array(8);
  for (let i = 7; i >= 0; i -= 1) {
    message[i] = counter & 0xff;
    counter = Math.floor(counter / 256);
  }
  const digest = hmacSha1(key, message);
  const offset = digest[19] & 0x0f;
  const value =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3];
  return String(value % 1000000).padStart(6, '0');
}
