phase('verify-and-onboard', async () => {
  await step('verify email with emailed token', async () => {
    await atPath('/login');
    await go(`/verify-email/?token=${encodeURIComponent(K.token)}`);
    await waitFor(
      () => /verified|verificado/i.test(pageText()),
      'verification confirmation',
    );
  });
  await step('sign in', async () => {
    await go('/login/');
    await fill('Email', K.email);
    await fill('Palavra-passe', K.password);
    await click('Entrar');
    await atPath('/onboarding');
  });
  await step('configure company', async () => {
    await fill('Nome da empresa', 'Pixart Desktop QA');
    await fill(
      'O que faz a tua empresa?',
      'Validates the Kiko macOS client end to end.',
    );
    const box = await waitFor(
      () =>
        document.querySelector('.onboarding-objectives input[type=checkbox]'),
      'objective checkbox',
    );
    box.click();
    await click('Concluir e criar');
    await atPath('/dashboard/commands/new');
  });
});
