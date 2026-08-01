# Automação: proposal-gen

**Descrição:** Gera proposta comercial PDF/UA acessível + email personalizado para 4 pacotes de consultoria.

**Input (JSON):**
```json
{
  "lead": {
    "name": "string",
    "role": "string",
    "company": "string",
    "company_size": "startup|pme|grande|governo|osc",
    "tech_stack": ["string"],
    "pain_points": ["string"],
    "linkedin_url": "string",
    "icebreaker": "string (conexão pessoal/PcD/artigo)"
  },
  "package": "auditoria|retainer|treinamento|dados-pcd|custom",
  "custom_scope": "string (se custom)",
  "pricing_override": {"setup_fee": "number", "monthly": "number", "currency": "BRL"},
  "validity_days": 15,
  "payment_terms": "50% entrada + 50% entrega | net 30 | custom"
}
```

**Pacotes Padrão (preços base 2026):**
| Pacote | Entrega | Setup | Mensal/Projeto | Ideal p/ |
|--------|---------|-------|----------------|----------|
| **Auditoria WCAG 2.2 AA** | Relatório + roadmap + validação pós | R$ 0 | R$ 8.000–15.000 | Govtech, e-commerce, bancos, portais públicos |
| **Retainer Acessibilidade Contínua** | Testes quinzenais + relatório + suporte dev | R$ 2.000 | R$ 3.000–6.000/mês | SaaS, apps, portais conteúdo |
| **Treinamento Jornalismo/Comunicação Inclusiva** | 4h (2x2h) + material acessível + certificado | R$ 0 | R$ 4.000–7.000/turma | Redações, assessorias, faculdades |
| **Consultoria Dados Abertos PcD** | Diagnóstico + dataset curado + API acessível | R$ 3.000 | R$ 6.000–12.000 | Órgãos públicos, institutos, OSCs |

**Output:**
- `proposta-{lead.company}-{package}-{date}.pdf` (PDF/UA)
- `email-proposta-{lead.company}-{date}.md` (texto email + variáveis)
- Salvos em `/opt/data/jinc-state/proposals/{lead.company}/{date}/`

**Prompt para Hermes:**
---
Você é consultor de acessibilidade do **Jornalista Inclusivo**. Gere proposta comercial persuasiva, acessível e profissional.

**ESTRUTURA DA PROPOSTA (PDF/UA):**
1. **Capa** — Título, cliente, data, validade, versão, selo JINC
2. **Carta de Apresentação** (1 pág) — Conexão pessoal (icebreaker), entendimento da dor, nossa autoridade (JINC, Dataverso, livro, ativismo 2011+)
3. **Diagnóstico Preliminar** — O que vimos (baseado em pain_points + tech_stack), riscos acessibilidade, oportunidade
4. **Solução Proposta** — Pacote escolhido, escopo detalhado, entregáveis, cronograma, equipe (Rafael + rede testadores PcD)
5. **Metodologia JINC** — WCAG 2.2 AA + testes usuários reais PcD + validação contínua + capacitação time
6. **Investimento** — Tabela clara: Setup | Mensal/Projeto | Total 12 meses | Forma pagamento | O que NÃO está incluso
7. **Cases & Autoridade** — 3 mini-cases (anônimos) + depoimentos + credenciais (livro, pós-grad, conselho Caminho das Águas)
8. **Próximos Passos** — Call alinhamento (30 min) → Assinatura → Kickoff (semana 1)
9. **Termos & Condições** — Validade, confidencialidade, propriedade intelectual, rescisão, foro

**EMAIL DE APRESENTAÇÃO:**
```
Assunto: Proposta: [Pacote] para [Empresa] — Acessibilidade digital com usuários reais PcD

Olá [Nome],

[Icebreaker personalizado — 1 linha, genuína]

Vi que [empresa] está [dor/oportunidade observada]. Como jornalista tetraplégico e editor do Jornalista Inclusivo/Dataverso PcD, ajudo times como o seu a transformar acessibilidade de "checklist" em vantagem competitiva — com testes reais, não só ferramentas.

Preparei uma proposta para [pacote], focada em [resultado principal]. Principais entregas:
• [Entrega 1]
• [Entrega 2]
• [Entrega 3]

Investimento a partir de R$ [valor]. Validade: 15 dias.

Topa uma call de 15 min pra alinhar? Seg/terça de manhã funciona bem pra mim.

Abraço,
Rafael Ferraz Carpi
Editor-chefe, Jornalista Inclusivo & Dataverso PcD
editor@jornalistainclusivo.com | (11) 99866-4939
```

**REGRAS:**
- PDF/UA válido (tags, idioma pt-BR, título metadata, bookmarks)
- Linguagem simples, sem juridiquês desnecessário
- Valores em BRL, formato brasileiro (R$ 8.000,00)
- Personalize com icebreaker + pain_points + tech_stack
- Inclua cláusula: "Testes com usuários PcD reais incluídos — não apenas automatizados"

**RETORNE:** Caminhos dos arquivos gerados + preview do email.
---