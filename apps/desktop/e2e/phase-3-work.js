phase('governed-work', async () => {
  await step('session restored from Keychain after relaunch', () =>
    atPath('/dashboard'),
  );
  await step('submit a command', async () => {
    await go('/dashboard/commands/new/');
    await fill(
      'Operational instruction',
      'Prepare a follow-up plan for the desktop QA client.',
    );
    const submit = await waitFor(
      () => document.querySelector('form button[type=submit]:not([disabled])'),
      'command submit',
    );
    submit.click();
    await waitFor(
      () =>
        /\/dashboard\/commands\/[^/]+/.test(location.pathname) &&
        !location.pathname.endsWith('/new/'),
      'command detail',
    );
  });
  await step(
    'Supervisor without an AI provider shows an honest unavailable state',
    async () => {
      await click('Gerar plano com Supervisor');
      await waitFor(
        () =>
          /AI provider|Supervisor planning failed|Não foi possível gerar/i.test(
            pageText(),
          ),
        'supervisor error',
        30000,
      );
      if (actionByText('Aprovar plano'))
        throw new Error('a plan appeared without an AI provider');
    },
  );
  await step('create a manual plan', async () => {
    const summary = await waitFor(
      () =>
        [...document.querySelectorAll('summary')].find((item) =>
          /Create a plan manually/.test(item.textContent),
        ),
      'manual plan summary',
    );
    summary.click();
    await fill('Title', 'Desktop QA plan');
    await fill('Objective', 'Follow up with the desktop QA client.');
    await click('Create plan');
    await waitFor(() => actionByText('Add task'), 'task form', 20000);
  });
  await step('add a task to the plan', async () => {
    await fill('Title', 'Call the QA client');
    await fill('Instructions', 'Confirm the desktop rollout window.');
    await click('Add task');
    await seeText('Call the QA client', 20000);
  });
  let commandPath = '';
  await step('approve the plan (human plan approval)', async () => {
    commandPath = location.pathname;
    await click('Aprovar plano');
    await waitFor(() => !actionByText('Aprovar plano'), 'plan approved', 20000);
  });
  await step('mark the task ready', async () => {
    if (
      await waitFor(
        () => document.querySelector('.action-composer'),
        'composer',
        3000,
      ).catch(() => null)
    )
      return;
    const select = await waitFor(
      () =>
        [...document.querySelectorAll('select')].find((item) =>
          [...item.options].some((option) => option.value === 'ready'),
        ),
      'status select',
    );
    setValue(select, 'ready');
    await click('Change status');
    await waitFor(
      () => document.querySelector('.action-composer'),
      'action composer',
      20000,
    );
  });
  await step('dispatch a governed action that requires approval', async () => {
    const composer = document.querySelector('.action-composer');
    setValue(
      composer.querySelector('select'),
      'internal.simulate_external_action',
    );
    setValue(
      composer.querySelector('input'),
      'Notify the QA client about the rollout window',
    );
    [...composer.querySelectorAll('button')]
      .find((b) => /Create & dispatch/.test(b.textContent))
      .click();
    await waitFor(
      () =>
        /waiting[_ ]approval/i.test(
          document.querySelector('.action-row')?.textContent ?? '',
        ),
      'action waiting for approval',
      20000,
    );
  });
  await step('approve it in the Approvals centre', async () => {
    await go('/dashboard/approvals/');
    await fill('Decision note', 'Approved from the macOS app.');
    await click('Aprovar');
    await waitFor(() => !actionByText('Aprovar'), 'approval recorded', 20000);
  });
  await step('approved action executed by the backend worker', async () => {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await go('/dashboard/executions/');
      await go(commandPath);
      await sleep(1500);
      const row = document.querySelector('.action-row')?.textContent ?? '';
      if (/completed/i.test(row)) return;
      if (/failed/i.test(row)) throw new Error(`action failed: ${row}`);
    }
    throw new Error('action did not complete');
  });
  await step('task persisted and opens from the task list', async () => {
    await go('/dashboard/tasks/');
    const link = await waitFor(
      () =>
        [...document.querySelectorAll('a')].find((item) =>
          item.textContent.includes('Call the QA client'),
        ),
      'task link',
      30000,
    );
    link.click();
    await waitFor(
      () => /\/dashboard\/tasks\/[^/]+/.test(location.pathname),
      'task detail',
    );
    await waitFor(
      () => !/Loading/.test(pageText().slice(0, 40)),
      'task loaded',
    );
  });
  await step('create a project', async () => {
    await go('/dashboard/projects/');
    await fill('Name', 'Desktop launch');
    await fill('Description', 'Created from the macOS app.');
    await click('Create project');
    await seeText('Desktop launch', 20000);
  });
  await step('Kiko AI conversation', async () => {
    await go('/dashboard/kiko/');
    const box = await waitFor(
      () => document.getElementById('kiko-message'),
      'kiko composer',
    );
    setValue(box, 'Summarise what is pending for the desktop launch.');
    const send = await waitFor(
      () =>
        document.querySelector(
          '.kiko-composer button[type=submit]:not([disabled])',
        ),
      'kiko send',
    );
    send.click();
    await waitFor(
      () =>
        /\/dashboard\/kiko\/[^/]+/.test(location.pathname) ||
        /AI provider|Não foi possível/i.test(pageText()),
      'conversation outcome',
      30000,
    );
    await report(
      /\/dashboard\/kiko\/[^/]+/.test(location.pathname)
        ? 'INFO Kiko AI: conversation created'
        : 'INFO Kiko AI: server reported AI unavailable (no provider configured)',
    );
  });
  await step('create a CRM contact', async () => {
    await go('/dashboard/crm/');
    const type = await waitFor(
      () => labelControl('Record type'),
      'record type',
    );
    const contactOption = [...type.options].find((option) =>
      /contact/i.test(option.textContent),
    );
    if (contactOption) setValue(type, contactOption.value);
    await fill('Full name', 'Ana Desktop');
    await fill('Email', 'ana.desktop@example.com');
    const save = await waitFor(
      () =>
        [...document.querySelectorAll('button.primary-button')].find(
          (b) => /create|save|add/i.test(b.textContent) && !b.disabled,
        ),
      'crm save',
    );
    save.click();
    await seeText('Ana Desktop', 20000);
  });
});
