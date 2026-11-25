import { expect, test, type APIRequestContext } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Authenticated quality sweep of every dashboard screen against a running local stack
 * (scripts/local/kiko-local.sh start): no uncaught page errors, no failed API calls
 * (>= 500), no horizontal overflow and no serious/critical WCAG 2 A/AA violations.
 * Requires E2E_MAILPIT_URL to read the verification email (verification stays enabled).
 */
const apiUrl = process.env.E2E_API_URL ?? 'http://localhost:8000';
const origin = process.env.E2E_WEB_URL ?? 'http://localhost:3000';
const mailpit = process.env.E2E_MAILPIT_URL;
const password = 'QualitySweep123!';

const ROUTES = [
  '/dashboard',
  '/dashboard/kiko',
  '/dashboard/commands',
  '/dashboard/commands/new',
  '/dashboard/tasks',
  '/dashboard/projects',
  '/dashboard/executions',
  '/dashboard/analytics',
  '/dashboard/agents',
  '/dashboard/automations',
  '/dashboard/knowledge',
  '/dashboard/approvals',
  '/dashboard/notifications',
  '/dashboard/codex',
  '/dashboard/email',
  '/dashboard/calendar',
  '/dashboard/crm',
  '/dashboard/marketing',
  '/dashboard/integrations',
  '/dashboard/settings',
  '/dashboard/subscription',
];

async function verifiedAccount(request: APIRequestContext) {
  const email = `quality-sweep-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;
  const headers = { Origin: origin };
  expect(
    (
      await request.post(`${apiUrl}/api/v1/auth/register`, {
        headers,
        data: {
          email,
          password,
          full_name: 'Quality Sweep',
          terms_accepted: true,
          privacy_accepted: true,
        },
      })
    ).status(),
  ).toBe(202);
  let token = '';
  for (let attempt = 0; attempt < 30 && !token; attempt += 1) {
    const search = await request.get(
      `${mailpit}/api/v1/search?query=${encodeURIComponent(`to:"${email}"`)}`,
    );
    const messages = ((await search.json()) as { messages?: { ID: string }[] })
      .messages;
    if (messages?.length) {
      const message = await request.get(
        `${mailpit}/api/v1/message/${messages[0].ID}`,
      );
      const text = ((await message.json()) as { Text: string }).Text;
      token = /token=([A-Za-z0-9_.~-]+)/.exec(text)?.[1] ?? '';
    }
    if (!token) await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  expect(token, 'verification email').not.toBe('');
  expect(
    (
      await request.post(`${apiUrl}/api/v1/auth/verify-email`, {
        headers,
        data: { token },
      })
    ).status(),
  ).toBe(200);
  return email;
}

test.describe('dashboard quality sweep', () => {
  test.skip(!mailpit, 'needs the local stack (E2E_MAILPIT_URL)');
  test.setTimeout(300_000);

  test('every dashboard screen renders cleanly and accessibly', async ({
    page,
    request,
  }) => {
    const email = await verifiedAccount(request);
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Email', exact: true }).fill(email);
    await page.getByLabel('Palavra-passe', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/onboarding/);
    await page.getByLabel('Nome da empresa').fill('Quality Sweep Lda');
    await page
      .getByLabel('O que faz a tua empresa?')
      .fill('Synthetic workspace for the dashboard quality sweep.');
    await page.getByLabel('Organizar tarefas do negócio').check();
    await page
      .getByRole('button', { name: 'Concluir e criar o meu primeiro comando' })
      .click();
    await expect(page).toHaveURL(/\/dashboard\/commands\/new/);

    const findings: string[] = [];
    for (const route of ROUTES) {
      const errors: string[] = [];
      const onError = (error: Error) =>
        errors.push(`pageerror ${error.message}`);
      const onResponse = (response: { status(): number; url(): string }) => {
        if (response.status() >= 500)
          errors.push(`${response.status()} ${response.url()}`);
      };
      page.on('pageerror', onError);
      page.on('response', onResponse);
      await page.goto(route, { waitUntil: 'load' });
      await expect(page.locator('main').first()).toBeVisible({
        timeout: 20_000,
      });
      // let client-side data loading settle (the dev server keeps a socket open, so
      // "networkidle" never happens)
      await page.waitForTimeout(1500);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth + 1,
      );
      if (overflow) errors.push('horizontal overflow');
      const axe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      for (const violation of axe.violations) {
        if (['critical', 'serious'].includes(violation.impact ?? ''))
          errors.push(
            `axe ${violation.impact} ${violation.id} (${violation.nodes.length}): ${violation.help} -> ${violation.nodes
              .slice(0, 4)
              .map(
                (node) =>
                  `${node.target.join(' ')} [${(node.any[0]?.message ?? '').slice(0, 90)}]`,
              )
              .join(' | ')}`,
          );
      }
      page.off('pageerror', onError);
      page.off('response', onResponse);
      for (const error of errors) findings.push(`${route}: ${error}`);
    }
    console.log(
      findings.length
        ? `QUALITY FINDINGS\n${findings.join('\n')}`
        : 'QUALITY FINDINGS none',
    );
    expect(findings).toEqual([]);
  });
});
