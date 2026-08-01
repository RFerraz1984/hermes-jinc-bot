#!/usr/bin/env python3
"""
Enriquecimento de proposições - tags, categorias, metadados.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Keywords para categorização temática
THEMATIC_KEYWORDS = {
    "transporte": ["transporte", "ônibus", "metrô", "estação", "terminal", "veículo", "frota", "bilhete", "passe livre"],
    "educacao": ["educação", "escola", "universidade", "ENEM", "vestibular", "matrícula", "sala de aula", "professor", "AEI"],
    "trabalho": ["trabalho", "emprego", "CLT", "contratação", "concurso", "cargo", "estabilidade", "readaptação"],
    "saude": ["saúde", "SUS", "reabilitação", "ortopedia", "fisioterapia", "fonoaudiologia", "prótese", "órtese"],
    "eleitoral": ["eleitoral", "voto", "urna", "seção", "mesário", "candidato", "campanha", "propaganda"],
    "habitacao": ["habitação", "moradia", "casa própria", "financiamento", "MCMV", "acessibilidade arquitetônica"],
    "tecnologia": ["tecnologia", "app", "site", "portal", "sistema", "software", "WCAG", "e-MAG", "tecnologia assistiva", "libras", "braille", "audiodescrição", "legendagem"],
}


def categorize_thematic(text: str) -> List[str]:
    """Identifica categorias temáticas no texto."""
    if not text:
        return []
    
    text_lower = text.lower()
    categories = []
    
    for cat, keywords in THEMATIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            categories.append(cat)
    
    return categories


def enrich_batch(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enriquece lote de proposições."""
    logger.info(f"Enriquecendo {len(items)} itens...")
    
    for item in items:
        # Texto combinado para análise
        full_text = " ".join(filter(None, [
            item.get("ementa", ""),
            " ".join(item.get("temas_oficiais", [])),
        ])).lower()
        
        # Categorias temáticas
        item["thematic_categories"] = categorize_thematic(full_text)
        
        # Autor conhecido (frente PcD) - placeholder
        item["known_pcd_author"] = False  # Implementar com lista real
    
    return items


if __name__ == "__main__":
    import json
    import logging
    logging.basicConfig(level=logging.INFO)
    
    test_items = [
        {"ementa": "PL sobre transporte acessível para pessoas com deficiência", "temas_oficiais": ["Transporte", "PcD"]},
        {"ementa": "Altera lei de cotas em universidades públicas", "temas_oficiais": ["Educação", "Cotas"]},
    ]
    
    result = enrich_batch(test_items)
    print(json.dumps(result, indent=2, ensure_ascii=False))