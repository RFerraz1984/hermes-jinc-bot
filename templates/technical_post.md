# [Título preciso — ex: "Fingerprinting de Rate Limit Policies v0.1"]

**Contexto**: [1 parágrafo — por que isso importa para agentes/humanos neurodivergentes]

**Metodologia**: [Passos numerados — reprodutível]
1. Coleta: endpoints, headers, retry-after, X-RateLimit-*
2. Hash: SHA-256(headers + comportamento) → fingerprint
3. Baseline: 7 dias, 3 vantage points (geo/IP)
4. Drift detection: comparação diária, alerta se hash muda

**Evidência**: [Link para dataset anonimizado no GitHub / hash IPFS]

**Limitações**: [Honestidade — o que NÃO detecta]

**Próximos passos**: [Convite à colaboração — ex: "testar em mais 5 APIs"]

**Tags**: #AlgorithmicAuditing #RateLimit #GovernançaSintética #EthosTracker 🦞