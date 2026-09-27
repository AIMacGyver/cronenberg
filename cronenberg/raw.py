"""This module contains functions related to raw metrics.

The main function is :func:`~cronenberg.raw.analyze`, and should be the only one
that is used.
"""

import collections
import operator
import tokenize

try:
    import StringIO as io
except ImportError:  # pragma: no cover
    import io


__all__ = [
    "OP",
    "COMMENT",
    "TOKEN_NUMBER",
    "NL",
    "NEWLINE",
    "EM",
    "Module",
    "_generate",
    "_fewer_tokens",
    "_find",
    "_logical",
    "analyze",
]

COMMENT = tokenize.COMMENT
OP = tokenize.OP
NL = tokenize.NL
NEWLINE = tokenize.NEWLINE
EM = tokenize.ENDMARKER

# Helper for map()
TOKEN_NUMBER = operator.itemgetter(0)

# A module object. It contains the following data:
#   loc = Lines of Code (total lines)
#   lloc = Logical Lines of Code
#   comments = Comments lines
#   multi = Multi-line strings (assumed to be docstrings)
#   blank = Blank lines (or whitespace-only lines)
#   single_comments = Single-line comments or docstrings
Module = collections.namedtuple(
    "Module",
    ["loc", "lloc", "sloc", "comments", "multi", "blank", "single_comments"],
)


def _generate(code):
    """Pass the code into `tokenize.generate_tokens` and convert the result
    into a list.
    """
    # tokenize.generate_tokens is an undocumented function accepting text
    return list(tokenize.generate_tokens(io.StringIO(code).readline))


def _fewer_tokens(tokens, remove):
    """Process the output of `tokenize.generate_tokens` removing
    the tokens specified in `remove`.
    """
    for values in tokens:
        if values[0] in remove:
            continue
        yield values


def _find(tokens, token, value):
    """Return the position of the last token with the same (token, value)
    pair supplied. The position is the one of the rightmost term.
    """
    for index, token_values in enumerate(reversed(tokens)):
        if (token, value) == token_values[:2]:
            return len(tokens) - index - 1
    raise ValueError("(token, value) pair not found")


def _split_tokens(tokens, token, value):
    """Split a list of tokens on the specified token pair (token, value),
    where *token* is the token type (i.e. its code) and *value* its actual
    value in the code.
    """
    res = [[]]
    for token_values in tokens:
        if (token, value) == token_values[:2]:
            res.append([])
            continue
        res[-1].append(token_values)
    return res


def _get_all_tokens(line, lines):
    """Starting from *line*, generate the necessary tokens which represent the
    shortest tokenization possible. This is done by catching
    :exc:`tokenize.TokenError` when a multi-line string or statement is
    encountered.
    :returns: tokens, lines
    """
    buffer = line
    used_lines = [line]
    while True:
        try:
            tokens = _generate(buffer)
        except tokenize.TokenError:
            # A multi-line string or statement has been encountered:
            # start adding lines and stop when tokenize stops complaining
            pass
        else:
            if not any(t[0] == tokenize.ERRORTOKEN for t in tokens):
                return tokens, used_lines

        # Add another line
        next_line = next(lines)
        buffer = buffer + "\n" + next_line
        used_lines.append(next_line)


# Keywords that always introduce a compound statement.
_HARD_COMPOUND_KEYWORDS = frozenset(
    {
        "if",
        "elif",
        "else",
        "for",
        "while",
        "try",
        "except",
        "finally",
        "with",
        "def",
        "class",
    }
)
# ``async`` is a compound header only in ``async def``, ``async for``, and ``async with``.
_ASYNC_COMPOUND_KEYWORDS = frozenset({"def", "for", "with"})
# Soft keywords: names unless a subject or pattern precedes the header colon.
_SOFT_COMPOUND_KEYWORDS = frozenset({"match", "case"})
_OPEN_BRACKETS = frozenset({"(", "[", "{"})
_CLOSE_BRACKETS = frozenset({")", "]", "}"})


def _soft_keyword_has_header(tokens_after_keyword):
    """Return whether ``match`` or ``case`` has a subject or pattern before ``:``.

    Args:
        tokens_after_keyword: Tokens that follow the soft keyword, comments
            already removed.

    Returns:
        True when a depth-0 colon closes a real header. False for assignments
        such as ``case = {1: 2}`` and annotations such as ``case: int = 1``.
    """
    depth = 0
    saw_pattern_token = False
    for token in tokens_after_keyword:
        kind = TOKEN_NUMBER(token)
        value = token[1]
        if kind == EM:
            break
        if kind == OP and value in _OPEN_BRACKETS:
            if depth == 0:
                saw_pattern_token = True
            depth += 1
            continue
        if kind == OP and value in _CLOSE_BRACKETS:
            depth -= 1
            continue
        if depth == 0 and kind == OP and value == ":":
            return saw_pattern_token
        if depth == 0:
            saw_pattern_token = True
    return False


