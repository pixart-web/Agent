phase('verify-and-onboard', async () => {
  await step('verify email with emailed token', async () => {
    await atPath('/login');
    await go(`/verify-email/?token=${encodeURIComponent(K.token)}`);
    await waitFor(
      () => /verified/i.test(pageText()),
      'verification confirmation',
    );
  });
  await step('sign in', async () => {
    await go('/login/');
    await fill('Email', K.email);
    await fill('Password', K.password);
    await click('Sign in');
    await atPath('/onboarding');
  });
  await step('configure company', async () => {
    await fill('Company name', 'Pixart Desktop QA');
    await fill(
      'What does your company do?',
      'Validates the Kiko macOS client end to end.',
    );
    const box = await waitFor(
      () =>
        document.querySelector('.onboarding-objectives input[type=checkbox]'),
      'objective checkbox',
    );
    box.click();
    await click('Finish and create');
    await atPath('/dashboard/commands/new');
  });
});
