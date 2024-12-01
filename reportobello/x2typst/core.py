from collections.abc import Iterator
import re

from .node import *
from .pipe import pipe


def is_valid_table_row(row: str) -> bool:
    return bool(re.match(r"^\|.*\|$", row))


def iter_code_block(first: Node, nodes: Iterator[Node]) -> Node:
    lang = first.contents[3:]
    next_node = next(nodes, None)

    if not next_node:
        raise ValueError("codeblock end not reached")

    codeblock = next_node.contents

    for node in nodes:
        if node.contents.startswith("```"):
            return CodeblockNode(contents=codeblock, language=lang)

        codeblock += f"\n{node.contents}"

    raise ValueError("codeblock end not reached")


def iter_block_quote(
    first: Node, nodes: Iterator[Node]
) -> tuple[Node, Node | None]:
    blockquote = first.contents[2:]

    for node in nodes:
        if not node.contents.startswith("> "):
            return (BlockquoteNode(contents=blockquote), node)

        blockquote += f"\n{node.contents[2:]}"

    return (BlockquoteNode(contents=blockquote), None)


def iter_html_comment(first: Node, nodes: Iterator[Node]) -> Node:
    if first.contents.endswith("-->"):
        return CommentNode(contents=first.contents[4:-3])

    comment = first.contents[4:]

    for node in nodes:
        if node.contents.endswith("-->"):
            comment += f"\n{node.contents[:-3]}"
            next(nodes)
            return CommentNode(contents=comment)

        comment += f"\n{node.contents}"

    raise ValueError("html comment not closed")


def iter_table(first: Node, nodes: Iterator[Node]) -> tuple[Node, Node | None]:
    def split_row(row: str) -> list[str]:
        return [x.strip() for x in row.split("|")[1:-1]]

    separator_node = next(nodes, None)

    if not separator_node:
        raise ValueError("table missing required header separator")

    if not is_valid_table_row(separator_node.contents):
        raise ValueError("line must start and end with pipe")

    separator_cells = split_row(separator_node.contents)

    def is_valid_separator_cell(cell: str) -> bool:
        return bool(re.match("^:?-{3,}:?$", cell.strip()))

    if not all(is_valid_separator_cell(x) for x in separator_cells):
        raise ValueError(
            "header separator must have:\n\n"
            "* At least 3 dashes\n"
            "* (optional) starting/ending ':'\n"
            "* (optional) whitespace at start/end\n"
        )

    header = [HeaderCell(name) for name in split_row(first.contents)]

    if len(separator_cells) != len(header):
        raise ValueError(
            f"expected {len(header)} cells, got {len(separator_cells)} instead"
        )

    for i, name in enumerate(separator_cells):
        match (name.startswith(":"), name.endswith(":")):
            case (True, True):
                header[i].alignment = HeaderAlignment.CENTER
            case (True, False):
                header[i].alignment = HeaderAlignment.LEFT
            case (False, True):
                header[i].alignment = HeaderAlignment.RIGHT
            case _:
                header[i].alignment = HeaderAlignment.DEFAULT

    rows: list[list[str]] = []

    while node := next(nodes, None):
        if not is_valid_table_row(node.contents):
            return (TableNode(header=header, rows=rows), node)

        rows.append(split_row(node.contents))

    return (TableNode(header=header, rows=rows), None)


def group_blocked_nodes(nodes: list[Node]) -> list[Node]:
    grouped_nodes = []
    nodes = iter(nodes)

    for node in nodes:
        if node.contents.startswith("```"):
            grouped_nodes.append(iter_code_block(node, nodes))

        elif node.contents.startswith("> "):
            blockquote, leftover = iter_block_quote(node, nodes)
            grouped_nodes.append(blockquote)

            if leftover:
                grouped_nodes.append(leftover)

        elif node.contents.startswith("<!--"):
            grouped_nodes.append(iter_html_comment(node, nodes))

        elif is_valid_table_row(node.contents):
            table, leftover = iter_table(node, nodes)
            grouped_nodes.append(table)

            if leftover:
                grouped_nodes.append(leftover)

        else:
            grouped_nodes.append(node)

    return grouped_nodes


