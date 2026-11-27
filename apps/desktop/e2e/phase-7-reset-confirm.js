phase('reset-confirm', async () => {
  await step('set a new password from the emailed link', async () => {
    await go(`/reset-password/?token=${encodeURIComponent(K.token)}`);
    await fill('Nova palavra-passe', K.newPassword);
    await fill('Confirmar palavra-passe', K.newPassword);
    await click('Guardar nova palavra-passe');
    await seeText('Palavra-passe alterada', 20000);
  });
  await step('sign in with the new password', async () => {
    await go('/login/');
    await fill('Email', K.email);
    await fill('Palavra-passe', K.newPassword);
    await click('Entrar');
    await atPath('/dashboard', 20000);
  });
  await step('log out', async () => {
    await click('Terminar sessão');
    await atPath('/login');
  });
});
