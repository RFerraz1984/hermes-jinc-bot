# Automação: lead-enrichment

**Descrição:** Enriquece lead (LinkedIn URL ou email) com dados públicos + icebreaker personalizado + sinais de dor acessibilidade. Salva no Notion CRM.

**Input (JSON):**
```json
{
  "identifier": "string (LinkedIn URL ou email)",
  "source": "linkedin|email|manual",
  "notes": "string (contexto adicional)"
}
```

**Output (stdout JSON):**
```json
{
  "lead": {
    "name": "string",
    "role": "string",
    "company": "string",
    "company_domain": "string",
    "company_size": "string",
    "industry": "string",
    "tech_stack": ["string"],
    "linkedin_url": "string",
    "email": "string",
    "location": "string",
    "pain_points": ["string"],
    "accessibility_signals": {
      "has_accessibility_page": "boolean",
      "has_vpats": "boolean",
      "lawsuits_br": "boolean",
      "gov_contracts": "boolean",
      "hiring_accessibility": "boolean"
    },
    "icebreaker": "string (1 linha, genuíno, conexão PcD/jornalismo/acessibilidade)",
    "priority_score": "integer 1-100",
    "suggested_package": "auditoria|retainer|treinamento|dados-pcd",
    "enriched_at": "ISO8601"
  }
}
```

**Fontes de Dados (usar ferramentas disponíveis):**
- LinkedIn (público, sem login): nome, cargo, empresa, localização, posts recentes
- Site empresa: stack (Wappalyzer), página acessibilidade, VPATs, contratos gov (PNCP), vagas
- Google/Bing: "[empresa] acessibilidade", "[empresa] processo judicial acessibilidade", "[empresa] VPAT"
- Dataverso PcD: cruzamento CNPJ → dados PcD (se público)
- JINC CRM (Notion): histórico contatos anteriores

**Prompt para Hermes:**
---
Você é analista de inteligência comercial do **Jornalista Inclusivo**. Enriqueça o lead com dados acionáveis para proposta de acessibilidade.

**PASSOS:**
1. **Identidade** — Nome, cargo atual, empresa, LinkedIn, email (se público)
2. **Empresa** — Porte, setor, domain, stack tech (CMS, framework, cloud), página acessibilidade/VPAT
3. **Sinais de Dor Acessibilidade** (buscar ativamente):
   - Contratos públicos (PNCP/Compras.gov) → exigência WCAG/Decreto 10.194
   - Processos judiciais/MPF (busca: "[empresa] acessibilidade" + "ação civil" OR "TAC" OR "inquérito")
   - Vagas "acessibilidade" / "UX inclusivo" / "WCAG" no LinkedIn/Glassdoor
   - Reclamações Reclame Aqui / redes: "não consigo acessar", "leitor de tela não funciona"
   - Certificações ISO 9001/27001 sem menção acessibilidade = gap
4. **Icebreaker** (escolha UMA, seja específico):
   - "Vi seu post sobre [tema] — como tetraplégico que usa [tech assistiva], senti na pele o que você descreveu."
   - "Sua vaga de [cargo] pede WCAG — no JINC testamos com usuários reais PcD, não só axe-core."
   - "O [produto] da [empresa] atende [setor público] — o Decreto 10.194 exige WCAG 2.1 AA em contratos."
   - "Li o relatório de sustentabilidade de [empresa] — cadê a acessibilidade digital? No Dataverso mapeamos isso."
5. **Score & Pacote** — Peso: dor (40%), fit (30%), autoridade decisor (20%), timing (10%). Pacote por perfil:
   - Govtech/portal público → Auditoria + Retainer
   - SaaS/app → Retainer
   - Redação/assessoria → Treinamento
   - Órgão público/instituto → Dados PcD

**RETORNE JSON VÁLIDO** com estrutura acima. Se dado não encontrado, use null (não invente).
---