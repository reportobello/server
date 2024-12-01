from pathlib import Path
from asyncio import subprocess
from tempfile import TemporaryDirectory
import shutil

import pytest

from reportobello.x2typst.core import *
from reportobello.x2typst.node import *
from reportobello.x2typst.main import convert_file_in_memory
from reportobello.x2typst.typst import markdown_to_typst as _markdown_to_typst


async def test_convert_pdf_to_typst() -> None:
    input_file = Path("test/data/typst/input.typst")
    expected_file = Path("test/data/typst/expected.typst")

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        copied_file = tmp_dir / "input.typst"
        output_pdf = tmp_dir / "input.pdf"

        shutil.copy2(input_file, copied_file)

        process = await subprocess.create_subprocess_exec(
            "typst",
            "compile",
            str(copied_file),
            str(output_pdf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        await process.wait()

        if process.returncode != 0:
            assert process.stdout
            print((await process.stdout.read()).decode())
            assert False

        assert output_pdf.exists()

        typst_file, extracted_data = convert_file_in_memory(output_pdf)

        expected_file.write_text(typst_file.strip())

        assert typst_file.strip() == expected_file.read_text().strip()

        tables = extracted_data["tables"]
        assert tables
        assert len(tables) == 1

        table = tables[0]

        assert table == [
            ['Row 1 Column 1', 'Row 1 Column 2', 'Row 1 Column 3'],
            ['Row 2 Column 1', 'Row 2 Column 2', 'Row 2 Column 3'],
            ['Row 3 Column 1', 'Row 3 Column 2', 'Row 3 Column 3'],
            ['Row 4 Column 1', 'Row 4 Column 2', 'Row 4 Column 3'],
        ]

def markdown_to_typst(md: str) -> str:
    template, _ =  _markdown_to_typst(markdown_to_nodes(md), {}, 0)

    return template


def make_node(s: str) -> Node:
    return Node(contents=s)


def make_nodes(strs: list[str]) -> list[Node]:
    return [make_node(s) for s in strs]


def test_setup_nodes() -> None:
    nodes = setup_nodes("a\nb\nc")

    assert all(isinstance(node, Node) for node in nodes)

    assert len(nodes) == 3
    assert nodes[0].contents == "a"
    assert nodes[1].contents == "b"
    assert nodes[2].contents == "c"


def test_group_codeblock() -> None:
    nodes = make_nodes(["```", "some", "code", "```"])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], CodeblockNode)
    assert got_nodes[0].contents == "some\ncode"
    assert not got_nodes[0].language


def test_group_codeblock_with_language() -> None:
    nodes = make_nodes(["```python", "code", "```"])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], CodeblockNode)
    assert got_nodes[0].contents == "code"
    assert got_nodes[0].language == "python"


def test_group_blockquote_blocks() -> None:
    nodes = make_nodes(["> this", "> is a", "> blockquote"])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], BlockquoteNode)
    assert got_nodes[0].contents == "this\nis a\nblockquote"


def test_table_header_with_missing_header_separator() -> None:
    nodes = make_nodes(["| A | B | C |"])

    with pytest.raises(ValueError, match="missing .* header"):
        group_blocked_nodes(nodes)


@pytest.mark.parametrize("row", ["x| y |", "| y |x"])
def test_table_header_check_separator_pipe(row: str) -> None:
    nodes = make_nodes(["| A |", row])

    msg = "line must start and end with pipe"

    with pytest.raises(ValueError, match=msg):
        group_blocked_nodes(nodes)


@pytest.mark.parametrize(
    "row",
    [
        "|--|",
        "|xxx|",
        "|-x-|",
        "|:--:|",
        "|::---|",
        "|---::|",
        "|x---|",
        "|---x|",
    ],
)
def test_table_header_check_separator_is_formatted_correctly(row: str) -> None:
    nodes = make_nodes(["| A |", row])

    msg = "header separator must have:"

    with pytest.raises(ValueError, match=msg):
        group_blocked_nodes(nodes)


