# Local demo accounts

The project can create four synthetic accounts for a local walkthrough. They use reserved example.com email addresses and must never be used for real cases or deployed publicly.

From the repository root in PowerShell, run:

```powershell
.\scripts\setup_demo_accounts.ps1
```

This creates or refreshes the accounts in the configured local database without adding sample evidence or starting blockchain transactions. It generates one strong local password shared by the four demo accounts and writes the sign-in details to `.demo-accounts.local.txt`. That file is excluded from Git. Keep it private and delete it when the demo is no longer needed.

| Email | Role | Intended walkthrough |
| --- | --- | --- |
| `demo.reporter@example.com` | Reporter | Create a case, save evidence, review suggestions, prepare a draft |
| `demo.investigator@example.com` | Investigator | Review evidence and AI suggestions, record review decisions |
| `demo.legal@example.com` | Legal | Read case material and reports according to legal-role permissions |
| `demo.admin@example.com` | Admin | Manage user accounts and workspace access |

Public sign-up always creates a reporter. Do not change an investigator, legal, or admin account into a reporter to get access to a case; reporter cases belong to the reporter who created them.

To deliberately rotate the shared demo password, run:

```powershell
.\scripts\setup_demo_accounts.ps1 -RotatePassword
```

The seeding command is opt-in and refuses to run when `APP_ENV` is set to production. If an older local seed created the same four users with `.example.test` emails, setup renames those synthetic rows to the `.example.com` addresses above. It only changes these synthetic demo users’ passwords and role accounts; it does not change real user roles.
