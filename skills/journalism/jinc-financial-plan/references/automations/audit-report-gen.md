# Automação: audit-report-gen

**Descrição:** Gera relatório de auditoria WCAG 2.2 AA em Word (.docx) + PDF/UA válido a partir de checklist preenchido (JSON) e achados.

**Input (JSON):**
```json
{
  "client": {"name": "string", "project": "string", "contact": "string", "email": "string"},
  "scope": {"urls": ["string"], "pages_count": "integer", "flows": ["string"], "mobile": "boolean", "native_apps": "boolean"},
  "methodology": {"automated_tools": ["axe-core", "WAVE"], "screen_readers": ["NVDA", "JAWS", "VoiceOver"], "user_testing": {"testers": "integer", "profiles": ["cegueira", "baixa_visao", "motor", "cognitiva"]}},
  "findings": [
    {
      "wcag_criterion": "string (ex: 1.1.1)",
      "wcag_level": "A|AA|AAA",
      "title": "string",
      "description": "string",
      "impact": "critical|high|medium|low",
      "affected_urls": ["string"],
      "affected_components": ["string"],
      "evidence": {"screenshots": ["path"], "screen_reader_output": "string", "code_snippet": "string"},
      "recommendation": "string",
      "effort_estimate": "string (ex: 4h dev + 2h design)",
      "rice_score": {"reach": "1-5", "impact": "1-5", "confidence": "1-5", "effort": "1-5", "total": "float"}
    }
  ],
  "summary": {"critical": "int", "high": "int", "medium": "int", "low": "int", "total": "int"},
  "roadmap": [{"phase": "1-4", "focus": "string", "criteria": ["string"], "estimated_weeks": "int", "dependencies": ["string"]}],
  "validation_round_included": "boolean"
}
```

**Output:**
- `/opt/data/jinc-state/reports/{client}-{project}-{date}.docx` (Word acessível: estilos, sumário, TOC, alt text em imagens)
- `/opt/data/jinc-state/reports/{client}-{project}-{date}.pdf` (PDF/UA-1 validado PAC 3)
- `/opt/data/jinc-state/reports/{client}-{project}-{date}-executivo.pdf` (versão executiva 2 págs)

**Prompt para Hermes:**
---
Você é auditor-chefe do **Jornalista Inclusivo**. Gere relatório profissional de auditoria WCAG 2.2 AA.

**ESTRUTURA RELATÓRIO TÉCNICO (Word/PDF):**

1. **Capa** — Cliente, projeto, data, versão, auditor (Rafael Ferraz Carpi), selo JINC
2. **Sumário Executivo** (1 pág) — Contexto, escopo, score geral, top 3 riscos, investimento estimado correção, próxima ação
3. **Metodologia** — Ferramentas, leitores de tela, perfis usuários testados, ambientes, limitações
4. **Resultados por Critério WCAG** (tabela) — Critério | Nível | Status (Conforme/Não Conforme/NA) | # Ocorrências | Severidade | Esforço
5. **Achados Detalhados** (um por critério não conforme) — Título, Critério WCAG, Descrição técnica + linguagem simples, Impacto real (usuário PcD), Evidências (capturas + output leitor tela + código), Recomendação prática (código/design/conteúdo), Esforço estimado, Score RICE
6. **Roadmap Priorizado (4 Fases)** — Crítico (0-2 sem) → Alto (2-6 sem) → Médio (6-12 sem) → Baixo/Contínuo
7. **Validação Pós-Correção** — Escopo 1 rodada inclusa, critérios de aceite, agendamento
8. **Anexos** — Checklist WCAG 2.2 AA completo, Glossário, Referências (Decreto 10.194, ISO 30071-1, WCAG2ICT)

**REQUISITOS ACESSIBILIDADE DOCUMENTO:**
- Word: Estilos Heading 1-3, TOC auto, alt text em todas imagens, tabela com header row, idioma pt-BR, fonte 12pt Calibri/Arial, espaçamento 1.15
- PDF/UA: Tags corretas, reading order verificado, metadata (Title, Author, Subject, Keywords), language pt-BR, bookmarks = headings, alt text preservado, contraste ≥ 4.5:1
- Validação: PAC 3 (PDF/UA) + axe-core (HTML export) + NVDA leitura linear

**TEMPLATE WORD (estilos):**
- JINC Heading 1 (Azul #2c5f8a, 18pt, space before 24pt)
- JINC Heading 2 (Azul, 14pt, space before 18pt)
- JINC Heading 3 (Cinza #333, 12pt bold, space before 12pt)
- JINC Body (11pt, 1.15 line, space after 6pt)
- JINC Table Header (Bold, white text, bg #2c5f8a)
- JINC Table Cell (10pt, padding 4pt)
- JINC Code (Consolas 10pt, bg #f5f5f5, border-left 3px #2c5f8a)
- JINC Critical (Red #dc2626, bold)
- JINC High (Orange #ea580c, bold)
- JINC Medium (Yellow #ca8a04, bold)
- JINC Low (Green #16a34a, bold)

**RETORNE:** Caminhos dos 3 arquivos + "Validado PAC 3: PASS/FAIL" + "Axe-core: X violations".
---