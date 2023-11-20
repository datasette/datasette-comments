# datasette-comments

[![PyPI](https://img.shields.io/pypi/v/datasette-comments.svg)](https://pypi.org/project/datasette-comments/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-comments?include_prereleases&label=changelog)](https://github.com/datasette/datasette-comments/releases)
[![Tests](https://github.com/datasette/datasette-comments/workflows/Test/badge.svg)](https://github.com/datasette/datasette-comments/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-comments/blob/main/LICENSE)

A Datasette plugin for commenting on tables, rows, and values. Work in progress, not ready yet!

## Installation

Install this plugin in the same environment as Datasette.
```bash
datasette install datasette-comments
```
## Usage

Once installed, users with the `datasette-comments-access` will be able to view and add comments on rows within their Datasette instance.

## Plugin hooks

This plugin provies the following plugin hook which can be used to customize its behavior:

### datasette_comments_users(datasette)

This hook should return a list of dictionaries, each representing a user that should be made available to the plugin. Each dictionary should have the following keys:

- `id`: A unique ID of the user, same as the actor ID.
- `username`: A unique string that is used in searches and @ mentions.
- `name`: A string of the user's natural name.
- `profile_photo_url`: Optional URL to the user's profile pic.
- `email`: Optional email used for gravatar profile photo, if enabled.

The plugin hook can return a list, or it can return an awaitable function that returns a list.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd datasette-comments
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
And for the JavaScript dependencies (needed to run a JavaScript build):
```bash
npm install
```
To run the tests:
```bash
pytest
```

To rebuild the minified JavaScript after making a change to a `.ts` or `.tsx` file:

```bash
just js
```
