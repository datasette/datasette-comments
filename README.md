# datasette-comments

[![PyPI](https://img.shields.io/pypi/v/datasette-comments.svg)](https://pypi.org/project/datasette-comments/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-comments?include_prereleases&label=changelog)](https://github.com/datasette/datasette-comments/releases)
[![Tests](https://github.com/datasette/datasette-comments/workflows/Test/badge.svg)](https://github.com/datasette/datasette-comments/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-comments/blob/main/LICENSE)

A Datasette plugin for commenting on tables, rows, and values. Work in progress, not ready yet!

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-comments

## Usage

TODO

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-comments
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
