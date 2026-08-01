#!/usr/bin/env python3
"""
Checklist e-MAG 3.1 - verificação semi-automatizada dos itens obrigatórios.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


# Itens do checklist e-MAG 3.1
EMAG_ITEMS = [
    # 1. Alternativas Textuais
    {
        "id": "1.1",
        "name": "Imagens com alternativa textual relevante",
        "wcag": "1.1.1",
        "level": "A",
        "automated": True,
        "axe_rule": "image-alt",
        "manual_check": False,
        "description": "Todas imagens devem ter alt text relevante (não 'imagem', 'figura', nome do arquivo)",
    },
    {
        "id": "1.2",
        "name": "Gráficos/complexos com descrição longa",
        "wcag": "1.1.1",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Verificar se gráficos, mapas, infográficos têm descrição longa (longdesc, aria-describedby ou texto adjacente)",
    },
    {
        "id": "1.3",
        "name": "CAPTCHA com alternativa acessível",
        "wcag": "1.1.1",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "CAPTCHA deve ter alternativa de áudio ou lógica acessível",
    },
    
    # 2. Tempo e Navegação
    {
        "id": "2.1",
        "name": "Skip link (pular para conteúdo principal) visível no foco",
        "wcag": "2.4.1",
        "level": "A",
        "automated": True,
        "axe_rule": "skip-link",
        "manual_check": False,
        "description": "Link 'Pular para conteúdo principal' deve aparecer no primeiro Tab",
    },
    {
        "id": "2.2",
        "name": "Ordem de tabulação lógica",
        "wcag": "2.4.3",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Tab por toda a página - ordem visual = ordem DOM",
    },
    {
        "id": "2.3",
        "name": "Foco visível em todos elementos interativos",
        "wcag": "2.4.7",
        "level": "AA",
        "automated": True,
        "axe_rule": "focus-visible",
        "manual_check": False,
        "description": "Links, botões, inputs devem ter outline/box-shadow visível no :focus",
    },
    {
        "id": "2.4",
        "name": "Sem armadilhas de teclado (modais, carrosséis)",
        "wcag": "2.1.2",
        "level": "A",
        "automated": True,
        "axe_rule": "keyboard-trap",
        "manual_check": False,
        "description": "Modais prendem foco, Esc fecha, Tab circular; carrosséis saem com Tab",
    },
    {
        "id": "2.5",
        "name": "Tempo ajustável (auto-refresh, timeouts)",
        "wcag": "2.2.1",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Verificar auto-refresh, carrosséis auto-play, timeouts sem opção de pausar/estender",
    },
    
    # 3. Legibilidade e Compreensão
    {
        "id": "3.1",
        "name": "Idioma da página definido",
        "wcag": "3.1.1",
        "level": "A",
        "automated": True,
        "axe_rule": "html-has-lang",
        "manual_check": False,
        "description": "html lang='pt-br' presente",
    },
    {
        "id": "3.2",
        "name": "Mudanças de idioma marcadas",
        "wcag": "3.1.2",
        "level": "AA",
        "automated": True,
        "axe_rule": "html-lang-valid",
        "manual_check": False,
        "description": "Trechos em outro idioma devem ter lang='en' etc.",
    },
    {
        "id": "3.3",
        "name": "Abreviações/siglas com expansão",
        "wcag": "3.1.4",
        "level": "AAA",
        "automated": False,
        "manual_check": True,
        "manual_test": "Verificar <abbr title='...'> ou primeira ocorrência com expansão",
    },
    {
        "id": "3.4",
        "name": "Nível de leitura adequado (português claro)",
        "wcag": "3.1.5",
        "level": "AAA",
        "automated": False,
        "manual_check": True,
        "manual_test": "Avaliar clareza textual, frases curtas, voz ativa, sem jargão desnecessário",
    },
    
    # 4. Previsibilidade e Consistência
    {
        "id": "4.1",
        "name": "Navegação consistente",
        "wcag": "3.2.3",
        "level": "AA",
        "automated": False,
        "manual_check": True,
        "manual_test": "Menu, busca, rodapé na mesma ordem em todas páginas",
    },
    {
        "id": "4.2",
        "name": "Identificação consistente",
        "wcag": "3.2.4",
        "level": "AA",
        "automated": False,
        "manual_check": True,
        "manual_test": "Mesmo rótulo = mesma função; ícones iguais = mesma ação",
    },
    {
        "id": "4.3",
        "name": "Mudança só sob solicitação",
        "wcag": "3.2.2",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Não abrir nova janela, redirecionar, submeter formulário sem ação do usuário",
    },
    
    # 5. Ajuda à Entrada de Dados
    {
        "id": "5.1",
        "name": "Rótulos associados (label for, aria-label, aria-labelledby)",
        "wcag": "3.3.2",
        "level": "A",
        "automated": True,
        "axe_rule": "label",
        "manual_check": False,
        "description": "Todos inputs, selects, textareas devem ter label associado",
    },
    {
        "id": "5.2",
        "name": "Instruções claras antes dos campos",
        "wcag": "3.3.2",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Placeholder não substitui label; instruções visíveis e claras",
    },
    {
        "id": "5.3",
        "name": "Erros identificados + descritos + sugestão de correção",
        "wcag": "3.3.1, 3.3.3",
        "level": "A",
        "automated": True,
        "axe_rule": "error-message",
        "manual_check": False,
        "description": "Validação deve mostrar erro, descrever problema e sugerir correção",
    },
    {
        "id": "5.4",
        "name": "Prevenção de erros graves (confirmação, revisão, desfazer)",
        "wcag": "3.3.4, 3.3.6",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Ações irreversíveis (exclusão, pagamento) devem ter confirmação ou revisão",
    },
    
    # 6. Compatibilidade
    {
        "id": "6.1",
        "name": "HTML válido (W3C validator)",
        "wcag": "4.1.1",
        "level": "A",
        "automated": True,
        "axe_rule": "duplicate-id",
        "manual_check": False,
        "description": "Sem IDs duplicados, tags fechadas corretamente, atributos válidos",
    },
    {
        "id": "6.2",
        "name": "ARIA usado corretamente (não sobrescreve semântica nativa)",
        "wcag": "4.1.2",
        "level": "A",
        "automated": True,
        "axe_rule": "aria-allowed-attr,aria-required-attr,aria-valid-attr-value",
        "manual_check": False,
        "description": "Roles, states, properties ARIA válidos e necessários",
    },
    {
        "id": "6.3",
        "name": "Nome, função, valor expostos",
        "wcag": "4.1.2",
        "level": "A",
        "automated": True,
        "axe_rule": "aria-required-attr,aria-valid-attr-value",
        "manual_check": False,
        "description": "Componentes customizados expõem name, role, value via ARIA",
    },
    
    # 7. Específicos GOV.BR
    {
        "id": "7.1",
        "name": "Barra de identidade GOV.BR funcional",
        "wcag": "",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Barra superior com logo, busca, acesso à conta, links de acessibilidade",
    },
    {
        "id": "7.2",
        "name": "Rodapé padronizado com links de acessibilidade",
        "wcag": "",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Links: Acessibilidade, Mapa do site, Contato, Privacidade, Redes sociais",
    },
    {
        "id": "7.3",
        "name": "Mapa do site acessível",
        "wcag": "",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Link no rodapé -> página com estrutura hierárquica navegável por teclado",
    },
    {
        "id": "7.4",
        "name": "Declaração de acessibilidade pública (link no rodapé)",
        "wcag": "",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Link 'Acessibilidade' no rodapé -> página com declaração, contato para barreiras, data",
    },
    {
        "id": "7.5",
        "name": "Canal de relato de barreiras (formulário/e-mail)",
        "wcag": "",
        "level": "A",
        "automated": False,
        "manual_check": True,
        "manual_test": "Formulário ou e-mail acessível para reportar problemas de acessibilidade",
    },
]


async def run_emag_checklist(
    url: str,
    output: Optional[Path] = None,
    include_manual: bool = True,
) -> Dict[str, Any]:
    """Executa checklist e-MAG 3.1 na URL."""
    logger.info(f"Executando checklist e-MAG: {url}")
    
    results = {
        "url": url,
        "items": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "manual": 0,
            "error": 0,
            "coverage": 0.0,
        },
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            for item in EMAG_ITEMS:
                result = await check_item(page, item)
                results["items"].append(result)
                
                # Atualiza summary
                results["summary"]["total"] += 1
                status = result.get("status")
                if status == "pass":
                    results["summary"]["passed"] += 1
                elif status == "fail":
                    results["summary"]["failed"] += 1
                elif status == "manual":
                    results["summary"]["manual"] += 1
                elif status == "error":
                    results["summary"]["error"] += 1
            
            # Calcula cobertura (automated + manual avaliados)
            evaluated = results["summary"]["passed"] + results["summary"]["failed"]
            total_auto = sum(1 for i in EMAG_ITEMS if i["automated"])
            results["summary"]["coverage"] = evaluated / total_auto if total_auto > 0 else 0.0
            
        finally:
            await browser.close()
    
    if output:
        with open(output, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Checklist salvo em: {output}")
    
    return results


async def check_item(page, item: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica um item do checklist."""
    result = {
        "id": item["id"],
        "name": item["name"],
        "wcag": item["wcag"],
        "automated": item["automated"],
        "status": "pending",
        "evidence": "",
    }
    
    try:
        if item["automated"] and "axe_rule" in item:
            # Usa axe-core para verificação automatizada
            axe_result = await page.evaluate(f"""
                () => {{
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js';
                    return new Promise((resolve) => {{
                        script.onload = async () => {{
                            const results = await axe.run(document, {{
                                runOnly: {{ type: 'rule', values: ['{item['axe_rule']}'] }},
                                resultTypes: ['violations']
                            }});
                            resolve(results);
                        }};
                        script.onerror = () => resolve({{ error: 'axe load failed' }});
                        document.head.appendChild(script);
                    }})
            """)
            
            if axe_result.get("error"):
                result["status"] = "error"
                result["evidence"] = f"axe-core error: {axe_result['error']}"
            elif axe_result.get("violations") and len(axe_result["violations"]) > 0:
                result["status"] = "fail"
                v = axe_result["violations"][0]
                result["evidence"] = f"{v.get('description', '')} - {len(v.get('nodes', []))} ocorrências"
            else:
                result["status"] = "pass"
                result["evidence"] = "Nenhuma violação encontrada"
                
        elif item["manual_check"] and include_manual:
            # Para itens manuais, marca como 'manual' - requer revisão humana
            result["status"] = "manual"
            result["evidence"] = item.get("manual_test", "Requer verificação manual")
            result["manual_test"] = item.get("manual_test", "")
            
        else:
            # Verificações semi-automatizadas (ex: skip link visível no foco)
            if item["id"] == "2.1":
                # Skip link
                skip_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href^="#"]');
                        const skips = [];
                        links.forEach(link => {
                            const text = link.textContent.trim().toLowerCase();
                            if (text.includes('pular') || text.includes('skip') || text.includes('conteúdo')) {
                                const style = getComputedStyle(link);
                                skips.push({
                                    text: link.textContent.trim(),
                                    href: link.getAttribute('href'),
                                    visible: style.display !== 'none' && style.visibility !== 'hidden',
                                    focusable: link.tabIndex >= 0,
                                });
                            }
                        });
                        return skips;
                    }
                """)
                if skip_links and any(s["visible"] and s["focusable"] for s in skip_links):
                    result["status"] = "pass"
                    result["evidence"] = f"Skip link encontrado: '{skip_links[0]['text']}' visível no foco"
                else:
                    result["status"] = "fail"
                    result["evidence"] = "Skip link não encontrado ou não visível no foco"
                    
            elif item["id"] == "2.3":
                # Foco visível - verifica se elementos têm focus style
                focus_check = await page.evaluate("""
                    () => {
                        const interactive = document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"]), [role="button"], [role="link"]');
                        let withoutFocus = 0;
                        let total = 0;
                        interactive.forEach(el => {
                            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                                total++;
                                const focusStyle = getComputedStyle(el, ':focus');
                                const focusVisibleStyle = getComputedStyle(el, ':focus-visible');
                                const outline = focusStyle.outline || focusVisibleStyle.outline;
                                const boxShadow = focusStyle.boxShadow || focusVisibleStyle.boxShadow;
                                const border = focusStyle.border || focusVisibleStyle.border;
                                if (outline === 'none' && boxShadow === 'none' && border === '0px') {
                                    withoutFocus++;
                                }
                            }
                        });
                        return { total, withoutFocus };
                    }
                """)
                if focus_check["withoutFocus"] > 0:
                    result["status"] = "fail"
                    result["evidence"] = f"{focus_check['withoutFocus']} de {focus_check['total']} elementos sem estilo de foco visível"
                else:
                    result["status"] = "pass"
                    result["evidence"] = f"Todos {focus_check['total']} elementos interativos têm foco visível"
                    
            elif item["id"] == "2.4":
                # Keyboard trap
                trap_check = await page.evaluate("""
                    () => {
                        const modals = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, .dialog, [aria-modal="true"]');
                        let traps = 0;
                        modals.forEach(modal => {
                            const style = getComputedStyle(modal);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                const focusable = modal.querySelectorAll('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
                                if (focusable.length === 0) {
                                    traps++;
                                }
                            }
                        });
                        return { traps, modalCount: modals.length };
                    }
                """)
                if trap_check["traps"] > 0:
                    result["status"] = "fail"
                    result["evidence"] = f"{trap_check['traps']} modal(ais) sem elementos focáveis ({trap_check['modalCount']} modal(ais) aberto(s))"
                else:
                    result["status"] = "pass"
                    result["evidence"] = f"Nenhuma armadilha de teclado detectada ({trap_check['modalCount']} modal(ais) verificado(s))"
                    
            elif item["id"] == "3.1":
                # Idioma da página
                lang = await page.evaluate("() => document.documentElement.lang")
                if lang and lang.lower().startswith("pt"):
                    result["status"] = "pass"
                    result["evidence"] = f"html lang='{lang}' presente"
                else:
                    result["status"] = "fail"
                    result["evidence"] = f"html lang='{lang or 'ausente'}' - deve ser 'pt-br'"
                    
            elif item["id"] == "4.1":
                # HTML válido - IDs duplicados
                dup_check = await page.evaluate("""
                    () => {
                        const ids = new Map();
                        document.querySelectorAll('[id]').forEach(el => {
                            if (el.id) ids.set(el.id, (ids.get(el.id) || 0) + 1);
                        });
                        const dups = Array.from(ids.entries()).filter(([_, count]) => count > 1);
                        return { duplicates: dups.length, details: dups.slice(0, 10) };
                    }
                """)
                if dup_check["duplicates"] > 0:
                    result["status"] = "fail"
                    result["evidence"] = f"{dup_check['duplicates']} IDs duplicados: {dup_check['details']}"
                else:
                    result["status"] = "pass"
                    result["evidence"] = "Nenhum ID duplicado encontrado"
                    
            elif item["id"] == "6.2":
                # ARIA usado corretamente
                aria_check = await page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('[role], [aria-*]');
                        let issues = 0;
                        elements.forEach(el => {
                            const role = el.getAttribute('role');
                            const attrs = Array.from(el.attributes).filter(a => a.name.startsWith('aria-'));
                            // Verifica role válido
                            if (role && !['alert','alertdialog','application','article','banner','button','cell','checkbox','columnheader','combobox','complementary','contentinfo','definition','dialog','directory','document','feed','figure','form','grid','gridcell','group','heading','img','link','list','listbox','listitem','log','main','marquee','math','menu','menubar','menuitem','menuitemcheckbox','menuitemradio','navigation','none','note','option','presentation','progressbar','radio','radiogroup','region','row','rowgroup','rowheader','scrollbar','search','searchbox','separator','slider','spinbutton','status','switch','tab','table','tablist','tabpanel','term','textbox','timer','toolbar','tooltip','tree','treegrid','treeitem'].includes(role)) {
                                issues++;
                            }
                        });
                        return { checked: elements.length, issues };
                    }
                """)
                if aria_check["issues"] > 0:
                    result["status"] = "fail"
                    result["evidence"] = f"{aria_check['issues']} elementos com role/ARIA inválido de {aria_check['checked']} verificados"
                else:
                    result["status"] = "pass"
                    result["evidence"] = f"ARIA válido em {aria_check['checked']} elementos"
            else:
                result["status"] = "skip"
                result["evidence"] = "Verificação não implementada"
                
    except Exception as e:
        logger.warning(f"Erro verificando item {item['id']}: {e}")
        result["status"] = "error"
        result["evidence"] = f"Erro: {str(e)}"
    
    return result


async def run_emag_checklist_cli(
    url: str,
    output: Optional[Path] = None,
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Executando checklist e-MAG 3.1: {url}")
    
    result = await run_emag_checklist(url, output)
    
    print(f"\n📋 Checklist e-MAG 3.1 - {url}")
    print(f"  Total: {result['summary']['total']}")
    print(f"  ✅ Passou: {result['summary']['passed']}")
    print(f"  ❌ Falhou: {result['summary']['failed']}")
    print(f"  📝 Manual: {result['summary']['manual']}")
    print(f"  ⚠️ Erro: {result['summary']['error']}")
    print(f"  📊 Cobertura automática: {result['summary']['coverage']*100:.0f}%")
    
    for item in result["items"]:
        status_icon = {"pass": "✅", "fail": "❌", "manual": "📝", "error": "⚠️", "skip": "⏭️"}.get(item["status"], "❓")
        print(f"  {status_icon} [{item['id']}] {item['name']}: {item['evidence'][:80]}")
    
    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Checklist e-MAG 3.1")
    parser.add_argument("url", help="URL para auditar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    args = parser.parse_args()
    
    await run_emag_checklist_cli(args.url, args.output)


if __name__ == "__main__":
    asyncio.run(main())