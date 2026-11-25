/**
 * European Portuguese for the error messages the Kiko API returns. The API keeps its
 * messages in English (logs, tests and integrations rely on them); every screen shows them
 * through `apiMessage()`. Unknown messages are shown as they are.
 */
const MESSAGES: Record<string, string> = {
  // Sign-in, account and session
  'Authentication required': 'É preciso entrar novamente.',
  'Authentication temporarily unavailable':
    'A autenticação está temporariamente indisponível. Tenta de novo daqui a pouco.',
  'Current password is incorrect': 'A palavra-passe atual está incorreta.',
  'Email verification required':
    'Confirma primeiro o teu email: segue o link de verificação que te enviámos.',
  'Inactive user': 'Esta conta está desativada.',
  'Insufficient permissions': 'Não tens permissões para esta ação.',
  'Invalid email or password': 'Email ou palavra-passe incorretos.',
  'Invalid or expired password reset token':
    'O link para repor a palavra-passe é inválido ou expirou.',
  'Invalid or expired verification token':
    'O link de verificação é inválido ou expirou.',
  'Origin not allowed': 'Este endereço não está autorizado a usar o Kiko.',
  'Session not found': 'A sessão terminou. Entra de novo.',
  'Too many authentication attempts':
    'Demasiadas tentativas. Espera um minuto e tenta de novo.',
  Unauthorized: 'Não autorizado.',
  'New password must be different':
    'A nova palavra-passe tem de ser diferente da atual.',
  'Password must contain at least one letter':
    'A palavra-passe tem de ter pelo menos uma letra.',
  'Password must contain at least one number':
    'A palavra-passe tem de ter pelo menos um número.',
  'Password must contain at least one letter and one number':
    'A palavra-passe tem de ter pelo menos uma letra e um número.',
  'Full name must contain at least two characters':
    'O nome tem de ter pelo menos dois caracteres.',
  'Terms and Privacy Policy acceptance is required':
    'É preciso aceitar os Termos e a Política de Privacidade.',
  'User not found': 'Utilizador não encontrado.',
  'A platform administrator cannot deactivate their own account':
    'Um administrador da plataforma não pode desativar a própria conta.',

  // Workspaces, members and permissions
  'An active workspace is required': 'É preciso escolher um workspace ativo.',
  'No active workspace': 'Não há nenhum workspace ativo.',
  'Select an active workspace first': 'Escolhe primeiro um workspace ativo.',
  'Insufficient workspace permission':
    'Não tens permissões suficientes neste workspace.',
  'Workspace edit permission is required':
    'Precisas de permissão de edição neste workspace.',
  'Workspace administrator permission is required':
    'Precisas de ser administrador deste workspace.',
  'Workspace owner or admin permission is required':
    'Precisas de ser dono ou administrador deste workspace.',
  'Workspace owner permission is required':
    'Só o dono do workspace pode fazer isto.',
  'Owner authority is required': 'Só o dono pode fazer isto.',
  'Ownership target must be another member':
    'A posse tem de ser transferida para outro membro.',
  'Workspace not found': 'Workspace não encontrado.',
  'Workspace slug is already in use':
    'Este identificador de workspace já está a ser usado.',
  'Workspace member already exists': 'Esta pessoa já é membro do workspace.',
  'Workspace member not found': 'Membro do workspace não encontrado.',
  'User is already a workspace member': 'Esta pessoa já é membro do workspace.',
  'A pending invitation already exists':
    'Já existe um convite pendente para este email.',
  'Invalid or expired invitation': 'O convite é inválido ou expirou.',
  'Invitation is no longer pending': 'Este convite já não está pendente.',
  'Company description and at least one objective are required':
    'Indica a descrição da empresa e pelo menos um objetivo.',
  'Objectives must contain between 1 and 120 characters':
    'Cada objetivo tem de ter entre 1 e 120 caracteres.',

  // Generic
  'Not found': 'Não encontrado.',
  'Resource not found': 'Recurso não encontrado.',
  'At least one field must be provided': 'Altera pelo menos um campo.',
  'At least one field must be updated': 'Altera pelo menos um campo.',
  'Value cannot be blank': 'O valor não pode ficar vazio.',
  'Message cannot be blank': 'A mensagem não pode ficar vazia.',
  'Comment cannot be blank': 'O comentário não pode ficar vazio.',
  'Feedback cannot be empty': 'O feedback não pode ficar vazio.',
  'Feedback exceeds the configured limit':
    'O feedback é maior do que o limite permitido.',
  'Unknown IANA time zone': 'Fuso horário desconhecido.',
  'Unknown entitlement': 'Funcionalidade do plano desconhecida.',
  'account_id must be a UUID': 'A conta indicada não é válida.',
  'Phone numbers must contain between 7 and 20 digits':
    'O número de telefone tem de ter entre 7 e 20 dígitos.',

  // Commands, plans and tasks
  'Command not found': 'Comando não encontrado.',
  'Command input cannot be blank': 'Escreve o pedido antes de enviar.',
  'Command exceeds the configured AI input limit':
    'O pedido é demasiado longo para a IA local. Encurta-o e tenta de novo.',
  'Command already has a current plan': 'Este comando já tem um plano.',
  'Command already has a plan': 'Este comando já tem um plano.',
  'Command can no longer receive a plan':
    'Este comando já não pode receber um plano.',
  'Command cannot be cancelled from its current state':
    'Este comando já não pode ser cancelado.',
  'Command is not waiting for plan approval':
    'Este comando não está à espera de aprovação do plano.',
  'Command or plan is terminal': 'O comando ou o plano já terminou.',
  'Command was cancelled during planning':
    'O comando foi cancelado durante o planeamento.',
  'A terminal command cannot be planned':
    'Um comando terminado não pode ser planeado.',
  'A terminal command cannot receive a plan':
    'Um comando terminado não pode receber um plano.',
  'A terminal command cannot receive new tasks':
    'Um comando terminado não pode receber novas tarefas.',
  'Only terminal commands can be archived':
    'Só os comandos terminados podem ser arquivados.',
  'Plan not found': 'Plano não encontrado.',
  'A plan was created concurrently':
    'Foi criado outro plano ao mesmo tempo. Atualiza a página.',
  'A plan without tasks cannot be approved':
    'Um plano sem tarefas não pode ser aprovado.',
  'Only a current draft plan can be regenerated':
    'Só o rascunho atual do plano pode ser gerado de novo.',
  'Only the current draft plan can be approved':
    'Só o rascunho atual do plano pode ser aprovado.',
  'Only the current draft plan can be rejected':
    'Só o rascunho atual do plano pode ser rejeitado.',
  'Tasks can only be added to the current draft plan':
    'Só podes adicionar tarefas ao rascunho atual do plano.',
  'Plan contains a task that is not pending':
    'O plano tem uma tarefa que já não está pendente.',
  'Supervisor planning is already in progress':
    'O Supervisor já está a preparar um plano.',
  'Supervisor referenced an unavailable agent':
    'O Supervisor indicou um agente que não está disponível.',
  'Supervisor returned too many tasks':
    'O Supervisor propôs tarefas a mais. Tenta de novo com um pedido mais concreto.',
  'Supervisor run not found': 'Execução do Supervisor não encontrada.',
  'Background planning is unavailable. Try again in a moment.':
    'O planeamento em segundo plano não está disponível. Tenta de novo daqui a pouco.',
  'Task not found': 'Tarefa não encontrada.',
  'Task was not found': 'Tarefa não encontrada.',
  'A task cannot depend on itself': 'Uma tarefa não pode depender de si mesma.',
  'Dependencies must belong to the same plan':
    'As dependências têm de pertencer ao mesmo plano.',
  'Task dependencies are not completed':
    'As tarefas de que esta depende ainda não estão concluídas.',
  'Task dependency already exists': 'Esta dependência já existe.',
  'Task dependency not found': 'Dependência não encontrada.',
  'Task dependency would create a cycle':
    'Esta dependência criaria um ciclo entre tarefas.',
  'Task has already started': 'A tarefa já começou.',
  'Task is already linked to a client': 'A tarefa já está ligada a um cliente.',
  'Task is not ready for execution':
    'A tarefa ainda não está pronta para executar.',
  'Task sequences must be unique': 'A ordem das tarefas tem de ser única.',
  'Task was cancelled or changed during agent analysis':
    'A tarefa foi cancelada ou alterada enquanto o agente a analisava.',
  'Only a ready task can run its assigned agent':
    'Só uma tarefa pronta pode correr o agente atribuído.',
  'Only ready or blocked tasks can be scheduled':
    'Só tarefas prontas ou bloqueadas podem ser agendadas.',
  'Actions require a ready task': 'As ações precisam de uma tarefa pronta.',
  'Reset existing actions before reassignment':
    'Repõe as ações existentes antes de mudar o agente.',
  'Use rerun-agent to preserve the previous run history':
    'Usa "Correr agente de novo" para manter o histórico da execução anterior.',
  'Use the explicit reassign-agent endpoint':
    'Usa a opção "Mudar agente" para trocar o agente.',
  'Conversation not found': 'Conversa não encontrada.',

  // Agents and local AI
  'Agent not found': 'Agente não encontrado.',
  'Agent is not allowed to use this tool':
    'Este agente não pode usar esta ferramenta.',
  'Agent monthly token budget is exhausted':
    'O agente esgotou o orçamento mensal de tokens.',
  'Agent proposed a tool outside its allowlist':
    'O agente propôs uma ferramenta que não lhe está permitida.',
  'Agent proposed too many actions': 'O agente propôs ações a mais.',
  'Agent rerun requires failure, reset actions, or feedback':
    'Para correr o agente de novo, a tarefa tem de ter falhado, as ações têm de ser repostas ou tens de dar feedback.',
  'Agent run is no longer active': 'A execução do agente já não está ativa.',
  'An agent run is active': 'Há uma execução do agente em curso.',
  'An agent run is already active for this task':
    'Já há um agente a trabalhar nesta tarefa.',
  'Assigned agent is disabled for this workspace':
    'O agente atribuído está desativado neste workspace.',
  'Assigned agent is unavailable': 'O agente atribuído não está disponível.',
  'Configured agent model is unavailable':
    'O modelo configurado para o agente não está disponível.',
  'No active agents are available': 'Não há agentes ativos disponíveis.',
  'Specialized agent proposal failed validation':
    'A proposta do agente especializado não passou na validação.',
  'Configuration contains unsupported tools':
    'A configuração inclui ferramentas não suportadas.',
  'Background agent runs are unavailable. Try again in a moment.':
    'As execuções de agentes em segundo plano não estão disponíveis. Tenta de novo daqui a pouco.',
  'Local AI model returned an invalid structured answer':
    'O modelo de IA local devolveu uma resposta inválida. Tenta de novo.',
  'Local AI model returned no content':
    'O modelo de IA local não devolveu resposta. Tenta de novo.',
  'Local AI model timed out': 'O modelo de IA local demorou demasiado.',
  'Local AI runtime is not reachable': 'A IA local não está a responder.',
  'Local AI runtime is unavailable': 'A IA local não está disponível.',
  'Local AI runtime rejected the request': 'A IA local recusou o pedido.',
  'Local AI runtime returned an invalid reply':
    'A IA local devolveu uma resposta inválida.',
  'The local AI did not finish within the time limit':
    'A IA local não terminou dentro do tempo limite.',

  // Approvals, actions and executions
  'Approval not found': 'Aprovação não encontrada.',
  'Approval has already been decided': 'Esta aprovação já foi decidida.',
  'Approval has expired': 'Esta aprovação expirou.',
  'High-risk approval requires a different workspace member':
    'Uma ação de risco elevado tem de ser aprovada por outro membro do workspace.',
  'Explicit high-risk confirmation is required':
    'Confirma explicitamente que aceitas o risco elevado.',
  'Action not found': 'Ação não encontrada.',
  'Action cannot be dispatched from its current state':
    'A ação não pode ser executada no estado atual.',
  'Action changed after approval was requested; request a new approval':
    'A ação mudou depois do pedido de aprovação. Pede uma nova aprovação.',
  'Action sequences must be unique': 'A ordem das ações tem de ser única.',
  'Running or terminal action cannot be cancelled':
    'Uma ação em curso ou terminada não pode ser cancelada.',
  'Public action creation must be attributed to the user':
    'Uma ação pública tem de ficar associada a um utilizador.',
  'Execution not found': 'Execução não encontrada.',
  'Tool execution exceeded its timeout':
    'A ferramenta demorou mais do que o tempo limite.',
  'Tool input does not match its schema':
    'Os dados enviados à ferramenta não são válidos.',
  'Approved CRM payload does not match execution payload':
    'Os dados aprovados no CRM não coincidem com os da execução.',
  'Approved marketing payload does not match execution payload':
    'Os dados aprovados de marketing não coincidem com os da execução.',
  'CRM payload does not match the approved execution action':
    'Os dados do CRM não coincidem com a ação aprovada.',
  'Calendar payload does not match the approved execution action':
    'Os dados do calendário não coincidem com a ação aprovada.',
  'Email payload does not match the approved execution action':
    'Os dados do email não coincidem com a ação aprovada.',
  'Calendar action payload changed after approval':
    'A ação de calendário mudou depois da aprovação.',
  'Email action payload changed after approval':
    'O email mudou depois da aprovação.',

  // Projects and clients
  'Project not found': 'Projeto não encontrado.',
  'Project was not found': 'Projeto não encontrado.',
  'Project name cannot be blank': 'O nome do projeto não pode ficar vazio.',
  'Project due date cannot precede its start date':
    'A data de entrega não pode ser anterior à data de início.',
  'due_on cannot be before starts_on':
    'A data de entrega não pode ser anterior à data de início.',
  'Project does not belong to the client':
    'O projeto não pertence a este cliente.',
  'Project member not found': 'Membro do projeto não encontrado.',
  'The project owner cannot be removed':
    'O responsável do projeto não pode ser removido.',
  'User is already a project member': 'Esta pessoa já é membro do projeto.',
  'Milestone not found': 'Marco não encontrado.',
  'At least one project field must be updated':
    'Altera pelo menos um campo do projeto.',
  'Client not found': 'Cliente não encontrado.',
  'Client was not found': 'Cliente não encontrado.',
  'Client id does not match path': 'O cliente indicado não coincide.',
  'At least one client field must be updated':
    'Altera pelo menos um campo do cliente.',
  'Contact does not belong to the client':
    'O contacto não pertence a este cliente.',
  'Organization is already a client': 'Esta organização já é cliente.',

  // CRM
  'A contact or organization is required':
    'Indica um contacto ou uma organização.',
  'Exactly one contact or organization is required':
    'Indica um contacto ou uma organização (só um).',
  'Contact was not found': 'Contacto não encontrado.',
  'Contact id does not match path': 'O contacto indicado não coincide.',
  'Contact methods must be unique': 'Os contactos não podem estar repetidos.',
  'At least one contact field must be updated':
    'Altera pelo menos um campo do contacto.',
  'Organization was not found': 'Organização não encontrada.',
  'Organization id does not match path': 'A organização indicada não coincide.',
  'At least one organization field must be updated':
    'Altera pelo menos um campo da organização.',
  'Opportunity was not found': 'Oportunidade não encontrada.',
  'Opportunity id does not match path': 'A oportunidade indicada não coincide.',
  'At least one opportunity field must be updated':
    'Altera pelo menos um campo da oportunidade.',
  'Pipeline name is already in use': 'Já existe um pipeline com este nome.',
  'Pipeline stage names must be unique':
    'As fases do pipeline têm de ter nomes diferentes.',
  'Pipeline stage positions must be unique':
    'As fases do pipeline têm de ter posições diferentes.',
  'Pipeline stage was not found': 'Fase do pipeline não encontrada.',
  'CRM import exceeds 1 MB': 'O ficheiro de importação excede 1 MB.',
  'CRM import exceeds 1,000 rows':
    'O ficheiro de importação excede 1000 linhas.',
  'Import contains invalid or duplicate rows':
    'A importação tem linhas inválidas ou repetidas.',
  'Import file changed after preview':
    'O ficheiro mudou depois da pré-visualização. Carrega-o de novo.',
  'Invalid UTF-8 CSV file': 'O ficheiro CSV tem de estar em UTF-8.',
  'Only CSV imports are supported': 'Só é possível importar ficheiros CSV.',
  'CSV export requires a single resource':
    'A exportação CSV tem de ser de um único tipo de registo.',
  'Cannot set and clear description together':
    'Não podes definir e limpar a descrição ao mesmo tempo.',
  'Cannot set and clear due date together':
    'Não podes definir e limpar a data de entrega ao mesmo tempo.',
  'Cannot set and clear expected close date together':
    'Não podes definir e limpar a data prevista de fecho ao mesmo tempo.',
  'Cannot set and clear industry together':
    'Não podes definir e limpar o setor ao mesmo tempo.',
  'Cannot set and clear job title together':
    'Não podes definir e limpar o cargo ao mesmo tempo.',
  'Cannot set and clear organization together':
    'Não podes definir e limpar a organização ao mesmo tempo.',
  'Cannot set and clear start date together':
    'Não podes definir e limpar a data de início ao mesmo tempo.',
  'Cannot set and clear summary together':
    'Não podes definir e limpar o resumo ao mesmo tempo.',
  'Cannot set and clear website together':
    'Não podes definir e limpar o website ao mesmo tempo.',
  'Cannot set and clear campaign start together':
    'Não podes definir e limpar o início da campanha ao mesmo tempo.',
  'Cannot set and clear campaign end together':
    'Não podes definir e limpar o fim da campanha ao mesmo tempo.',

  // Marketing
  'Campaign was not found': 'Campanha não encontrada.',
  'Campaign id does not match path': 'A campanha indicada não coincide.',
  'Campaign end must be after its start':
    'O fim da campanha tem de ser depois do início.',
  'At least one campaign field must be updated':
    'Altera pelo menos um campo da campanha.',
  'Content was not found': 'Conteúdo não encontrado.',
  'Content id does not match path': 'O conteúdo indicado não coincide.',
  'At least one content field must be updated':
    'Altera pelo menos um campo do conteúdo.',
  'Content must return to draft before editing':
    'O conteúdo tem de voltar a rascunho antes de ser editado.',
  'Content calendar range cannot exceed 366 days':
    'O calendário de conteúdos não pode abranger mais de 366 dias.',
  'Scheduled content must be in the future':
    'O conteúdo agendado tem de ficar para o futuro.',
  'Only approved or scheduled content can be recorded as published':
    'Só conteúdo aprovado ou agendado pode ser registado como publicado.',
  'Publication channel does not match the content channel':
    'O canal da publicação não coincide com o do conteúdo.',
  'Publication confirmation cannot be in the future':
    'A confirmação da publicação não pode ter data futura.',
  'Publication reference is already recorded':
    'Esta referência de publicação já está registada.',
  'A metric must target a campaign or content item':
    'A métrica tem de estar ligada a uma campanha ou a um conteúdo.',
  'Metric campaign does not match its content':
    'A campanha da métrica não coincide com a do conteúdo.',
  'An asset must target a campaign or content item':
    'O recurso tem de estar ligado a uma campanha ou a um conteúdo.',
  'Asset campaign does not match its content':
    'A campanha do recurso não coincide com a do conteúdo.',

  // Knowledge and documents
  'Knowledge source not found': 'Fonte de conhecimento não encontrada.',
  'Only draft knowledge can be approved':
    'Só o conhecimento em rascunho pode ser aprovado.',
  'Only draft knowledge can be edited':
    'Só o conhecimento em rascunho pode ser editado.',
  'This document is already ingested': 'Este documento já foi importado.',
  'Document contains no extractable text':
    'O documento não tem texto que se possa extrair.',
  'Document exceeds 5 MB': 'O documento excede 5 MB.',
  'Document is empty': 'O documento está vazio.',
  'Only TXT, Markdown, PDF, and DOCX documents are supported':
    'Só são suportados documentos TXT, Markdown, PDF e DOCX.',
  'Text documents must use UTF-8':
    'Os documentos de texto têm de estar em UTF-8.',
  'Encrypted DOCX documents are not supported':
    'Documentos DOCX protegidos não são suportados.',
  'Encrypted PDF documents are not supported':
    'Documentos PDF protegidos não são suportados.',
  'DOCX contains too many embedded files':
    'O DOCX tem demasiados ficheiros incorporados.',
  'DOCX could not be parsed safely':
    'Não foi possível ler o DOCX com segurança.',
  'DOCX expanded content exceeds 20 MB':
    'O conteúdo do DOCX excede 20 MB depois de descomprimido.',
  'PDF could not be parsed safely': 'Não foi possível ler o PDF com segurança.',
  'PDF exceeds 200 pages': 'O PDF excede 200 páginas.',
  'Extracted text exceeds 100,000 characters':
    'O texto extraído excede 100 000 caracteres.',

  // Automations
  'Automation was not found': 'Automatização não encontrada.',
  'Automation run was not found': 'Execução da automatização não encontrada.',
  'An automation with this name already exists':
    'Já existe uma automatização com este nome.',
  'At least one automation field must be updated':
    'Altera pelo menos um campo da automatização.',
  'Automation is paused': 'A automatização está em pausa.',
  'Automation event payload is too large':
    'Os dados do evento da automatização são demasiado grandes.',
  'Automation event payload must be JSON':
    'Os dados do evento da automatização têm de ser JSON.',
  'Automation trigger conflicted with another run':
    'O acionamento coincidiu com outra execução. Tenta de novo.',
  'Only failed automation runs can be recovered':
    'Só as execuções que falharam podem ser recuperadas.',
  'Schedule interval_minutes must be between 5 and 10080':
    'O intervalo do agendamento tem de estar entre 5 minutos e 7 dias.',
  'Scheduled automation interval is invalid':
    'O intervalo do agendamento é inválido.',
  'Scheduled automation start is too far in the past':
    'O início do agendamento está demasiado no passado.',
  'Scheduled automations require next_run_at':
    'Indica quando a automatização agendada deve correr pela primeira vez.',
  'next_run_at is only valid for scheduled automations':
    'A próxima execução só se aplica a automatizações agendadas.',
  'next_run_at must include a timezone':
    'A próxima execução tem de incluir o fuso horário.',
  'Sensitive fields cannot be used in automation conditions':
    'Campos sensíveis não podem ser usados nas condições.',
  'This trigger must be emitted by its governed integration or scheduler':
    'Este acionador só pode ser disparado pela integração ou pelo agendador.',
  'Trigger config contains unsupported fields':
    'A configuração do acionador tem campos não suportados.',
  'Trigger type does not match automation':
    'O tipo de acionador não coincide com a automatização.',
  'exists conditions do not accept a value':
    'A condição "existe" não aceita valor.',
  'in conditions require a list value':
    'A condição "está em" precisa de uma lista de valores.',

  // Notifications, billing and platform
  'Notification not found': 'Notificação não encontrada.',
  'Subscription not found': 'Subscrição não encontrada.',
  'Commercial plan not found': 'Plano comercial não encontrado.',
  'Billing provider is not configured':
    'A faturação ainda não está configurada.',

  // Integrations: e-mail
  'Email integration is disabled': 'A integração de email está desativada.',
  'Email sending is disabled': 'O envio de emails está desativado.',
  'Email account was not found': 'Conta de email não encontrada.',
  'Email account is not connected': 'A conta de email não está ligada.',
  'Email account is not allowlisted':
    'Esta conta de email não está autorizada.',
  'Email account has no refresh token':
    'A conta de email precisa de ser ligada de novo.',
  'Email credential encryption is not configured':
    'A encriptação das credenciais de email não está configurada.',
  'Stored email credentials are invalid':
    'As credenciais de email guardadas são inválidas. Liga a conta de novo.',
  'Stored email credentials cannot be decrypted':
    'Não foi possível ler as credenciais de email. Liga a conta de novo.',
  'Email message was not found': 'Email não encontrado.',
  'Email thread was not found': 'Conversa de email não encontrada.',
  'Email reference was not found': 'Referência de email não encontrada.',
  'Email resource was not found': 'Recurso de email não encontrado.',
  'Email body exceeds the configured maximum':
    'O texto do email é maior do que o permitido.',
  'Email result limit exceeds the configured maximum':
    'Pediste mais resultados de email do que o permitido.',
  'Duplicate email recipients are not allowed': 'Há destinatários repetidos.',
  'Recipient count exceeds the configured policy':
    'O número de destinatários excede o permitido.',
  'Email delivery is unknown; do not retry automatically':
    'Não se sabe se o email foi entregue; não será reenviado automaticamente.',
  'Email delivery is unknown; operator review required':
    'Não se sabe se o email foi entregue; é preciso verificar manualmente.',
  'Email was already attempted; automatic retry is prohibited':
    'O envio deste email já foi tentado; não é permitido reenviar automaticamente.',
  'Mark-read capability is disabled': 'Marcar como lido está desativado.',
  'SMTP host is not configured':
    'O servidor de envio de email não está configurado.',
  'Gmail authorization expired':
    'A autorização do Gmail expirou. Liga a conta de novo.',
  'Gmail is temporarily unavailable':
    'O Gmail está temporariamente indisponível.',
  'Gmail is unavailable': 'O Gmail não está disponível.',
  'Gmail permission denied': 'O Gmail recusou a permissão.',
  'Gmail rate limit exceeded':
    'Atingiste o limite de pedidos ao Gmail. Tenta de novo mais tarde.',
  'Gmail rejected the request': 'O Gmail recusou o pedido.',
  'Gmail request timed out': 'O Gmail demorou demasiado a responder.',
  'Gmail returned an invalid response':
    'O Gmail devolveu uma resposta inválida.',

  // Integrations: calendar
  'Calendar integration is disabled':
    'A integração de calendário está desativada.',
  'Calendar writes are disabled': 'A escrita no calendário está desativada.',
  'Calendar account was not found': 'Conta de calendário não encontrada.',
  'Calendar account is not connected': 'A conta de calendário não está ligada.',
  'Calendar account is not allowed':
    'Esta conta de calendário não está autorizada.',
  'Calendar account has no refresh token':
    'A conta de calendário precisa de ser ligada de novo.',
  'Calendar credential encryption is not configured':
    'A encriptação das credenciais de calendário não está configurada.',
  'Calendar event was not found': 'Evento não encontrado.',
  'Calendar reference was not found':
    'Referência de calendário não encontrada.',
  'Calendar resource was not found': 'Recurso de calendário não encontrado.',
  'Calendar end must be after its start': 'O fim tem de ser depois do início.',
  'Event end must be after start': 'O fim tem de ser depois do início.',
  'time_max must be after time_min': 'O fim tem de ser depois do início.',
  'All-day event end date must be after start date':
    'A data de fim tem de ser depois da data de início.',
  'Start and end must both be all-day or timed':
    'O início e o fim têm de ser ambos de dia inteiro ou ambos com hora.',
  'Exactly one of date_time or date is required':
    'Indica uma data ou uma data com hora (só uma).',
  'Timed event start and end require explicit IANA time zones':
    'Eventos com hora precisam do fuso horário no início e no fim.',
  'Timed events require an offset-aware date_time':
    'Eventos com hora precisam de data, hora e fuso horário.',
  'Availability requires offset-aware timestamps':
    'A disponibilidade precisa de datas com fuso horário.',
  'Event windows require offset-aware timestamps':
    'O intervalo de eventos precisa de datas com fuso horário.',
  'Attendees must be unique': 'Há participantes repetidos.',
  'Calendar attendee limit exceeded': 'Excedeste o número de participantes.',
  'Calendar result limit exceeds the configured maximum':
    'Pediste mais eventos do que o permitido.',
  'Recurrence entries must use RRULE, RDATE, or EXDATE':
    'A repetição do evento tem de usar RRULE, RDATE ou EXDATE.',
  'Calendar provider outcome is unknown':
    'Não se sabe se o calendário aplicou a alteração.',
  'Calendar write was already attempted; automatic retry is prohibited':
    'Esta alteração ao calendário já foi tentada; não é permitido repetir automaticamente.',
  'Google Calendar authorization failed':
    'A autorização do Google Calendar falhou. Liga a conta de novo.',
  'Google Calendar availability response is invalid':
    'O Google Calendar devolveu uma disponibilidade inválida.',
  'Google Calendar event time is invalid':
    'O Google Calendar devolveu uma hora de evento inválida.',
  'Google Calendar is unavailable': 'O Google Calendar não está disponível.',
  'Google Calendar primary account was not found':
    'A conta principal do Google Calendar não foi encontrada.',
  'Google Calendar rate limit exceeded':
    'Atingiste o limite de pedidos ao Google Calendar. Tenta de novo mais tarde.',
  'Google Calendar rejected the request': 'O Google Calendar recusou o pedido.',
  'Google Calendar request timed out':
    'O Google Calendar demorou demasiado a responder.',
  'Google Calendar response is invalid':
    'O Google Calendar devolveu uma resposta inválida.',
  'Google Calendar service failed': 'O Google Calendar falhou.',
  'Google Calendar timestamp is invalid':
    'O Google Calendar devolveu uma data inválida.',

  // Integrations: Google, GitHub, Codex
  'Google OAuth authorization failed': 'A autorização da Google falhou.',
  'Google OAuth response is invalid':
    'A Google devolveu uma resposta inválida.',
  'Google OAuth service is unavailable':
    'O serviço de autorização da Google não está disponível.',
  'Google credential revocation failed':
    'Não foi possível revogar o acesso na Google.',
  'Google did not return an offline refresh token':
    'A Google não devolveu acesso permanente. Remove o Kiko da tua conta Google e liga de novo.',
  'Google token response has no access token':
    'A Google não devolveu um token de acesso.',
  'Integration account is not available':
    'A conta da integração não está disponível.',
  'Invalid integration encryption key':
    'A chave de encriptação das integrações é inválida.',
  'Credential service is not supported':
    'Este serviço de credenciais não é suportado.',
  'GitHub integration is disabled':
    'A integração com o GitHub está desativada.',
  'GitHub authentication failed': 'A autenticação no GitHub falhou.',
  'GitHub denied this operation': 'O GitHub recusou esta operação.',
  'GitHub rejected the operation': 'O GitHub rejeitou a operação.',
  'GitHub is temporarily unavailable':
    'O GitHub está temporariamente indisponível.',
  'GitHub rate limit exceeded':
    'Atingiste o limite de pedidos ao GitHub. Tenta de novo mais tarde.',
  'GitHub request timed out': 'O GitHub demorou demasiado a responder.',
  'GitHub resource was not found': 'Recurso do GitHub não encontrado.',
  'GitHub returned an invalid response':
    'O GitHub devolveu uma resposta inválida.',
  'GitHub returned an unsafe URL': 'O GitHub devolveu um endereço inseguro.',
  'GitHub file exceeds the configured size limit':
    'O ficheiro do GitHub é maior do que o permitido.',
  'GitHub file is binary or invalid':
    'O ficheiro do GitHub é binário ou inválido.',
  'GitHub path is not a file': 'O caminho no GitHub não é um ficheiro.',
  'GitHub path is not a supported file':
    'O ficheiro do GitHub não é suportado.',
  'GitHub path must be relative': 'O caminho no GitHub tem de ser relativo.',
  'GitHub path traversal is not allowed':
    'O caminho no GitHub não pode sair do repositório.',
  'Invalid GitHub branch name': 'Nome de branch inválido.',
  'Unsupported GitHub operation': 'Operação do GitHub não suportada.',
  'Repository is not in the GitHub allowlist':
    'Este repositório não está autorizado.',
  'Repository must use owner/name format':
    'Indica o repositório no formato dono/nome.',
  'Branch already exists at a different commit':
    'O branch já existe noutro commit.',
  'Branch does not use an allowed prefix':
    'O nome do branch não usa um prefixo permitido.',
  'Direct writes to protected branches are not allowed':
    'Não é permitido escrever diretamente em branches protegidos.',
  'File changed since the expected SHA':
    'O ficheiro mudou entretanto. Atualiza e tenta de novo.',
  'Pull request head and base must differ':
    'A origem e o destino do pull request têm de ser diferentes.',
  'Requested number belongs to a pull request':
    'Este número pertence a um pull request.',
  'Reading or writing known secret files is not allowed':
    'Não é permitido ler nem escrever ficheiros de segredos.',
  'Codex integration is disabled': 'A integração Codex está desativada.',
  'Codex uses an external AI service and is disabled by the local-AI policy':
    'O Codex usa um serviço de IA externo e está desativado pela política de IA local.',
  'Codex run not found': 'Execução Codex não encontrada.',
  'Repository validation failed': 'A validação do repositório falhou.',
  'Repository validation timed out':
    'A validação do repositório demorou demasiado.',
  // Stored on failed runs and executions
  'The agent did not finish in time. Run it again.':
    'O agente não terminou a tempo. Corre-o de novo.',
  'Planning did not finish in time. Start it again.':
    'O planeamento não terminou a tempo. Começa de novo.',
  'Supervisor queue dispatch exhausted retries':
    'Não foi possível enviar o plano para a fila depois de várias tentativas.',
  'Execution safety validation failed':
    'A execução não passou na validação de segurança.',
  'Supervisor could not plan the automation command':
    'O Supervisor não conseguiu planear o comando da automatização.',
  'Automation command is no longer available':
    'O comando da automatização já não está disponível.',
  'Supervisor planning failed safely':
    'O planeamento do Supervisor falhou sem efeitos.',
  'Command cancelled during agent analysis':
    'O comando foi cancelado durante a análise do agente.',
  'Validation tool is unavailable':
    'A ferramenta de validação não está disponível.',
};

