---
name: social-media
description: "Social media workflows for accessibility/PcD journalism: news gathering, content creation, and posting to X/Twitter via xurl."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [social-media, journalism, accessibility, pcd, xurl, twitter]
    homepage: https://github.com/openclaw/openclaw
---

# Social Media — Jornalismo Inclusivo & PcD

Skill para fluxos de mídia social focados em **jornalismo inclusivo, acessibilidade e direitos das pessoas com deficiência (PcD)** no Brasil.

## Capacidades

| Área | Ferramenta | Descrição |
|------|------------|-----------|
| **Busca de notícias** | `web_search` + `web_extract` | Coleta de notícias em fontes brasileiras sobre PcD/acessibilidade |
| **Postagem no X/Twitter** | `xurl` (opcional) | Publicação, reply, quote, media upload — requer setup prévio do usuário |
| **Monitoramento de feeds** | `blogwatcher-cli` (opcional) | RSS/Atom de fontes especializadas — requer instalação separada |

## Uso no Cron Job (News Digest)

O prompt padrão para o job diário:

```
Busque notícias atuais (últimos 7 dias) sobre acessibilidade e inclusão de pessoas com deficiência no Brasil.
Use web_search com consultas como:
- "acessibilidade PcD Brasil site:jornalistainclusivo.com"
- "inclusão deficiência site:diariopcd.com.br"
- "direitos humanos acessibilidade site:agenciabrasil.ebc.com.br"
- "MDHC acessibilidade"
- "Dataverso PcD"
Depois use web_extract nas URLs mais relevantes.
Entregue em markdown com até 10 itens (título, fonte, link, 1 frase).
Se nada novo, responda apenas [SILENT].
```

## Fontes Prioritárias (Brasil)

| Fonte | URL Base | Feed RSS | Foco |
|-------|----------|----------|------|
| Jornalista Inclusivo | `jornalistainclusivo.com.br` | `https://jornalistainclusivo.com.br/feed` | Jornalismo independente, protagonismo, audiodescrição |
| Diário PcD | `diariopcd.com.br` | — | Jornalismo especializado, Radar Inclusão |
| Dataverso PcD | `pcd.dataverso.org` | — | Dados, pesquisas, observatórios |
| Agência Brasil — DH | `agenciabrasil.ebc.com.br/tag/direitos-humanos` | — | Políticas, legislação |
| MDHC | `gov.br/mdh` | — | "Novo Viver sem Limite", LBI |
| Gov.br Acessibilidade Digital | `governodigital.gov.br/acessibilidade` | — | eMAG, WCAG, AMAWeb |

## Automação RSS → X/Twitter (Cron Job)

Para postar automaticamente novos artigos do site no X/Twitter:

**Script:** `templates/rss-to-x.sh` (copiar para `/opt/data/scripts/` e dar `chmod +x`)

**Cron job** (a cada 30 min):
```bash
cronjob create --name "JINC Auto-post RSS→X" --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/rss-to-x.sh que monitora RSS do jornalistainclusivo.com.br/feed e posta novidades no X via xurl"
```

**Pré-requisitos no container Umbrel:**
1. Instalar xurl: `curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash`
2. Configurar OAuth (fora da sessão do agente, com `HOME=/opt/data/home`):
   ```bash
   HOME=/opt/data/home xurl auth apps add jinc-app --client-id SEU_ID --client-secret SEU_SECRET
   HOME=/opt/data/home xurl auth oauth2 --app jinc-app @seu_usuario
   HOME=/opt/data/home xurl auth default jinc-app
   ```
3. O script usa `HOME=/opt/data/home` para encontrar `~/.xurl` (Hermes roda com HOME=/opt/data, mas subprocessos usam /opt/data/home)

## Postagem no X/Twitter (via xurl)

**Pré-requisito**: usuário deve configurar `xurl` fora da sessão do agente (ver skill `xurl`).

```bash
# Verificar auth
xurl auth status

# Postar thread de notícias
xurl post "🧵 Novidades em acessibilidade e inclusão PcD (Brasil):\n\n1. [Título](link)\n2. [Título](link)\n\n#Acessibilidade #PcD #Inclusão"
```

## Variáveis de Ambiente (opcional)

| Variável | Descrição |
|----------|-----------|
| `SOCIAL_MEDIA_SOURCES` | JSON array de fontes customizadas |
| `SOCIAL_MEDIA_MAX_ITEMS` | Limite de itens no digest (default: 10) |

## Exemplo de Uso Direto

```
Use a skill social-media para buscar notícias de acessibilidade PcD no Brasil
e preparar uma thread para o X/Twitter com as 5 principais.
```

## Notas

- **Sem dependências obrigatórias** — funciona com `web_search`/`web_extract` nativos do Hermes
- **xurl é opcional** — só necessário se for postar no X/Twitter
- **blogwatcher-cli é opcional** — para monitoramento contínuo de RSS
- O skill é desenhado para rodar em container (Umbrel/Hermes) sem binários extras