def test_table_header() -> None:
    nodes = make_nodes(["| A | B | C |", "|---|---|---|"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TableNode(
            header=[
                HeaderCell("A"),
                HeaderCell("B"),
                HeaderCell("C"),
            ],
            rows=[],
        )
    ]


def test_table_header_separator_needs_same_number_of_cells() -> None:
    nodes = make_nodes(["| A |", "|---|---|"])

    with pytest.raises(ValueError, match="expected 1 cells, got 2 instead"):
        group_blocked_nodes(nodes)


def test_table_with_rows() -> None:
    nodes = make_nodes(["| A |", "|---|", "| row 1 |", "| row 2 |"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TableNode(header=[HeaderCell("A")], rows=[["row 1"], ["row 2"]])
    ]


def test_table_with_trailing_content() -> None:
    nodes = make_nodes(["| A |", "|---|", "| row 1 |", "some text"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TableNode(header=[HeaderCell("A")], rows=[["row 1"]]),
        Node(contents="some text"),
    ]


def test_table_with_alignment() -> None:
    nodes = make_nodes(
        ["|default|left|center|right|", "|---|:---|:---:|---:|"]
    )

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TableNode(
            header=[
                HeaderCell("default", alignment=HeaderAlignment.DEFAULT),
                HeaderCell("left", alignment=HeaderAlignment.LEFT),
                HeaderCell("center", alignment=HeaderAlignment.CENTER),
                HeaderCell("right", alignment=HeaderAlignment.RIGHT),
            ],
            rows=[],
        ),
    ]


def test_table_with_trailing_content_after_separator() -> None:
    nodes = make_nodes(["| A |", "|---|", "some text"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TableNode(header=[HeaderCell("A")], rows=[]),
        Node(contents="some text"),
    ]


def test_group_html_comments() -> None:
    nodes = make_nodes(["<!--this", "is a", "comment-->", ""])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], CommentNode)
    assert got_nodes[0].contents == "this\nis a\ncomment"


def test_group_html_comments_one_line() -> None:
    nodes = make_nodes(["<!--this is a comment-->"])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], CommentNode)
    assert got_nodes[0].contents == "this is a comment"


def test_group_html_comments_two_lines() -> None:
    nodes = make_nodes(["<!--this is\na comment-->"])

    got_nodes = group_blocked_nodes(nodes)

    assert len(got_nodes) == 1
    assert isinstance(got_nodes[0], CommentNode)
    assert got_nodes[0].contents == "this is\na comment"


def test_preserve_nodes_next_to_codeblock() -> None:
    nodes = make_nodes(["pre", "```", "code", "```", "post"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        Node(contents="pre"),
        CodeblockNode(contents="code"),
        Node(contents="post"),
    ]


def test_preserve_nodes_next_to_blockquote() -> None:
    nodes = make_nodes(["pre", "> line", "post"])

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        Node(contents="pre"),
        BlockquoteNode(contents="line"),
        Node(contents="post"),
    ]


def test_exception_throw_if_codeblock_end_isnt_hit() -> None:
    nodes = make_nodes(["```", "code"])

    with pytest.raises(ValueError):
        group_blocked_nodes(nodes)


def test_exception_throw_if_codeblock_without_body_is_missing_end() -> None:
    nodes = make_nodes(["```"])

    with pytest.raises(ValueError):
        group_blocked_nodes(nodes)


def test_exception_throw_if_html_comment_not_closed() -> None:
    nodes = make_nodes(["<!--"])

    with pytest.raises(ValueError):
        group_blocked_nodes(nodes)


def test_classify_nodes() -> None:
    def run(x: str, expected: Node) -> None:
        assert classify_node(make_node(x)) == expected

    run("# hello", HeaderNode(level=1, contents="hello"))
    run("## hello", HeaderNode(level=2, contents="hello"))
    run("### hello", HeaderNode(level=3, contents="hello"))
    run("#### hello", HeaderNode(level=4, contents="hello"))

    run("", NewlineNode())

    run("* hello", BulletNode(contents="hello"))

    run("1. hello", NumListNode(contents="hello"))
    run("9. hello", NumListNode(contents="hello"))
    run("99. hello", NumListNode(contents="hello"))

    run("<html>", HtmlNode(contents="<html>"))

    # run("- [ ] hello", CheckboxNode(checked=False, contents="hello"))
    # run("- [x] hello", CheckboxNode(checked=True, contents="hello"))

    run("hello", TextNode(contents="hello"))


