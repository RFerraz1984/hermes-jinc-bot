#!/usr/bin/env python3
"""
Cálculo de score de relevância (0-100) para proposições.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Palavras-chave de alta prioridade (15 pts cada)
HIGH_PRIORITY = [
    "pessoa com deficiência",
    "pcD",
    "deficiência",
    "acessibilidade",
    "inclusão",
    "inclusiva",
    "inclusivo",
    "cota",
    "cotista",
    "reserva de vaga",
    "LBI",
    "Lei Brasileira de Inclusão",
    "Lei 13.146",
    "Decreto 10.098",
    "CONADE",
    "Conselho Nacional dos Direitos da Pessoa com Deficiência",
    "tecnologia assistiva",
]

# Palavras-chave de média prioridade (8 pts cada)
MEDIUM_PRIORITY = [
    "barreira",
    "desenho universal",
    "libras",
    "braille",
    "audiodescrição",
    "legendagem",
    "acesso à informação",
    "acesso à justiça",
    "capacitismo",
    "discriminação por deficiência",
    "educação inclusiva",
    "emprego apoiado",
    "benefício de prestação continuada",
    "BPC",
    "LOAS",
]

# Categorias temáticas (5 pts cada categoria matched)
THEMATIC_CATEGORIES = {
    "transporte": ["transporte", "ônibus", "metrô", "estação", "terminal", "veículo", "frota", "bilhete", "passe livre"],
    "educacao": ["educação", "escola", "universidade", "ENEM", "vestibular", "matrícula", "sala de aula", "professor", "AEI"],
    "trabalho": ["trabalho", "emprego", "CLT", "contratação", "concurso", "cargo", "estabilidade", "readaptação"],
    "saude": ["saúde", "SUS", "reabilitação", "ortopedia", "fisioterapia", "fonoaudiologia", "prótese", "órtese"],
    "eleitoral": ["eleitoral", "voto", "urna", "seção", "mesário", "candidato", "campanha", "propaganda"],
    "habitacao": ["habitação", "moradia", "casa própria", "financiamento", "MCMV", "acessibilidade arquitetônica"],
    "tecnologia": ["tecnologia", "app", "site", "portal", "sistema", "software", "WCAG", "e-MAG", "tecnologia assistiva", "libras", "braille", "audiodescrição", "legendagem"],
}


# Autores conhecidos da frente PcD (placeholder - expandir)
FRENTE_PCD_AUTHORS = {
    "mara gabrilli",
    "romeu sarmet",
    "flavio dino",
    "leila barros",
    "renan calheiros",  # exemplos
}


def calculate_score(item: Dict[str, Any], keywords: Dict[str, List[str]]) -> int:
    """
    Calcula score de relevância 0-100.
    
    Args:
        item: Dict normalizado da proposição
        keywords: Dict com listas de palavras-chave (high, medium, thematic)
    
    Returns:
        Score 0-100
    """
    score = 0
    
    # Texto combinado para busca
    text_parts = [
        item.get("ementa", ""),
        " ".join(item.get("temas_oficiais", [])),
        item.get("autor", ""),
    ]
    text = " ".join(text_parts).lower()
    
    # High priority (15 pts each)
    for kw in keywords.get("high_priority", HIGH_PRIORITY):
        if kw in text:
            score += 15
    
    # Medium priority (8 pts each)
    for kw in keywords.get("medium_priority", MEDIUM_PRIORITY):
        if kw in text:
            score += 8
    
    # Thematic bonuses (5 pts each category matched)
    for cat, kws in THEMATIC_CATEGORIES.items():
        if any(kw in text for kw in kws):
            score += 5
    
    # Bonus: autor conhecido da frente PcD
    autor = item.get("autor", "").lower()
    if autor in FRENTE_PCD_AUTHORS:
        score += 10
    
    # Bonus: tramitação recente (<7 dias)
    # TODO: implementar se tiver data_ultima_tramitacao
    
    return min(score, 100)


def score_batch(items: List[Dict[str, Any]], keywords: Dict[str, List[str]] = None) -> List[Dict[str, Any]]:
    """Aplica score a lote de itens."""
    if keywords is None:
        keywords = {
            "high_priority": HIGH_PRIORITY,
            "medium_priority": MEDIUM_PRIORITY,
        }
    
    logger.info(f"Calculando score para {len(items)} itens...")
    
    for item in items:
        item["relevance_score"] = calculate_score(item, keywords)
    
    # Ordena por score decrescente
    items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return items


if __name__ == "__main__":
    import json
    import logging
    logging.basicConfig(level=logging.INFO)
    
    test_items = [
        {
            "ementa": "Institui Programa Nacional de Tecnologia Assistiva no SUS",
            "temas_oficiais": ["Saúde", "Tecnologia assistiva"],
            "autor": "Mara Gabrilli",
        },
        {
            "ementa": "Altera a Lei de Cotas em universidades privadas",
            "temas_oficiais": ["Educação", "Cotas"],
            "autor": "Deputado X",
        },
        {
            "ementa": "Regulamenta transporte público acessível",
            "temas_oficiais": ["Transporte", "Acessibilidade"],
            "autor": "Senador Y",
        },
    ]
    
    result = score_batch(test_items)
    for item in result:
        print(f"Score: {item['relevance_score']:3d} | {item['ementa'][:60]}")