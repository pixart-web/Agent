phase('local-ai', async () => {
  // Real generation with the local model (Ollama on this Mac); can take about a minute.
  await step('submit a command for the local AI Supervisor', async () => {
    await go('/dashboard/commands/new/');
    await fill(
      'Instrução operacional',
      'Prepare an internal plan to follow up the quotes requested this week.',
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
  await step('local model generates a plan shown in the app', async () => {
    await click('Gerar plano com Supervisor');
    await waitFor(
      () => actionByText('Aprovar plano'),
      'generated plan',
      240000,
    );
    if (/AI provider|is not configured|not reachable/i.test(pageText()))
      throw new Error('AI reported unavailable');
  });
  await step('approve the AI-generated plan', async () => {
    await click('Aprovar plano');
    await waitFor(() => !actionByText('Aprovar plano'), 'plan approved', 20000);
  });
});
