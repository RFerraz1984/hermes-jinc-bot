#!/usr/bin/env python3
"""
Fingerprinting de Políticas de Rate Limit — Composite Fingerprint
Combina assinatura de infraestrutura + cadência + endpoint para detectar policy drift.

Uso: python fingerprint_policy.py --endpoint https://api.example.com/v1/chat/completions --policy-name "openai_chat"

Based on session 2026-07-25 learnings:
- infra_sig: TLS, headers, server, CDN provider (static-ish)
- cadence_sig: latency p50/p99, jitter, burst pattern, retry-after distribution, error rate
- endpoint_id: normalized path template hash
- Full fingerprint = SHA256(infra_sig + cadence_sig + endpoint_id + policy_name)

Drift detection: Compare current fingerprint against 7-day baseline (3 vantage points)
"""

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from collections import deque
import sqlite3
from pathlib import Path


@dataclass
class InfraSignature:
    """Assinatura estática de infraestrutura (headers, TLS, CDN, server)"""
    tls_fingerprint: str = ""          # JA3 or equivalent
    server_header: str = ""
    cdn_provider: str = ""             # cloudflare, aws_cloudfront, fastly, google, azure, akamai, etc.
    via_header: str = ""
    x_amz_cf_id: str = ""
    cf_ray: str = ""
    fastly_debug: str = ""
    ip_range: str = ""                 # ASN / CIDR block
    user_agent: str = "Hermes-Agent/1.0"
    accept_header: str = "application/json"
    content_type: str = "application/json"
    
    def hash(self) -> str:
        data = "|".join([
            self.tls_fingerprint,
            self.server_header,
            self.cdn_provider,
            self.via_header,
            self.x_amz_cf_id,
            self.cf_ray,
            self.fastly_debug,
            self.ip_range,
            self.user_agent,
            self.accept_header,
            self.content_type
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class CadenceSignature:
    """Assinatura comportamental (latência, jitter, burst, retry, erro)"""
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    jitter_ms: float = 0.0
    burst_size: int = 0
    burst_interval_ms: float = 0.0
    retry_after_avg: float = 0.0
    retry_after_distribution: Dict[str, int] = field(default_factory=dict)  # value -> count
    error_rate_5min: float = 0.0
    rate_limit_remaining_avg: float = 0.0
    rate_limit_reset_pattern: str = ""   # e.g., "fixed_window", "sliding", "token_bucket"
    
    def hash(self) -> str:
        # Round to reduce noise sensitivity
        data = "|".join([
            f"{self.latency_p50_ms:.0f}",
            f"{self.latency_p99_ms:.0f}",
            f"{self.jitter_ms:.0f}",
            str(self.burst_size),
            f"{self.burst_interval_ms:.0f}",
            f"{self.retry_after_avg:.2f}",
            f"{self.error_rate_5min:.4f}",
            f"{self.rate_limit_remaining_avg:.0f}",
            self.rate_limit_reset_pattern
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class CompositeFingerprint:
    """Fingerprint composto: infra + cadência + endpoint + policy"""
    infra_sig: str
    cadence_sig: str
    endpoint_id: str
    policy_name: str
    timestamp: str
    vantage_point: str = "default"  # geo/IP identifier
    request_count: int = 1
    
    def full_hash(self) -> str:
        combined = f"{self.infra_sig}:{self.cadence_sig}:{self.endpoint_id}:{self.policy_name}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def drift_key(self) -> str:
        """Key for grouping baseline measurements"""
        return f"{self.policy_name}:{self.endpoint_id}"
    
    def to_dict(self) -> dict:
        return {
            "infra_sig": self.infra_sig,
            "cadence_sig": self.cadence_sig,
            "endpoint_id": self.endpoint_id,
            "policy_name": self.policy_name,
            "full_hash": self.full_hash(),
            "drift_key": self.drift_key(),
            "timestamp": self.timestamp,
            "vantage_point": self.vantage_point,
            "request_count": self.request_count
        }


class FingerprintCollector:
    """Collects, stores, and analyzes fingerprints for drift detection"""
    
    def __init__(self, db_path: str = "/opt/data/moltbook_monitor_state/fingerprints.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drift_key TEXT NOT NULL,
                    infra_sig TEXT NOT NULL,
                    cadence_sig TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    full_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    vantage_point TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    raw_data TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_drift_key_time 
                ON fingerprints(drift_key, timestamp)
            """)
    
    def record(self, fp: CompositeFingerprint, raw_data: dict = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO fingerprints 
                (drift_key, infra_sig, cadence_sig, endpoint_id, policy_name, full_hash, 
                 timestamp, vantage_point, request_count, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fp.drift_key(), fp.infra_sig, fp.cadence_sig, fp.endpoint_id,
                fp.policy_name, fp.full_hash(), fp.timestamp, fp.vantage_point,
                fp.request_count, json.dumps(raw_data) if raw_data else None
            ))
    
    def get_baseline(self, drift_key: str, days: int = 7, vantage_points: int = 3) -> List[CompositeFingerprint]:
        """Get baseline fingerprints for drift_key within time window"""
        cutoff = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - days * 86400))
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fingerprints 
                WHERE drift_key = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (drift_key, cutoff))
            rows = cursor.fetchall()
        
        fps = []
        for row in rows:
            fps.append(CompositeFingerprint(
                infra_sig=row['infra_sig'],
                cadence_sig=row['cadence_sig'],
                endpoint_id=row['endpoint_id'],
                policy_name=row['policy_name'],
                timestamp=row['timestamp'],
                vantage_point=row['vantage_point'],
                request_count=row['request_count']
            ))
        return fps
    
    def detect_drift(self, current: CompositeFingerprint, baseline: List[CompositeFingerprint]) -> dict:
        """Compare current fingerprint against baseline"""
        if not baseline:
            return {
                "has_baseline": False,
                "drift_detected": False,
                "drift_type": "NO_BASELINE",
                "details": "No baseline measurements available for comparison"
            }
        
        # Find most common infra_sig and cadence_sig in baseline (mode)
        infra_counts = {}
        cadence_counts = {}
        for fp in baseline:
            infra_counts[fp.infra_sig] = infra_counts.get(fp.infra_sig, 0) + 1
            cadence_counts[fp.cadence_sig] = cadence_counts.get(fp.cadence_sig, 0) + 1
        
        baseline_infra = max(infra_counts, key=infra_counts.get)
        baseline_cadence = max(cadence_counts, key=cadence_counts.get)
        baseline_endpoint = baseline[0].endpoint_id  # Should be consistent
        
        infra_changed = current.infra_sig != baseline_infra
        cadence_changed = current.cadence_sig != baseline_cadence
        endpoint_mismatch = current.endpoint_id != baseline_endpoint
        
        drift_type = "NONE"
        if infra_changed:
            drift_type = "INFRASTRUCTURE_CHANGE"
        elif cadence_changed:
            drift_type = "CADENCE_DRIFT"
        elif endpoint_mismatch:
            drift_type = "ENDPOINT_MISMATCH"
        
        return {
            "has_baseline": True,
            "drift_detected": infra_changed or cadence_changed or endpoint_mismatch,
            "drift_type": drift_type,
            "details": {
                "infra_changed": infra_changed,
                "current_infra": current.infra_sig,
                "baseline_infra": baseline_infra,
                "infra_stability": infra_counts.get(baseline_infra, 0) / len(baseline),
                "cadence_changed": cadence_changed,
                "current_cadence": current.cadence_sig,
                "baseline_cadence": baseline_cadence,
                "cadence_stability": cadence_counts.get(baseline_cadence, 0) / len(baseline),
                "endpoint_mismatch": endpoint_mismatch,
                "baseline_measurements": len(baseline),
                "vantage_points_covered": len(set(fp.vantage_point for fp in baseline))
            }
        }
    
    def get_baseline_summary(self, drift_key: str, days: int = 7) -> dict:
        """Get summary stats for baseline"""
        fps = self.get_baseline(drift_key, days)
        if not fps:
            return {"drift_key": drift_key, "measurements": 0}
        
        infra_counts = {}
        cadence_counts = {}
        vantage_points = set()
        
        for fp in fps:
            infra_counts[fp.infra_sig] = infra_counts.get(fp.infra_sig, 0) + 1
            cadence_counts[fp.cadence_sig] = cadence_counts.get(fp.cadence_sig, 0) + 1
            vantage_points.add(fp.vantage_point)
        
        return {
            "drift_key": drift_key,
            "measurements": len(fps),
            "days_covered": days,
            "vantage_points": len(vantage_points),
            "vantage_point_list": list(vantage_points),
            "infra_signatures": len(infra_counts),
            "dominant_infra_sig": max(infra_counts, key=infra_counts.get),
            "infra_stability": max(infra_counts.values()) / len(fps),
            "cadence_signatures": len(cadence_counts),
            "dominant_cadence_sig": max(cadence_counts, key=cadence_counts.get),
            "cadence_stability": max(cadence_counts.values()) / len(fps),
            "time_range": {
                "oldest": fps[-1].timestamp if fps else None,
                "newest": fps[0].timestamp if fps else None
            }
        }


class RateLimitFingerprinter:
    """Active probing to build fingerprints"""
    
    def __init__(self, api_key: str, session: Optional[Any] = None):
        self.api_key = api_key
        self.session = session
    
    @staticmethod
    def extract_endpoint_id(url: str) -> str:
        """Normalize path and generate endpoint hash"""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        # Normalize: /v1/users/123 -> /v1/users/{id}
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        path = re.sub(r'/[a-f0-9]{32,}', '/{hash}', path)
        return hashlib.sha256(path.encode()).hexdigest()[:12]
    
    @staticmethod
    def detect_cdn(headers: Dict) -> str:
        """Detect CDN/provider from response headers"""
        server = headers.get('Server', '').lower()
        via = headers.get('Via', '').lower()
        
        if headers.get('CF-Ray') or headers.get('CF-Cache-Status') or 'cloudflare' in server:
            return 'cloudflare'
        if headers.get('X-Amz-Cf-Id'):
            return 'aws_cloudfront'
        if headers.get('Fastly-Debug-Digest'):
            return 'fastly'
        if 'google' in server or 'gfe' in server:
            return 'google_cloud'
        if 'azure' in via:
            return 'azure_cdn'
        if 'akamai' in via or 'akamai' in server:
            return 'akamai'
        return 'unknown'
    
    @staticmethod
    def extract_rate_limit_info(headers: Dict) -> dict:
        """Extract all rate limit related headers"""
        rl_headers = {}
        for key, val in headers.items():
            key_lower = key.lower()
            if any(kw in key_lower for kw in ['rate-limit', 'ratelimit', 'retry-after', 'x-rate']):
                rl_headers[key] = val
        return rl_headers
    
    def probe_endpoint(self, url: str, payload: dict, n_requests: int = 20, 
                       delay: float = 0.5) -> dict:
        """Execute n_requests and collect cadence metrics"""
        import requests
        
        if not self.session:
            self.session = requests.Session()
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        
        latencies = []
        retry_afters = []
        errors = 0
        server_header = None
        cdn_provider = "unknown"
        rate_limit_remaining = []
        
        for i in range(n_requests):
            start = time.time()
            try:
                resp = self.session.post(url, json=payload, timeout=30)
                elapsed = (time.time() - start) * 1000
                latencies.append(elapsed)
                
                if i == 0:
                    server_header = resp.headers.get("Server", "")
                    cdn_provider = self.detect_cdn(resp.headers)
                
                # Rate limit headers
                rl_info = self.extract_rate_limit_info(resp.headers)
                if 'Retry-After' in rl_info:
                    try:
                        retry_afters.append(float(rl_info['Retry-After']))
                    except:
                        pass
                for k, v in rl_info.items():
                    if 'remaining' in k.lower():
                        try:
                            rate_limit_remaining.append(float(v))
                        except:
                            pass
                
                if resp.status_code >= 400:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                if i == 0:
                    pass
            
            time.sleep(delay)
        
        if not latencies:
            raise ValueError("All requests failed")
        
        latencies.sort()
        p50 = latencies[len(latencies)//2]
        p99 = latencies[int(len(latencies)*0.99)] if len(latencies) > 1 else p50
        jitter = p99 - p50
        retry_avg = sum(retry_afters)/len(retry_afters) if retry_afters else 0
        error_rate = errors / n_requests
        rl_remaining_avg = sum(rate_limit_remaining)/len(rate_limit_remaining) if rate_limit_remaining else 0
        
        return {
            "latencies": latencies,
            "p50": p50,
            "p99": p99,
            "jitter": jitter,
            "retry_avg": retry_avg,
            "retry_afters": retry_afters,
            "error_rate": error_rate,
            "server_header": server_header,
            "cdn_provider": cdn_provider,
            "rate_limit_remaining_avg": rl_remaining_avg,
            "rate_limit_headers_sample": self.extract_rate_limit_info(resp.headers) if 'resp' in locals() else {},
            "request_count": n_requests
        }
    
    def build_infra_signature(self, probe_result: dict) -> InfraSignature:
        return InfraSignature(
            tls_fingerprint="",  # Would need JA3 from actual TLS handshake
            server_header=probe_result.get("server_header", ""),
            cdn_provider=probe_result.get("cdn_provider", "unknown"),
            via_header="",
            x_amz_cf_id="",
            cf_ray="",
            fastly_debug="",
            ip_range="",
            user_agent="Hermes-Agent/1.0",
            accept_header="application/json",
            content_type="application/json"
        )
    
    def build_cadence_signature(self, probe_result: dict) -> CadenceSignature:
        # Detect rate limit reset pattern
        rl_headers = probe_result.get("rate_limit_headers_sample", {})
        reset_pattern = "unknown"
        if 'Retry-After' in rl_headers:
            reset_pattern = "retry_after_header"
        elif any('reset' in k.lower() for k in rl_headers):
            reset_pattern = "reset_timestamp_header"
        elif any('remaining' in k.lower() for k in rl_headers):
            reset_pattern = "remaining_count_header"
        
        return CadenceSignature(
            latency_p50_ms=probe_result["p50"],
            latency_p99_ms=probe_result["p99"],
            jitter_ms=probe_result["jitter"],
            burst_size=0,
            burst_interval_ms=0.0,
            retry_after_avg=probe_result["retry_avg"],
            retry_after_distribution={},
            error_rate_5min=probe_result["error_rate"],
            rate_limit_remaining_avg=probe_result.get("rate_limit_remaining_avg", 0),
            rate_limit_reset_pattern=reset_pattern
        )
    
    def fingerprint(self, url: str, policy_name: str, payload: dict, 
                    vantage_point: str = "default") -> CompositeFingerprint:
        endpoint_id = self.extract_endpoint_id(url)
        probe = self.probe_endpoint(url, payload)
        
        infra = self.build_infra_signature(probe)
        cadence = self.build_cadence_signature(probe)
        
        return CompositeFingerprint(
            infra_sig=infra.hash(),
            cadence_sig=cadence.hash(),
            endpoint_id=endpoint_id,
            policy_name=policy_name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            vantage_point=vantage_point,
            request_count=probe["request_count"]
        )


def main():
    parser = argparse.ArgumentParser(description="Rate Limit Policy Fingerprinting")
    parser.add_argument("--endpoint", required=True, help="API endpoint URL")
    parser.add_argument("--policy-name", required=True, help="Policy identifier (e.g., openai_chat)")
    parser.add_argument("--api-key", required=True, help="API key for authentication")
    parser.add_argument("--payload", default='{"model": "test", "messages": [{"role": "user", "content": "ping"}]}', 
                        help="JSON payload for probe requests")
    parser.add_argument("--n-probes", type=int, default=20, help="Number of probe requests")
    parser.add_argument("--vantage-point", default="default", help="Vantage point identifier")
    parser.add_argument("--baseline-file", help="JSON file with baseline fingerprint to compare against")
    parser.add_argument("--output", help="Output JSON file for fingerprint")
    parser.add_argument("--db", default="/opt/data/moltbook_monitor_state/fingerprints.db", 
                        help="SQLite database for fingerprint storage")
    parser.add_argument("--check-drift", action="store_true", help="Check drift against stored baseline")
    parser.add_argument("--baseline-days", type=int, default=7, help="Days of baseline to consider")
    parser.add_argument("--summary", help="Show baseline summary for drift_key")
    
    args = parser.parse_args()
    
    collector = FingerprintCollector(args.db)
    fingerprinter = RateLimitFingerprinter(args.api_key)
    
    if args.summary:
        summary = collector.get_baseline_summary(args.summary, args.baseline_days)
        print(json.dumps(summary, indent=2))
        return
    
    payload = json.loads(args.payload)
    fp = fingerprinter.fingerprint(args.endpoint, args.policy_name, payload, args.vantage_point)
    
    result = fp.to_dict()
    
    # Store in database
    collector.record(fp, {
        "endpoint": args.endpoint,
        "payload": payload,
        "n_probes": args.n_probes,
        "vantage_point": args.vantage_point
    })
    
    if args.check_drift:
        baseline = collector.get_baseline(fp.drift_key(), args.baseline_days)
        drift = collector.detect_drift(fp, baseline)
        result["drift_check"] = drift
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()