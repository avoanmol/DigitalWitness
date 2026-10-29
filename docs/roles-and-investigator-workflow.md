# Roles and investigator workflow

DigitalWitness has four account roles:

- **Reporter:** the person documenting an incident. Public registration creates this role. Reporters write the account, open a case, upload evidence, and prepare a complaint packet for their own review.
- **Investigator:** an authorized case reviewer, such as a cybercrime or law-enforcement officer in a real agency deployment. Investigators review submissions; they do not create reporter cases or decide guilt from AI output.
- **Legal reviewer:** reads authorized case material and reports, with no evidence-submission or AI-decision controls.
- **Administrator:** provisions accounts and manages the demonstration workspace. This role should be limited to trusted staff.

Users should not be able to select investigator, legal, or administrator during public sign-up. Those roles must be granted by a trusted administrator after the organization verifies the person's authority.

## Investigator review sequence

1. Read the reporter's case description and recorded activity timeline.
2. Open each original evidence file. Compare it with the stored SHA-256 fingerprint, upload time, and anchor or verification state.
3. Review extracted text, analysis coverage, technical observations, and potential flags. Check each excerpt against the original file and its surrounding context.
4. Inspect suggested related cases and shared account or contact details. Confirm or reject a connection only after reviewing both reports; save a reason for the decision.
5. Confirm or reject each AI flag with a reason. The AI result remains a review lead, not a finding.
6. Generate the review report. It contains evidence metadata, saved human-review decisions, and the case audit trail. Share it only with authorized recipients.

## Current prototype limitation

The current prototype does not yet store agency membership or case-level investigator assignments. Its investigator, legal, and admin roles can read all cases in the configured database. Use synthetic demo records only until case assignment and organization-level access controls are implemented and reviewed.