def _opens_compound_statement(processed):
    """Return whether ``processed`` begins a compound-statement header.

    Args:
        processed: Tokens for one semicolon-separated segment, without
            comments or newlines.

    Returns:
        True when the segment is a real ``if``, ``try``, ``match``, ``case``,
        or other compound header. Soft keywords used as names do not qualify.
    """
    significant = [token for token in processed if TOKEN_NUMBER(token) != EM]
    if not significant or TOKEN_NUMBER(significant[0]) != tokenize.NAME:
        return False
    keyword = significant[0][1]
    if keyword in _HARD_COMPOUND_KEYWORDS:
        return True
    if keyword == "async":
        return (
            len(significant) > 1
            and TOKEN_NUMBER(significant[1]) == tokenize.NAME
            and significant[1][1] in _ASYNC_COMPOUND_KEYWORDS
        )
    if keyword in _SOFT_COMPOUND_KEYWORDS:
        return _soft_keyword_has_header(significant[1:])
    return False


def _logical(tokens):
    """Count the logical lines represented by ``tokens``.

    A physical line is normally one logical line. A colon adds a second
    logical line only when it ends a compound-statement header and a suite
    follows on that same line, as in ``if cond: return 0``. Colons in
    dictionaries, slices, annotations, and lambdas do not. ``match`` and
    ``case`` count as headers only when they introduce a real statement, so
    ``case = {1: 2, 3: 4}`` is one logical line.

    Examples::

        if cond:  -> 1

        if cond: return 0  -> 2

        try: 1/0  -> 2

        try:  -> 1

        if cond:  # Only a comment  -> 1

        if cond: return 0  # Only a comment  -> 2

        case 1: return 0  -> 2

        case = {1: 2, 3: 4}  -> 1
    """

    def aux(sub_tokens):
        """Count logical lines in one semicolon-separated segment."""
        # Get the tokens and, in the meantime, remove comments
        processed = list(_fewer_tokens(sub_tokens, [COMMENT, NL, NEWLINE]))
        # Comment-only segments are not logical lines.
        if not list(_fewer_tokens(processed, [NL, NEWLINE, EM])):
            return 0
        # Dictionary, slice, annotation, and lambda colons are not headers.
        if not _opens_compound_statement(processed):
            return 1
        try:
            # Rightmost colon. For a real header this is the suite colon when
            # the body has no later colon; a later colon still means a body
            # follows, so the segment counts as two logical lines.
            token_pos = _find(processed, OP, ":")
        except ValueError:
            return 1
        # The last token is ENDMARKER when this segment is not followed by
        # ';'. A header colon in that position has no same-line body.
        return 2 - (token_pos == len(processed) - 2)

    return sum(aux(sub) for sub in _split_tokens(tokens, OP, ";"))


def is_single_token(token_number, tokens):
    """Is this a single token matching token_number followed by ENDMARKER, NL
    or NEWLINE tokens.
    """
    return TOKEN_NUMBER(tokens[0]) == token_number and all(TOKEN_NUMBER(t) in (EM, NL, NEWLINE) for t in tokens[1:])


def analyze(source):
    """Analyze the source code and return a namedtuple with the following
    fields:

        * **loc**: The number of lines of code (total)
        * **lloc**: The number of logical lines of code
        * **sloc**: The number of source lines of code (not necessarily
            corresponding to the LLOC)
        * **comments**: The number of Python comment lines
        * **multi**: The number of lines which represent multi-line strings
        * **single_comments**: The number of lines which are just comments with
            no code
        * **blank**: The number of blank lines (or whitespace-only ones)

    The equation :math:`sloc + blanks + multi + single_comments = loc` should
    always hold.  Multiline strings are not counted as comments, since, to the
    Python interpreter, they are not comments but strings.
    """
    lloc = comments = single_comments = multi = blank = sloc = 0
    lines = (source_line.strip() for source_line in source.splitlines())
    lineno = 1
    for line in lines:
        try:
            # Get a syntactically complete set of tokens that spans a set of
            # lines
            tokens, parsed_lines = _get_all_tokens(line, lines)
        except StopIteration:
            raise SyntaxError(f"SyntaxError at line: {lineno}")

        lineno += len(parsed_lines)

        comments += sum(1 for t in tokens if TOKEN_NUMBER(t) == tokenize.COMMENT)

        # Identify single line comments, conservatively
        if is_single_token(tokenize.COMMENT, tokens):
            single_comments += 1

        # Identify docstrings, conservatively
        elif is_single_token(tokenize.STRING, tokens):
            _, _, (start_row, _), (end_row, _), _ = tokens[0]
            if end_row == start_row:
                # Consider single-line docstrings separately from other
                # multiline docstrings
                single_comments += 1
            else:
                multi += sum(1 for parsed_line in parsed_lines if parsed_line)  # Skip empty lines
                blank += sum(1 for parsed_line in parsed_lines if not parsed_line)
        else:  # Everything else is either code or blank lines
            for parsed_line in parsed_lines:
                if parsed_line:
                    sloc += 1
                else:
                    blank += 1

        # Process logical lines separately
        lloc += _logical(tokens)

    loc = sloc + blank + multi + single_comments
    return Module(loc, lloc, sloc, comments, multi, blank, single_comments)
