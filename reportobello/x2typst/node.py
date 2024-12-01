from __future__ import annotations

from enum import auto, Enum
from dataclasses import dataclass, field
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(kw_only=True)
class Node:
    contents: str = ""

    def is_classified(self) -> bool:
        # since we know "node" derives from Node, we can check if the type is
        # anything other then Node, and if it is, we will know it is derived,
        # and thus is already classified.
        return type(self) != Node

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_node(self)  # pragma: no cover


@dataclass(kw_only=True)
class CommentNode(Node):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_comment_node(self)


@dataclass(kw_only=True)
class DataNode(Node):
    data: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class ListNode(DataNode):
    pass


@dataclass(kw_only=True)
class BulletNode(ListNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_bullet_list_node(self)


@dataclass(kw_only=True)
class NumListNode(ListNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_num_list_node(self)


@dataclass(kw_only=True)
class CheckboxNode(Node):
    checked: bool

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_checkbox_node(self)


@dataclass(kw_only=True)
class TextNode(Node):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_text_node(self)


@dataclass(kw_only=True)
class ComplextTextNode(Node):
    parts: list[ComplextTextNode | TextNode] = field(default_factory=list)

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_complex_text_node(self)


@dataclass(kw_only=True)
class UrlTextNode(Node):
    text: ComplextTextNode
    url: str | None
    is_image: bool = False

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_url_text_node(self)


@dataclass(kw_only=True)
class BoldTextNode(ComplextTextNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_bold_text_node(self)


@dataclass(kw_only=True)
class ItalicTextNode(ComplextTextNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_italic_text_node(self)


@dataclass(kw_only=True)
class StrikethroughTextNode(ComplextTextNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_strikethrough_text_node(self)


@dataclass(kw_only=True)
class InlineCodeTextNode(TextNode):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_inline_code_text_node(self)


@dataclass(kw_only=True)
class CodeblockNode(Node):
    language: str = ""

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_codeblock_node(self)


@dataclass(kw_only=True)
class HtmlNode(Node):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_html_node(self)


@dataclass(kw_only=True)
class HeaderNode(Node):
    level: int = 1

    text: ComplextTextNode = field(default_factory=ComplextTextNode)

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_header_node(self)


@dataclass(kw_only=True)
class NewlineNode(Node):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_newline_node(self)


@dataclass(kw_only=True)
class DividerNode(Node):
    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_divider_node(self)


@dataclass(kw_only=True)
class BlockquoteNode(Node):
    text: ComplextTextNode = field(default_factory=ComplextTextNode)

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_blockquote_node(self)


class HeaderAlignment(Enum):
    DEFAULT = auto()
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


@dataclass
class HeaderCell:
    name: str
    alignment: HeaderAlignment = HeaderAlignment.DEFAULT


@dataclass(kw_only=True)
class TableNode(Node):
    header: list[HeaderCell]
    rows: list[list[str]]

    def accept(self, visitor: NodeVisitor[T]) -> T:
        return visitor.visit_table_node(self)


class NodeVisitor(Generic[T]):
    def visit_node(self, node: Node) -> T:
        raise NotImplementedError

    def visit_comment_node(self, node: CommentNode) -> T:
        raise NotImplementedError

    def visit_bullet_list_node(self, node: BulletNode) -> T:
        raise NotImplementedError

    def visit_num_list_node(self, node: NumListNode) -> T:
        raise NotImplementedError

    def visit_checkbox_node(self, node: CheckboxNode) -> T:
        raise NotImplementedError

    def visit_text_node(self, node: TextNode) -> T:
        raise NotImplementedError

    def visit_complex_text_node(self, node: ComplextTextNode) -> T:
        raise NotImplementedError

    def visit_bold_text_node(self, node: BoldTextNode) -> T:
        raise NotImplementedError

    def visit_italic_text_node(self, node: ItalicTextNode) -> T:
        raise NotImplementedError

    def visit_strikethrough_text_node(self, node: StrikethroughTextNode) -> T:
        raise NotImplementedError

    def visit_inline_code_text_node(self, node: InlineCodeTextNode) -> T:
        raise NotImplementedError

    def visit_url_text_node(self, node: UrlTextNode) -> T:
        raise NotImplementedError

    def visit_codeblock_node(self, node: CodeblockNode) -> T:
        raise NotImplementedError

    def visit_html_node(self, node: HtmlNode) -> T:
        raise NotImplementedError

    def visit_header_node(self, node: HeaderNode) -> T:
        raise NotImplementedError

    def visit_newline_node(self, node: NewlineNode) -> T:
        raise NotImplementedError

    def visit_divider_node(self, node: DividerNode) -> T:
        raise NotImplementedError

    def visit_blockquote_node(self, node: BlockquoteNode) -> T:
        raise NotImplementedError

    def visit_table_node(self, node: TableNode) -> T:
        raise NotImplementedError