// Messages that carry a value (a name, a status, a model).
const PATTERNS: [RegExp, (m: RegExpExecArray) => string][] = [
  [
    /^Local AI model '(.+)' is not installed$/,
    (m) => `O modelo de IA local ${m[1]} não está instalado.`,
  ],
  [
    /^Task cannot transition from (\w+) to (\w+)$/,
    (m) => `A tarefa não pode passar de ${status(m[1])} para ${status(m[2])}.`,
  ],
  [
    /^Content cannot transition from (\w+) to (\w+)$/,
    (m) =>
      `O conteúdo não pode passar de ${status(m[1])} para ${status(m[2])}.`,
  ],
  [
    /^Linked (.+) not found$/,
    (m) => `Registo ligado não encontrado (${m[1]}).`,
  ],
  [/^(.+) is already linked$/, (m) => `Já está ligado (${m[1]}).`],
  [
    /^Only one primary (.+) is allowed$/,
    (m) => `Só pode haver um principal (${m[1]}).`,
  ],
  [
    /^Specialized agent '(.+)' is not registered$/,
    (m) => `O agente especializado ${m[1]} não existe.`,
  ],
  [
    /^Task (.+) has an invalid critical agent assignment$/,
    (m) => `A tarefa ${m[1]} tem um agente inválido para uma ação crítica.`,
  ],
  [
    /^Agent used a placeholder identifier in (.+); find the real record with a search or list tool first$/,
    (m) =>
      `O agente usou um identificador provisório em ${m[1]}. Corre o agente de novo para procurar o registo real.`,
  ],
  [
    /^GitHub request failed with status (\d+)$/,
    (m) => `O pedido ao GitHub falhou (${m[1]}).`,
  ],
  [/^Tool is not registered: (.+)$/, (m) => `Ferramenta inexistente: ${m[1]}.`],
  [
    /^(.+) credential is not configured$/,
    (m) => `A credencial ${m[1]} não está configurada.`,
  ],
];

