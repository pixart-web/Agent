# Permissions

| Capability                                       | Owner | Admin | Manager | Member  | Viewer |
| ------------------------------------------------ | :---: | :---: | :-----: | :-----: | :----: |
| Read workspace work                              |  yes  |  yes  |   yes   |   yes   |  yes   |
| Create and update operational work               |  yes  |  yes  |   yes   |   yes   |   no   |
| Coordinate projects and routine approvals        |  yes  |  yes  |   yes   | limited |   no   |
| Invite and manage members                        |  yes  |  yes  |   no    |   no    |   no   |
| Configure workspace/integrations                 |  yes  |  yes  |   no    |   no    |   no   |
| Transfer ownership, retention execution, billing |  yes  |  no   |   no    |   no    |   no   |

Routes enforce membership and role server-side; hiding a button is never the authorization boundary.
Foreign workspace objects return not found where disclosure itself would leak data. High-risk writes
require both role permission and a valid approval fingerprint, and separation of duty prevents the
requester from self-approving. Platform operators do not implicitly become workspace members.
