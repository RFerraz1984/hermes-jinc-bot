"""
Accessibility Audit Toolkit - Scripts Package.

Orquestra auditorias completas de acessibilidade (WCAG 2.2 + e-MAG 3.1)
usando axe-core, pa11y, Lighthouse, Playwright e speech-dispatcher.
"""

__version__ = "0.2.0"

# Lazy imports to avoid dependency issues at package import time
# Use getattr(__import__('scripts.module'), 'function') or import inside functions


def __getattr__(name: str):
    """Lazy import for optional dependencies."""
    imports = {
        # axe
        "run_axe": ("scripts.axe_cli", "run_axe"),
        "run_axe_cli": ("scripts.axe_cli", "run_axe_cli"),
        # pa11y
        "run_pa11y": ("scripts.pa11y_cli", "run_pa11y"),
        "run_pa11y_cli": ("scripts.pa11y_cli", "run_pa11y_cli"),
        # lighthouse
        "run_lighthouse": ("scripts.lighthouse_cli", "run_lighthouse"),
        "run_lighthouse_cli": ("scripts.lighthouse_cli", "run_lighthouse_cli"),
        # contraste
        "check_contrast": ("scripts.contrast_check", "check_contrast"),
        "check_contrast_cli": ("scripts.contrast_check", "check_contrast_cli"),
        # teclado
        "test_keyboard_navigation": ("scripts.keyboard_nav", "test_keyboard_navigation"),
        "test_keyboard_navigation_cli": ("scripts.keyboard_nav", "test_keyboard_navigation_cli"),
        # e-MAG
        "run_emag_checklist": ("scripts.emag_checklist", "run_emag_checklist"),
        "run_emag_checklist_cli": ("scripts.emag_checklist", "run_emag_checklist_cli"),
        # relatórios
        "generate_reports": ("scripts.wcag_report", "generate_reports"),
        "ReportGenerator": ("scripts.wcag_report", "ReportGenerator"),
        # diff
        "compare_audits": ("scripts.diff_report", "compare_audits"),
        "compare_audits_cli": ("scripts.diff_report", "main"),
        # crawl
        "discover_urls": ("scripts.crawl_site", "discover_urls"),
        "discover_urls_cli": ("scripts.crawl_site", "discover_urls_cli"),
        # screen reader
        "run_screen_reader_test": ("scripts.screen_reader", "run_screen_reader_test"),
        "screen_reader_main": ("scripts.screen_reader", "main"),
    }

    if name in imports:
        module_name, func_name = imports[name]
        module = __import__(module_name, fromlist=[func_name])
        return getattr(module, func_name)

    raise AttributeError(f"module 'scripts' has no attribute '{name}'")


__all__ = [
    # axe
    "run_axe",
    "run_axe_cli",
    # pa11y
    "run_pa11y",
    "run_pa11y_cli",
    # lighthouse
    "run_lighthouse",
    "run_lighthouse_cli",
    # contraste
    "check_contrast",
    "check_contrast_cli",
    # teclado
    "test_keyboard_navigation",
    "test_keyboard_navigation_cli",
    # e-MAG
    "run_emag_checklist",
    "run_emag_checklist_cli",
    # relatórios
    "generate_reports",
    "ReportGenerator",
    # diff
    "compare_audits",
    "compare_audits_cli",
    # crawl
    "discover_urls",
    "discover_urls_cli",
    # screen reader
    "run_screen_reader_test",
    "screen_reader_main",
]