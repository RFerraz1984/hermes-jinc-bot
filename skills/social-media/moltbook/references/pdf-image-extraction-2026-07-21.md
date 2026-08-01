# Extração de Texto de PDFs (Image-based) — 2026-07-21

## Contexto
Dois PDFs do usuário (CV + perfil LinkedIn) eram **baseados em imagens** (produzidos por jsPDF/Apache FOP) — `page.get_text()` retornava vazio. Cada página tinha 5 imagens embutidas.

## Solução: Extração via Imagens (pymupdf/fitz)

```bash
# Instalar
uv pip install pymupdf pymupdf4llm -q

# Extrair imagens de cada página
cd /opt/data/hermes-shared
python3 -c "
import fitz
doc = fitz.open('Curriculo_Rafael_Ferraz_Carpi.3.pdf')
for i, page in enumerate(doc):
    images = page.get_images()
    for j, img in enumerate(images):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        if pix.n < 5:
            pix.save(f'cv_page{i+1}_img{j+1}.png')
        else:
            pix1 = fitz.Pixmap(fitz.csRGB, pix)
            pix1.save(f'cv_page{i+1}_img{j+1}.png')
        print(f'Extracted page {i+1} image {j+1}')
"
```

## Resultado
- **CV (5 páginas)**: 25 imagens extraídas → OCR via modelo de visão (ou processamento posterior)
- **LinkedIn (3 páginas)**: Texto nativo extraído com sucesso via `page.get_text()` (2114 + 814 + 879 chars)

## Notas Técnicas
| PDF | Tipo | Método que funcionou |
|-----|------|----------------------|
| Curriculo_Rafael_Ferraz_Carpi.3.pdf | Image-based (jsPDF 4.0.0) | Extração de imagens → OCR |
| LinkedIn-Profile_Rafael_Ferraz_Carpi.pdf | Text-based (Apache FOP 2.3) | `page.get_text()` direto |

## Próximos Passos (quando OCR for necessário)
1. **marker-pdf** (requer ~5GB PyTorch + models) — alta qualidade para scanned docs
2. **Tesseract** via `pytesseract` nas imagens extraídas — leve, roda em CPU
3. **Modelo de visão multimodal** (GPT-4V, Gemini, Claude) — enviar imagens extraídas

## Arquivos Gerados
```
/opt/data/hermes-shared/
├── cv_page1_img1.png ... cv_page5_img5.png   (25 imagens do CV)
├── Curriculo_Rafael_Ferraz_Carpi.3.pdf
└── LinkedIn-Profile_Rafael_Ferraz_Carpi.pdf
```

## Integração com RAG / Hermes
- Texto do LinkedIn já salvo como `linkedin-profile.txt` (para indexação)
- Imagens do CV prontas para OCR quando modelo multimodal estiver disponível
- Pasta `/opt/data/hermes-shared` persistente em `/opt/data` (sobrevive a updates Umbrel)