def test_group_text_nodes() -> None:
    nodes: list[Node] = [
        TextNode(contents="hello"),
        TextNode(contents="world"),
    ]

    got_nodes = group_text_nodes(nodes)

    assert got_nodes == [TextNode(contents="hello\nworld")]


def test_only_group_adjacent_nodes() -> None:
    nodes = [
        TextNode(contents="hello"),
        NewlineNode(),
        TextNode(contents="world"),
    ]

    got_nodes = group_blocked_nodes(nodes)

    assert got_nodes == [
        TextNode(contents="hello"),
        NewlineNode(),
        TextNode(contents="world"),
    ]


def test_group_bullet_nodes() -> None:
    nodes: list[Node] = [
        BulletNode(contents="item"),
        BulletNode(contents="another item"),
        BulletNode(contents="last item"),
    ]

    got_nodes = group_bullet_nodes(nodes)

    assert got_nodes == [
        BulletNode(data=["item", "another item", "last item"])
    ]


def test_group_only_adjacent_bullet_nodes() -> None:
    nodes = [
        BulletNode(contents="item"),
        TextNode(contents="text"),
        BulletNode(contents="item"),
    ]

    got_nodes = group_bullet_nodes(nodes)

    assert got_nodes == [
        BulletNode(data=["item"]),
        TextNode(contents="text"),
        BulletNode(data=["item"]),
    ]


def test_group_numbered_list_nodes() -> None:
    nodes: list[Node] = [
        NumListNode(contents="item 1"),
        NumListNode(contents="item 2"),
        NumListNode(contents="item 3"),
    ]

    got_nodes = group_number_list_nodes(nodes)

    assert got_nodes == [NumListNode(data=["item 1", "item 2", "item 3"])]


def test_group_only_adjacent_num_list_nodes() -> None:
    nodes = [
        NumListNode(contents="item"),
        TextNode(contents="text"),
        NumListNode(contents="item"),
    ]

    got_nodes = group_number_list_nodes(nodes)

    assert got_nodes == [
        NumListNode(data=["item"]),
        TextNode(contents="text"),
        NumListNode(data=["item"]),
    ]


def test_convert_node() -> None:
    def run(s: str, expected: str) -> None:
        assert markdown_to_typst(s) == expected

    run("# hello", "= hello")
    run("## hello", "== hello")
    run("### hello", "=== hello")
    run("#### hello", "==== hello")

    run("hello", "hello")

    run("", "")
    run("\n", "")

    # run("<html>", "<html>")

    run("> hello\n> world", "#set quote(block: true)\n#quote[hello\nworld]")

    run("* hello\n* world", "- hello\n- world")

    run("1. hello\n2. world", "1. hello\n2. world")

    run("```\nhello world\n```", "```\nhello world\n```")


def test_convert_table_node() -> None:
    markdown = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |"

    typst = """\
#table(
	columns: (auto, auto, auto),
	align: (left, left, left),
	table.header(
		align(center)[A],
		align(center)[B],
		align(center)[C],
	),
	..data.tables.at(0).flatten(),
)"""

    assert markdown_to_typst(markdown) == typst


def test_expand_inline_code_in_lists() -> None:
    assert markdown_to_typst("* **hello**") == "- *hello*"

    assert markdown_to_typst("1. **hello**") == "1. *hello*"


def test_inline_markdown_expanded() -> None:
    tests = {
        # "abc *hello* xyz": "abc _hello_ xyz",
        "abc **hello** xyz": "abc *hello* xyz",
        "abc `hello` xyz": "abc `hello` xyz",
        "abc ~~hello~~ xyz": "abc #strike[hello] xyz",
    }

    for md, expected in tests.items():
        got = markdown_to_typst(md)

        assert got == expected


