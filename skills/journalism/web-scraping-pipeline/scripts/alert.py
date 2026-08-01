#!/usr/bin/env python3
"""
Módulo de alertas - envia notificações Telegram e gera daily digest.
"""

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envia mensagens via Bot API do Telegram."""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram não configurado (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
    ) -> bool:
        """Envia mensagem simples."""
        if not self.base_url:
            logger.warning("Telegram não configurado - pulando envio")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                logger.info("Mensagem Telegram enviada com sucesso")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Erro enviando Telegram: {e}")
            return False
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Envia alerta formatado para item relevante."""
        text = self._format_alert(alert)
        return await self.send_message(text)
    
    async def send_digest(self, digest: Dict[str, Any]) -> bool:
        """Envia digest diário."""
        text = self._format_digest(digest)
        return await self.send_message(text)
    
    def _format_alert(self, alert: Dict[str, Any]) -> str:
        """Formata alerta individual."""
        score = alert.get("relevance_score", 0)
        emoji = "🚨" if score >= 70 else "⚠️" if score >= 40 else "📰"
        
        lines = [
            f"{emoji} **NOVO ITEM RELEVANTE ({score}/100)**",
            "",
            f"**{alert.get('title', 'Sem título')}**",
            f"🏛️ {alert.get('source_name', alert.get('source_id', 'Desconhecido'))} | {alert.get('date', 'Data desconhecida')}",
        ]
        
        tags = alert.get("tags", [])
        if tags:
            lines.append(f"🏷️ {' '.join(tags[:8])}")
        
        link = alert.get("link") or alert.get("url")
        if link:
            lines.append(f"🔗 {link}")
        
        return "\n".join(lines)
    
    def _format_digest(self, digest: Dict[str, Any]) -> str:
        """Formata digest diário."""
        today = date.today().strftime("%d/%m/%Y")
        total = digest.get("total_processed", 0)
        new_items = digest.get("total_new", 0)
        relevant = digest.get("total_relevant", 0)
        
        lines = [
            f"📊 **DIGEST DIÁRIO PcD — {today}**",
            "",
            f"🔍 Processados: {total} | 🆕 Novos: {new_items} | 🎯 Relevantes: {relevant}",
            "",
        ]
        
        high = [i for i in digest.get("items", []) if i.get("relevance_score", 0) >= 70]
        medium = [i for i in digest.get("items", []) if 40 <= i.get("relevance_score", 0) < 70]
        low = [i for i in digest.get("items", []) if i.get("relevance_score", 0) < 40]
        
        if high:
            lines.append(f"**🔴 ALTA RELEVÂNCIA ({len(high)})**")
            for item in high[:5]:
                lines.append(f"  • {item.get('title', 'Sem título')} ({item.get('relevance_score', 0)}) — {item.get('source_name', item.get('source_id'))}")
                if item.get("link"):
                    lines.append(f"    🔗 {item['link']}")
            lines.append("")
        
        if medium:
            lines.append(f"**🟡 MÉDIA RELEVÂNCIA ({len(medium)})**")
            for item in medium[:5]:
                lines.append(f"  • {item.get('title', 'Sem título')} ({item.get('relevance_score', 0)})")
            lines.append("")
        
        if low:
            lines.append(f"**🟢 BAIXA RELEVÂNCIA ({len(low)})**")
            lines.append("")
        
        # Estatísticas por fonte
        lines.append("**📈 POR FONTE:**")
        for src, count in digest.get("by_source", {}).items():
            lines.append(f"  • {src}: {count}")
        
        lines.append("")
        lines.append(f"📁 Detalhes em: `/opt/data/web-scraping/digest/{date.today().isoformat()}.md`")
        
        return "\n".join(lines)


