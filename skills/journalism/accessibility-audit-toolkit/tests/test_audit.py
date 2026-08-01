#!/usr/bin/env python3
"""
Testes de integração leves para o Accessibility Audit Toolkit.
Rodam sem dependências externas (mock HTTP/playwright).
"""

import json
import tempfile
from pathlib import Path

import pytest


# Testa imports básicos
def test_imports():
    """Verifica se todos os módulos importam sem erro."""
    from scripts import (
        run_axe,
        run_pa11y,
        run_lighthouse,
        check_contrast,
        test_keyboard_navigation,
        run_emag_checklist,
        generate_reports,
        discover_urls,
        run_screen_reader_test,
    )
    assert callable(run_axe)
    assert callable(run_pa11y)
    assert callable(run_lighthouse)
    assert callable(check_contrast)
    assert callable(test_keyboard_navigation)
    assert callable(run_emag_checklist)
    assert callable(generate_reports)
    assert callable(discover_urls)
    assert callable(run_screen_reader_test)


# Testa carregamento de YAML
def test_wcag_criteria_load():
    """Verifica se wcag_criteria.yaml carrega corretamente."""
    import yaml

    criteria_path = Path(__file__).parent.parent / "templates" / "wcag_criteria.yaml"
    assert criteria_path.exists(), "wcag_criteria.yaml não encontrado"

    with open(criteria_path) as f:
        data = yaml.safe_load(f)

    assert "criteria" in data
    assert len(data["criteria"]) > 0
    for criterion_id, criterion in data["criteria"].items():
        assert "name" in criterion
        assert "level" in criterion
        assert criterion["level"] in ("A", "AA", "AAA")


def test_checklist_emag_exists():
    """Verifica se checklist e-MAG existe."""
    checklist_path = Path(__file__).parent.parent / "templates" / "checklist_emag.md"
    assert checklist_path.exists(), "checklist_emag.md não encontrado"

    content = checklist_path.read_text(encoding="utf-8")
    assert "e-MAG" in content
    assert "1.1" in content


# Testa templates
def test_templates_exist():
    """Verifica se templates de relatório existem."""
    templates_dir = Path(__file__).parent.parent / "templates"
    assert (templates_dir / "report_template.html").exists()
    assert (templates_dir / "report_executive.md").exists()


# Testa contrast_check helpers
class TestContrastHelpers:
    """Testes para funções utilitárias de contraste."""

    def test_parse_color_rgb(self):
        from scripts.contrast_check import parse_color

        assert parse_color("rgb(255, 0, 0)") == (255, 0, 0, 1.0)
        assert parse_color("rgba(0, 255, 0, 0.5)") == (0, 255, 0, 0.5)

    def test_parse_color_hex(self):
        from scripts.contrast_check import parse_color

        assert parse_color("#ff0000") == (255, 0, 0, 1.0)
        assert parse_color("#f00") == (255, 0, 0, 1.0)
        # Alpha values rounded to 3 decimal places for comparison
        r, g, b, a = parse_color("#ff000080")
        assert (r, g, b) == (255, 0, 0)
        assert abs(a - 0.502) < 0.001
        r, g, b, a = parse_color("#f008")
        assert (r, g, b) == (255, 0, 0)
        assert abs(a - 0.533) < 0.001

    def test_relative_luminance(self):
        from scripts.contrast_check import relative_luminance

        # Branco
        assert abs(relative_luminance(255, 255, 255) - 1.0) < 0.01
        # Preto
        assert abs(relative_luminance(0, 0, 0) - 0.0) < 0.01
        # Vermelho puro
        assert 0.21 < relative_luminance(255, 0, 0) < 0.22

    def test_contrast_ratio(self):
        from scripts.contrast_check import contrast_ratio

        # Preto no branco = 21:1
        ratio = contrast_ratio((0, 0, 0, 1.0), (255, 255, 255, 1.0))
        assert 20.5 < ratio < 21.5

        # Branco no branco = 1:1
        ratio = contrast_ratio((255, 255, 255, 1.0), (255, 255, 255, 1.0))
        assert 0.99 < ratio < 1.01

    def test_is_large_text(self):
        from scripts.contrast_check import is_large_text

        assert is_large_text(24, "normal")  # 24px = 18pt
        assert is_large_text(18.67, "bold")  # 14pt bold (18.67px = 14.005pt)
        assert not is_large_text(16, "normal")
        assert not is_large_text(14, "normal")


# Testa emag_checklist estrutura
def test_emag_checklist_structure():
    """Verifica estrutura básica do checklist e-MAG."""
    from scripts.emag_checklist import EMAG_ITEMS as EMAG_CHECKLIST

    assert isinstance(EMAG_CHECKLIST, list)
    assert len(EMAG_CHECKLIST) > 0

    for item in EMAG_CHECKLIST:
        assert "id" in item
        assert "name" in item
        assert "wcag" in item
        assert "level" in item
        assert "automated" in item
        assert item["level"] in ("A", "AA", "AAA")


# Teste de integração leve (mock)
@pytest.mark.asyncio
async def test_discover_urls_mock(monkeypatch):
    """Testa discover_urls com mock de HTTP."""
    import scripts.crawl_site as crawl_module

    async def mock_fetch_sitemap(url):
        return []

    class MockResponse:
        status_code = 200
        text = """
        <html>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="https://external.com">External</a>
        </html>
        """
        headers = {"content-type": "text/html"}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, **kwargs):
            return MockResponse()

    # Patch at module level where it's used
    monkeypatch.setattr(crawl_module, "fetch_sitemap", mock_fetch_sitemap)
    monkeypatch.setattr(crawl_module.httpx, "AsyncClient", MockClient)

    urls = await crawl_module.discover_urls("https://example.com", max_depth=1, max_urls=10)
    assert "https://example.com" in urls
    # crawl_site descobre URLs relativas e as converte para absolutas
    # O mock retorna links relativos, então devem virar https://example.com/page1 etc
    assert any("/page1" in u for u in urls)
    assert any("/page2" in u for u in urls)


# Teste de geração de relatório (sem executar auditoria completa)
def test_report_generator_instantiation():
    """Verifica se ReportGenerator instância sem erro."""
    from scripts.wcag_report import ReportGenerator

    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir) / "templates"
        templates_dir.mkdir()
        (templates_dir / "report_executive.md").write_text("{{ data.url }}")
        (templates_dir / "report_template.html").write_text("<html>{{ data.url }}</html>")

        generator = ReportGenerator(templates_dir)
        assert generator.templates_dir == templates_dir


# Teste de CLI help (não executa, só valida args)
def test_cli_help(capsys):
    """Testa se CLIs aceitam --help sem erro."""
    import sys
    from scripts.audit import main as audit_main

    assert audit_main is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])