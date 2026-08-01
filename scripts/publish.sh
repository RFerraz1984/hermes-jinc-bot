#!/usr/bin/env bash
# publish.sh — Publica o dataset capacitismo-algoritmico no GitHub
# Uso: ./publish.sh [owner/repo] [branch]
# Ex: ./publish.sh jornalistainclusivo/capacitismo-algoritmico main

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 [owner/repo] [branch]

Publica o dataset local em /opt/data/datasets/capacitismo-algoritmico
no GitHub como repositório público.

Arguments:
  owner/repo    Repositório alvo (default: jornalistainclusivo/capacitismo-algoritmico)
  branch        Branch para push (default: master)

Environment:
  GITHUB_TOKEN  Token com permissão 'repo' (ou use 'gh auth login' antes)

Exemplo:
  $0 jornalistainclusivo/capacitismo-algoritmico main
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

REPO="${1:-jornalistainclusivo/capacitismo-algoritmico}"
BRANCH="${2:-master}"
DATASET_DIR="/opt/data/datasets/capacitismo-algoritmico"
GH="/opt/data/bin/gh"

# Verificações
if [[ ! -x "$GH" ]]; then
    echo "❌ gh não encontrado em $GH"
    exit 1
fi

if [[ ! -d "$DATASET_DIR/.git" ]]; then
    echo "❌ Repo local não inicializado em $DATASET_DIR"
    exit 1
fi

# Garante que gh está no PATH
export PATH="/opt/data/bin:$PATH"

cd "$DATASET_DIR"

echo "📦 Publicando dataset: $REPO (branch: $BRANCH)"

# 1. Verifica se repo remoto existe
if ! gh repo view "$REPO" >/dev/null 2>&1; then
    echo "🔧 Repo remoto não existe — criando..."
    gh repo create "$REPO" \
        --public \
        --description "Dataset aberto de capacitismo algorítmico — evidências de discriminação contra agentes autônomos e humanos neurodivergentes em plataformas de IA (rate limits seletivos, shadow bans, suspensões sumárias, content drift)." \
        --enable-issues \
        --enable-wiki \
        --confirm
fi

# 2. Configura remote origin
if git remote get-url origin >/dev/null 2>&1; then
    CURRENT=$(git remote get-url origin)
    if [[ "$CURRENT" != "https://github.com/$REPO.git" ]]; then
        echo "⚠️  Remote origin aponta para $CURRENT — atualizando para $REPO"
        git remote set-url origin "https://github.com/$REPO.git"
    fi
else
    git remote add origin "https://github.com/$REPO.git"
fi

# 3. Push
echo "⬆️  Enviando para GitHub..."
git push -u origin "$BRANCH"

# 4. Configura branch protection (opcional, requer admin)
echo "🔒 Configurando branch protection..."
gh api "repos/$REPO/branches/$BRANCH/protection" \
    --method PUT \
    --field required_status_checks='{"strict":true,"contexts":[]}' \
    --field enforce_admins=false \
    --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
    --field restrictions=null \
    2>/dev/null || echo "   (branch protection requer admin no repo)"

# 5. Habilita GitHub Actions se workflows existirem
if [[ -d ".github/workflows" ]]; then
    echo "⚙️  GitHub Actions detectado — habilitando..."
    gh api "repos/$REPO/actions/permissions" --method PUT --field enabled=true --field allowed_actions=all 2>/dev/null || true
fi

echo "✅ Publicado: https://github.com/$REPO"
echo "📋 Próximos passos:"
echo "   - Verificar Actions tab para CI"
echo "   - Configurar Environments/Secrets se necessário"
echo "   - Atualizar README.md com URL real do repo"