def classify_node(node: Node) -> Node:
    if node.is_classified():
        return node

    if node.contents.startswith("# "):
        return HeaderNode(level=1, contents=node.contents[2:])

    if node.contents.startswith("## "):
        return HeaderNode(level=2, contents=node.contents[3:])

    if node.contents.startswith("### "):
        return HeaderNode(level=3, contents=node.contents[4:])

    if node.contents.startswith("#### "):
        return HeaderNode(level=4, contents=node.contents[5:])

    if not node.contents:
        return NewlineNode()

    stripped = node.contents.strip()

    if stripped.startswith(("* ", "- ")):
        return BulletNode(contents=node.contents[2:].strip())

    if stripped.startswith("<"):
        return HtmlNode(contents=node.contents)

    if re.match(r"^\d+\. ", stripped):
        item = node.contents.lstrip()

        return NumListNode(contents=item[item.index(" ") + 1 :])

    if node.contents.startswith("- [ ] "):
        return CheckboxNode(checked=False, contents=node.contents[6:])

    if node.contents.startswith("- [x] "):
        return CheckboxNode(checked=True, contents=node.contents[6:])

    if node.contents == "---":
        return DividerNode()

    return TextNode(contents=node.contents)


class FixupComplexNodeVisitor(NodeVisitor[None]):
    def visit_complex_text_node(self, node: ComplextTextNode) -> None:
        self.combine_text_nodes(node)

    def visit_text_node(self, node: TextNode) -> None:
        return None

    def visit_inline_code_text_node(self, node: InlineCodeTextNode) -> None:
        return None

    def visit_bold_text_node(self, node: BoldTextNode) -> None:
        self.combine_text_nodes(node)

    def visit_strikethrough_text_node(self, node: StrikethroughTextNode) -> None:
        self.combine_text_nodes(node)

    def visit_italic_text_node(self, node: ItalicTextNode) -> None:
        self.combine_text_nodes(node)

    def visit_url_text_node(self, node: UrlTextNode) -> None:
        self.combine_text_nodes(node.text)

    def combine_text_nodes(self, node: ComplextTextNode) -> None:
        for n in node.parts:
            n.accept(self)

        if len(node.parts) <= 1:
            return

        modified = [node.parts[0]]

        for part in node.parts[1:]:
            # We use type() because we do not want to include subtypes
            if type(modified[-1]) is TextNode and type(part) is TextNode:
                modified[-1].contents += part.contents

            else:
                modified.append(part)

        node.parts = modified


def parse_complex_text_node(contents: str) -> ComplextTextNode:
    node = _parse_complex_text_node(iter(contents))

    visitor = FixupComplexNodeVisitor()
    node.accept(visitor)

    return node


def _parse_complex_text_node(contents: Iterator[str]) -> ComplextTextNode:
    stack = []
    chunk = ""

    for c in contents:
        if c == "\\":
            c = next(contents, None)

            if c:
                chunk += c

        elif c == "*":
            if chunk:
                stack.append(TextNode(contents=chunk))

            chunk = ""

            c = next(contents, None)

            if c is None:
                pass

            elif c == "*":
                stack.append(parse_bold_text_node(contents))

            else:
                stack.extend(parse_italic_text_node(c, contents))

        elif c == "`":
            if chunk:
                stack.append(TextNode(contents=chunk))

            chunk = ""

            stack.append(parse_inline_code_text_node(contents))

        elif c == "[":
            if chunk:
                stack.append(TextNode(contents=chunk))

            chunk = ""

            stack.append(parse_inline_url(contents))

        elif c == "~":
            if chunk:
                stack.append(TextNode(contents=chunk))

            chunk = ""

            stack.append(parse_inline_strikethrough_text_node(contents))

        else:
            chunk += c

    if chunk:
        stack.append(TextNode(contents=chunk))

    return ComplextTextNode(parts=stack)


def parse_italic_text_node(start: str, contents: Iterator[str]) -> list[Node]:
    chunk = start
    node = ItalicTextNode()
    nodes: list[Node] = [node]

    for c in contents:
        if c == "*":
            node.parts.append(TextNode(contents=chunk))
            chunk = ""

            c = next(contents, None)

            if c == "*":
                node.parts.append(parse_bold_text_node(contents))

            elif c:
                nodes.append(TextNode(contents=c))
                break

        else:
            chunk += c

    if chunk:
        node.parts.append(TextNode(contents=chunk))

    return nodes


