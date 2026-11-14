# First-run onboarding

Newly registered users are redirected to `/onboarding` before entering authenticated
dashboard routes. The flow persists against the user's active workspace:

- company name and description;
- up to six normalized primary objectives;
- current onboarding step;
- immutable first completion timestamp.

Completion requires a company description and at least one objective. Optional
integrations are presented as a separate real configuration route and are never
reported as connected by the onboarding flow. The primary completion action opens
the real command composer, so the user's first success continues through Supervisor
and the governed Execution Engine.

Workspace owners and administrators may edit company fields. Other members can keep
their personal onboarding progress but cannot change shared company configuration.
Existing users are marked complete by migration `20261010_0025` to avoid disrupting
established accounts; users created after the migration start at step zero.
