#!/usr/bin/env python3
"""
Gerador de relatórios WCAG 2.2 + e-MAG 3.1 — HTML, PDF, Markdown (executivo/técnico).
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Define BASE_DIR for template loading
BASE_DIR = Path(__file__).parent.parent


class ReportGenerator:
    """Gera relatórios em múltiplos formatos a partir de dados de auditoria."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_all(
        self,
        audit_data: Dict[str, Any],
        output_dir: Path,
        audit_id: str = "audit",
    ) -> Dict[str, Path]:
        """Gera todos os formatos de relatório."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        
        # HTML navegável
        paths["html"] = self._generate_html(audit_data, output_dir, audit_id)
        
        # Markdown executivo
        paths["markdown_executive"] = self._generate_markdown_executive(audit_data, output_dir, audit_id)
        
        # Markdown técnico
        paths["markdown_technical"] = self._generate_markdown_technical(audit_data, output_dir, audit_id)
        
        # JSON bruto
        paths["json"] = self._save_json(audit_data, output_dir, audit_id)
        
        logger.info(f"Relatórios gerados em: {output_dir}")
        return paths

    def _generate_html(self, data: Dict, out_dir: Path, audit_id: str) -> Path:
        template = self.env.get_template("report_template.html")
        
        # Prepara dados para template
        summary = self._compute_summary(data)
        top_violations = self._get_top_violations(data, limit=10)
        risks = self._get_legal_risks(data)
        actions = self._generate_action_plan(data)
        
        today = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        html = template.render(
            data=data,
            summary=summary,
            top_violations=top_violations,
            risks=risks,
            actions=actions,
            today=today,
            audit_id=audit_id,
            compliance_pct=summary.get("compliance_pct", 0),
        )
        
        out_path = out_dir / f"{audit_id}_report.html"
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def _generate_markdown_executive(self, data: Dict, out_dir: Path, audit_id: str) -> Path:
        summary = self._compute_summary(data)
        top = self._get_top_violations(data, limit=5)
        
        lines = [
            f"# Relatório Executivo de Acessibilidade — {data.get('url', 'N/A')}",
            "",
            f"**Audit ID:** {audit_id}  ",
            f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}  ",
            f"**Escopo:** {summary.get('urls_tested', 0)} páginas  ",
            "",
            "## 📊 Resumo",
            f"- Violações totais: **{summary.get('total_violations', 0)}**",
            f"- Nível A: **{summary.get('by_level', {}).get('A', 0)}**",
            f"- Nível AA: **{summary.get('by_level', {}).get('AA', 0)}**",
            f"- Conformidade WCAG 2.2 AA: **{summary.get('compliance_pct', 0)}%**",
            f"- Cobertura e-MAG 3.1: **{summary.get('emag_coverage', 0)*100:.0f}%**",
            "",
            "## 🚨 Top 5 Violações",
        ]
        
        for i, v in enumerate(top, 1):
            lines.append(f"{i}. **{v['name']}** (WCAG {v['wcag']}, {v['level']}) — {v['pages']} páginas — *{v['impact']}*")
        
        lines.extend([
            "",
            "## 📋 Próximos Passos",
            "1. Corrigir violações nível A (bloqueadores legais)",
            "2. Corrigir violações nível AA (risco de processo)",
            "3. Completar itens manuais do checklist e-MAG",
            "4. Re-auditoria após correções",
        ])
        
        out_path = out_dir / f"{audit_id}_executive.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def _generate_markdown_technical(self, data: Dict, out_dir: Path, audit_id: str) -> Path:
        summary = self._compute_summary(data)
        
        lines = [
            f"# Relatório Técnico de Acessibilidade — {data.get('url', 'N/A')}",
            "",
            f"**Audit ID:** {audit_id}",
            f"**Data:** {datetime.now().isoformat()}",
            f"**URL base:** {data.get('url')}",
            f"**Páginas testadas:** {summary.get('urls_tested', 0)}",
            "",
            "## Configuração da Auditoria",
            f"- Ferramentas: axe-core, pa11y, Lighthouse CI",
            f"- Níveis: WCAG 2.1/2.2 A + AA",
            f"- Checklist: e-MAG 3.1",
            f"- Profundidade crawl: {data.get('config', {}).get('depth', 3)}",
            "",
            "## Violações por Ferramenta",
        ]
        
        # Agrupa por ferramenta
        for url, results in data.get("auto_results", {}).items():
            lines.append(f"\n### {url}")
            for tool, tool_data in results.items():
                if "error" in tool_data:
                    lines.append(f"- **{tool}:** ERRO — {tool_data['error']}")
                    continue
                violations = tool_data.get("violations", [])
                if violations:
                    lines.append(f"- **{tool}:** {len(violations)} violações")
                    for v in violations[:3]:
                        lines.append(f"  - {v.get('id', 'N/A')}: {v.get('description', 'Sem descrição')}")
                else:
                    lines.append(f"- **{tool}:** ✅ Passou")
        
        # Testes manuais
        lines.append("\n## Testes Manuais")
        manual = data.get("manual_results", {})
        
        if "contrast" in manual:
            lines.append("\n### Contraste")
            for url, c in manual["contrast"].items():
                if "error" in c:
                    lines.append(f"- {url}: ERRO — {c['error']}")
                else:
                    lines.append(f"- {url}: {c.get('passed', 0)} OK, {c.get('failed', 0)} falharam")
        
        if "keyboard" in manual:
            k = manual["keyboard"]
            if "error" in k:
                lines.append(f"\n### Teclado: ERRO — {k['error']}")
            else:
                lines.append(f"\n### Teclado")
                lines.append(f"- Tab stops: {k.get('tab_stops', 0)}")
                lines.append(f"- Skip links visíveis: {k.get('has_skip_link', False)}")
                lines.append(f"- Focus visible issues: {len(k.get('focus_visible_issues', []))}")
                lines.append(f"- Keyboard traps: {len(k.get('keyboard_traps', []))}")
        
        if "emag" in manual:
            e = manual["emag"]
            if "error" in e:
                lines.append(f"\n### e-MAG: ERRO — {e['error']}")
            else:
                lines.append(f"\n### Checklist e-MAG 3.1")
                lines.append(f"- Itens totais: {e.get('total_items', 0)}")
                lines.append(f"- Passaram: {e.get('passed', 0)}")
                lines.append(f"- Falharam: {e.get('failed', 0)}")
                lines.append(f"- Manuais: {e.get('manual', 0)}")
        
        out_path = out_dir / f"{audit_id}_technical.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def _save_json(self, data: Dict, out_dir: Path, audit_id: str) -> Path:
        out_path = out_dir / f"{audit_id}_raw.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

    def _compute_summary(self, data: Dict) -> Dict:
        """Calcula resumo agregado."""
        total_violations = 0
        by_level = {"A": 0, "AA": 0, "AAA": 0}
        urls_tested = len(data.get("auto_results", {}))
        
        for url, results in data.get("auto_results", {}).items():
            for tool, tool_data in results.items():
                if "error" in tool_data:
                    continue
                for v in tool_data.get("violations", []):
                    total_violations += 1
                    level = v.get("impact", "").upper()
                    if level in by_level:
                        by_level[level] += 1
        
        # Estimativa de conformidade
        compliance_pct = max(0, 100 - (total_violations * 2))
        
        # e-MAG coverage
        emag = data.get("manual_results", {}).get("emag", {})
        emag_coverage = 0
        if emag and "error" not in emag:
            total = emag.get("total_items", 1)
            passed = emag.get("passed", 0)
            emag_coverage = passed / total if total > 0 else 0
        
        return {
            "total_violations": total_violations,
            "by_level": by_level,
            "urls_tested": urls_tested,
            "compliance_pct": compliance_pct,
            "emag_coverage": emag_coverage,
        }

    def _get_top_violations(self, data: Dict, limit: int = 10) -> List[Dict]:
        """Agrega violações por regra."""
        violations_map = {}
        
        for url, results in data.get("auto_results", {}).items():
            for tool, tool_data in results.items():
                if "error" in tool_data:
                    continue
                for v in tool_data.get("violations", []):
                    rule_id = v.get("id", "unknown")
                    if rule_id not in violations_map:
                        violations_map[rule_id] = {
                            "name": v.get("description", rule_id),
                            "wcag": v.get("tags", ["WCAG"])[0] if v.get("tags") else "WCAG",
                            "level": v.get("impact", "unknown").upper(),
                            "impact": v.get("impact", "moderate"),
                            "pages": set(),
                            "fix": self._get_fix_suggestion(rule_id),
                        }
                    violations_map[rule_id]["pages"].add(url)
        
        # Ordena por número de páginas afetadas
        sorted_violations = sorted(
            violations_map.values(),
            key=lambda x: len(x["pages"]),
            reverse=True,
        )
        
        for v in sorted_violations:
            v["pages"] = len(v["pages"])
        
        return sorted_violations[:limit]

    def _get_legal_risks(self, data: Dict) -> List[Dict]:
        """Identifica riscos jurídicos baseados em violações A/AA."""
        risks = []
        summary = self._compute_summary(data)
        
        if summary["by_level"].get("A", 0) > 0:
            risks.append({
                "law": "LBI 10.098/2000 + Decreto 5.296/2004",
                "description": f"{summary['by_level']['A']} violações nível A — barreiras absolutas que impedem acesso. Risco de ação civil pública e multa diária."
            })
        
        if summary["by_level"].get("AA", 0) > 0:
            risks.append({
                "law": "e-MAG 3.1 (Gov.br) + LGPD Art. 9º",
                "description": f"{summary['by_level']['AA']} violações nível AA — descumpre padrão federal obrigatório. Impede contratações públicas e expõe a sanções administrativas."
            })
        
        return risks

    def _generate_action_plan(self, data: Dict) -> List[Dict]:
        """Gera plano de ação priorizado."""
        actions = []
        top = self._get_top_violations(data, limit=5)
        
        for i, v in enumerate(top):
            priority = "🔴 Crítica" if v["level"] == "A" else "🟡 Alta"
            actions.append({
                "priority": priority,
                "action": f"Corrigir '{v['name']}' em {v['pages']} página(s)",
                "owner": "Dev Frontend",
                "deadline": "Sprint atual" if v["level"] == "A" else "Próxima sprint",
                "criterion": f"WCAG {v['wcag']} ({v['level']})",
            })
        
        # Ações manuais
        manual = data.get("manual_results", {})
        if manual.get("emag", {}).get("manual", 0) > 0:
            actions.append({
                "priority": "🟡 Alta",
                "action": f"Completar {manual['emag']['manual']} itens manuais do checklist e-MAG",
                "owner": "Equipe Acessibilidade",
                "deadline": "2 semanas",
                "criterion": "e-MAG 3.1 (obrigatório Gov.br)",
            })
        
        return actions

    def _get_fix_suggestion(self, rule_id: str) -> str:
        fixes = {
            "image-alt": "Adicionar atributo alt descritivo em <img>",
            "label": "Associar <label for> ou aria-label em inputs",
            "color-contrast": "Ajustar cores para ratio ≥ 4.5:1 (AA) ou 3:1 (large text/UI)",
            "keyboard": "Garantir tabindex e handlers keydown/enter/space",
            "focus-visible": "Adicionar :focus-visible { outline: 2px solid }",
            "skip-link": "Adicionar <a href='#main' class='skip-link'>Pular para conteúdo</a>",
            "heading-order": "Corrigir hierarquia h1→h2→h3 sem pular níveis",
            "aria-required-attr": "Adicionar atributos ARIA obrigatórios para o role",
            "html-has-lang": "Adicionar lang='pt-BR' no <html>",
            "button-name": "Dar nome acessível a botões (texto, aria-label, ou aria-labelledby)",
        }
        return fixes.get(rule_id, "Consultar documentação WCAG para técnica de correção")


def generate_reports(audit_data: Dict[str, Any], output_dir: Path):
    """Função principal chamada pelo audit.py."""
    generator = ReportGenerator(BASE_DIR / "templates")
    audit_id = audit_data.get("audit_id", "audit")
    return generator.generate_all(audit_data, output_dir, audit_id)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Gerador de relatórios de acessibilidade")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Arquivo JSON de auditoria")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Diretório de saída")
    args = parser.parse_args()
    
    with open(args.input) as f:
        audit_data = json.load(f)
    
    paths = generate_reports(audit_data, args.output)
    print(f"Relatórios gerados:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")