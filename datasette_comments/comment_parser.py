from typing import List, Union, Literal
from dataclasses import asdict, dataclass
from urllib.parse import urlparse


def valid_url(s):
    try:
        result = urlparse(s)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


@dataclass
class Token:
    start: int
    end: int
    value: str


def tokenize(source: str) -> List[Token]:
    tokens = []
    characters = list(source)
    current = []
    start = None
    for idx, c in enumerate(characters):
        if c.isspace():
            if len(current) > 0:
                tokens.append(Token(start, idx, "".join(current)))
                current = []
                start = None
        else:
            if len(current) == 0:
                start = idx
            current.append(c)

    if len(current) > 0:
        tokens.append(Token(start, len(source), "".join(current)))

    return tokens


# assert tokenize("") == []
# assert tokenize(" ") == []
# assert tokenize("a") == [Token(0, 1, "a")]
# assert tokenize("abc") == [Token(0, 3, "abc")]
# assert tokenize("alex garcia") == [Token(0, 4, "alex"), Token(5, 11, "garcia")]

# source = "does this look right @simonw and #urgent #oncall https://google.com httpnot ?"


@dataclass
class RenderNode:
    node_type: Union[
        Literal["raw"],
        Literal["tag"],
        Literal["mention"],
        Literal["url"],
        Literal["linebreak"],
    ]
    value: str


def split_raw_paragraphs(src: str) -> List[RenderNode]:
    newline_idxs = [index for index, char in enumerate(src) if char == "\n"]
    if len(newline_idxs) == 0:
        return [RenderNode("raw", src)]
    nodes = []
    prev = 0
    for idx in newline_idxs:
        start = prev if prev == 0 else prev + 1
        end = idx
        # happens when comment starts with a line break
        if start == end:
            nodes.append(RenderNode("linebreak", ""))
        else:
            nodes.extend(
                [
                    RenderNode("raw", src[start:end]),
                    RenderNode("linebreak", ""),
                ]
            )
        prev = idx
    if prev + 1 < len(src):
        nodes.append(RenderNode("raw", src[prev + 1 :]))
    return nodes


def render_nodes(source: str, tokens: List[Token]) -> List[RenderNode]:
    render_nodes = []
    last_idx = 0
    for token in tokens:
        if token.value.startswith("@"):
            render_nodes.extend(split_raw_paragraphs(source[last_idx : token.start]))
            render_nodes.append(RenderNode("mention", token.value))
            last_idx = token.end
        elif token.value.startswith("#"):
            render_nodes.extend(split_raw_paragraphs(source[last_idx : token.start]))
            render_nodes.append(RenderNode("tag", token.value))
            last_idx = token.end
        elif token.value.startswith("http") and valid_url(token.value):
            render_nodes.extend(split_raw_paragraphs(source[last_idx : token.start]))
            render_nodes.append(RenderNode("url", token.value))
            last_idx = token.end
        else:
            pass
    render_nodes.extend(split_raw_paragraphs(source[last_idx : len(source)]))
    return [asdict(node) for node in render_nodes]


@dataclass
class ParseResult:
    """A fully parsed comment in the format datasette-comments understands"""

    tokens: List[Token]
    """all parsed tokens in the comment"""

    rendered: List[RenderNode]
    """Parsed render list of nodes that clients can use to safely render a comment"""

    tags: List[Token]
    """token that start with a `#` hashtag"""

    mentions: List[Token]
    """tokens that start with `@` mention"""

    urls: List[Token]
    """Tokens that are URLs"""


def parse(source: str):
    tokens = tokenize(source)
    rendered = render_nodes(source, tokens)
    tags = list(filter(lambda token: token.value.startswith("#"), tokens))
    mentions = list(filter(lambda token: token.value.startswith("@"), tokens))
    urls = list(
        filter(
            lambda token: token.value.startswith("http") and valid_url(token.value),
            tokens,
        )
    )
    return ParseResult(tokens, rendered, tags, mentions, urls)
