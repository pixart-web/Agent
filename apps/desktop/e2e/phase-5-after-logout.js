phase('after-logout', async () => {
  await step('relaunch after logout requires sign-in', () => atPath('/login'));
  await step('sign-in asks for the second factor', async () => {
    await fill('Email', K.email);
    await fill('Palavra-passe', K.password);
    await click('Entrar');
    await seeText('Confirma que és tu', 20000);
  });
  await step(
    'authenticator code completes sign-in (tokens kept by the shell)',
    async () => {
      // The enrolment used the then-current step; the next step is always accepted.
      await fill('Código', totp(K.mfaSecret, 1));
      await click('Confirmar');
      await atPath('/dashboard', 20000);
    },
  );
  await step('disable two-factor with a recovery code', async () => {
    await go('/dashboard/settings/');
    // Settings has two "Palavra-passe atual" fields; work inside the two-factor panel only.
    const panel = await waitFor(
      () => document.querySelector('.mfa-settings'),
      'two-factor panel',
    );
    const inPanel = (text) =>
      [...panel.querySelectorAll('label')]
        .find((item) => item.textContent.trim().startsWith(text))
        ?.querySelector('input');
    (
      await waitFor(
        () =>
          [...panel.querySelectorAll('button')].find(
            (button) => button.textContent.trim() === 'Desativar',
          ),
        'disable action',
      )
    ).click();
    setValue(
      await waitFor(() => inPanel('Palavra-passe atual'), 'panel password'),
      K.password,
    );
    setValue(
      await waitFor(() => inPanel('Código da app'), 'panel code'),
      K.mfaRecovery,
    );
    (
      await waitFor(
        () =>
          [...panel.querySelectorAll('button[type=submit]')].find(
            (button) => !button.disabled,
          ),
        'disable button',
      )
    ).click();
    await seeText('Verificação em dois passos desativada', 20000);
  });
  await step('log out again', async () => {
    await click('Terminar sessão');
    await atPath('/login');
  });
});
