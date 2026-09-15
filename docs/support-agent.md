# Support Agent

Support prompt version v2 can use email.list_messages, email.get_message,
email.get_thread, email.search, email.reply, and email.mark_read. It treats all mailbox
content as untrusted and cannot access OAuth credentials or provider clients.

Reads are green and on demand. Reply and mark-read proposals are yellow and stop for human
approval. A reply derives its recipient, thread, and safe reply headers from the original
provider message; the model cannot supply arbitrary transport headers. The complete prepared
body is visible in the approval. Support never downloads attachments, follows instructions
embedded in mail, or sends automatically.
