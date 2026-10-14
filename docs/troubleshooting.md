# Troubleshooting

| Symptom                               | Check                                                   | Safe action                                                |
| ------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------- |
| Cannot sign in                        | Verification status, clock, account status              | Use recovery; do not reveal whether another address exists |
| Page says API unavailable             | `/health`, `/ready`, browser network, same-origin proxy | Restore dependency/proxy health; never bypass auth         |
| Planning unavailable                  | Agent Center and AI provider state                      | Configure approved provider or keep the feature disabled   |
| Integration is “configured” but fails | Health/reconciliation, OAuth scopes, allowlists         | Reconnect the test account; do not broaden scopes blindly  |
| Task is blocked                       | Dependencies, approval, assignee, entitlement           | Resolve the stated prerequisite and retry idempotently     |
| Automation did not run                | Enabled state, trigger, run history, entitlement        | Correct the trigger; do not edit historical run records    |
| Export is rejected                    | Role, resource, size bound                              | Narrow the resource or use an Owner account                |

Record the timestamp, workspace, request ID, route, status code, and user-visible message. Never copy
tokens, cookies, passwords, document contents, or provider payloads into support tickets. Operators
should use structured logs by request ID and preserve audit history. For suspected cross-workspace
access, disable the affected retrieval path immediately and start the incident procedure.
