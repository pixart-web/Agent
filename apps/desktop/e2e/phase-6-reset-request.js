phase('reset-request', async () => {
  await step('request a password reset', async () => {
    await go('/forgot-password/');
    await fill('Email', K.email);
    await click('Pedir reposição');
    await waitFor(
      () => document.querySelector('[role=status]')?.textContent,
      'reset confirmation',
    );
  });
});
