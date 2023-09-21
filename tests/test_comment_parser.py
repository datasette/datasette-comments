from datasette_comments.comment_parser import (
    valid_url,
    parse,
    ParseResult,
    Token,
    RenderNode,
)
from dataclasses import asdict


def test_valid_url():
    assert not valid_url("http")
    assert not valid_url("https://")
    assert valid_url("https://google")
    assert valid_url("https://google.com")


def test_parse():
    assert parse("") == ParseResult(
        tokens=[],
        rendered=[{"node_type": "raw", "value": ""}],
        tags=[],
        mentions=[],
        urls=[],
    )
    assert parse("alex garcia").tokens == [Token(0, 4, "alex"), Token(5, 11, "garcia")]
    result = parse("yo #sus @alex g")
    assert result.tokens == [
        Token(start=0, end=2, value="yo"),
        Token(start=3, end=7, value="#sus"),
        Token(start=8, end=13, value="@alex"),
        Token(start=14, end=15, value="g"),
    ]
    assert result.tags == [
        Token(start=3, end=7, value="#sus"),
    ]
    assert result.mentions == [
        Token(start=8, end=13, value="@alex"),
    ]
    assert result.rendered == [
        asdict(RenderNode("raw", "yo ")),
        asdict(RenderNode("tag", "#sus")),
        asdict(RenderNode("raw", " ")),
        asdict(RenderNode("mention", "@alex")),
        asdict(RenderNode("raw", " g")),
    ]

    assert (
        parse(
            """first line
second line"""
        ).rendered
        == [
            asdict(RenderNode("raw", "first line")),
            asdict(RenderNode("linebreak", "")),
            asdict(RenderNode("raw", "second line")),
        ]
    )
    assert (
        parse(
            """first line
second line
third line"""
        ).rendered
        == [
            asdict(RenderNode("raw", "first line")),
            asdict(RenderNode("linebreak", "")),
            asdict(RenderNode("raw", "second line")),
            asdict(RenderNode("linebreak", "")),
            asdict(RenderNode("raw", "third line")),
        ]
    )
    assert (
        parse(
            """
first is empty"""
        ).rendered
        == [
            # asdict(RenderNode("raw", "")),
            asdict(RenderNode("linebreak", "")),
            asdict(RenderNode("raw", "first is empty")),
        ]
    )
    assert (
        parse(
            """ends on line
"""
        ).rendered
        == [
            asdict(RenderNode("raw", "ends on line")),
            asdict(RenderNode("linebreak", "")),
        ]
    )
    assert (
        parse(
            """

"""
        ).rendered
        == [
            asdict(RenderNode("linebreak", "")),
            # TODO not sure if we can remove the need for this
            asdict(RenderNode("raw", "\n")),
            asdict(RenderNode("linebreak", "")),
        ]
    )
