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
                if pix.width < 400 or pix.height < 400:
                    pix = None
                    continue
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

    images.sort(key=lambda x: x["width"] * x["height"], reverse=True)
    return images


def _compress_jpeg(raw_bytes: bytes, max_width: int = 1500, quality: int = 75) -> bytes:
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
        pass

    if raw is None:
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
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text


def generate_hebrew_content(client: anthropic.Anthropic, packaging_text: str, style: str = "long") -> str:
    """Use Claude to turn extracted text into Hebrew website copy."""
    if style == "short":
        prompt = f"""מתוך טקסט האריזה באנגלית, כתוב תוכן שיווקי **מינימליסטי** בעברית לאתר איקומרס.

טקסט האריזה:
{packaging_text}

המבנה:
1. שורת כותרת ראשית: תיאור המוצר + מותג
2. פסקה קצרה (3-4 משפטים) על מה המוצר עושה ויתרונותיו העיקריים
3. 3-4 bullets על התכונות הבולטות ביותר

טון שיווקי מקצועי, תמציתי. החזר רק את הטקסט בעברית, בלי הסברים."""
    else:
        prompt = MARKETING_TEMPLATE.format(packaging_text=packaging_text)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return len(doc)


def resize_to_square(img_bytes: bytes, size: int | None = None) -> bytes:
    """Crop image to center square and resize. If size is None, keep original resolution."""
    img = Image.open(io.BytesIO(img_bytes))
    side = min(img.width, img.height)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    if size and img.width != size:
        img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def remove_background(img_bytes: bytes) -> bytes:
    """Remove background using rembg. Returns PNG bytes with transparency."""
    from rembg import remove
    return remove(img_bytes)


def is_product_image(client: anthropic.Anthropic, img_bytes: bytes) -> bool:
    """Use Claude Vision to decide if an image is a clean product shot worth keeping.
    Filters out: designer PSD mockups, instructional diagrams, small logos/icons,
    images with overlaid instructional text, multi-product collages."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if max(img.size) > 800:
        ratio = 800 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": (
                    "Is this a clean product photograph suitable for use on an e-commerce website? "
                    "Reply NO if the image contains: overlaid instructional text like 'PSD', 'TRANSPARENT', 'MOCKUP'; "
                    "visible arrows or step-by-step diagrams; checkered transparency background; icons/logos only; "
                    "or a mosaic/collage of many different products. "
                    "Reply YES if it's a professional product shot, a clean food/lifestyle photo, or a clean product-in-use shot. "
                    "Reply with only the single word YES or NO."
                )},
            ],
        }],
    )
    answer = msg.content[0].text.strip().upper()
    return answer.startswith("Y")


def generate_hebrew_from_images(client: anthropic.Anthropic, img_bytes_list: list[bytes], style: str = "short") -> str:
    """Generate Hebrew marketing copy from one or more product images."""
    content_blocks = []
    for raw in img_bytes_list:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if max(img.size) > 1200:
            ratio = 1200 / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode()
        content_blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})

    if style == "long":
        instruction = (
            f"קיבלת {len(img_bytes_list)} תמונות של אותו מוצר חשמלי למטבח (המוצר עצמו + אביזרים נלווים / זוויות שונות). "
            "למד על המוצר מכל התמונות יחד וכתוב תוכן שיווקי **מפורט וארוך** בעברית לאתר איקומרס.\n\n"
            "המבנה (3-4 פסקאות):\n"
            "1. שורת כותרת ראשית: תיאור המוצר + שם/מותג אם נראה\n"
            "2. פסקה ראשית: מה המוצר עושה, יתרונות מרכזיים, אופן שימוש - פסקה רציפה וזורמת\n"
            "3. פסקת ביצועים ועמידות: חומרים, עיצוב, איכות בנייה (רק מה שרואים)\n"
            "4. פסקת תכונות: אביזרים נלווים (אם יש בתמונות!), עיצוב, קלות תפעול\n\n"
            "טון שיווקי נלהב ומקצועי, כמו פרסומת אמיתית. "
            "אם אתה רואה אביזרים נלווים (מסננות, תוספות, כיסויים) - הזכר אותם. "
            "אל תמציא מפרט טכני שאתה לא רואה. החזר רק את הטקסט השיווקי בעברית."
        )
    else:
        instruction = (
            f"קיבלת {len(img_bytes_list)} תמונות של אותו מוצר חשמלי למטבח. "
            "למד על המוצר מכל התמונות יחד וכתוב תוכן שיווקי **מינימליסטי** בעברית.\n\n"
            "המבנה:\n"
            "1. שורת כותרת ראשית: סוג המוצר + שם/מותג אם נראה\n"
            "2. פסקה קצרה (3-4 משפטים) על מה המוצר עושה ויתרונותיו\n"
            "3. 3-4 bullets על תכונות בולטות (חומרים, עיצוב, שימושיות, אביזרים אם יש)\n\n"
            "טון שיווקי מקצועי אך קצר ותמציתי. "
            "אם אתה רואה אביזרים נלווים בתמונות - הזכר אותם בקצרה. "
            "אל תמציא מפרט טכני שאתה לא רואה. החזר רק את הטקסט השיווקי בעברית."
        )
    content_blocks.append({"type": "text", "text": instruction})

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000 if style == "long" else 800,
        messages=[{"role": "user", "content": content_blocks}],
    )
    return msg.content[0].text


def create_zip(images: list[dict], hebrew_text: str, bg_removed: bool = False) -> bytes:
    """Pack product images + (optional) Hebrew text file into a ZIP."""
    ext = "png" if bg_removed else "jpg"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if hebrew_text:
            zf.writestr("marketing_content_he.txt", hebrew_text.encode("utf-8"))
        for i, img in enumerate(images):
            zf.writestr(f"product_image_{i+1}.{ext}", img["bytes"])
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────

st.markdown("## 📦 Packaging Extractor")
st.markdown("העלה PDF של אריזת מוצר וקבל תמונות נקיות + תוכן שיווקי בעברית")

with st.sidebar:
    st.markdown("### ⚙️ הגדרות")

    def _safe_secret(key: str) -> str:
        try:
            return st.secrets.get(key, "")
        except Exception:
            return ""

    default_key = _safe_secret("ANTHROPIC_API_KEY")
    if default_key:
        api_key = default_key
    else:
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

    st.markdown("---")
    st.markdown("**מה האפליקציה עושה:**")
    st.markdown("""