class DigestGenerator:
    """Gera digests diários em Markdown e JSON."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, items: List[Dict[str, Any]], stats: Dict[str, int]) -> Dict[str, Any]:
        """Gera digest a partir dos itens do dia."""
        today = date.today()
        
        # Filtra itens de hoje
        today_items = []
        for item in items:
            processed = item.get("processed_at", "")
            if processed.startswith(today.isoformat()):
                today_items.append(item)
        
        # Separa por score
        high = [i for i in today_items if i.get("relevance_score", 0) >= 70]
        medium = [i for i in today_items if 40 <= i.get("relevance_score", 0) < 70]
        low = [i for i in today_items if i.get("relevance_score", 0) < 40]
        
        # Por fonte
        by_source = {}
        for item in today_items:
            src = item.get("source_id", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
        
        digest = {
            "date": today.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "total_processed": stats.get("total_processed", 0),
            "total_new": stats.get("total_new", 0),
            "total_duplicates": stats.get("total_duplicates", 0),
            "total_errors": stats.get("total_errors", 0),
            "total_relevant": len(high) + len(medium),
            "items": today_items,
            "by_source": by_source,
            "summary": {
                "high_relevance": len(high),
                "medium_relevance": len(medium),
                "low_relevance": len(low),
            }
        }
        
        # Salva JSON
        json_path = self.output_dir / f"{today.isoformat()}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(digest, f, ensure_ascii=False, indent=2)
        
        # Salva Markdown
        self._save_markdown(digest, high, medium, low)
        
        logger.info(f"Digest salvo: {json_path}")
        return digest
    
    def _save_markdown(self, digest: Dict, high: List, medium: List, low: List):
        """Salva versão Markdown legível."""
        today = date.today()
        md_path = self.output_dir / f"{today.isoformat()}.md"
        
        lines = [
            f"# 📊 Digest Diário PcD — {today.strftime('%d/%m/%Y')}",
            f"*Gerado em {datetime.now().strftime('%H:%M')} | Total processados: {digest['total_processed']} | Novos: {digest['total_new']} | Relevantes: {digest['total_relevant']}*",
            "",
        ]
        
        # Alta relevância
        if high:
            lines.append(f"## 🔴 Alta Relevância ({len(high)})")
            for item in high:
                lines.append(f"### {item.get('title', 'Sem título')} ({item.get('relevance_score', 0)}/100)")
                lines.append(f"**Fonte:** {item.get('source_name', item.get('source_id'))} | **Data:** {item.get('date', '?')}")
                tags = item.get("tags", [])
                if tags:
                    lines.append(f"**Tags:** {' '.join(tags[:6])}")
                if item.get("link"):
                    lines.append(f"**Link:** {item['link']}")
                lines.append("")
        
        # Média
        if medium:
            lines.append(f"## 🟡 Média Relevância ({len(medium)})")
            for item in medium:
                lines.append(f"- {item.get('title', 'Sem título')} ({item.get('relevance_score', 0)}) — {item.get('source_id')}")
            lines.append("")
        
        # Baixa
        if low:
            lines.append(f"## 🟢 Baixa Relevância ({len(low)})")
            lines.append("*Não listados individualmente*")
            lines.append("")
        
        # Por fonte
        lines.append("## 📈 Por Fonte")
        for src, count in digest["by_source"].items():
            lines.append(f"- {src}: {count}")
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class AlertManager:
    """Gerencia alertas - combina Telegram + Digest."""
    
    def __init__(self, data_dir: Path = Path("/opt/data/web-scraping")):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.telegram = TelegramNotifier()
        self.digest_gen = DigestGenerator(self.data_dir / "digest")
        
        # Log de alertas enviados
        self.alerts_log = self.data_dir / "logs" / "alerts.log"
        self.alerts_log.parent.mkdir(exist_ok=True)
    
    async def send_alerts(self, new_items: List[Dict[str, Any]], source_config: Dict[str, Any]) -> int:
        """Envia alertas imediatos para itens novos e relevantes."""
        if not new_items:
            return 0
        
        source_name = source_config.get("name", source_config.get("id", "Fonte"))
        sent = 0
        
        for item in new_items:
            score = item.get("relevance_score", 0)
            
            # Alerta imediato para score >= 50
            if score >= 50:
                alert = {
                    **item,
                    "source_name": source_name,
                }
                success = await self.telegram.send_alert(alert)
                if success:
                    sent += 1
                    self._log_alert(item, "sent")
                else:
                    self._log_alert(item, "failed")
            
            # Rate limit
            import asyncio
            await asyncio.sleep(0.5)
        
        return sent
    
    async def send_daily_digest(self, all_items: List[Dict[str, Any]], stats: Dict[str, int]) -> bool:
        """Gera e envia digest diário."""
        digest = self.digest_gen.generate(all_items, stats)
        success = await self.telegram.send_digest(digest)
        
        if success:
            self._log_alert({"type": "daily_digest", "date": date.today().isoformat()}, "sent")
        
        return success
    
    def _log_alert(self, item: Dict[str, Any], status: str):
        """Registra alerta no log."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "title": item.get("title", "N/A"),
            "source": item.get("source_id", "unknown"),
            "relevance_score": item.get("relevance_score", 0),
        }
        
        with open(self.alerts_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


async def main():
    import argparse
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Alert Manager Test")
    parser.add_argument("--test-telegram", action="store_true", help="Testa envio Telegram")
    parser.add_argument("--test-digest", action="store_true", help="Testa geração digest")
    args = parser.parse_args()
    
    if args.test_telegram:
        telegram = TelegramNotifier()
        await telegram.send_message("🧪 Teste do Web Scraping Pipeline - Jornalista Inclusivo")
    
    if args.test_digest:
        # Testa digest com dados mock
        test_items = [
            {"title": "PL 1234/2026", "relevance_score": 87, "source_id": "camara", "source_name": "Câmara", "date": "2026-07-24", "link": "http://ex.com/1", "tags": ["#PcD", "#tecnologia"]},
            {"title": "Decreto acessibilidade", "relevance_score": 82, "source_id": "dou", "source_name": "DOU", "date": "2026-07-24", "link": "http://ex.com/2", "tags": ["#acessibilidade"]},
        ]
        
        stats = {"total_processed": 150, "total_new": 12, "total_duplicates": 138, "total_errors": 0}
        
        gen = DigestGenerator(Path("/opt/data/web-scraping/digest"))
        digest = gen.generate(test_items, stats)
        print("Digest gerado:", digest["summary"])
        
        telegram = TelegramNotifier()
        await telegram.send_digest(digest)


if __name__ == "__main__":
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())