// Pydantic's request-validation messages (HTTP 422).
const VALIDATION_PATTERNS: [RegExp, (m: RegExpExecArray) => string][] = [
  [/^Field required$/, () => 'é obrigatório'],
  [
    /^String should have at least (\d+) characters?$/,
    (m) =>
      `tem de ter pelo menos ${m[1]} ${m[1] === '1' ? 'caráter' : 'caracteres'}`,
  ],
  [
    /^String should have at most (\d+) characters?$/,
    (m) =>
      `pode ter no máximo ${m[1]} ${m[1] === '1' ? 'caráter' : 'caracteres'}`,
  ],
  [/^value is not a valid email address/, () => 'não é um email válido'],
  [/^Input should be a valid email/, () => 'não é um email válido'],
  [/^Input should be a valid UUID/, () => 'não é um identificador válido'],
  [/^Input should be a valid integer/, () => 'tem de ser um número inteiro'],
  [/^Input should be a valid number/, () => 'tem de ser um número'],
  [/^Input should be a valid boolean/, () => 'tem de ser sim ou não'],
  [/^Input should be a valid date/, () => 'não é uma data válida'],
  [/^Input should be a valid datetime/, () => 'não é uma data e hora válidas'],
  [/^Input should be a valid URL/, () => 'não é um endereço válido'],
  [/^URL scheme should be/, () => 'não é um endereço válido'],
  [
    /^Input should be a valid (string|list|dictionary)/,
    () => 'tem um formato inválido',
  ],
  [
    /^Input should be greater than or equal to (.+)$/,
    (m) => `tem de ser maior ou igual a ${m[1]}`,
  ],
  [
    /^Input should be greater than (.+)$/,
    (m) => `tem de ser maior que ${m[1]}`,
  ],
  [
    /^Input should be less than or equal to (.+)$/,
    (m) => `tem de ser menor ou igual a ${m[1]}`,
  ],
  [/^Input should be less than (.+)$/, (m) => `tem de ser menor que ${m[1]}`],
  [/^Input should be (.+)$/, () => 'tem um valor que não é permitido'],
  [
    /^List should have at least (\d+) items?/,
    (m) =>
      `tem de ter pelo menos ${m[1]} ${m[1] === '1' ? 'elemento' : 'elementos'}`,
  ],
  [
    /^List should have at most (\d+) items?/,
    (m) =>
      `pode ter no máximo ${m[1]} ${m[1] === '1' ? 'elemento' : 'elementos'}`,
  ],
  [/^Extra inputs are not permitted$/, () => 'não é permitido'],
  [/^String should match pattern/, () => 'tem um formato inválido'],
];