- 🖼️ שולפת תמונות מוצר נקיות מה-PDF
- 📝 קוראת את הטקסט האנגלי מהאריזה
- ✍️ ממירה לתוכן שיווקי בעברית
- 📥 מייצרת ZIP להורדה
    """)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="step-badge">1</span> העלאת קובץ</div>', unsafe_allow_html=True)

    upload_mode = st.radio(
        "סוג קלט",
        options=["PDF של אריזה", "תמונות מוצר"],
        horizontal=True,
    )

    if upload_mode == "PDF של אריזה":
        uploaded_files = st.file_uploader("גרור PDF של אריזת מוצר", type=["pdf"], label_visibility="collapsed", key="pdf_upl")
        uploaded = uploaded_files
        upload_count = 1 if uploaded else 0
    else:
        uploaded_files = st.file_uploader(
            "גרור תמונות מוצר (אפשר כמה - למשל מוצר + אביזרים)",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="img_upl",
        )
        uploaded = uploaded_files if uploaded_files else None
        upload_count = len(uploaded_files) if uploaded_files else 0

    if uploaded:
        if upload_mode == "PDF של אריזה":
            st.success(f"✅ {uploaded.name} ({uploaded.size // 1024} KB)")
        else:
            st.success(f"✅ הועלו {upload_count} תמונות: " + ", ".join(f.name for f in uploaded_files))

        st.markdown('<div class="section-title">הגדרות</div>', unsafe_allow_html=True)

        text_style = st.radio(
            "אורך טקסט שיווקי",
            options=["ללא תיאור שיווקי", "ארוך ומפורט", "קצר ומינימליסטי"],
            index=0,
            horizontal=True,
            help="ללא = רק תמונות מוצר, בלי טקסט בעברית (מהיר וחינמי). ארוך = 3-4 פסקאות. קצר = פסקה + bullets.",
        )

        image_size = st.radio(
            "גודל תמונות",
            options=["900x900", "גודל מקסימלי"],
            horizontal=True,
        )

        bg_choice = st.radio(
            "רקע התמונות",
            options=["רקע לבן", "רקע שקוף"],
            index=0,
            horizontal=True,
            help="לבן = הרקע המקורי מה-PDF (בדר\"כ לבן). שקוף = הסרת רקע אוטומטית והוצאת PNG עם שקיפות.",
        )
        remove_bg = bg_choice == "רקע שקוף"

        run_btn = st.button("🚀 עבד", use_container_width=True)
    else:
        run_btn = False
        text_style = "ארוך ומפורט"
        remove_bg = False
        st.info("📂 ממתין לקובץ...")
    st.markdown('</div>', unsafe_allow_html=True)

if run_btn and uploaded:
    if not api_key:
        st.error("הכנס Anthropic API Key בסרגל השמאלי")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)

    if upload_mode == "PDF של אריזה":
        file_bytes = uploaded.read()
        display_filename = uploaded.name
    else:
        all_image_bytes = [f.read() for f in uploaded_files]
        display_filename = Path(uploaded_files[0].name).stem + "_multi"

    skip_hebrew = text_style == "ללא תיאור שיווקי"
    style_arg = "long" if text_style == "ארוך ומפורט" else "short"

    try:
        if upload_mode == "תמונות מוצר":
            # === MULTI-IMAGE MODE ===
            with col1:
                with st.status(f"מעבד {len(all_image_bytes)} תמונות...", expanded=True) as status:
                    target_size = 900 if image_size == "900x900" else None
                    images = []
                    for i, raw in enumerate(all_image_bytes):
                        resized = resize_to_square(raw, target_size)
                        pil = Image.open(io.BytesIO(resized))
                        images.append({"bytes": resized, "width": pil.width, "height": pil.height, "xref": i})
                    status.update(label=f"{len(images)} תמונות מעובדות", state="complete")

                bg_removed = False
                if remove_bg:
                    with st.status("מסיר רקע מתמונות...", expanded=True) as status:
                        for i, img in enumerate(images):
                            img["bytes"] = remove_background(img["bytes"])
                            status.update(label=f"מסיר רקע... ({i+1}/{len(images)})")
                        bg_removed = True
                        status.update(label="רקע הוסר בהצלחה!", state="complete")

                hebrew_content = ""
                if not skip_hebrew:
                    with st.status(f"מייצר תוכן שיווקי ({text_style}) בעברית מכל התמונות...", expanded=True) as status:
                        hebrew_content = generate_hebrew_from_images(client, [img["bytes"] for img in images], style=style_arg)
                        status.update(label="תוכן שיווקי מוכן!", state="complete")

                packaging_text = ""

            st.session_state["results"] = {
                "images": images,
                "packaging_text": packaging_text,
                "hebrew_content": hebrew_content,
                "filename": display_filename,
                "bg_removed": bg_removed,
            }

        else:
            # === PDF MODE ===
            pdf_bytes = file_bytes
            with col1:
                with st.status("שולף תמונות מה-PDF...", expanded=True) as status:
                    raw_images = extract_images_from_pdf(pdf_bytes)
                    status.update(label=f"נמצאו {len(raw_images)} תמונות, מסנן...")

                    images = []
                    for i, img in enumerate(raw_images):
                        status.update(label=f"מסנן תמונות ({i+1}/{len(raw_images)})...")
                        try:
                            if is_product_image(client, img["bytes"]):
                                images.append(img)
                        except Exception:
                            images.append(img)

                    target_size = 900 if image_size == "900x900" else None
                    for img in images:
                        img["bytes"] = resize_to_square(img["bytes"], target_size)
                        pil = Image.open(io.BytesIO(img["bytes"]))
                        img["width"], img["height"] = pil.width, pil.height
                    status.update(label=f"{len(images)} תמונות מוצר איכותיות (סוננו {len(raw_images)-len(images)})", state="complete")

                bg_removed = False
                if remove_bg:
                    with st.status("מסיר רקע מתמונות...", expanded=True) as status:
                        for i, img in enumerate(images):
                            img["bytes"] = remove_background(img["bytes"])
                            status.update(label=f"מסיר רקע... ({i+1}/{len(images)})")
                        bg_removed = True
                        status.update(label="רקע הוסר בהצלחה!", state="complete")

                packaging_text = ""
                hebrew_content = ""
                if not skip_hebrew:
                    with st.status("קורא טקסט מהאריזה...", expanded=True) as status:
                        num_pages = get_pdf_page_count(pdf_bytes)
                        page_jpegs = []
                        for p in range(1, num_pages + 1):
                            page_jpegs.append(rasterize_pdf_page(pdf_bytes, page=p, dpi=200))
                        packaging_text = extract_packaging_text(client, page_jpegs)
                        status.update(label=f"טקסט אריזה חולץ ({num_pages} עמודים)", state="complete")

                    with st.status(f"מייצר תוכן שיווקי ({text_style}) בעברית...", expanded=True) as status:
                        hebrew_content = generate_hebrew_content(client, packaging_text, style=style_arg)
                        status.update(label="תוכן שיווקי מוכן!", state="complete")

            st.session_state["results"] = {
                "images": images,
                "packaging_text": packaging_text,
                "hebrew_content": hebrew_content,
                "filename": display_filename,
                "bg_removed": bg_removed,
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

# ── Show results ──
results = st.session_state.get("results")
if results:
    images = results["images"]
    packaging_text = results["packaging_text"]
    hebrew_content = results["hebrew_content"]
    filename = results["filename"]
    bg_removed = results.get("bg_removed", False)

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

        download_step = 3
        if hebrew_content:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title"><span class="step-badge">3</span> תוכן שיווקי – עברית</div>', unsafe_allow_html=True)

            if packaging_text:
                with st.expander("טקסט אנגלי שחולץ מהאריזה"):
                    st.text(packaging_text)

            st.markdown(f'<div class="hebrew-content">{hebrew_content.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            st.code(hebrew_content, language=None)
            st.markdown('</div>', unsafe_allow_html=True)
            download_step = 4

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title"><span class="step-badge">{download_step}</span> הורדה</div>', unsafe_allow_html=True)
        zip_bytes = create_zip(images, hebrew_content, bg_removed)
        zip_label = "הורד ZIP (תמונות + תוכן עברי)" if hebrew_content else "הורד ZIP (תמונות)"
        st.download_button(
            label=zip_label,
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
