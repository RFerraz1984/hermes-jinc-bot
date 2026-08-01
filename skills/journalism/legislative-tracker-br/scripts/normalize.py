#!/usr/bin/env python3
"""
Normalização de proposições de Câmara, Senado e DOU para schema unificado.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def normalize_camara(prop: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza proposição da Câmara dos Deputados."""
    
    # Extrai autor principal
    autor = ""
    partido_autor = ""
    uf_autor = ""
    autores = prop.get("autores", [])
    if autores and isinstance(autores, list) and autores:
        autor = autores[0].get("nome", "")
        partido_autor = autores[0].get("siglaPartido", "")
        uf_autor = autores[0].get("siglaUf", "")
    
    # Última tramitação
    ultima_tramitacao = ""
    data_ultima = ""
    tramitacoes = prop.get("tramitacoes", [])
    if tramitacoes:
        ultima = tramitacoes[-1]
        ultima_tramitacao = ultima.get("descricaoSituacao", "")
        data_ultima = ultima.get("dataHora", "")[:10]  # YYYY-MM-DD
    
    return {
        "id_externo": f"{prop.get('siglaTipo', '')}-{prop.get('numero', '')}/{prop.get('ano', '')}",
        "casa": "camara",
        "casa_tipo": prop.get("siglaTipo", "").upper(),
        "numero": prop.get("numero"),
        "ano": prop.get("ano"),
        "ementa": prop.get("ementa", ""),
        "autor": prop.get("autor_nome", autor),
        "partido_autor": prop.get("autor_partido", partido_autor),
        "uf_autor": prop.get("autor_uf", uf_autor),
        "data_apresentacao": prop.get("dataApresentacao", "")[:10],
        "situacao_atual": prop.get("statusProposicao", {}).get("descricaoSituacao", ""),
        "ultima_tramitacao": ultima_tramitacao,
        "data_ultima_tramitacao": data_ultima,
        "url_oficial": prop.get("uriProposicao", ""),
        "url_texto_inteiro": prop.get("uriInteiroTeor", ""),
        "temas_oficiais": [t.get("tema", "") for t in prop.get("temas", []) if t.get("tema")],
        "hash_conteudo": "",  # preenchido no dedup
    }


def normalize_senado(materia: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza matéria do Senado Federal."""
    
    # Tema principal
    temas = materia.get("temas", [])
    if isinstance(temas, list):
        temas_oficiais = temas
    elif isinstance(temas, str):
        temas_oficiais = [temas]
    else:
        temas_oficiais = []
    
    return {
        "id_externo": materia.get("id_externo", ""),
        "casa": "senado",
        "casa_tipo": materia.get("sigla_tipo", "").upper(),
        "numero": materia.get("numero"),
        "ano": materia.get("ano"),
        "ementa": materia.get("ementa", ""),
        "autor": materia.get("autor_nome", ""),
        "partido_autor": materia.get("autor_partido", ""),
        "uf_autor": materia.get("autor_uf", ""),
        "data_apresentacao": materia.get("data_apresentacao", "")[:10],
        "situacao_atual": materia.get("situacao_atual", ""),
        "ultima_tramitacao": materia.get("ultima_tramitacao", ""),
        "data_ultima_tramitacao": materia.get("data_ultima_tramitacao", "")[:10],
        "url_oficial": materia.get("link_inteiro_teor", ""),
        "url_texto_inteiro": materia.get("link_inteiro_teor", ""),
        "temas_oficiais": temas_oficiais,
        "hash_conteudo": "",
    }


def normalize_dou(ato: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza ato do Diário Oficial da União."""
    
    return {
        "id_externo": f"DOU-{ato.get('secao', '')}-{ato.get('data', '')}-{ato.get('id', '')}",
        "casa": "dou",
        "casa_tipo": ato.get("tipo_ato", "").upper(),  # LEI, DECRETO, MP, PORTARIA
        "numero": ato.get("numero"),
        "ano": ato.get("data", "")[:4],
        "ementa": ato.get("title", ato.get("titulo", "")),
        "autor": ato.get("orgao", "Presidência da República"),
        "partido_autor": "",
        "uf_autor": "DF",
        "data_apresentacao": ato.get("data", "")[:10],
        "situacao_atual": "Publicada",
        "ultima_tramitacao": f"Publicado no DOU Seção {ato.get('secao', '')}",
        "data_ultima_tramitacao": ato.get("data", "")[:10],
        "url_oficial": ato.get("link", ""),
        "url_texto_inteiro": ato.get("link", ""),
        "temas_oficiais": [ato.get("secao_name", "")],
        "hash_conteudo": "",
    }


def normalize_proposicao(item: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Dispatch para normalizador apropriado."""
    
    if source == "camara":
        return normalize_camara(item)
    elif source == "senado":
        return normalize_senado(item)
    elif source == "dou":
        return normalize_dou(item)
    else:
        logger.warning(f"Fonte desconhecida: {source}")
        return {}


if __name__ == "__main__":
    import json
    
    # Teste rápido
    test_camara = {
        "siglaTipo": "PL",
        "numero": 1234,
        "ano": 2026,
        "ementa": "Institui Programa Nacional de Tecnologia Assistiva",
        "autor_nome": "Mara Gabrilli",
        "autor_partido": "PSD",
        "autor_uf": "SP",
        "dataApresentacao": "2026-07-20T10:00:00",
        "statusProposicao": {"descricaoSituacao": "Em tramitação"},
        "temas": [{"tema": "Tecnologia assistiva"}, {"tema": "Saúde"}],
        "tramitacoes": [{"descricaoSituacao": "Em tramitação na CCJ", "dataHora": "2026-07-22T14:00:00"}],
    }
    
    result = normalize_camara(test_camara)
    print(json.dumps(result, indent=2, ensure_ascii=False))