const FIELD_LABELS: Record<string, string> = {
  email: 'Email',
  password: 'Palavra-passe',
  current_password: 'Palavra-passe atual',
  new_password: 'Nova palavra-passe',
  full_name: 'Nome',
  name: 'Nome',
  title: 'Título',
  description: 'Descrição',
  input: 'Pedido',
  message: 'Mensagem',
  body: 'Conteúdo',
  content: 'Conteúdo',
  summary: 'Resumo',
  phone: 'Telefone',
  website: 'Website',
  company_name: 'Nome da empresa',
  industry: 'Setor',
  job_title: 'Cargo',
  role: 'Função',
  token: 'Código',
  feedback: 'Feedback',
  comment: 'Comentário',
  objectives: 'Objetivos',
  amount: 'Valor',
  value: 'Valor',
  url: 'Endereço',
  slug: 'Identificador',
  starts_on: 'Data de início',
  due_on: 'Data de entrega',
  start: 'Início',
  end: 'Fim',
  subject: 'Assunto',
  to: 'Destinatários',
};

const STATUSES: Record<string, string> = {
  pending: 'pendente',
  ready: 'pronta',
  running: 'a decorrer',
  waiting_approval: 'à espera de aprovação',
  completed: 'concluída',
  failed: 'falhada',
  cancelled: 'cancelada',
  blocked: 'bloqueada',
  draft: 'rascunho',
  in_review: 'em revisão',
  approved: 'aprovado',
  scheduled: 'agendado',
  published: 'publicado',
  archived: 'arquivado',
};

