import streamlit as st
import anthropic
import base64
import os
import zipfile
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import subprocess
import tempfile
import io

# ─────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Packaging Extractor",
    page_icon="📦",
    layout="wide",
)

# ─────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #f8f9fa; }
    .stButton>button {
        background: linear-gradient(135deg, #6c63ff, #48bfef);
        color: white; border: none; border-radius: 10px;
        padding: 0.6rem 2rem; font-size: 1rem; font-weight: 600;
        transition: opacity .2s;
    }
    .stButton>button:hover { opacity: .85; color: white; }
    .card {
        background: white; border-radius: 14px;
        padding: 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 2px 12px rgba(0,0,0,.07);
    }
    .step-badge {
        display: inline-block;
        background: #6c63ff; color: white;
        border-radius: 50%; width: 28px; height: 28px;
        text-align: center; line-height: 28px;
        font-weight: 700; margin-left: 8px;
    }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #333; margin-bottom: .5rem; }
    .hebrew-content {
        direction: rtl; text-align: right;
        font-family: 'Segoe UI', Arial, sans-serif;
        line-height: 1.8; color: #222;
    }
    .img-thumb { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  Marketing template (from user example)
# ─────────────────────────────────────────
MARKETING_TEMPLATE = """
אתה כותב תוכן שיווקי מקצועי בעברית למוצרי חשמל לבית לאתר איקומרס ישראלי.
הנה דוגמא לסגנון ולמבנה שאני רוצה – שמור בדיוק על אותה מבנה ומינוח:

---דוגמא---
מכשיר להכנת מאפים עם 4 פלטות מתחלפות ANYBAKE מבית Food appeal
ANYBAKE - Multi Baker מכשיר אחד, אינסוף פינוקים קינוחים מוכנים תוך דקות: מערכת אחת להכנת מגוון קינוחים בקלות: 7 מיני דונאטס, 7 מיני מאפינס, 12 קייק-פופס ו-4 וופלים בלגיים. אין צורך בהכנות מורכבות! פשוט מכניסים את הפלטות הרצויות, מחברים לחשמל ומתחילים לאפות.
ביצועים ועמידות ללא פשרות עוצמה חזקה: הספק עוצמתי של 1000 וואט המבטיח ביצועים גבוהים, עבודה מהירה ותוצאות מושלמות בכל שימוש. עמידות לאורך זמן: גוף המכשיר עשוי פלדת אל-חלד (נירוסטה) איכותית, הכוללת ציפוי צבע ייחודי בסגנון רטרו המעניק למטבח מראה יוקרתי ונוסטלגי.
פלטות נשלפות: המכשיר כולל פלטות ייעודיות ומתחלפות להכנת מיני דונאטס, מיני מאפינס ומיני וופל. הכל במכשיר אחד (All-In-One): מערכת מושלמת להכנת קינוחים שתופסת מקום מינימלי על השיש שלכם ומספקת תוצאות מקצועיות. ציפוי Non-Stick (מונע הידבקות): הפלטות הנשלפות מצופות בשכבת נון-סטיק איכותית המאפשרת הוצאה קלה של הקינוחים ושמירה על צורתם. הפלטות נשלפות בקלות ובטוחות לשטיפה במדיח הכלים לניקוי מהיר וללא מאמץ.
---סוף דוגמא---

קיבלת את הטקסט האנגלי הבא מאריזת המוצר:
{packaging_text}

כתוב תוכן שיווקי בעברית לאתר בדיוק באותו מבנה וסגנון של הדוגמא.
המבנה:
1. שורת כותרת ראשית: [תיאור מוצר בעברית] + [שם המוצר באנגלית] + מבית [שם המותג]
2. [שם מוצר באנגלית] + כותרת משנה קליטה + תיאור ראשי: הסבר מה המוצר עושה, פירוט יתרונות מרכזיים ואופן שימוש פשוט. הכל בפסקה אחת רציפה וזורמת.
3. פסקת ביצועים ועמידות: עוצמה (ואט), חומרי גוף (נירוסטה/פלסטיק), עיצוב ומראה.
4. פסקת תכונות עיקריות: אביזרים/פלטות נשלפים, All-In-One, ציפוי Non-Stick, קלות ניקוי ושטיפה במדיח.

כללים חשובים:
- שמור על אותו טון שיווקי נלהב ומקצועי כמו בדוגמא
- השתמש במונחים עבריים מקצועיים (פלדת אל-חלד, נון-סטיק, הספק וכו׳)
- אם יש מפרט טכני באנגלית – תרגם ושלב בצורה טבעית
- אל תמציא מפרט שלא מופיע בטקסט המקורי
- החזר רק את הטקסט השיווקי, בלי הסברים נוספים
"""

# ─────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────

def extract_images_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract all significant raster images from PDF using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    seen_xrefs = set()

    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                pix = fitz.Pixmap(doc, xref)
                # Skip tiny images (icons, masks, etc.)
                if pix.width < 400 or pix.height < 400:
                    pix = None
                    continue
                # Convert CMYK / non-RGB to RGB
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("jpeg")
                images.append({
                    "xref": xref,
                    "width": pix.width,
                    "height": pix.height,
                    "bytes": img_bytes,
                })
                pix = None
            except Exception:
                continue

    # Sort by area descending (largest first)
    images.sort(key=lambda x: x["width"] * x["height"], reverse=True)
    return images


def _compress_jpeg(raw_bytes: bytes, max_width: int = 1500, quality: int = 75) -> bytes:
    """Resize to max_width (keeping aspect ratio) and re-encode as JPEG."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def rasterize_pdf_page(pdf_bytes: bytes, page: int = 1, dpi: int = 100) -> bytes:
    """Rasterize a PDF page to JPEG bytes. Tries pdftoppm, falls back to PyMuPDF."""
    raw = None
    # Try pdftoppm first (better quality)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            out_prefix = os.path.join(tmpdir, "page")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            subprocess.run(
                ["pdftoppm", "-jpeg", "-r", str(dpi), "-f", str(page), "-l", str(page), pdf_path, out_prefix],
                check=True, capture_output=True,
            )
            files = sorted(Path(tmpdir).glob("page-*.jpg"))
            if files:
                raw = files[0].read_bytes()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # pdftoppm not installed or failed — use PyMuPDF

    if raw is None:
        # Fallback: PyMuPDF rasterization
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_obj = doc[page - 1]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page_obj.get_pixmap(matrix=mat)
        raw = pix.tobytes("jpeg")

    return _compress_jpeg(raw)


def extract_packaging_text(client: anthropic.Anthropic, page_jpegs: list[bytes]) -> str:
    """Use Claude Vision to extract all marketing text from packaging images (all pages)."""
    content = []
    for jpeg in page_jpegs:
        b64 = base64.standard_b64encode(jpeg).decode()
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content.append({"type": "text", "text": (
        "These are images of product packaging (one or more sides/pages). "
        "Extract ALL the English marketing text you can see from ALL images. "
        "Include every feature description, benefit, specification, and marketing claim. "
        "Preserve the hierarchy (headers and their details). "
        "Ignore barcodes, copyright notices, and pure logo text. "
        "Return structured plain text, combining text from all images into one coherent document."
    )})
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text


def generate_hebrew_content(client: anthropic.Anthropic, packaging_text: str) -> str:
    """Use Claude to turn extracted text into Hebrew website copy."""
    prompt = MARKETING_TEMPLATE.format(packaging_text=packaging_text)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Return number of pages in a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return len(doc)


def create_zip(images: list[dict], hebrew_text: str) -> bytes:
    """Pack images + text file into a ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("marketing_content_he.txt", hebrew_text.encode("utf-8"))
        for i, img in enumerate(images):
            zf.writestr(f"product_image_{i+1}.jpg", img["bytes"])
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────

st.markdown("## 📦 Packaging Extractor")
st.markdown("העלה PDF של אריזת מוצר וקבל תמונות נקיות + תוכן שיווקי בעברית")

# ── API Key ──
with st.sidebar:
    st.markdown("### ⚙️ הגדרות")
    default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    api_key = st.text_input("Anthropic API Key", value=default_key, type="password", placeholder="sk-ant-...")
    st.markdown("---")
    st.markdown("**מה האפליקציה עושה:**")
    st.markdown("""
- 🖼️ שולפת תמונות מוצר נקיות מה-PDF
- 📝 קוראת את הטקסט האנגלי מהאריזה
- ✍️ ממירה לתוכן שיווקי בעברית
- 📥 מייצרת ZIP להורדה
    """)

# ── Upload ──
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="step-badge">1</span> העלאת PDF</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("גרור PDF של אריזת מוצר", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        st.success(f"✅ {uploaded.name} ({uploaded.size // 1024} KB)")
        run_btn = st.button("🚀 עבד את האריזה", use_container_width=True)
    else:
        run_btn = False
        st.info("📂 ממתין לקובץ PDF...")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Process ──
if run_btn and uploaded:
    if not api_key:
        st.error("הכנס Anthropic API Key בסרגל השמאלי")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    pdf_bytes = uploaded.read()

    try:
        with col1:
            # Step 1 – Extract images
            with st.status("שולף תמונות מה-PDF...", expanded=True) as status:
                images = extract_images_from_pdf(pdf_bytes)
                status.update(label=f"נמצאו {len(images)} תמונות מוצר", state="complete")

            # Step 2 – Rasterize all pages + OCR
            with st.status("קורא טקסט מהאריזה...", expanded=True) as status:
                num_pages = get_pdf_page_count(pdf_bytes)
                page_jpegs = []
                for p in range(1, num_pages + 1):
                    page_jpegs.append(rasterize_pdf_page(pdf_bytes, page=p, dpi=200))
                packaging_text = extract_packaging_text(client, page_jpegs)
                status.update(label=f"טקסט אריזה חולץ ({num_pages} עמודים)", state="complete")

            # Step 3 – Generate Hebrew
            with st.status("מייצר תוכן שיווקי בעברית...", expanded=True) as status:
                hebrew_content = generate_hebrew_content(client, packaging_text)
                status.update(label="תוכן שיווקי מוכן!", state="complete")

        # Save to session state so results survive reruns
        st.session_state["results"] = {
            "images": images,
            "packaging_text": packaging_text,
            "hebrew_content": hebrew_content,
            "filename": uploaded.name,
        }

    except anthropic.AuthenticationError:
        st.error("API Key לא תקין. בדוק את המפתח ונסה שוב.")
        st.stop()
    except anthropic.APIError as e:
        st.error(f"שגיאת API: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"שגיאה: {e}")
        st.stop()

# ── Show results (from session state or fresh run) ──
results = st.session_state.get("results")
if results:
    images = results["images"]
    packaging_text = results["packaging_text"]
    hebrew_content = results["hebrew_content"]
    filename = results["filename"]

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">2</span> תמונות מוצר נקיות</div>', unsafe_allow_html=True)

        if images:
            img_cols = st.columns(min(len(images), 3))
            for i, img_data in enumerate(images[:6]):
                with img_cols[i % 3]:
                    pil_img = Image.open(io.BytesIO(img_data["bytes"]))
                    st.image(pil_img, caption=f"תמונה {i+1}", use_container_width=True)
        else:
            st.warning("לא נמצאו תמונות מוצר מוטמעות ב-PDF")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">3</span> תוכן שיווקי – עברית</div>', unsafe_allow_html=True)

        with st.expander("טקסט אנגלי שחולץ מהאריזה"):
            st.text(packaging_text)

        st.markdown(f'<div class="hebrew-content">{hebrew_content.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        st.code(hebrew_content, language=None)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Download ZIP ──
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">4</span> הורדה</div>', unsafe_allow_html=True)
        zip_bytes = create_zip(images, hebrew_content)
        st.download_button(
            label="הורד ZIP (תמונות + תוכן עברי)",
            data=zip_bytes,
            file_name=f"{Path(filename).stem}_processed.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

elif not uploaded:
    with col2:
        st.markdown('<div class="card" style="min-height:300px; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#aaa;">', unsafe_allow_html=True)
        st.markdown("### 📦")
        st.markdown("תוצאות יופיעו כאן לאחר עיבוד ה-PDF")
        st.markdown('</div>', unsafe_allow_html=True)
