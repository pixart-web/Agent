phase('register', async () => {
  await step('launch without a session opens sign-in', () => atPath('/login'));
  await step('open registration', async () => {
    await go('/register/');
    await seeText('Cria a tua conta');
  });
  await step('submit registration', async () => {
    await fill('Nome completo', 'Desktop Owner');
    await fill('Email', K.email);
    await fill('Palavra-passe', K.password);
    await fill('Confirmar palavra-passe', K.password);
    await check('Aceito os Termos');
    await check('Aceito a Política');
    await click('Criar conta');
    await atPath('/verify-email');
  });
  await step('unverified account cannot sign in', async () => {
    await go('/login/');
    await fill('Email', K.email);
    await fill('Palavra-passe', K.password);
    await click('Entrar');
    await waitFor(
      () => /verification|verifica/i.test(pageText()),
      'verification required message',
    );
  });
});
