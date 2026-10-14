import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const apiUrl = process.env.E2E_API_URL ?? 'http://127.0.0.1:58001';
const origin = process.env.E2E_WEB_URL ?? 'http://127.0.0.1:53001';
const password = 'ReleaseJourney123!';

async function registerApi(request: APIRequestContext, label: string) {
  const email = `${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  const registration = await request.post(`${apiUrl}/api/v1/auth/register`, {
    headers: { Origin: origin },
    data: {
      email,
      password,
      full_name: `${label} operator`,
      terms_accepted: true,
      privacy_accepted: true,
    },
  });
  expect(registration.status()).toBe(202);
  const login = await request.post(`${apiUrl}/api/v1/auth/login`, {
    headers: { Origin: origin },
    data: { email, password },
  });
  expect(login.status()).toBe(200);
  const body = (await login.json()) as { access_token: string };
  return {
    email,
    headers: { Authorization: `Bearer ${body.access_token}`, Origin: origin },
  };
}

async function assertNoRuntimeErrors(page: Page, errors: string[]) {
  expect(errors, `browser errors: ${errors.join('\n')}`).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}

test('Journey A: registration, login and onboarding persist in the real API', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('response', (response) => {
    if (
      response.status() >= 400 &&
      !(response.status() === 401 && response.url().endsWith('/api/v1/auth/me'))
    )
      errors.push(`${response.status()} ${response.url()}`);
  });
  const email = `journey-a-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByLabel('Full name').fill('Release Owner');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByLabel('I accept the Terms of Service.').check();
  await page.getByLabel('I accept the Privacy Policy.').check();
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/verify-email/);
  await page.getByRole('link', { name: 'Return to sign in' }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByRole('textbox', { name: 'Email', exact: true }).fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByLabel('Company name').fill('Northstar Release Lab');
  await page
    .getByLabel('What does your company do?')
    .fill('A synthetic QA workspace.');
  await page.getByLabel('Organize business tasks').check();
  await page
    .getByRole('button', { name: 'Finish and create my first command' })
    .click();
  await expect(page).toHaveURL(/\/dashboard\/commands\/new/);
  await expect(
    page.getByRole('heading', { name: /O que queres/ }),
  ).toBeVisible();
  await assertNoRuntimeErrors(page, errors);
});

test('Journeys B/H: membership and CRM object boundaries reject another tenant', async ({
  request,
}) => {
  const owner = await registerApi(request, 'tenant-owner');
  const outsider = await registerApi(request, 'tenant-outsider');
  const ownerSettings = await request.get(
    `${apiUrl}/api/v1/workspaces/settings`,
    {
      headers: owner.headers,
    },
  );
  const ownerWorkspace = (await ownerSettings.json()) as { id: string };
  const invitation = await request.post(
    `${apiUrl}/api/v1/workspaces/${ownerWorkspace.id}/invitations`,
    { headers: owner.headers, data: { email: outsider.email, role: 'member' } },
  );
  expect(invitation.status()).toBe(201);
  const forbiddenInvitations = await request.get(
    `${apiUrl}/api/v1/workspaces/${ownerWorkspace.id}/invitations`,
    { headers: outsider.headers },
  );
  expect([403, 404]).toContain(forbiddenInvitations.status());
  const organization = await request.post(
    `${apiUrl}/api/v1/crm/organizations`,
    {
      headers: owner.headers,
      data: { name: 'Tenant A private customer' },
    },
  );
  expect(organization.status()).toBe(201);
  const organizationId = ((await organization.json()) as { id: string }).id;
  const hidden = await request.get(
    `${apiUrl}/api/v1/crm/organizations/${organizationId}`,
    {
      headers: outsider.headers,
    },
  );
  expect(hidden.status()).toBe(404);
});

test('responsive public shell has no horizontal overflow', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ['critical', 'serious'].includes(violation.impact ?? ''),
    ),
  ).toEqual([]);
  await assertNoRuntimeErrors(page, errors);
});
