# Sales Agent

Sales prompt version v2 can use email.search, email.get_message, email.get_thread,
email.send, and email.reply. It has no bulk, newsletter, scraping, mailbox-rule, or mass
prospecting capability.

Reads are green. Every send or reply is yellow and requires a human to review the mailbox
account, complete recipients, external-recipient warning, subject, body, and fingerprint.
Recipient count is bounded and sending is disabled globally by default. Sales must respect
consent and anti-spam rules, must not infer delivery after a timeout, and never receives
Google credentials or direct provider access.
