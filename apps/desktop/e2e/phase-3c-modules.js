phase('modules', async () => {
  await step('session restored for the module checks', () =>
    atPath('/dashboard'),
  );
  await step('create a marketing campaign', async () => {
    await go('/dashboard/marketing/');
    await fill('Nome da campanha', 'Campanha desktop');
    await fill('Objetivo', 'Apresentar a app macOS aos clientes.');
    await click('Criar campanha');
    await seeText('Campanha desktop', 20000);
  });
  await step('create a manual automation', async () => {
    await go('/dashboard/automations/');
    await fill('Nome', 'Resumo diário desktop');
    await fill('Comando fixo', 'Resume o trabalho pendente de hoje.');
    await click('Criar automatização');
    await seeText('Resumo diário desktop', 20000);
  });
  await step('save a knowledge draft', async () => {
    await go('/dashboard/knowledge/');
    await fill('Título', 'Política de devoluções desktop');
    await fill('Conteúdo', 'Os clientes podem devolver produtos em 30 dias.');
    await click('Guardar rascunho');
    await seeText('Política de devoluções desktop', 20000);
  });
  await step('enable two-factor authentication', async () => {
    await go('/dashboard/settings/');
    await click('Ativar verificação em dois passos');
    const secret = (
      await waitFor(
        () => document.querySelector('.mfa-secret')?.textContent,
        'two-factor secret',
      )
    ).trim();
    await fill('Código de 6 dígitos', totp(secret));
    (
      await waitFor(
        () =>
          [...document.querySelectorAll('.mfa-setup button[type=submit]')].find(
            (button) => !button.disabled,
          ),
        'enable button',
      )
    ).click();
    const codes = await waitFor(() => {
      const items = [...document.querySelectorAll('.mfa-recovery__codes code')];
      return items.length === 10 ? items.map((item) => item.textContent) : null;
    }, 'recovery codes');
    // Local temporary test account only: the runner passes these to the sign-in phase.
    await report(`DATA mfa ${secret} ${codes[0]}`);
    await click('Já guardei os códigos');
    await seeText('Ativa desde', 20000);
  });
});
