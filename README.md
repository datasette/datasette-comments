# datasette-comments

[![PyPI](https://img.shields.io/pypi/v/datasette-comments.svg)](https://pypi.org/project/datasette-comments/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-comments?include_prereleases&label=changelog)](https://github.com/datasette/datasette-comments/releases)
[![Tests](https://github.com/datasette/datasette-comments/workflows/Test/badge.svg)](https://github.com/datasette/datasette-comments/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-comments/blob/main/LICENSE)

A Datasette plugin for commenting on data in tables.

Read [Annotate and explore your data with datasette-comments](https://www.datasette.cloud/blog/2023/datasette-comments/) for background on this project.

<img src="https://datasette-cloud-assets.s3.amazonaws.com/blog/2023/datasette-comments/hero.jpg"/>

## Installation

`datasette-comments` requires a recent 1.0 alpha version of Datasette to work.

```bash
pip install datasette==1.0a7
```

Afterwards, install this plugin in the same environment as Datasette.

```bash
datasette install datasette-comments
```

## Usage

`datasette-comments` store comments in [Datasette's internal database](https://docs.datasette.io/en/latest/internals.html#datasette-s-internal-database). So to persistent comments across multiple restarts, supply an database path on startup like so:

```bash
datasette --internal internal.db my_data.db
```

When comments are made on rows inside `my_data.db`, the comment themselves are stored separately in `internal.db`.

The `datasette-comments-access` permission is required to be able to view and add comments. To give permissions to specfic users, set up your `metadata.yaml` like so:

```yaml
permissions:
  datasette-comments-access:
    id: ["simonw", "asg017"]
```

To provide actors and IDs, you'll need to setup a separate Datasette authentication plugin. Consider [datasette-auth-passwords](https://datasette.io/plugins/datasette-auth-passwords) for a simple username/password setup.

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