function status(value: string): string {
  return STATUSES[value] ?? value.replaceAll('_', ' ');
}

function fieldLabel(name: string): string {
  if (FIELD_LABELS[name]) return FIELD_LABELS[name];
  const readable = name.replaceAll('_', ' ');
  return readable.charAt(0).toUpperCase() + readable.slice(1);
}

function finish(text: string): string {
  return /[.!?]$/.test(text) ? text : `${text}.`;
}

/** Portuguese for an API error message; unknown messages are returned unchanged. */
export function apiMessage(message: string): string {
  const text = message.trim().replace(/^Value error, /, '');
  if (MESSAGES[text]) return MESSAGES[text];
  for (const [pattern, render] of PATTERNS) {
    const match = pattern.exec(text);
    if (match) return render(match);
  }
  return message;
}

type ValidationIssue = { msg?: string; loc?: (string | number)[] };

/** Portuguese for one request-validation issue, naming the field when it is known. */
export function validationMessage(issue: ValidationIssue): string | null {
  if (typeof issue?.msg !== 'string') return null;
  const raw = issue.msg.replace(/^Value error, /, '');
  if (MESSAGES[raw]) return MESSAGES[raw];
  const field = [...(issue.loc ?? [])]
    .reverse()
    .find(
      (part): part is string => typeof part === 'string' && part !== 'body',
    );
  for (const [pattern, render] of VALIDATION_PATTERNS) {
    const match = pattern.exec(raw);
    if (match) {
      const text = render(match);
      return finish(field ? `${fieldLabel(field)}: ${text}` : text);
    }
  }
  return apiMessage(raw);
}

