from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import json
import re
import math
import subprocess
from pathlib import Path
from typing import Any
from contextlib import redirect_stderr, redirect_stdout
from base64 import b64encode

import pymupdf4llm
import pymupdf.pro
import pymupdf
import fitz

from .node import *
from .core import markdown_to_nodes
from .typst import Font, escape, markdown_to_typst, Text


with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
    pymupdf.pro.unlock()


def load_installed_fonts() -> dict[str, Font]:
    stdout = subprocess.check_output(["fc-list", "-v"])  # noqa: S607

    fonts = {}

    current = Font()

    for line in stdout.splitlines():
        line = line.decode().strip()

        if not line:
            fonts[current.filename] = current
            current = Font()
            continue

        if line.startswith("family:"):
            if match := re.search(r'"(.*?)"', line):
                current.family = match.group(1)

        elif line.startswith("file:"):
            if match := re.search(r'"(.*?)"', line):
                current.filename = Path(match.group(1)).with_suffix("").name

        elif line.startswith("weight:"):  # noqa: SIM102
            if match := re.search(r"weight: ([0-9]+)", line):
                current.weight = int(match.group(1))

    fonts[current.filename] = current

    return fonts


FONTS = load_installed_fonts()


PAGE_SIZES: dict[tuple[float, float], str] = {
    (2383.94, 3370.39): "a0",
    (1683.78, 2383.94): "a1",
    (73.7, 104.88): "a10",
    (1190.55, 1683.78): "a2",
    (841.89, 1190.55): "a3",
    (595.28, 841.89): "a4",
    (419.53, 595.28): "a5",
    (297.64, 419.53): "a6",
    (209.76, 297.64): "a7",
    (147.4, 209.76): "a8",
    (104.88, 147.4): "a9",
    (2834.65, 4008.19): "iso-b0",
    (2004.09, 2834.65): "iso-b1",
    (87.87, 124.72): "iso-b10",
    (1417.32, 2004.09): "iso-b2",
    (1000.63, 1417.32): "iso-b3",
    (708.66, 1000.63): "iso-b4",
    (498.9, 708.66): "iso-b5",
    (354.33, 498.9): "iso-b6",
    (249.45, 354.33): "iso-b7",
    (175.75, 249.45): "iso-b8",
    (124.72, 175.75): "iso-b9",
    (2599.37, 3676.54): "iso-c0",
    (1836.85, 2599.37): "iso-c1",
    (79.37, 113.39): "iso-c10",
    (1298.27, 1836.85): "iso-c2",
    (918.43, 1298.27): "iso-c3",
    (649.13, 918.43): "iso-c4",
    (459.21, 649.13): "iso-c5",
    (323.15, 459.21): "iso-c6",
    (229.61, 323.15): "iso-c7",
    (161.57, 229.61): "iso-c8",
    (113.39, 161.57): "iso-c9",
    (2919.69, 4127.24): "jis-b0",
    (2063.62, 2919.69): "jis-b1",
    (90.71, 127.56): "jis-b10",
    (62.36, 90.71): "jis-b11",
    (45.35, 62.36): "jis-b12",
    (1459.84, 2063.62): "jis-b2",
    (1031.81, 1459.84): "jis-b3",
    (728.5, 1031.81): "jis-b4",
    (515.91, 728.5): "jis-b5",
    (362.83, 515.91): "jis-b6",
    (257.95, 362.83): "jis-b7",
    (181.42, 257.95): "jis-b8",
    (127.56, 181.42): "jis-b9",
    (521.57, 756.85): "us-executive",
    (612.28, 1009.13): "us-legal",
    (612.28, 790.87): "us-letter",
    (790.87, 1224.57): "us-tabloid",
}


def get_page_size(width: float, height: float, margin_x: float, margin_y: float) -> str | None:
    args = []

    tolerance = 0.01

    # TODO: optimize
    # TODO: also check if the page is flipped
    for (w, h), page_size in PAGE_SIZES.items():
        if (
            math.isclose(w, width, rel_tol=tolerance)
            and math.isclose(h, height, rel_tol=tolerance)
        ):
            args.append(f'"{page_size}"')

            break

    else:
        w = f"width: {round(width, 2)}pt"
        h = f"height: {round(height, 2)}pt"

        args.extend((w, h))

    args.append(f"margin: (x: {round(margin_x, 2)}pt, y: {round(margin_y, 2)}pt)")

    return f"#set page({', '.join(args)})"


