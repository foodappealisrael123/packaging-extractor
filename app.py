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
import gc
import shutil

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
    """Pad the image with white to a square canvas (max dimension), then resize.
    Preserves the entire product — no cropping. If size is None, keep the padded resolution."""
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode == "RGBA":
        white = Image.new("RGB", img.size, (255, 255, 255))
        white.paste(img, mask=img.split()[3])
        img = white
    else:
        img = img.convert("RGB")
    if size and max(img.size) > size:
        img.thumbnail((size, size), Image.LANCZOS)  # shrink before padding to save memory
    side = max(img.width, img.height)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    offset_x = (side - img.width) // 2
    offset_y = (side - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))
    if size and canvas.width != size:
        canvas = canvas.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@st.cache_resource
def get_rembg_session():
    """Load a lightweight rembg model once. Newer rembg versions default to
    bria-rmbg (~1GB), which crashes Streamlit Cloud's memory limit."""
    import onnxruntime as ort
    from rembg import new_session
    opts = ort.SessionOptions()
    opts.enable_cpu_mem_arena = False  # the arena only grows; never hands memory back
    opts.enable_mem_pattern = False
    return new_session("isnet-general-use", sess_opts=opts)


MASK_WORK_SIDE = 1024  # isnet runs at 1024×1024 internally, so a bigger input adds no detail


def _foreground_mask(img: Image.Image) -> Image.Image:
    """Run rembg on a small copy and scale the mask back up. rembg's own
    full-resolution post-processing is what pushed memory over the limit."""
    from rembg import remove
    small = img.convert("RGB")
    if max(small.size) > MASK_WORK_SIDE:
        small.thumbnail((MASK_WORK_SIDE, MASK_WORK_SIDE), Image.LANCZOS)
    mask = remove(small, session=get_rembg_session(), only_mask=True)
    return mask.convert("L").resize(img.size, Image.LANCZOS)


def remove_background(img_bytes: bytes) -> bytes:
    """Remove background using rembg. Returns PNG bytes with transparency."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    out = img.convert("RGBA")
    out.putalpha(_foreground_mask(img))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def remove_background_to_white(img_bytes: bytes) -> bytes:
    """Remove background and composite the product onto a clean white canvas.
    Returns JPG bytes."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    white = Image.new("RGB", img.size, (255, 255, 255))
    white.paste(img, mask=_foreground_mask(img))
    buf = io.BytesIO()
    white.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


FSRCNN_URL = "https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x{scale}.pb"
MAX_UPSCALED_SIDE = 3000  # keeps memory within Streamlit Cloud's limit


@st.cache_resource
def get_upscaler(scale: int):
    """Load the FSRCNN super-resolution model (~40KB) once per scale."""
    import cv2
    import urllib.request
    model_path = Path(tempfile.gettempdir()) / f"FSRCNN_x{scale}.pb"
    if not model_path.exists():
        urllib.request.urlretrieve(FSRCNN_URL.format(scale=scale), model_path)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(model_path))
    sr.setModel("fsrcnn", scale)
    return sr


