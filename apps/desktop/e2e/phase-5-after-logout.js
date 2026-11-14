phase('after-logout', async () => {
  await step('relaunch after logout requires sign-in', () => atPath('/login'));
});
