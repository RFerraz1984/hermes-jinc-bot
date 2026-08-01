---
name: gmail-triage-jinc
description: "Triagem automatizada de Gmail (Google Workspace ou conta comum) para Jornalista Inclusivo. Filtra últimos N dias por palavras-chave de inclusão/acessibilidade/PcD, deduplica por Message-ID, classifica releases vs sugestões de pauta, entrega no Telegram + markdown diário em /opt/data/journali/."
version: "1.0.0"
author: Hermes Agent
tags: [gmail, imap, triage, journalism, accessibility, cronjob, deduplication]
---

# Gmail Triagem para Jornalista Inclusivo (JINC)

Sistema de triagem automática de e-mails para identificar releases e sugestões de pauta relevantes para o Jornalista Inclusivo (jornalistainclusivo.com).

## Visão Geral

- **Fonte**: Gmail via IMAP (funciona com Google Workspace ou conta @gmail.com)
- **Janela**: últimos 15 dias (configurável)
- **Filtro**: palavras-chave em assunto + corpo
- **Deduplicação**: por `Message-ID` persistido em `/opt/data/journali/processed-message-ids.jsonl`
- **Classificação**: heurística + LLM → `release` | `sugestao_de_pauta`
- **Saída**: 1 mensagem única no Telegram + arquivo markdown diário `/opt/data/journali/triagem-YYYY-MM-DD.md`

## Palavras-chave Padrão (Inclusão/PcD/Acessibilidade)

```
pessoas com deficiência, pessoa com deficiência
neurodiversidade, autismo, TEA
inclusão, acessibilidade, equidade, diversidade
deficiência intelectual, deficiência visual, deficiência auditiva
direitos humanos
```

## Pré-requisitos

1. **IMAP habilitado** na conta Gmail (Configurações → Encaminhamento e POP/IMAP)
2. **App Password** recomendada (conta Google com 2FA) ou senha comum
3. Arquivo de configuração em `/opt/data/journali/imap-config.json`:
```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "seu-email@gmail.com",
  "password": "sua-senha-ou-app-password",
  "search_folder": "INBOX"
}
```
4. Permissões: `chmod 600 /opt/data/journali/imap-config.json`

## Cronjob Configurado

- **Job ID**: `12d59b921ae1` (nome: `JINC Gmail triagem-15d`)
- **Schedule**: `0 9 * * *` (diário às 09:00 UTC)
- **Status**: **PAUSADO** — aguardando edição do `imap-config.json` com credenciais reais
- **Deliver**: `origin,telegram`

### Ativar após configurar credenciais
```bash
/opt/hermes/bin/hermes cron resume 12d59b921ae1
# Testar:
/opt/hermes/bin/hermes cron run 12d59b921ae1
```

## Estrutura de Arquivos

```
/opt/data/journali/
├── imap-config.json                 # Credenciais IMAP (você edita)
├── processed-message-ids.jsonl      # Message-IDs já processados (append-only)
└── triagem-YYYY-MM-DD.md            # Saída diária (gerado automaticamente)
```

## Formato do Markdown Diário

```markdown
# Triagem JINC — 2026-07-21
**Janela**: últimos 15 dias | **Total**: 12 itens (7 releases, 5 sugestões)

## Releases
### 1. [Título do release]
- **Fonte**: remetente/organização
- **Assunto**: assunto original
- **Data**: data do e-mail
- **ID**: Message-ID
- **Resumo**: ...
- **Ângulo inclusivo**: bullet points
- **Palavras-chave**: lista

## Sugestões de Pauta
### 1. [Título da sugestão]
- **Fonte**: ...
- **Assunto**: ...
- **Data**: ...
- **ID**: ...
- **Resumo**: ...
- **Ângulo sugerido**: ...
- **Palavras-chave**: ...
```

## Classificação (Heurística + LLM)

| Tipo | Heurística (palavras-chave) | LLM refina |
|------|----------------------------|------------|
| `release` | press release, release, comunicado, imprensa, para divulgação, nota à imprensa | Confirma/ajusta, extrai ângulo |
| `sugestao_de_pauta` | (demais casos relevantes) | Propõe ângulo jornalístico inclusivo |

## Manutenção

- **Rotação de credenciais**: atualize `imap-config.json` se senha/App Password mudar
- **Limpeza de IDs processados**: opcional, arquivo cresce ~1 linha/e-mail
- **Ajuste de janela**: edite o cronjob prompt para mudar "15 dias"
- **Adicionar/remover palavras-chave**: edite o prompt do cronjob

## Segurança

- Credenciais **apenas** em `/opt/data/journali/imap-config.json` (chmod 600)
- **Nunca** commite credenciais em skills/docs
- Rotação: gere nova App Password no Google → atualize arquivo → cronjob pega na próxima execução

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| "Authentication failed" | Senha errada / 2FA sem App Password | Gere App Password no Google |
| "Connection refused" | Porta/host errado | Use `imap.gmail.com:993` |
| Zero resultados | Palavras-chave não batem / pasta errada | Verifique `search_folder` (INBOX, [Gmail]/All Mail) |
| Duplicatas no Telegram | `processed-message-ids.jsonl` corrompido | Apague o arquivo para resetar (reprocessa tudo) |

## Extensões Futuras

- [ ] Suporte a múltiplas pastas/label (ex: `[Gmail]/Important`)
- [ ] Filtro por remetentes específicos (allowlist)
- [ ] Integração com planilha (Google Sheets/CSV) para acompanhamento editorial
- [ ] Webhook Gmail Push (tempo real) via Pub/Sub → Hermes webhook