def test_expand_inline_markdown_in_blockquote() -> None:
    assert markdown_to_typst("> **hello**") == "#set quote(block: true)\n#quote[*hello*]"


def test_expand_inline_markdown_in_table() -> None:
    markdown = "|*hello*|\n|---|\n|*world*|"

    got = """\
#table(
	columns: (auto,),
	align: (left,),
	table.header(
		align(center)[*hello*],
	),
	..data.tables.at(0).flatten(),
)"""

    assert markdown_to_typst(markdown) == got


def test_convert_table_with_alignment() -> None:
    markdown = """\
|default|left|center|right|
|-------|:---|:----:|----:|
|1|2|3|4|"""

    got = """\
#table(
	columns: (auto, auto, auto, auto),
	align: (left, left, center, right),
	table.header(
		align(center)[default],
		align(center)[left],
		align(center)[center],
		align(center)[right],
	),
	..data.tables.at(0).flatten(),
)"""

    assert markdown_to_typst(markdown) == got


def test_escape_sensitive_chars() -> None:
    markdown = r"""
# #$@<

## #$@<

### #$@<

#### #$@<

* #$@<

1. #$@<

```
#$@<
```

> #$@<

some text #$@<

| #$@< |
| ---- |
| #$@< |

"""

    expected = r"""
#set quote(block: true)

= \#\$\@\<

== \#\$\@\<

=== \#\$\@\<

==== \#\$\@\<

- \#\$\@\<

1. \#\$\@\<

```
#$@<
```

#quote[\#\$\@\<]

some text \#\$\@\<

#table(
	columns: (auto,),
	align: (left,),
	table.header(
		align(center)[\#\$\@\<],
	),
	..data.tables.at(0).flatten(),
)
"""

    got = markdown_to_typst(markdown)

    assert got.strip() == expected.strip()


def test_convert_html_comment_doesnt_throw_assertion() -> None:
    markdown_to_typst("<!-- comment -->")


def test_convert_divider() -> None:
    assert markdown_to_typst("---") == ""


def test_parse_inline_markdown_basic() -> None:
    node = parse_complex_text_node("Hello world")

    match node:
        case ComplextTextNode(parts=[TextNode(contents="Hello world")]):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")

def test_parse_inline_markdown_italic() -> None:
    node = parse_complex_text_node("*Hello world*")

    match node:
        case ComplextTextNode(parts=[ItalicTextNode(parts=[TextNode(contents="Hello world")])]):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")