def parse_bold_text_node(contents: Iterator[str]) -> BoldTextNode:
    chunk = ""
    parts = []

    for c in contents:
        if c == "*":
            parts.append(TextNode(contents=chunk))
            chunk = ""

            c = next(contents, None)

            if c == "*":
                break

            elif c:
                parts.extend(parse_italic_text_node(c, contents))

        else:
            chunk += c

    if chunk:
        parts.append(TextNode(contents=chunk))

    return BoldTextNode(parts=parts)


def parse_inline_code_text_node(contents: Iterator[str]) -> InlineCodeTextNode:
    chunk = ""

    for c in contents:
        if c == "`":
            break

        else:
            chunk += c

    return InlineCodeTextNode(contents=chunk)


def parse_inline_strikethrough_text_node(contents: Iterator[str]) -> Node:
    chunk = ""

    c = next(contents, None)

    if c is None:
        return TextNode(contents="~")

    # TODO: allow for escaped "~" chars in string
    for c in contents:
        if c == "~":
            break

        chunk += c

    # TODO: ensure this is "~"
    _ = next(contents, None)

    node = _parse_complex_text_node(iter(chunk))

    return StrikethroughTextNode(parts=node.parts)


def parse_inline_url(contents: Iterator[str]) -> Node:
    text = ""
    url = ""

    # TODO: allow for escaped "]" chars in string
    for c in contents:
        if c == "]":
            break

        text += c

    c = next(contents, None)

    if c != "(":
        node = _parse_complex_text_node(iter(text))

        node.parts = [
            TextNode(contents="["),
            *node.parts,
            TextNode(contents=f"]{c or ''}")
        ]

        return node

    for c in contents:
        # TODO: check for balanced brackets to support wikipedia URLs
        if c == ")":
            break

        url += c

    return UrlTextNode(
        # TODO: This is probably a better way of doing this
        text=_parse_complex_text_node(iter(text)),
        url=url or None,
    )


def classify_nodes(nodes: list[Node]) -> list[Node]:
    return [classify_node(node) for node in nodes]


def group_text_nodes(nodes: list[Node]) -> list[Node]:
    groups: list[Node] = []

    for node in nodes:
        if isinstance(node, TextNode):
            if not groups or not isinstance(groups[-1], TextNode):
                groups.append(node)

            else:
                groups[-1].contents += f"\n{node.contents}"

        else:
            groups.append(node)

    return groups


def group_html_nodes(nodes: list[Node]) -> list[Node]:
    groups: list[Node] = []

    for node in nodes:
        if isinstance(node, HtmlNode):
            if not groups or not isinstance(groups[-1], HtmlNode):
                groups.append(node)

            else:
                groups[-1].contents += f"\n{node.contents}"

        else:
            groups.append(node)

    return groups


def group_bullet_nodes(nodes: list[Node]) -> list[Node]:
    groups: list[Node] = []

    for node in nodes:
        if isinstance(node, BulletNode):
            if groups and isinstance(groups[-1], BulletNode):
                groups[-1].data.append(node.contents)

            # TODO: replace with match?
            elif (
                len(groups) >= 2
                and isinstance(groups[-2], BulletNode)
                and isinstance(groups[-1], NewlineNode)
            ):
                groups[-2].data.append(node.contents)

                groups.pop()

            else:
                groups.append(BulletNode(data=[node.contents]))

        else:
            groups.append(node)

    return groups


def group_number_list_nodes(nodes: list[Node]) -> list[Node]:
    groups: list[Node] = []

    for node in nodes:
        if isinstance(node, NumListNode):
            if groups and isinstance(groups[-1], NumListNode):
                groups[-1].data.append(node.contents)

            # TODO: replace with match?
            elif (
                len(groups) >= 2
                and isinstance(groups[-2], NumListNode)
                and isinstance(groups[-1], NewlineNode)
            ):
                groups[-2].data.append(node.contents)

                groups.pop()

            else:
                groups.append(NumListNode(data=[node.contents]))

        else:
            groups.append(node)

    return groups


def setup_nodes(markdown: str) -> list[Node]:
    return [Node(contents=line) for line in markdown.splitlines()]


def expand_text_nodes(nodes: list[Node]) -> list[Node]:
    return [
        parse_complex_text_node(node.contents) if isinstance(node, TextNode) else node
        for node in nodes
    ]


def markdown_to_nodes(markdown: str) -> list[Node]:
    return pipe(
        setup_nodes(markdown),
        group_blocked_nodes,
        classify_nodes,
        group_text_nodes,
        group_html_nodes,
        group_bullet_nodes,
        group_number_list_nodes,
        expand_text_nodes,
    )
