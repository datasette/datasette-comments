# datasette-comments

[![PyPI](https://img.shields.io/pypi/v/datasette-comments.svg)](https://pypi.org/project/datasette-comments/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-comments?include_prereleases&label=changelog)](https://github.com/datasette/datasette-comments/releases)
[![Tests](https://github.com/datasette/datasette-comments/workflows/Test/badge.svg)](https://github.com/datasette/datasette-comments/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-comments/blob/main/LICENSE)

A Datasette plugin for commenting on tables, rows, and values

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-comments

## Usage

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-comments
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest

- "Views"
  - Threads, connected to targets
  - Threads, disconnected
  - All comments on a table
  - All comments: `/-/datasette-comments/all`
  - All comments with a hashtag `/-/datasette-comments/tag/<id>`
  - All comments written by author `/-/datasette-comments/author/<id>`
  - All comments with specific @ mention `/-/datasette-comments/mentioned/<id>`

```py
def comments_for_database(database):
  pass
def comments_for_table(database, table):
  pass
def comments_for_column(database, table, column):
  pass
def comments_for_row(database, table, rowids):
  pass
def comments_for_value(database, table, rowids, column):
  pass
```

thread entrypoints

- homepage view:

  1. `database`: from h2s?

- database view:

  1. `database`: from h1?
  2. `table`: on table names, h2?

- table view:

  1. `table`: table name `<h1/>`
  2. `column`: columns `<th>/>`
  3. `rows`: rows `tbody > tr > td.type-pk` ?
  4. `values`: `tbody td`

- row view:
  1. `row`: on h1?
  2. `values`: `tbody td`

endpoints:

1. Get unresolved threads for different views
2. Thread actions (new, mark/unmarked)
3. Comment actions (new, edit, delete)
4. Reactions actials (add, remove)
