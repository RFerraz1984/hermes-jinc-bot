#!/usr/bin/env python3
"""
Comparador de auditorias - detecção de regressões e melhorias.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditComparator:
    """Compara duas auditorias e detecta regressões/melhorias."""
    
    def __init__(self, before_path: Path, after_path: Path):
        self.before_path = Path(before_path)
        self.after_path = Path(after_path)
        
        with open(before_path) as f:
            self.before = json.load(f)
        with open(after_path) as f:
            self.after = json.load(f)
    
    def compare(self) -> Dict[str, Any]:
        """Compara auditorias e retorna diff."""
        logger.info(f"Comparando {self.before_path} -> {self.after_path}")
        
        # Violações antes/depois
        before_violations = self._normalize_violations(self.before.get("violations", []))
        after_violations = self._normalize_violations(self.after.get("violations", []))
        
        # Detecta mudanças
        new_violations = after_violations - before_violations
        fixed_violations = before_violations - after_violations
        persistent = before_violations & after_violations
        
        # Resumo
        result = {
            "before_audit": {
                "audit_id": self.before.get("audit_id"),
                "timestamp": self.before.get("timestamp"),
                "total_violations": len(before_violations),
            },
            "after_audit": {
                "audit_id": self.after.get("audit_id"),
                "timestamp": self.after.get("timestamp"),
                "total_violations": len(after_violations),
            },
            "summary": {
                "new_violations": len(new_violations),
                "fixed_violations": len(fixed_violations),
                "persistent_violations": len(persistent),
                "net_change": len(after_violations) - len(before_violations),
            },
            "details": {
                "new": sorted(list(new_violations)),
                "fixed": sorted(list(fixed_violations)),
                "persistent": sorted(list(persistent)),
            },
            "emag_comparison": self._compare_emag(),
            "score_changes": self._compare_scores(),
        }
        
        return result
    
    def _normalize_violations(self, violations: List[Dict]) -> set:
        """Normaliza violações para conjunto comparável."""
        normalized = set()
        for v in violations:
            # Cria chave única: regra + seletor + URL
            key_parts = [
                v.get("id", v.get("wcag", "")),
                v.get("pages", [{}])[0].get("selector", "") if v.get("pages") else "",
                v.get("pages", [{}])[0].get("url", "") if v.get("pages") else "",
            ]
            normalized.add("|".join(key_parts))
        return normalized
    
    def _compare_emag(self) -> Dict[str, Any]:
        """Compara cobertura e-MAG."""
        before_emag = self.before.get("emag_checklist", {})
        after_emag = self.after.get("emag_checklist", {})
        
        before_items = {item["id"]: item for item in before_emag.get("items", [])}
        after_items = {item["id"]: item for item in after_emag.get("items", [])}
        
        improved = []
        regressed = []
        
        for item_id, after_item in after_items.items():
            before_item = before_items.get(item_id)
            if before_item:
                before_status = before_item.get("status")
                after_status = after_item.get("status")
                
                if before_status == "fail" and after_status == "pass":
                    improved.append({
                        "id": item_id,
                        "name": after_item.get("name"),
                        "before": before_status,
                        "after": after_status,
                    })
                elif before_status == "pass" and after_status == "fail":
                    regressed.append({
                        "id": item_id,
                        "name": after_item.get("name"),
                        "before": before_status,
                        "after": after_status,
                    })
        
        return {
            "improved": improved,
            "regressed": regressed,
            "before_coverage": before_emag.get("summary", {}).get("coverage", 0),
            "after_coverage": after_emag.get("summary", {}).get("coverage", 0),
            "coverage_change": after_emag.get("summary", {}).get("coverage", 0) - before_emag.get("summary", {}).get("coverage", 0),
        }
    
    def _compare_scores(self) -> Dict[str, Any]:
        """Compara scores Lighthouse/pa11y se disponíveis."""
        # Placeholder - implementar se tiver dados de score
        return {
            "lighthouse_a11y_before": None,
            "lighthouse_a11y_after": None,
            "pa11y_errors_before": None,
            "pa11y_errors_after": None,
        }
    
    def generate_report(self, output_path: Path) -> str:
        """Gera relatório de diff em Markdown."""
        diff = self.compare()
        
        lines = [
            f"# 📊 Relatório de Regressão de Acessibilidade",
            f"**Antes:** {diff['before_audit']['audit_id']} ({diff['before_audit']['timestamp']})",
            f"**Depois:** {diff['after_audit']['audit_id']} ({diff['after_audit']['timestamp']})",
            f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            "## 📈 Resumo",
            "",
            f"| Métrica | Antes | Depois | Mudança |",
            f"|---------|-------|--------|---------|",
            f"| Violações totais | {diff['before_audit']['total_violations']} | {diff['after_audit']['total_violations']} | {diff['summary']['net_change']:+d} |",
            f"| Novas violações | — | {diff['summary']['new_violations']} | +{diff['summary']['new_violations']} |",
            f"| Violações corrigidas | {diff['summary']['fixed_violations']} | — | -{diff['summary']['fixed_violations']} |",
            f"| Persistentes | {diff['summary']['persistent_violations']} | {diff['summary']['persistent_violations']} | = |",
            "",
            "## 🚨 Regressões (Novas Violações)",
        ]
        
        if diff["details"]["new"]:
            for v in diff["details"]["new"]:
                lines.append(f"- `{v}`")
        else:
            lines.append("*Nenhuma nova violação detectada ✅*")
        
        lines.extend(["", "## ✅ Correções (Violações Corrigidas)", ""])
        
        if diff["details"]["fixed"]:
            for v in diff["details"]["fixed"]:
                lines.append(f"- `{v}`")
        else:
            lines.append("*Nenhuma violação corrigida*")
        
        lines.extend(["", "## 📋 e-MAG 3.1 - Mudanças", ""])
        
        emag = diff["emag_comparison"]
        lines.append(f"- Cobertura antes: {emag['before_coverage']:.1f}%")
        lines.append(f"- Cobertura depois: {emag['after_coverage']:.1f}%")
        lines.append(f"- Mudança: {emag['coverage_change']:+.1f}%")
        
        if emag["improved"]:
            lines.append("\n### ✅ Itens Melhorados (fail → pass)")
            for item in emag["improved"]:
                lines.append(f"- [{item['id']}] {item['name']}")
        
        if emag["regressed"]:
            lines.append("\n### ❌ Itens Regrididos (pass → fail)")
            for item in emag["regressed"]:
                lines.append(f"- [{item['id']}] {item['name']}")
        
        lines.extend(["", "## ⚠️ Violações Persistentes", ""])
        
        if diff["details"]["persistent"]:
            lines.append(f"*{len(diff['details']['persistent'])} violações não resolvidas:*")
            for v in sorted(diff["details"]["persistent"])[:20]:
                lines.append(f"- `{v}`")
        else:
            lines.append("*Nenhuma violação persistente ✅*")
        
        report = "\n".join(lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        return report


async def compare_audits(
    before: Path,
    after: Path,
    output: Optional[Path] = None,
    fail_on_regression: bool = False,
) -> Dict[str, Any]:
    """Função principal para CLI."""
    comparator = AuditComparator(before, after)
    diff = comparator.compare()
    
    if output:
        comparator.generate_report(output)
        logger.info(f"Relatório de diff salvo em: {output}")
    
    # Print summary
    print(f"\n📊 Comparação: {before.name} -> {after.name}")
    print(f"  Antes: {diff['before_audit']['total_violations']} violações")
    print(f"  Depois: {diff['after_audit']['total_violations']} violações")
    print(f"  Mudança líquida: {diff['summary']['net_change']:+d}")
    print(f"  Novas: {diff['summary']['new_violations']}")
    print(f"  Corrigidas: {diff['summary']['fixed_violations']}")
    print(f"  Persistentes: {diff['summary']['persistent_violations']}")
    print(f"  e-MAG cobertura: {diff['emag_comparison']['before_coverage']:.1f}% -> {diff['emag_comparison']['after_coverage']:.1f}% ({diff['emag_comparison']['coverage_change']:+.1f}%)")
    
    if fail_on_regression and diff["summary"]["new_violations"] > 0:
        print("\n❌ REGRESSÃO DETECTADA - Novas violações encontradas!")
        return {"diff": diff, "regression": True}
    
    return {"diff": diff, "regression": False}


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Compara duas auditorias de acessibilidade")
    parser.add_argument("before", type=Path, help="Arquivo JSON da auditoria anterior")
    parser.add_argument("after", type=Path, help="Arquivo JSON da auditoria atual")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo Markdown de saída")
    parser.add_argument("--fail-on-regression", action="store_true", help="Exit code 1 se houver regressão")
    args = parser.parse_args()
    
    result = await compare_audits(args.before, args.after, args.output, args.fail_on_regression)
    
    if args.fail_on_regression and result.get("regression"):
        exit(1)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())