def _sr_tiled(sr, bgr, scale: int, tile: int = 384, pad: int = 8):
    """Run super-resolution in overlapping tiles so large images don't exhaust memory."""
    import numpy as np
    h, w = bgr.shape[:2]
    out = np.zeros((h * scale, w * scale, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, x0 = max(y - pad, 0), max(x - pad, 0)
            y1, x1 = min(y + tile + pad, h), min(x + tile + pad, w)
            up = sr.upsample(np.ascontiguousarray(bgr[y0:y1, x0:x1]))
            th, tw = (min(y + tile, h) - y) * scale, (min(x + tile, w) - x) * scale
            oy, ox = (y - y0) * scale, (x - x0) * scale
            out[y * scale:y * scale + th, x * scale:x * scale + tw] = up[oy:oy + th, ox:ox + tw]
    return out


def upscale_image(img_bytes: bytes, scale: int) -> tuple[bytes, bool]:
    """Upscale ×scale with FSRCNN (Lanczos fallback). Keeps transparency.
    Returns (bytes, used_ai). Output is capped at MAX_UPSCALED_SIDE."""
    import numpy as np
    img = Image.open(io.BytesIO(img_bytes))
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")

    side = max(img.size)
    out_side = min(side * scale, MAX_UPSCALED_SIDE)
    target = (round(img.width * out_side / side), round(img.height * out_side / side))
    rgb = img.convert("RGB")
    used_ai = True

    factor = out_side / side
    if factor < 1.5:
        # At/near the cap already – a plain high-quality resize is enough
        up_rgb = rgb.resize(target, Image.LANCZOS)
    else:
        # Smallest model scale that reaches the target; shrink the input so the
        # model never produces more pixels than needed (keeps memory low)
        model_scale = min(scale, max(2, -(-out_side // side)))
        need = -(-out_side // model_scale)
        src = rgb if need >= side else rgb.resize(
            (round(rgb.width * need / side), round(rgb.height * need / side)), Image.LANCZOS)
        try:
            sr = get_upscaler(model_scale)
            bgr = np.array(src)[:, :, ::-1]
            up_rgb = Image.fromarray(_sr_tiled(sr, bgr, model_scale)[:, :, ::-1].copy())
            if up_rgb.size != target:
                up_rgb = up_rgb.resize(target, Image.LANCZOS)
        except Exception:
            used_ai = False
            up_rgb = rgb.resize(target, Image.LANCZOS)

    buf = io.BytesIO()
    if has_alpha:
        up = up_rgb.convert("RGBA")
        up.putalpha(img.split()[3].resize(target, Image.LANCZOS))
        up.save(buf, format="PNG")
    else:
        up_rgb.save(buf, format="JPEG", quality=95)
    return buf.getvalue(), used_ai


def fit_to_size(img_bytes: bytes, size: int) -> bytes:
    """Resize a square image to size×size, keeping transparency if present."""
    img = Image.open(io.BytesIO(img_bytes))
    has_alpha = img.mode in ("RGBA", "LA")
    img = img.convert("RGBA" if has_alpha else "RGB").resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    if has_alpha:
        img.save(buf, format="PNG")
    else:
        img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def make_thumbnail(img_bytes: bytes, size: int = 360) -> bytes:
    img = Image.open(io.BytesIO(img_bytes))
    img.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def finish_images(raw_list: list[bytes], transparent: bool, scale: int, target_size: int | None,
                  out_dir: str, status, label_prefix: str = "") -> tuple[list[dict], bool]:
    """Square-pad → remove background → upscale → optional final resize.
    Full-size results are written to out_dir (not kept in memory); returns
    (images with path + thumbnail, all_used_ai)."""
    images = []
    all_ai = True
    for i, raw in enumerate(raw_list):
        status.update(label=f"{label_prefix}מסיר רקע ומגדיל תמונה {i+1}/{len(raw_list)}...")
        # Huge sources would blow the memory limit in rembg; the output is capped anyway
        side = max(Image.open(io.BytesIO(raw)).size)
        squared = resize_to_square(raw, MAX_UPSCALED_SIDE if side > MAX_UPSCALED_SIDE else None)
        clean = remove_background(squared) if transparent else remove_background_to_white(squared)
        del squared
        up, used_ai = upscale_image(clean, scale)
        del clean
        all_ai = all_ai and used_ai
        if target_size:
            up = fit_to_size(up, target_size)
        pil = Image.open(io.BytesIO(up))
        path = Path(out_dir) / f"{len(os.listdir(out_dir))}.{'png' if transparent else 'jpg'}"
        path.write_bytes(up)
        images.append({"path": str(path), "thumb": make_thumbnail(up), "width": pil.width, "height": pil.height})
        del up, pil
        gc.collect()
    return images, all_ai


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


def create_zip(groups: list[dict], ext: str, selected: set[tuple[int, int]] | None = None) -> bytes:
    """Pack images (+ Hebrew text per source file) into a ZIP, one folder per source.
    If `selected` is given, only those (group_idx, image_idx) pairs are included."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for g, group in enumerate(groups):
            folder = group["name"]
            picked = [i for i in range(len(group["images"])) if selected is None or (g, i) in selected]
            if not picked:
                continue
            if group["hebrew"]:
                zf.writestr(f"{folder}/marketing_content_he.txt", group["hebrew"].encode("utf-8"))
            for i in picked:
                zf.write(group["images"][i]["path"], f"{folder}/product_image_{i+1}.{ext}")
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

MAX_PDFS = 10
UPSCALE_OPTIONS = {"×2": 2, "×3": 3, "×4": 4}

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="step-badge">1</span> העלאת קבצים</div>', unsafe_allow_html=True)

    upload_mode = st.radio(
        "סוג קלט",
        options=["PDF של אריזה", "תמונות מוצר"],
        horizontal=True,
    )

    if upload_mode == "PDF של אריזה":
        uploaded_files = st.file_uploader(
            f"גרור עד {MAX_PDFS} קבצי PDF של אריזות",
            type=["pdf"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="pdf_upl",
        )
    else:
        uploaded_files = st.file_uploader(
            "גרור תמונות מוצר (אפשר כמה - למשל מוצר + אביזרים)",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="img_upl",
        )
    uploaded_files = uploaded_files or []
    too_many = upload_mode == "PDF של אריזה" and len(uploaded_files) > MAX_PDFS

    if uploaded_files:
        kind = "קבצי PDF" if upload_mode == "PDF של אריזה" else "תמונות"
        if too_many:
            st.error(f"הועלו {len(uploaded_files)} קבצים – אפשר עד {MAX_PDFS} בבת אחת. הסר חלק מהקבצים.")
        else:
            st.success(f"✅ הועלו {len(uploaded_files)} {kind}: " + ", ".join(f.name for f in uploaded_files))

        st.markdown('<div class="section-title">הגדרות</div>', unsafe_allow_html=True)

        text_style = st.radio(
            "אורך טקסט שיווקי",
            options=["ללא תיאור שיווקי", "ארוך ומפורט", "קצר ומינימליסטי"],
            index=0,
            horizontal=True,
            help="ללא = רק תמונות מוצר, בלי טקסט בעברית (מהיר וחינמי). ארוך = 3-4 פסקאות. קצר = פסקה + bullets. "
                 "במצב PDF נכתב טקסט נפרד לכל קובץ.",
        )

        upscale_choice = st.radio(
            "הגדלת רזולוציה (Upscale)",
            options=list(UPSCALE_OPTIONS),
            index=0,
            horizontal=True,
            help=f"הגדלה חכמה (AI) של כל תמונה. הצד הארוך מוגבל ל-{MAX_UPSCALED_SIDE}px.",
        )

        image_size = st.radio(
            "גודל תמונות סופי",
            options=["גודל מקסימלי (אחרי הגדלה)", "900x900"],
            horizontal=True,
        )

        bg_choice = st.radio(
            "רקע התמונות",
            options=["רקע לבן", "רקע שקוף"],
            index=0,
            horizontal=True,
            help="בשתי האופציות הרקע המקורי מוסר אוטומטית. לבן = המוצר על קנבס לבן נקי (JPG). שקוף = המוצר עם שקיפות (PNG).",
        )
        transparent_output = bg_choice == "רקע שקוף"

        run_btn = st.button("🚀 עבד", use_container_width=True, disabled=too_many)
    else:
        run_btn = False
        st.info("📂 ממתין לקבצים...")
    st.markdown('</div>', unsafe_allow_html=True)

if run_btn and uploaded_files and not too_many:
    if not api_key:
        st.error("הכנס Anthropic API Key בסרגל השמאלי")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    skip_hebrew = text_style == "ללא תיאור שיווקי"
    style_arg = "long" if text_style == "ארוך ומפורט" else "short"
    scale = UPSCALE_OPTIONS[upscale_choice]
    target_size = 900 if image_size == "900x900" else None

    # Full-size outputs live on disk; drop the previous run's folder and results first
    st.session_state.pop("zip_ready", None)
    old = st.session_state.pop("results", None)
    if old and old.get("out_dir"):
        shutil.rmtree(old["out_dir"], ignore_errors=True)
    gc.collect()
    out_dir = tempfile.mkdtemp(prefix="pe_")

    groups = []
    all_ai = True
    try:
        with col1:
            if upload_mode == "תמונות מוצר":
                # === MULTI-IMAGE MODE: all images are one product ===
                all_image_bytes = [f.read() for f in uploaded_files]
                with st.status(f"מעבד {len(all_image_bytes)} תמונות...", expanded=True) as status:
                    images, used_ai = finish_images(all_image_bytes, transparent_output, scale, target_size,
                                                    out_dir, status)
                    all_ai = all_ai and used_ai
                    hebrew_content = ""
                    if not skip_hebrew:
                        status.update(label=f"מייצר תוכן שיווקי ({text_style}) בעברית...")
                        hebrew_content = generate_hebrew_from_images(
                            client, [Path(img["path"]).read_bytes() for img in images], style=style_arg)
                    status.update(label=f"{len(images)} תמונות מוכנות", state="complete")
                groups.append({
                    "name": Path(uploaded_files[0].name).stem + "_multi",
                    "images": images,
                    "hebrew": hebrew_content,
                    "packaging_text": "",
                })
            else:
                # === PDF MODE: each PDF is processed separately ===
                total = len(uploaded_files)
                used_names = set()
                for n, f in enumerate(uploaded_files, start=1):
                    prefix = f"[{n}/{total}] {f.name}: "
                    pdf_bytes = f.read()
                    with st.status(f"{prefix}שולף תמונות...", expanded=False) as status:
                        raw_images = extract_images_from_pdf(pdf_bytes)
                        kept = []
                        for i, img in enumerate(raw_images):
                            status.update(label=f"{prefix}מסנן תמונות ({i+1}/{len(raw_images)})...")
                            try:
                                if is_product_image(client, img["bytes"]):
                                    kept.append(img["bytes"])
                            except Exception:
                                kept.append(img["bytes"])

                        filtered_out = len(raw_images) - len(kept)
                        del raw_images
                        images, used_ai = finish_images(kept, transparent_output, scale, target_size,
                                                        out_dir, status, prefix)
                        del kept
                        all_ai = all_ai and used_ai

                        packaging_text = ""
                        hebrew_content = ""
                        if not skip_hebrew:
                            status.update(label=f"{prefix}קורא טקסט מהאריזה...")
                            num_pages = get_pdf_page_count(pdf_bytes)
                            page_jpegs = [rasterize_pdf_page(pdf_bytes, page=p, dpi=200) for p in range(1, num_pages + 1)]
                            packaging_text = extract_packaging_text(client, page_jpegs)
                            status.update(label=f"{prefix}מייצר תוכן שיווקי בעברית...")
                            hebrew_content = generate_hebrew_content(client, packaging_text, style=style_arg)

                        status.update(
                            label=f"{prefix}{len(images)} תמונות מוכנות (סוננו {filtered_out})",
                            state="complete",
                        )

                    name = Path(f.name).stem
                    while name in used_names:
                        name += "_"
                    used_names.add(name)
                    groups.append({
                        "name": name,
                        "images": images,
                        "hebrew": hebrew_content,
                        "packaging_text": packaging_text,
                    })

        st.session_state["run_id"] = st.session_state.get("run_id", 0) + 1
        st.session_state["results"] = {
            "groups": groups,
            "ext": "png" if transparent_output else "jpg",
            "zip_name": Path(uploaded_files[0].name).stem if len(uploaded_files) == 1 else "packaging_batch",
            "scale": scale,
            "all_ai": all_ai,
            "out_dir": out_dir,
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
def _set_all_selection(keys: list[str], value: bool):
    for k in keys:
        st.session_state[k] = value


@st.fragment
def render_gallery(results: dict, run_id: int):
    """Image grid with per-image checkboxes + download buttons.
    A fragment, so ticking a checkbox doesn't rerun the whole app."""
    groups = results["groups"]
    ext = results["ext"]
    keys = {(g, i): f"sel_{run_id}_{g}_{i}" for g, group in enumerate(groups) for i in range(len(group["images"]))}

    b1, b2 = st.columns(2)
    b1.button("☑️ בחר הכל", on_click=_set_all_selection, args=(list(keys.values()), True), use_container_width=True)
    b2.button("✖️ נקה בחירה", on_click=_set_all_selection, args=(list(keys.values()), False), use_container_width=True)

    for g, group in enumerate(groups):
        st.markdown(f"**📄 {group['name']}** – {len(group['images'])} תמונות")
        if not group["images"]:
            st.caption("לא נמצאו תמונות מוצר בקובץ הזה")
            continue
        cols = st.columns(3)
        for i, img in enumerate(group["images"]):
            with cols[i % 3]:
                st.image(img["thumb"], use_container_width=True)
                st.checkbox(f"תמונה {i+1} · {img['width']}×{img['height']}", key=keys[(g, i)])

    selected = {gi for gi, k in keys.items() if st.session_state.get(k)}
    st.markdown("---")
    has_text = any(group["hebrew"] for group in groups)

    # Two-step download: build the ZIP on demand, then hand it over as plain bytes.
    # Only one prepared ZIP is held in memory, and it's dropped once it no longer
    # matches what's on screen.
    c1, c2 = st.columns(2)
    if c1.button(f"📦 הכן את כל התמונות ({len(keys)})", use_container_width=True, disabled=not keys):
        st.session_state["zip_ready"] = {
            "sig": (run_id, "all"),
            "data": create_zip(groups, ext),
            "name": f"{results['zip_name']}_processed.zip",
            "label": f"⬇️ הורד הכל ({len(keys)} תמונות{' + טקסטים' if has_text else ''})",
        }
    if c2.button(f"✅ הכן את הנבחרות ({len(selected)})", use_container_width=True, disabled=not selected):
        st.session_state["zip_ready"] = {
            "sig": (run_id, frozenset(selected)),
            "data": create_zip(groups, ext, selected),
            "name": f"{results['zip_name']}_selected.zip",
            "label": f"⬇️ הורד {len(selected)} תמונות נבחרות",
        }

    ready = st.session_state.get("zip_ready")
    if ready and ready["sig"] not in ((run_id, "all"), (run_id, frozenset(selected))):
        del st.session_state["zip_ready"]  # selection changed – stale ZIP
        ready = None
    if ready:
        st.download_button(
            label=ready["label"],
            data=ready["data"],
            file_name=ready["name"],
            mime="application/zip",
            use_container_width=True,
            type="primary",
            on_click="ignore",
        )
    else:
        st.caption("בחר תמונות (או הכל), לחץ \"הכן\" ואז יופיע כפתור ההורדה.")


results = st.session_state.get("results")
if results and "groups" in results:
    groups = results["groups"]
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">2</span> תמונות מוצר והורדה</div>', unsafe_allow_html=True)
        if not results["all_ai"]:
            st.warning("מודל ההגדלה החכמה לא נטען – חלק מהתמונות הוגדלו בשיטה רגילה (Lanczos).")
        render_gallery(results, st.session_state.get("run_id", 0))
        st.markdown('</div>', unsafe_allow_html=True)

        text_groups = [group for group in groups if group["hebrew"]]
        if text_groups:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title"><span class="step-badge">3</span> תוכן שיווקי – עברית</div>', unsafe_allow_html=True)
            for group in text_groups:
                with st.expander(f"📄 {group['name']}", expanded=len(text_groups) == 1):
                    if group["packaging_text"]:
                        with st.popover("טקסט אנגלי שחולץ מהאריזה"):
                            st.text(group["packaging_text"])
                    st.markdown(f'<div class="hebrew-content">{group["hebrew"].replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                    st.code(group["hebrew"], language=None)
            st.markdown('</div>', unsafe_allow_html=True)

elif not uploaded_files:
    with col2:
        st.markdown('<div class="card" style="min-height:300px; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#aaa;">', unsafe_allow_html=True)
        st.markdown("### 📦")
        st.markdown("תוצאות יופיעו כאן לאחר העיבוד")
        st.markdown('</div>', unsafe_allow_html=True)
