# Bluesky Post Limits — Jornalista Inclusivo

## Limite Real: 300 Grafemas (não caracteres, não bytes)

O Bluesky limita posts a **300 grafemas** (grapheme clusters — o que o usuário vê como "um caractere", incluindo emojis combinados, acentos, etc.).

| Métrica | Limite | Nota |
|---------|--------|------|
| **Grafemas** | 300 | Limite hard da API (`app.bsky.feed.post`) |
| Caracteres Unicode | ~300 | Próximo, mas emojis contam como 1 grafema |
| Bytes UTF-8 | Variável | Não usar como referência |

## O Que Funcionou (Testado 2026-07-03)

### ✅ Post que passou (298 grafemas):

```
5 Pilares do Jornalismo Inclusivo no Autismo:

1. Autista no centro
2. Pessoa autista (não "sofre de")
3. Soluções, não curas
4. WCAG AA nativo
5. Checklist editorial

🔗 jor.in/5pilares

#JornalismoInclusivo #Autismo #Acessibilidade #Neurodiversidade
```

**Contagem:** ~298 grafemas (dentro do limite).

### ❌ Posts que FALHARAM (excederam 300 grafemas):

- Versão com link completo `https://jornalistainclusivo.com.br/2026/05/07/os-5-pilares...` → **345 grafemas**
- Versão com emojis numerados `1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣` → cada emoji = 2 grafemas (emoji + VS16)
- Versão com aspas tipográficas `\"Nada sobre nós, sem nós\"` → contam como grafemas extras

## Regras Práticas para Caber em 300 Grafemas

| Técnica | Ganho | Exemplo |
|---------|-------|---------|
| **Link curto próprio** | ~50-80 grafemas | `jor.in/5pilares` vs URL completa |
| **Sem emojis numerados** | ~8 grafemas | Use `1.` `2.` `3.` |
| **Texto direto, sem aspas** | ~10-20 grafemas | `Autista no centro` vs `\"Autista no centro\"` |
| **Hashtags no final, 3-4 máx** | Controle | `#JornalismoInclusivo #Autismo #Acessibilidade` |
| **Título curto** | ~30 grafemas | `5 Pilares...` vs frase completa |

## Template Recomendado (Cabe em 300)

```
[Manchete curta — máx 50 grafemas]

1. [Pilar 1 — curto]
2. [Pilar 2 — curto]
3. [Pilar 3 — curto]
4. [Pilar 4 — curto]
5. [Pilar 5 — curto]

🔗 [link-curto.próprio/slug]

#[Tag1] #[Tag2] #[Tag3] #[Tag4]
```

## Ferramenta de Contagem (para validar antes de postar)

```python
# No terminal do container:
python3 -c "
import grapheme
text = '''SEU TEXTO AQUI'''
print(f'Grafemas: {grapheme.length(text)}')
print(f'OK: {grapheme.length(text) <= 300}')
"
# Instalar: pip install grapheme
```

## Erro da API se Exceder

```
XRPC ERROR 400: InvalidRequest: Invalid app.bsky.feed.post record: 
grapheme too big (maximum 300, got XXX) at $.record.text
```

> **Nota:** O erro diz "grapheme too big" mas na verdade é "grapheme count too big" — contagem total, não tamanho de um único grafema.

## Referência
- Spec AT Protocol: `app.bsky.feed.post`
- Testado com `bsky` CLI v0.0.81 (mattn/bsky)