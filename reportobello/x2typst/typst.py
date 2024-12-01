from __future__ import annotations
from collections import defaultdict

from dataclasses import field, dataclass
from typing import Any, ClassVar
import re

from .core import parse_complex_text_node
from .node import *


@dataclass(unsafe_hash=True)
class Font:
    family: str = ""
    filename: str = ""
    weight: int = -1

    @property
    def is_bold(self) -> bool:
        return self.filename.endswith("-Bold")


@dataclass(unsafe_hash=True)
class Text:
    bbox: tuple[float, float, float, float]
    font: str = ""
    size: float = 0
    color: tuple[int, int, int, float] = field(default=(0, 0, 0, 1))
    chars: str = ""


URL_ONLY_REGEX = re.compile(r"\[\]\(([^()]*)\)")
CUSTOM_URL_REGEX = re.compile(r"\[([^[\]]*)\]\(([^()]*)\)")


def escape(s: str) -> str:
    return (
        s
            .replace("$", r"\$")
            .replace("#", r"\#")
            .replace("@", r"\@")
            .replace("<", r"\<")
    )


PLACEHOLDER_HEADER_NAME = re.compile(r"Col\d+")


class TypstGeneratorVisitor(NodeVisitor[str]):
    tables: list[Any]
    boilerplate: list[str]

    def __init__(self, pdf_table_cells: dict[tuple[int, int, int], list[Text]], most_common_font_size: float) -> None:
        self.tables = []

        self.pdf_table_cells = pdf_table_cells
        self.most_common_font_size = most_common_font_size
        self.table_index = -1

        self.boilerplate = []
        self.includes_links = False
        self.includes_quotes = False

    alignment_to_style: ClassVar[dict[HeaderAlignment, str]] = {
        HeaderAlignment.DEFAULT: "left",
        HeaderAlignment.LEFT: "left",
        HeaderAlignment.CENTER: "center",
        HeaderAlignment.RIGHT: "right",
    }

    def visit_comment_node(self, node: CommentNode) -> str:
        return ""

    def visit_bullet_list_node(self, node: BulletNode) -> str:
        lines = [line.accept(self) for line in node.data]

        return "\n".join(f"- {line}" for line in lines)

    def visit_num_list_node(self, node: NumListNode) -> str:
        lines = [line.accept(self) for line in node.data]

        return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines))

    def visit_text_node(self, node: TextNode) -> str:
        # TODO: this is a PyMuPDF implementation detail, move to a different pass
        if node.contents == "-----":
            return "#pagebreak(weak: true)"

        return escape(node.contents).replace("\n", "\\\n")

    def visit_complex_text_node(self, node: ComplextTextNode) -> str:
        segments = [part.accept(self) for part in node.parts]

        return "".join(segments)

    def visit_bold_text_node(self, node: BoldTextNode) -> str:
        segments = [part.accept(self) for part in node.parts]

        return f"*{''.join(segments)}*"

    def visit_italic_text_node(self, node: ItalicTextNode) -> str:
        segments = [part.accept(self) for part in node.parts]

        return f"_{''.join(segments)}_"

    def visit_strikethrough_text_node(self, node: StrikethroughTextNode) -> str:
        segments = [part.accept(self) for part in node.parts]

        return f"#strike[{''.join(segments)}]"

    def visit_inline_code_text_node(self, node: InlineCodeTextNode) -> str:
        return f"`{node.contents}`"

    def visit_url_text_node(self, node: UrlTextNode) -> str:
        text = node.text.accept(self)

        if node.url:
            return f'#link("{node.url}")[{text}]'

        if not self.includes_links:
            self.includes_links = True
            self.boilerplate.append("#show link: underline")

        return f'#link("{text}")[{text}]'


    def visit_codeblock_node(self, node: CodeblockNode) -> str:
        if node.language:
            return f"```{node.language}\n{node.contents}\n```"

        return f"```\n{node.contents}\n```"

    # TODO: once HTML to Typst is implemented, add a nested generator here.
    def visit_html_node(self, node: HtmlNode) -> str:
        return f"```html\n{node.contents}\n```"

    def visit_header_node(self, node: HeaderNode) -> str:
        text = node.text.accept(self)

        return f"{'=' * node.level} {text}"

    def visit_newline_node(self, node: NewlineNode) -> str:
        return ""

    def visit_divider_node(self, node: DividerNode) -> str:
        return ""

    def visit_blockquote_node(self, node: BlockquoteNode) -> str:
        text = node.text.accept(self)

        if not self.includes_quotes:
            self.includes_quotes = True
            self.boilerplate.append("#set quote(block: true)")

        return f"#quote[{text}]"

    def visit_table_node(self, node: TableNode) -> str:
        self.table_index += 1

        header: list[str] = []

        for i, cell in enumerate(node.header):
            pdf_cell = self.pdf_table_cells.get((self.table_index, 0, i))

            # TODO: this is PyMuPDF specific change, move to a dedicated pass
            if PLACEHOLDER_HEADER_NAME.match(cell.name):
                cell = ""

            else:
                # TODO: move parser layer
                cell = parse_complex_text_node(cell.name).accept(self)

            args = []

            if pdf_cell and len(pdf_cell) == 1:
                # TODO: clean this up
                if pdf_cell[0].font.endswith("-Bold"):
                    cell = f"*{cell}*"

                if pdf_cell[0].size != self.most_common_font_size:
                    args.append(f"size: {pdf_cell[0].size}pt")

            # TODO: don't assume all headers are center aligned
            cell = f'\t\talign(center)[{cell}],'

            header.append(cell)

        col_bbox_left = defaultdict[int, list[float]](list)
        col_bbox_right = defaultdict[int, list[float]](list)

        for (table_id, row, col), pdf_cell in self.pdf_table_cells.items():
            if row == 0 or table_id != self.table_index:
                continue

            x1, _, x2, _ = pdf_cell[0].bbox

            col_bbox_left[col].append(x1)
            col_bbox_right[col].append(x2)

        def max_diff(nums: list[float]) -> float:
            return max(nums) - min(nums)

        # TODO: detect center aligned bboxes as well
        for col, bbox in col_bbox_left.items():
            if max_diff(bbox) < 0.5:
                node.header[col].alignment = HeaderAlignment.LEFT

        for col, bbox in col_bbox_right.items():
            if max_diff(bbox) < 0.5:
                node.header[col].alignment = HeaderAlignment.RIGHT

        # TODO: clean this up
        for (col, bbox_left), (_, bbox_right) in zip(col_bbox_left.items(), col_bbox_right.items()):
            avgs = []

            for lhs, rhs in zip(bbox_left, bbox_right):
                avgs.append((lhs + rhs) / 2)

            if max_diff(avgs) < 0.5:
                node.header[col].alignment = HeaderAlignment.CENTER

        self.tables.append(node.rows)

        columns = ", ".join(["auto"] * len(node.header))
        alignments = ", ".join([self.alignment_to_style[x.alignment] for x in node.header])

        if len(node.header) == 1:
            columns += ","
            alignments += ","

        columns = f"\tcolumns: ({columns}),"
        align = f"\talign: ({alignments}),"

        return "\n".join([
            f"#table(",
            columns,
            align,
            "\ttable.header(",
            *header,
            "\t),",
            f"\t..data.tables.at({self.table_index}).flatten(),",
            ")",
        ])


def markdown_to_typst(nodes: list[Node], table_cells: dict[tuple[int, int, int], list[Text]], most_common_font_size: float) -> tuple[str, dict[str, Any]]:
    visitor = TypstGeneratorVisitor(table_cells, most_common_font_size)

    segments = [node.accept(visitor) for node in nodes]

    if visitor.boilerplate:
        segments = [*visitor.boilerplate, *segments]

    data = {
        "tables": visitor.tables,
    }

    template = "\n".join(segments)

    return template, data
