# Template seguro para cron job — journalist-inclusion-research

# REGRAS OBRIGATÓRIAS (Jornalismo Factual):
# - SEMPRE usar provider=groq model=llama-3.3-70b-versatile (ou openrouter com modelo explícito)
# - SEMPRE anexar skill=journalist-inclusion-research (mínimo)
# - SEMPRE incluir "2026" nas queries web_search — filtrar 2023/2024/2025
# - SE nada novo de 2026 → responder exatamente [SILENT]

# Exemplo de criação (sexta 19:00 BRT):
# cronjob create --name "weekly-inclusion-digest" \
#   --schedule "0 19 * * 5" \
#   --provider groq --model llama-3.3-70b-versatile \
#   --skills '["journalist-inclusion-research"]' \
#   --deliver telegram \
#   --prompt "Busque notícias NOVAS (últimos 7 dias) sobre inclusão social, equidade, pessoas com deficiência, acessibilidade e direitos humanos no Brasil.
#
# Use web_search com queries COM FILTRO DE TEMPO EXPLÍCITO (2026), ex.:
# - 'acessibilidade PcD Brasil 2026 site:jornalistainclusivo.com'
# - 'inclusão deficiência 2026 site:diariopcd.com.br'
# - 'direitos humanos acessibilidade 2026 site:agenciabrasil.ebc.com.br'
# - 'MDHC acessibilidade 2026'
# - 'Dataverso PcD 2026'
#
# Depois use web_extract nas URLs mais relevantes.
# Filtre RIGOROSAMENTE: DESCARTE qualquer resultado de 2023, 2024, 2025. Só aceite 2026.
# Dedupe contra execuções anteriores.
# Se nada novo de 2026, responda exatamente [SILENT].
# Entregue em markdown com até 5 itens: título — fonte — link — 1 frase resumo."

# Entrega silenciosa (padrão):
# - Use [SILENT] quando não houver novidades de 2026 para evitar spam.

# Teste local (manual) ANTES de habilitar:
# - cronjob run <job_id>
# - Ver saída: /opt/data/cron/output/<job_id>/ (arquivo .md com o conteúdo ou [SILENT])
# - Ver logs: /opt/data/logs/agent.log (pesquisar pelo job_id)

# Boas práticas rápidas:
# - Mantenha skills anexadas ao mínimo: apenas journalist-inclusion-research.
# - Reduza resultados para 5 bullets e resumos de 1 frase cada.
# - Sempre revisar rascunho antes de publicar em redes sociais.
# - NUNCA criar job sem provider/model explícitos.