def test_parse_inline_markdown_italic_complex() -> None:
    node = parse_complex_text_node("Hello *there* world")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Hello "),
                ItalicTextNode(parts=[TextNode(contents="there")]),
                TextNode(contents=" world"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_bold_basic() -> None:
    node = parse_complex_text_node("**Hello world**")

    match node:
        case ComplextTextNode(parts=[BoldTextNode(parts=[TextNode(contents="Hello world")])]):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_bold_complex() -> None:
    node = parse_complex_text_node("Hello **there** world")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Hello "),
                BoldTextNode(parts=[TextNode(contents="there")]),
                TextNode(contents=" world"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_bold_with_nested_italics() -> None:
    node = parse_complex_text_node("**Hello *there* world**")

    match node:
        case ComplextTextNode(
            parts=[
                BoldTextNode(
                    parts=[
                        TextNode(contents="Hello "),
                        ItalicTextNode(parts=[TextNode(contents="there")]),
                        TextNode(contents=" world"),
                    ]
                ),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_bold_with_multiple_nested_italics() -> None:
    node = parse_complex_text_node("**ABC *DEF* GHI *JKL* MNO**")

    match node:
        case ComplextTextNode(
            parts=[
                BoldTextNode(
                    parts=[
                        TextNode(contents="ABC "),
                        ItalicTextNode(parts=[TextNode(contents="DEF")]),
                        TextNode(contents=" GHI "),
                        ItalicTextNode(parts=[TextNode(contents="JKL")]),
                        TextNode(contents=" MNO"),
                    ]
                ),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_italic_with_nested_bold() -> None:
    node = parse_complex_text_node("*Hello **there** world*")

    match node:
        case ComplextTextNode(
            parts=[
                ItalicTextNode(
                    parts=[
                        TextNode(contents="Hello "),
                        BoldTextNode(parts=[TextNode(contents="there")]),
                        TextNode(contents=" world"),
                    ]
                ),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_italic_with_multiple_nested_bold() -> None:
    node = parse_complex_text_node("*ABC **DEF** GHI **JKL** MNO*")

    match node:
        case ComplextTextNode(
            parts=[
                ItalicTextNode(
                    parts=[
                        TextNode(contents="ABC "),
                        BoldTextNode(parts=[TextNode(contents="DEF")]),
                        TextNode(contents=" GHI "),
                        BoldTextNode(parts=[TextNode(contents="JKL")]),
                        TextNode(contents=" MNO"),
                    ]
                ),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_inline_code() -> None:
    node = parse_complex_text_node("`Hello world`")

    match node:
        case ComplextTextNode(parts=[InlineCodeTextNode(contents="Hello world")]):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_inline_code_complex() -> None:
    node = parse_complex_text_node("Hello `there` world")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Hello "),
                InlineCodeTextNode(contents="there"),
                TextNode(contents=" world"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_url() -> None:
    node = parse_complex_text_node("Before [Some Text](https://example.com) After")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Before "),
                UrlTextNode(
                    text=ComplextTextNode(parts=[TextNode(contents="Some Text")]),
                    url="https://example.com",
                ),
                TextNode(contents=" After"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_url_shorthand() -> None:
    node = parse_complex_text_node("Before [https://example.com]() After")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Before "),
                UrlTextNode(
                    text=ComplextTextNode(parts=[TextNode(contents="https://example.com")]),
                    url=None,
                ),
                TextNode(contents=" After"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_url_nested_markdown() -> None:
    node = parse_complex_text_node("[*Hello **there** world*](https://example.com)")

    match node:
        case ComplextTextNode(
            parts=[
                UrlTextNode(
                    text=ComplextTextNode(
                        parts=[
                            ItalicTextNode(
                                parts=[
                                    TextNode(contents="Hello "),
                                    BoldTextNode(parts=[TextNode(contents="there")]),
                                    TextNode(contents=" world"),
                                ]
                            ),
                        ]
                    ),
                    url="https://example.com",
                ),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_url_invalid_url_is_just_text() -> None:
    node = parse_complex_text_node("[*Hello **there** world*] (https://example.com)")

    match node:
        case ComplextTextNode(
            parts=[
                ComplextTextNode(
                    parts=[
                        TextNode(contents="["),
                        ItalicTextNode(
                            parts=[
                                TextNode(contents="Hello "),
                                BoldTextNode(parts=[TextNode(contents="there")]),
                                TextNode(contents=" world")
                            ]
                        ),
                        TextNode(contents="] ")
                    ]
                ),
                TextNode(contents="(https://example.com)")
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_escaped_characters() -> None:
    node = parse_complex_text_node(r"A \\ B \[ C \! D \* E \_")

    match node:
        case ComplextTextNode(parts=[TextNode(contents=r"A \ B [ C ! D * E _")]):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_strikethrough() -> None:
    node = parse_complex_text_node("Hello ~~there~~ world")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="Hello "),
                StrikethroughTextNode(parts=[TextNode(contents="there")]),
                TextNode(contents=" world"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")


def test_parse_inline_markdown_strikethrough_complex() -> None:
    node = parse_complex_text_node("ABC ~~DEF **GHI** JKL~~ MNO")

    match node:
        case ComplextTextNode(
            parts=[
                TextNode(contents="ABC "),
                StrikethroughTextNode(
                    parts=[
                        TextNode(contents="DEF "),
                        BoldTextNode(parts=[TextNode(contents="GHI")]),
                        TextNode(contents=" JKL"),
                    ],
                ),
                TextNode(contents=" MNO"),
            ]
        ):
            pass

        case _:
            pytest.fail(f"Node did not match: {node}")
