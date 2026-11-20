/**
 * Recovery hints for the local AI errors the API reports, so a person knows what to do
 * instead of only reading "Local AI runtime is not reachable".
 */
export function aiErrorHint(message: string | null | undefined): string | null {
  if (!message) return null;
  const text = message.toLowerCase();
  if (text.includes('runtime is not reachable')) {
    return 'O Ollama não está a responder. Neste Mac, abre a app Ollama (ou corre "ollama serve") e tenta de novo. Num servidor da empresa, fala com o administrador.';
  }
  if (text.includes('is not installed')) {
    const model = /model '?([^' ]+)'? is not installed/i.exec(message)?.[1];
    return `O modelo de IA ainda não está instalado. Corre "ollama pull ${model ?? '<modelo>'}" e tenta de novo, ou fala com o administrador.`;
  }
  if (text.includes('timed out') || text.includes('did not finish in time')) {
    return 'O modelo demorou demasiado. Tenta de novo; se voltar a acontecer, fecha apps pesadas ou pede um servidor com GPU ao administrador.';
  }
  if (text.includes('background') && text.includes('unavailable')) {
    return 'O serviço que corre a IA em segundo plano não está a responder. Reinicia o ambiente local ("kiko-local.sh restart") ou fala com o administrador.';
  }
  return null;
}
