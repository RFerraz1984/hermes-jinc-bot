#!/usr/bin/env python3
"""
Módulo de enriquecimento - tags automáticas, NER leve, score de relevância.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Mapeamento palavras-chave -> tags
KEYWORD_TAGS = {
    # Deficiência / PcD
    "pessoa com deficiência": "#PcD",
    "pcD": "#PcD",
    "deficiência": "#PcD",
    "deficiente": "#PcD",
    
    # Acessibilidade
    "acessibilidade": "#acessibilidade",
    "acessível": "#acessibilidade",
    "barreira": "#acessibilidade",
    "desenho universal": "#acessibilidade",
    
    # Inclusão
    "inclusão": "#inclusão",
    "inclusiva": "#inclusão",
    "inclusivo": "#inclusão",
    
    # Cotas
    "cota": "#cotas",
    "cotista": "#cotas",
    "reserva de vaga": "#cotas",
    "lei de cotas": "#cotas",
    
    # LBI
    "LBI": "#LBI",
    "Lei Brasileira de Inclusão": "#LBI",
    "Lei 13.146": "#LBI",
    "Decreto 10.098": "#LBI",
    
    # CONADE
    "CONADE": "#CONADE",
    "Conselho Nacional dos Direitos": "#CONADE",
    
    # Transporte
    "transporte": "#transporte",
    "ônibus": "#transporte",
    "metrô": "#transporte",
    "estação": "#transporte",
    "terminal": "#transporte",
    "frota": "#transporte",
    "bilhete": "#transporte",
    "passe livre": "#transporte",
    
    # Educação
    "educação": "#educação",
    "escola": "#educação",
    "universidade": "#educação",
    "ENEM": "#educação",
    "vestibular": "#educação",
    "matrícula": "#educação",
    "sala de aula": "#educação",
    "professor": "#educação",
    "AEI": "#educação",
    
    # Trabalho
    "trabalho": "#trabalho",
    "emprego": "#trabalho",
    "CLT": "#trabalho",
    "contratação": "#trabalho",
    "concurso": "#trabalho",
    "cargo": "#trabalho",
    "estabilidade": "#trabalho",
    "readaptação": "#trabalho",
    
    # Saúde
    "saúde": "#saúde",
    "SUS": "#saúde",
    "reabilitação": "#saúde",
    "ortopedia": "#saúde",
    "fisioterapia": "#saúde",
    "fonoaudiologia": "#saúde",
    "prótese": "#saúde",
    "órtease": "#saúde",
    
    # Eleitoral
    "eleitoral": "#eleitoral",
    "voto": "#eleitoral",
    "urna": "#eleitoral",
    "seção": "#eleitoral",
    "mesário": "#eleitoral",
    "candidato": "#eleitoral",
    "campanha": "#eleitoral",
    "propaganda": "#eleitoral",
    
    # Habitação
    "habitação": "#habitação",
    "moradia": "#habitação",
    "casa própria": "#habitação",
    "financiamento": "#habitação",
    "MCMV": "#habitação",
    "acessibilidade arquitetônica": "#habitação",
    
    # Tecnologia
    "tecnologia": "#tecnologia",
    "app": "#tecnologia",
    "site": "#tecnologia",
    "portal": "#tecnologia",
    "sistema": "#tecnologia",
    "software": "#tecnologia",
    "WCAG": "#tecnologia",
    "e-MAG": "#tecnologia",
    
    # Tecnologia Assistiva
    "tecnologia assistiva": "#tecnologia",
    "leitor de tela": "#tecnologia",
    "Libras": "#tecnologia",
    "braille": "#tecnologia",
    "audiodescrição": "#tecnologia",
    "legendagem": "#tecnologia",
    
    # Capacitismo
    "capacitismo": "#capacitismo",
    "discriminação por deficiência": "#capacitismo",
    
    # Legislação geral
    "BPC": "#saúde",
    "LOAS": "#saúde",
    "benefício de prestação continuada": "#saúde",
}


THEMATIC_CATEGORIES = {
    "transporte": ["transporte", "ônibus", "metrô", "estação", "terminal", "veículo", "frota", "bilhete", "passe livre"],
    "educacao": ["educação", "escola", "universidade", "ENEM", "vestibular", "matrícula", "sala de aula", "professor", "AEI"],
    "trabalho": ["trabalho", "emprego", "CLT", "contratação", "concurso", "cargo", "estabilidade", "readaptação"],
    "saude": ["saúde", "SUS", "reabilitação", "ortopedia", "fisioterapia", "fonoaudiologia", "prótese", "órtease"],
    "eleitoral": ["eleitoral", "voto", "urna", "seção", "mesário", "candidato", "campanha", "propaganda"],
    "habitacao": ["habitação", "moradia", "casa própria", "financiamento", "MCMV", "acessibilidade arquitetônica"],
    "tecnologia": ["tecnologia", "app", "site", "portal", "sistema", "software", "WCAG", "e-MAG", "tecnologia assistiva", "libras", "braille", "audiodescrição", "legendagem"],
}


def extract_tags(text: str) -> List[str]:
    """Extrai tags baseadas em palavras-chave no texto."""
    if not text:
        return []
    
    text_lower = text.lower()
    tags = set()
    
    for keyword, tag in KEYWORD_TAGS.items():
        if keyword.lower() in text_lower:
            tags.add(tag)
    
    return sorted(tags)


def extract_entities_spacy(text: str) -> Dict[str, List[str]]:
    """Extrai entidades nomeadas usando spaCy (se disponível)."""
    entities = {
        "ORG": [],
        "PER": [],
        "LOC": [],
        "LAW": [],
        "DATE": [],
    }
    
    try:
        import spacy
        nlp = spacy.load("pt_core_news_sm")
        doc = nlp(text[:10000])  # Limita para performance
        
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
    except ImportError:
        logger.debug("spaCy não disponível - pulando NER")
    except OSError:
        logger.debug("Modelo pt_core_news_sm não instalado - pulando NER")
    except Exception as e:
        logger.warning(f"Erro no NER spaCy: {e}")
    
    # Deduplica
    for k in entities:
        entities[k] = list(set(entities[k]))
    
    return entities


def categorize_thematic(text: str) -> List[str]:
    """Identifica categorias temáticas no texto."""
    if not text:
        return []
    
    text_lower = text.lower()
    categories = []
    
    for cat, keywords in THEMATIC_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            categories.append(cat)
    
    return categories


def calculate_relevance_score(item: Dict[str, Any]) -> int:
    """Calcula score de relevância 0-100."""
    score = 0
    text = " ".join(filter(None, [
        item.get("title", ""),
        item.get("content", ""),
        item.get("ementa", ""),
        " ".join(item.get("temas_oficiais", [])) if isinstance(item.get("temas_oficiais"), list) else "",
    ])).lower()
    
    # High priority keywords (15 pts each)
    high_priority = [
        "pessoa com deficiência", "pcD", "deficiência", "acessibilidade", 
        "inclusão", "inclusiva", "inclusivo", "cota", "cotista", "reserva de vaga",
        "LBI", "Lei Brasileira de Inclusão", "Lei 13.146", "Decreto 10.098",
        "CONADE", "Conselho Nacional dos Direitos", "tecnologia assistiva",
        "libras", "braille", "audiodescrição", "legendagem", "capacitismo",
    ]
    for kw in high_priority:
        if kw in text:
            score += 15
    
    # Medium priority (8 pts each)
    medium_priority = [
        "barreira", "desenho universal", "libras", "braille", "audiodescrição",
        "legendagem", "capacitismo", "discriminação por deficiência",
        "educação inclusiva", "emprego apoiado", "benefício de prestação continuada",
        "BPC", "LOAS", "transporte acessível", "acessibilidade arquitetônica",
    ]
    for kw in medium_priority:
        if kw in text:
            score += 8
    
    # Thematic bonuses (5 pts each category matched)
    for cat, keywords in THEMATIC_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            score += 5
    
    # Bonus: autor conhecido (frente PcD)
    author = item.get("autor", "").lower()
    frente_pcd_authors = ["mara gabrilli", "romeu sarmet", "flavio dino"]
    if any(a in author for a in frente_pcd_authors):
        score += 10
    
    # Bonus: tramitação recente (<7 dias)
    # TODO: implementar se tiver data_ultima_tramitacao
    
    return min(score, 100)


def enrich_item(item: Dict[str, Any], source_config: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece um item individual."""
    # Texto combinado para análise
    full_text = " ".join(filter(None, [
        item.get("title", ""),
        item.get("content", ""),
        item.get("ementa", ""),
        " ".join(item.get("temas_oficiais", [])) if isinstance(item.get("temas_oficiais"), list) else "",
    ]))
    
    # Tags automáticas
    auto_tags = extract_tags(full_text)
    
    # Categorias temáticas
    thematic_cats = categorize_thematic(full_text)
    
    # Entidades (NER)
    entities = extract_entities_spacy(full_text)
    
    # Score de relevância
    relevance = calculate_relevance_score(item)
    
    # Atualiza item
    enriched = item.copy()
    enriched["tags"] = sorted(set(enriched.get("tags", []) + auto_tags))
    enriched["thematic_categories"] = thematic_cats
    enriched["entities"] = entities
    enriched["relevance_score"] = relevance
    enriched["auto_enriched"] = True
    
    return enriched


def enrich_batch(items: List[Dict[str, Any]], source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enriquece lote de itens."""
    logger.info(f"Enriquecendo {len(items)} itens...")
    
    enriched = []
    for item in items:
        try:
            enriched = enrich_item(item, source_config)
            enriched.append(enriched)
        except Exception as e:
            logger.warning(f"Erro enriquecendo item: {e}")
            enriched.append(item)  # Mantém original se falhar
    
    return enriched


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Teste rápido
    test_item = {
        "title": "PL 1234/2026 - Institui Programa Nacional de Tecnologia Assistiva no SUS",
        "content": "O projeto de lei visa garantir acesso a tecnologia assistiva para pessoas com deficiência no Sistema Único de Saúde.",
        "ementa": "Institui Programa Nacional de Tecnologia Assistiva no SUS",
        "temas_oficiais": ["Tecnologia assistiva", "Saúde", "PcD"],
        "source_id": "camara_proposicoes",
    }
    
    enriched = enrich_item(test_item, {})
    
    print("=== Item Enriquecido ===")
    print(f"Tags: {enriched['tags']}")
    print(f"Categorias: {enriched['thematic_categories']}")
    print(f"Entidades: {enriched['entities']}")
    print(f"Relevância: {enriched['relevance_score']}/100")