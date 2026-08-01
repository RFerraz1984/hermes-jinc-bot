---
name: jinc-gmail-triagem
description: "Triagem inteligente de Gmail (Google Workspace) para gerar releases e sugestões de pautas do JornalistaInclusivo.com com deduplicação robusta e entrega (Telegram + markdown diário)."
version: 1.0.0
author: Rafael Ferraz Carpi + Hermes Agent
defined_class: "Sistema de triagem por cron para Gmail"
---

# jinc-gmail-triagem

## Quando usar
Use este skill quando você quiser que o Hermes:
- leia mensagens de um **Gmail Google Workspace**;
- aplique **filtros por janela de tempo** (ex.: últimos 15 dias);
- filtre por **palavras-chave e/ou assuntos** (ex.: deficiência, neurodiversidade, autismo/TEA, inclusão/acessibilidade/equidade/diversidade, direitos humanos);
- classifique em **release** vs **sugestão de pauta**;
- produza um **output diário** em `/opt/data` e envie para o **Telegram**.

## Princípios operacionais (do JINC)
- **Robustez > “tempo real”.** Comece com **cron por 1x/dia**.
- **Deduplicação por `messageId`** (append-only) para não reprocessar.
- **Sem ranqueamento por alta/média/baixa** quando o usuário não pedir; em vez disso: classifique e extraia ângulo inclusivo.
- **Saída reprodutível e estruturada** (markdown diário com seções e campos fixos).

## Estado persistente
- Arquivo de dedupe (append-only):
  - `/opt/data/journali/processed-message-ids.jsonl`
- Cada linha contém: o `messageId` processado.

## Pipeline (passo a passo)
1) **Coletar candidatos**
   - Buscar no Gmail apenas mensagens com `internalDate` dentro da janela:
     - padrão: `últimos 15 dias`.
   - Campo mínimo necessário para dedupe e classificação:
     - `messageId`, `subject`, `from`, `date`, e o conteúdo/trecho principal (ou `snippet`), além de links se existirem.

2) **Filtro por palavras-chave**
   - Aplicar match por presença (case-insensitive) para o conjunto configurado.
   - Termos sugeridos (exatamente como você listou):
     - “pessoas com deficiência”, “pessoa com deficiência”
     - “neurodiversidade”, “autismo”, “TEA”, “inclusão”, “acessibilidade”, “equequidade” (se necessário ajustar ortografia), “diversidade”
     - “deficiência intelectual”, “deficiência visual”, “deficiência auditiva”
     - “direitos humanos”

3) **Deduplicar por `messageId`**
   - Ler `processed-message-ids.jsonl`.
   - Ignorar mensagens cujo `messageId` já exista.

4) **Classificar release vs sugestão de pauta**
   - Heurística + reforço por LLM:
     - release: indícios como “press release”, “comunicado”, “release”, “para divulgação”, “imprensa”, “assessoria”.
     - sugestão de pauta: indícios de convite para cobertura/tema com contexto editorial (“sugere pauta”, “agenda”, “tema para matéria”, “oportunidade de pauta”).
   - Quando houver dúvida, classificar como o tipo que melhor combine com o objetivo do texto.

5) **Extrair campos para publicação**
   - `tipo` (release|sugestao_de_pauta)
   - `fonte` (from)
   - `assunto` (subject)
   - `data_email` (date/internalDate)
   - `links/identificador` (Message-ID e links se existirem)
   - `resumo` (3-6 linhas)
   - `angulo_inclusivo_sugerido` (2-4 bullets)
   - `palavras_chave_encontradas`

6) **Entregar resultado**
   - Markdown diário:
     - `/opt/data/journali/triagem-YYYY-MM-DD.md`
   - Telegram:
     - mensagem única do dia (não “por item”).

7) **Persistir dedupe**
   - Após classificar/entregar, append dos `messageId` processados.

## Pitfalls / cuidados
- **Não fazer ranqueamento de prioridade** se o usuário disser explicitamente que “não”.
- **Não deixar o cron “reprocessar tudo”**:
  - sempre dedupe por `messageId`;
  - sempre append-only.
- **Não misturar busca “global” com filtros**:
  - a janela de 15 dias deve entrar antes da filtragem por palavras.

## Template de output (markdown)
- Cabeçalho:
  - `# Triagem Gmail - últimos 15 dias`
  - `Run: <timestamp>`
  - `Janela: <YYYY-MM-DD> .. <YYYY-MM-DD>`
  - `Total filtradas: N`
- `## Releases`
- `## Sugestões de pautas`
- Item (formato fixo):
  - `### Tipo: release`
  - `**Fonte:** ...`
  - `**Assunto:** ...`
  - `**Data do e-mail:** ...`
  - `**Link/Identificador:** ...`
  - `**Resumo:** ...`
  - `**Ângulo inclusivo sugerido:**` (bullets)
  - `**Palavras-chave encontradas:**` (lista)

## Como ativar no Hermes (cron)
- Criar/editar um cronjob 1x/dia (ex.: 09:00 UTC ou horário local).
- Delivery recomendado:
  - `origin,telegram` (Telegram + registro no chat atual).
- O prompt do cron deve ser auto-contido e incluir:
  - janela 15 dias;
  - lista de palavras-chave;
  - dedupe por `/opt/data/journali/processed-message-ids.jsonl`;
  - geração de markdown diário em `/opt/data/journali/triagem-YYYY-MM-DD.md`;
  - classificação release vs sugestão de pauta;
  - mensagem única no Telegram.

## O que ainda precisa ser configurado
- Integração Gmail OAuth/credenciais do Hermes para leitura do Gmail.
- (Opcional) parser de conteúdo/link se o Gmail retornar apenas snippet.