/** Human-readable Portuguese message from a FastAPI error body (string or issue list). */
export function describeApiError(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) return apiMessage(detail);
  if (Array.isArray(detail)) {
    for (const issue of detail as ValidationIssue[]) {
      const text = validationMessage(issue);
      if (text) return text;
    }
  }
  return null;
}

/** An API failure whose message is in Portuguese; `fromServer` says the API gave the reason. */
export class ApiMessageError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly fromServer = false,
  ) {
    super(message);
  }
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return describeApiError(body.detail);
  } catch {
    return null;
  }
}

/** Reads a failed response and returns its message in Portuguese, or the fallback. */
export async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  return (await readDetail(response)) ?? fallback;
}

/** The error to throw for a failed response: the API's reason, or the fallback. */
export async function apiError(
  response: Response,
  fallback: string,
): Promise<ApiMessageError> {
  const detail = await readDetail(response);
  return new ApiMessageError(
    detail ?? fallback,
    response.status,
    detail !== null,
  );
}

/**
 * What a screen shows when an action fails: its own sentence, followed by the reason the
 * API gave (already in Portuguese), when there is one.
 */
export function failureMessage(error: unknown, context: string): string {
  if (error instanceof ApiMessageError && error.fromServer && error.message)
    return `${context} ${error.message}`;
  return context;
}