def convert_file(filename: str) -> None:
    file = Path(filename)

    typst, data = convert_file_in_memory(file, extension=Path(filename).suffix)

    file.with_suffix(".typ").write_text(typst)
    file.with_name("data.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


def convert_file_in_memory(file: Path, extension: str = ".pdf") -> tuple[str, dict[str, Any]]:
    extension = extension.lower()

    if extension in {".pdf", ".docx", ".doc"}:
        return _convert_file_in_memory(file)

    if extension in {".md", ".markdown"}:
        return convert_markdown_file_in_memory(file.read_text(), font_family="DejaVu Sans")

    raise NotImplementedError


def extract_pdf_images(doc: pymupdf.Document) -> tuple[dict[int, tuple[str, bytes]], list[tuple[int, float, float]]]:
    img_info: dict[int, tuple[str, bytes]] = {}
    img_refs: list[tuple[int, float, float]] = []

    for page in doc.pages():
        page_img_info = {img["xref"]: img for img in page.get_image_info(xrefs=True)}  # type: ignore

        for img in page.get_images(full=True):
            img_xref = img[0]
            img_mask_xref = img[1]

            try:
                image_data = doc.extract_image(img_xref)
                root = fitz.Pixmap(image_data["image"])

                if img_mask_xref == 0:
                    # Image doesn't have a mask, so return image directly
                    masked = root

                else:
                    mask = fitz.Pixmap(doc.extract_image(img_mask_xref)["image"])
                    masked = fitz.Pixmap(root, mask)

                info = page_img_info.get(img_xref)

                if not info:
                    continue

                img_x1, img_y1, img_x2, img_y2 = info["bbox"]
                img_width = img_x2 - img_x1
                img_height = img_y2 - img_y1

                if img_xref not in img_info:
                    ext = "pam" if root.n > 3 else "png"

                    img_info[img_xref] = (ext, masked.tobytes(ext))

                img_refs.append((img_xref, img_width, img_height))

            except Exception:  # noqa: BLE001, S110
                # Image failed to extract, maybe show error in the future?
                pass

    return img_info, img_refs


# TODO: rename function
def _convert_file_in_memory(file: Path) -> tuple[str, dict[str, Any]]:
    font_family = None
    page = None
    title = None
    language = None

    # Get the top left-most text to determine margins (assuming margins are symmetric)
    min_x = None
    min_y = None

    # Get the most common font size so that we don't scatter redundant font sizes everywhere
    most_common_font_size = None

    with pymupdf.open(file) as f:
        # TODO: support multiple pages
        page = f[0]
        assert isinstance(page, pymupdf.Page)

        img_info, img_refs = extract_pdf_images(f)

        bbox_to_table_id: dict[tuple[float, float, float, float], tuple[int, int, int]] = {}

        table_id_to_cells = defaultdict[tuple[int, int, int], list[Text]](list)

        for table_number, table in enumerate(page.find_tables()):
            for row_number, row in enumerate(table.rows):
                for cell_number, cell in enumerate(row.cells):
                    if cell:
                        bbox_to_table_id[cell] = (table_number, row_number, cell_number)

        # TODO: should the mediabox be used or some other coordinate system?
        x1, y1, x2, y2 = page.mediabox

        metadata = getattr(f, "metadata", {})

        title = metadata.get("title", None)
        author = metadata.get("author", None)
        keywords = metadata.get("keywords", None)

        if "creationDate" in metadata:
            creation_date = metadata["creationDate"]
            created = (
                int(creation_date[2:6]),
                int(creation_date[6:8]),
                int(creation_date[8:10]),
            )

        else:
            created = None

        language = page.language

        for _, _, _, font_name, _, _ in page.get_fonts():
            font_family = font_name.split("+", maxsplit=1)[-1]
            font_family = font_family.split("-", maxsplit=1)[0]

            # Get the display name of a font from the filename, if we have it installed
            if font := FONTS.get(font_family):
                font_family = font.family

        # TODO: style text content based on this (ie, set font, bold text, etc)
        text_objects = []

        for text_object in page.get_texttrace():
            txt = Text(
                bbox=text_object["bbox"],
                font=text_object["font"],
                color=(*text_object["color"], text_object["opacity"]),
                size=text_object["size"],
                chars="".join(chr(x[0]) for x in text_object["chars"]),
            )

            text_objects.append(txt)

            # TODO: move to different function
            bx1, by1, bx2, by2 = text_object["bbox"]

            if min_x is None or bx1 < min_x:
                min_x = bx1
            if min_y is None or by1 < min_y:
                min_y = by1

            # TODO: optimize (use a quadtree?)
            for (tx1, ty1, tx2, ty2), table_id in bbox_to_table_id.items():
                if (
                    (tx1 < bx1 < bx2 < tx2)
                    and (ty1 < by1 < by2 < ty2)
                ):
                    table_id_to_cells[table_id].append(txt)

        most_common_font_size = 12.0

        # Clamp margin to (0pt, 100pt) as anything bigger is probably a sign of extra padding
        min_x = max(0, min(min_x or 0.0, 100.0))
        min_y = max(0, min(min_y or 0.0, 100.0))

        if text_objects:
            most_common_font_size = Counter(t.size for t in text_objects).most_common()[0][0]

        page = get_page_size(x2 - x1, y2 - y1, min_x or 0, min_y or 0)

    markdown = pymupdf4llm.to_markdown(
        file,
        # TODO: disable this for now until images are supported
        # write_images=True,  # noqa: ERA001
        margins=(0, 0, 0, 0),
        show_progress=False,
    )

    foss_font_map = {
        "helvetica": "Liberation Sans",
        "times-roman": "Liberation Serif",
        "courier": "Liberation Mono",
    }

    typst, data = convert_markdown_file_in_memory(
        markdown,
        page=page,
        title=title,
        author=author,
        keywords=keywords,
        created=created,
        font_family=foss_font_map.get((font_family or "").lower(), font_family),
        language=language,
        most_common_font_size=most_common_font_size,
        table_cells=table_id_to_cells,
    )

    if img_refs:
        typst = f'#import "@preview/based:0.1.0": base64\n\n{typst}\n'

        xref_to_index = {k: x for x, k in enumerate(img_info)}

        for xref, (ext, img) in img_info.items():
            typst += f'\n#let img_{xref_to_index[xref]} = image.decode(base64.decode("{b64encode(img).decode()}"), format: "{ext}", fit: "stretch", width: 100%)'

        for xref, width, height in img_refs:
            typst += f'\n#box(width: {round(width, 2)}pt, height: {round(height, 2)}pt, img_{xref_to_index[xref]})'

    return typst, data


def convert_markdown_file_in_memory(
    markdown: str,
    page: str | None = None,
    title: str | None = None,
    author: str | None = None,
    keywords: str | None = None,
    created: tuple[int, int, int] | None = None,
    font_family: str | None = None,
    language: str | None = None,
    most_common_font_size: float = 12.0,
    table_cells: dict[tuple[int, int, int], list[Text]] | None = None,
) -> tuple[str, dict[str, Any]]:
    nodes = markdown_to_nodes(markdown)

    # TODO: move args to context object
    typst, data = markdown_to_typst(nodes, table_cells or {}, most_common_font_size)

    # TODO: create a typst AST abstraction layer?
    typst = f'#import "@rpbl/util:0.0.1": *\n\n{typst}'

    if page:
        typst = f"{page}\n\n{typst}"

    document_args = []

    if title is not None:
        document_args.append(f"title: [{escape(title)}]")

    if author is not None:
        document_args.append(f'author: "{author}"')

    if keywords is not None:
        document_args.append(f'keywords: "{keywords}"')

    if created is not None:
        y, m, d = created

        document_args.append(f'date: datetime(year: {y}, month: {m}, day: {d})')

    if document_args:
        typst = f"#set document({', '.join(document_args)})\n\n{typst}"

    if font_family or language:
        # TODO: escape these
        args = (
            f"size: {round(most_common_font_size, 2)}pt" if most_common_font_size else "",
            f'lang: "{language}"' if language else "",
            f'font: "{font_family}"' if font_family else "",
        )

        typst = f'#set text({', '.join(arg for arg in args if arg)})\n\n{typst}'

    return typst, data


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(f"usage: {argv[0]} <FILE> [...FILES]")  # noqa: T201
        return

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(convert_file, filename) for filename in argv[1:]
        ]

        for future in futures:
            if ex := future.exception():
                raise ex
