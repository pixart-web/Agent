phase('register', async () => {
  await step('launch without a session opens sign-in', () => atPath('/login'));
  await step('open registration', async () => {
    await go('/register/');
    await seeText('Create your account');
  });
  await step('submit registration', async () => {
    await fill('Full name', 'Desktop Owner');
    await fill('Email', K.email);
    await fill('Password', K.password);
    await fill('Confirm password', K.password);
    await check('I accept the Terms');
    await check('I accept the Privacy');
    await click('Create account');
    await atPath('/verify-email');
  });
  await step('unverified account cannot sign in', async () => {
    await go('/login/');
    await fill('Email', K.email);
    await fill('Password', K.password);
    await click('Sign in');
    await seeText('verification');
  });
});
