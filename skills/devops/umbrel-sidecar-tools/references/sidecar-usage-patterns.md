# Hermes Sidecar Usage Patterns

## Calling Sidecar from Hermes Scripts

### Pattern 1: Direct docker exec (recommended)
```python
import subprocess

def pandoc_md_to_pdf(input_md: str, output_pdf: str) -> bool:
    cmd = [
        "docker", "exec", "hermes-tools",
        "pandoc", f"/opt/data/{input_md}",
        "-o", f"/opt/data/{output_pdf}",
        "--pdf-engine=xelatex",
        "-V", "geometry:margin=2cm"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def weasyprint_html_to_pdf(input_html: str, output_pdf: str) -> bool:
    script = f"""
import weasyprint
weasyprint.HTML('/opt/data/{input_html}').write_pdf('/opt/data/{output_pdf}')
"""
    cmd = [
        "docker", "exec", "hermes-tools",
        "python3", "-c", script
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def libreoffice_convert(input_file: str, output_format: str = "pdf") -> bool:
    cmd = [
        "docker", "exec", "hermes-tools",
        "libreoffice", "--headless",
        "--convert-to", output_format,
        "--outdir", "/opt/data",
        f"/opt/data/{input_file}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

### Pattern 2: Wrapper script for repeated use
```bash
#!/bin/bash
# /opt/data/scripts/sidecar-tools.sh

set -e

TOOL=$1
shift

case $TOOL in
    pandoc)
        docker exec hermes-tools pandoc "$@"
        ;;
    weasyprint)
        docker exec hermes-tools python3 -c "
import weasyprint, sys
weasyprint.HTML(sys.argv[1]).write_pdf(sys.argv[2])
" "$@"
        ;;
    libreoffice)
        docker exec hermes-tools libreoffice --headless --convert-to pdf --outdir /opt/data "$@"
        ;;
    *)
        echo "Unknown tool: $TOOL"
        exit 1
        ;;
esac
```

Usage:
```bash
/opt/data/scripts/sidecar-tools.sh pandoc /opt/data/input.md -o /opt/data/output.pdf --pdf-engine=xelatex
/opt/data/scripts/sidecar-tools.sh weasyprint /opt/data/input.html /opt/data/output.pdf
/opt/data/scripts/sidecar-tools.sh libreoffice /opt/data/doc.docx
```

### Pattern 3: Python context manager for temp files
```python
import tempfile
import os
from pathlib import Path

class SidecarTools:
    def __init__(self, data_dir: str = "/opt/data"):
        self.data_dir = Path(data_dir)
    
    def _run(self, cmd: list) -> subprocess.CompletedProcess:
        full_cmd = ["docker", "exec", "hermes-tools"] + cmd
        return subprocess.run(full_cmd, capture_output=True, text=True)
    
    def md_to_pdf(self, md_content: str, output_name: str) -> Path:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', dir=self.data_dir, delete=False) as f:
            f.write(md_content)
            md_path = f.name
        
        try:
            output_path = self.data_dir / output_name
            cmd = ["pandoc", f"/opt/data/{md_path.name}", "-o", f"/opt/data/{output_name}", "--pdf-engine=xelatex"]
            result = self._run(cmd)
            if result.returncode != 0:
                raise RuntimeError(f"Pandoc failed: {result.stderr}")
            return output_path
        finally:
            os.unlink(md_path)
    
    def html_to_pdf(self, html_content: str, output_name: str) -> Path:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', dir=self.data_dir, delete=False) as f:
            f.write(html_content)
            html_path = f.name
        
        try:
            output_path = self.data_dir / output_name
            script = f"""
import weasyprint
weasyprint.HTML('/opt/data/{Path(html_path).name}').write_pdf('/opt/data/{output_name}')
"""
            result = self._run(["python3", "-c", script])
            if result.returncode != 0:
                raise RuntimeError(f"WeasyPrint failed: {result.stderr}")
            return self.data_dir / output_name
        finally:
            os.unlink(html_path)
    
    def docx_to_pdf(self, docx_path: Path) -> Path:
        result = self._run([
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", "/opt/data", f"/opt/data/{docx_path.name}"
        ])
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice failed: {result.stderr}")
        return docx_path.with_suffix(".pdf")
```

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `container "hermes-tools" not found` | Sidecar not running | Start via Umbrel app manager |
| `permission denied` on /opt/data | Volume permissions | Check `docker volume inspect hermes-agent_data` |
| `weasyprint: error: cairo` | Missing system deps | Add `python3-cairo python3-pango python3-gi` to Dockerfile |
| `libreoffice: command not found` | Not installed | Add `libreoffice-headless` to Dockerfile |
| `xelatex not found` | LaTeX missing | Add `texlive-xetex` to Dockerfile |

## Testing Sidecar

```bash
# Test all three tools
docker exec hermes-tools pandoc --version
docker exec hermes-tools python3 -c "import weasyprint; print('weasyprint OK')"
docker exec hermes-tools libreoffice --version

# Full pipeline test
echo "# Hello World" | docker exec -i hermes-tools pandoc -f markdown -t pdf --pdf-engine=xelatex -o /opt/data/test.pdf
docker exec hermes-tools ls -la /opt/data/test.pdf
```