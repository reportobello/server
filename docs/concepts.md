# Core Concepts

Here are a few basic concepts that will make using Reportobello a bit easier.

## Templates

At the core of Reportobello are templates. Templates are [Typst](https://typst.app/docs/reference) files that are used
for creating reports.

For reports to be useful, they need data.
When building the report, Reportobello puts your JSON data in a file called `data.json`, which your template can load and use:

```typst
#let data = json("data.json")

Gross earnings: $#data.total
```

Once it has been loaded, you can access the JSON data using the `data` variable.

## Reports

Reports are PDFs that are built from templates.
Reports also have some metadata like when they were built, who built them, etc.

In the event that a report failed to build,
you can use the API to get recently built reports and diagnose why they failed.

## Environment Variables

Often times you have data that is shared between lots of reports, for example, your company name, phone number, etc.
Environment variables are ways to inject key-value pairs into all your templates.

For example, if you set the key `company_name` to `ACME Corp.`, you can use that value in your reports like so:

```typst
Company Name: #sys.inputs.company_name
```

Using environment variables has lots of advantages:

* One source of truth: Updating your values in one place will update them globally
* Less hard-coding: Using environment variables means less hard coded data in your templates and applications
* Less bandwidth: Storing these values server-side means that you don't have to re-send them along with your report data

You don't have to use environment variables, but they are there if you need/want them.

> Reportobello currently does not support namespaced env vars, meaning all reports will be able to see
> all env vars. We are working on adding namespaces so that env vars are only scoped to specific reports
> or groups of reports.
