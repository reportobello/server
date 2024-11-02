# Reportobello CLI

If you want to interact with your Reportobello instance using the command line, the Reportobello CLI has you covered.

The Reportobello CLI is written in Python and uses the [Python SDK](./libraries/python.md).

Example CLI usage:

```
$ cat demo.typ
Example Title: #sys.input.TITLE

$ rpbl env set TITLE "Hello World"
$ rpbl push demo.typ
$ rpbl ls -a
╭──────────┬─────────┬─────────────────────────────────╮
│ Name     │ Version │ Template                        │
├──────────┼─────────┼─────────────────────────────────┤
│ demo     │ 1       │ Example Title: #sys.input.TITLE │
╰──────────┴─────────┴─────────────────────────────────╯
```

## Installing

To install the Reportobello CLI, install the [`reportobello` package](https://pypi.org/project/reportobello/) using `pipx`:

```
$ pipx install reportobello

$ rpbl --help
```

## Setup

You must set the `REPORTOBELLO_API_KEY` environment variable in order to make certain API requests,
and if you are using a self-hosted version of Reportobello, you must set `REPORTOBELLO_HOST` as well.

The CLI will automatically load a `.env` file if it exists in the current directory.
For example, your `.env` file might look like this:

```shell
REPORTOBELLO_API_KEY=rpbl_YOUR_API_KEY_HERE
REPORTOBELLO_HOST=https://example.com
```

You can also specify these env vars via the command line:

```
$ export REPORTOBELLO_API_KEY=rpbl_YOUR_API_KEY_HERE
$ export REPORTOBELLO_HOST=https://example.com

$ rpbl --help
```

## Build a Template

### Building On Your Reportobello Instance

```
$ rpbl build TEMPLATE [JSON]
```

Build the template `TEMPLATE` on your Reportobello instance (*not* on your local machine).
To specify a JSON file to read and pass to the template, set the `JSON` argument (defaults to `data.json`).
Use `-` to read from `stdin`.

### Build a File Locally

```
$ rpbl build TEMPLATE --local [--env KEY=VALUE]
```

Build the template file `TEMPLATE` on your local machine.
You can pass additional environment variables using the `--env` flag. This can be repeated.

```
$ rpbl watch TEMPLATE [--env KEY=VALUE]
```

Use the `watch` command to rebuild whenever `TEMPLATE` changes.

> You can read more about environment variables [here](./concepts.md#environment-variables).

## Publish a Template

```
$ rpbl push TEMPLATE
```

Upload `TEMPLATE` to your Reportobello instance, or if it already exists, create a new version of the template.

## Pull a Template

```
$ rpbl pull TEMPLATE [--version 123]
```

Pull the latest version of a template `TEMPLATE`, or pull a specific version using `--version` or `-v`.

## List Templates

```
$ rpbl ls [--format=json]
```

List all templates your Reportobello instance. This will include:

* Template name
* Most recent version number
* Last time template was built (coming soon)
* Number of builds for this template (coming soon)

By default, a pretty-printed table is displayed. To display JSON instead, use `--format=json`.

## List Template Versions

```
$ rpbl ls TEMPLATE [-a] [--diff] [--format=json]
```

List template versions for `TEMPLATE`. By default, the template content is not shown.
To show the template content, use `-a` (for all).

To show only the differences between the templates, use the `--diff` option. This implies `-a`.

By default, a pretty-printed table is displayed. To display JSON instead, use `--format=json`.
Diff output is not shown when using the JSON format.

## List Recent Builds For Template

```
$ rpbl builds ls TEMPLATE [--format=json]
```

List recent builds for `TEMPLATE`.

By default, a pretty-printed table is displayed. To display JSON instead, use `--format=json`.

## Environment Variables

### List Environment Variables

```
$ rpbl env
$ rpbl env ls
```

List all environment variables in your Reportobello instance.

By default, a pretty-printed table is displayed. To display JSON instead, use `--format=json`.

### Set Environment Variables

```
$ rpbl env set KEY VALUE
```

Set the environment variable `KEY` to `VALUE`. If `KEY` already exists, override it.

### Remove Environment Variables

```
$ rpbl env rm KEY [KEY...]
```

Remove the environment variable `KEY`. Can be repeated.
No error is returned when trying to delete a key that doesn't exist.
