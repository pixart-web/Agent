// Builds the Kiko web UI as a static export for the desktop bundle and copies it to ../dist.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const desktopDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const webDir = resolve(desktopDir, '../web');
const outDir = resolve(webDir, 'out');
const distDir = resolve(desktopDir, 'dist');

rmSync(outDir, { recursive: true, force: true });
execFileSync('pnpm', ['exec', 'next', 'build'], {
  cwd: webDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    NEXT_OUTPUT_MODE: 'export',
    NEXT_PUBLIC_KIKO_PLATFORM: 'desktop',
    NEXT_TELEMETRY_DISABLED: '1',
  },
});
if (!existsSync(resolve(outDir, 'index.html'))) {
  throw new Error('Static export did not produce index.html');
}
rmSync(distDir, { recursive: true, force: true });
cpSync(outDir, distDir, { recursive: true });
console.log(`Desktop UI copied to ${distDir}`);
