phase('persistence-and-logout', async () => {
  await step('relaunch restores session and last screen', () =>
    atPath('/dashboard/crm'),
  );
  await step('CRM contact persisted', () => seeText('Ana Desktop', 20000));
  await step('project persisted', async () => {
    await go('/dashboard/projects/');
    await seeText('Desktop launch', 20000);
  });
  await step('log out', async () => {
    await click('Log out');
    await atPath('/login');
  });
});
