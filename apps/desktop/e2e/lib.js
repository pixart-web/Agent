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
  window.next.router.push(path);
  await atPath(path.split('?')[0].replace(/\/$/, ''));
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
