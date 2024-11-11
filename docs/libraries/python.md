# Python

## Installing

```
$ pip install reportobello
```

## Configuring Reportobello

To start using Reportobello, create a new API instance:

```python
from reportobello import ReportobelloApi

# Automatically read the REPORTOBELLO_API_KEY and REPORTOBELLO_HOST env var
api = ReportobelloApi()

# Explicitly pass API key
api = ReportobelloApi("rpbl_YOUR_API_KEY_HERE")
```

> Never hard code API keys! This is only an example. Use `os.getenv()` to read API keys from environment variables.

If you are using a self-hosted version of Reportobello, make sure to set the `host` argument:

```python
api = ReportobelloApi(host="https://example.com")
```

## Creating Templates

Before you can build a report, you need to upload it's template file.
You only need to upload a template when you first create it or when you modify it.
You can upload it using the user interface, or by using a code-first approach, which is discussed below.

```python
from dataclasses import dataclass

from reportobello import Template


@dataclass
class QuarterlyReport(Template):
    # The name to use for this template
    name = "quarterly_report"

    # Path to Typst template file
    file = "path/to/report.typ"

    # Template data
    quarter: int
    earnings: float

# Upload template via API
await api.create_or_update_template(template)
```

The `path/to/report.typ` file is a [Typst](https://typst.app) template file for building the report.
In this example, the `report.typ` file will use the following contents:

```typst
#import "@rpbl/util:0.0.1": *

= Q#data.quarter Earnings Report

Generated: #datetime.today().display()

Earnings: #data.earnings
```

> Typst is a powerful templating language which supports rich typesetting, variables, conditions, functions, and much much more.
> Refer to the [Typst docs](https://typst.app/docs) to learn more about Typst templates.

If you would rather store the template in the class directly you can set the `content` property instead:

```python
@dataclass
class QuarterlyReport(Template):
    # ...

    content = """
#import "@rpbl/util:0.0.1": *

= Q#data.quarter Earnings Report

Generated: #datetime.today().display()

Earnings: #data.earnings
"""

  # ...
```

## Building Reports

Once you have a template you can start building reports!
The `QuarterlyReport` template we created can be passed to most `template=` arguments,
and contains all the metadata needed for dealing with templates.
To build a template, run the following:

```python
# Create a new template instance
template = QuarterlyReport(quarter=1, earnings=123_456)

# Build the report
pdf = await api.build_template(template)
```

In some cases though, it might be desirable to separate the template name from the template data,
for instance, if you are not using dataclasses.
In that case, you can pass the template name, and the template data as a dictionary or dataclass:

```python
pdf = await api.build_template("quarterly_report", {"quarter": 1, "earnings": 123_456})

# or, if you want to use a Template object, but not the data:
pdf = await api.build_template(QuarterlyReport(), {"quarter": 1, "earnings": 123_456})
```

The rest of the code examples below will start with the following boilerplate:

```python
template = QuarterlyReport(quarter=1, earnings=123_456)

pdf = await api.build_template(template)
```

### Download PDF To Disk

To build a report and download the file directly use the following:

```python
await pdf.save_to("output.pdf")

# or, using Path:
await pdf.save_to(Path("output.pdf"))
```

### Download PDF In-Memory

To build a report and save the PDF blob directly to a variable, use the following:

```python
blob = await pdf.as_blob()
```

### Just Get URL

If you only want to get the URL of the built report, use the following:

```python
url = pdf.url
```

### Pure PDFs

A "pure" PDF is a PDF built using only the JSON body, and doesn't use environment variables or non-deterministic side-effects like `datetime.today()`.
This means that if the JSON is the same, a cached version can be returned instead.

To use a cached PDF if one exists (or build one like normal if it doesnt exist), set the `is_pure` keyword arg:

```python
pdf = await api.build_template(template, is_pure=True)
```

## Deleting Templates

When you delete a template it will be "soft-deleted",
meaning you will not be able to access it,
but it will still exist in the system for billing purposes.

When you delete a template you will not be able to access report metadata for reports built for that template,
though you will still be able to download PDFs if you have the direct URL.

```python
await api.delete_template("quarterly_report")

# or, using existing template instance
await api.delete_template(template)
```

## Uploading Data Files

If you have a template that requires custom fonts, images, or other data files (JSON, txt, csv, etc),
you can upload these files using the `upload_data_files()` method:

```python
# You can upload files via Path or str objects
files = [Path("img1.jpg"), "img2.jpg"]

await api.upload_data_files(template, *files)
```

After uploading these files you will be able to use the files in your template:

```typst
= Example Image

#image("img.jpg")
```

> Note: Directories are stripped from filename when uploading.
> For example, if you upload `images/img.jpg`, the file will be uploaded as `img.jpg`.

## Get Recent Builds for a Template

To get a list of all the reports that have been built for a given template,
use one of the following:

```python
reports = await api.get_recent_builds("quarterly_report")

# or, using existing template instance
reports = await api.get_recent_builds(template)
```

To get reports built before a given time, use the `before` keyword:

```python
reports = await api.get_recent_builds(template, before=datetime.now(tz=utc))
```

Note that the `datetime` object passed to `before` must be a UTC datetime!

> Note that the API/SDK currently does not support filtering, pages, or page size, it only supports the `before` keyword.

## Environment Variables

You can read more about environment variables in Reportobello [here](../concepts.md).

### Creating/Updating Environment Variables

```python
await api.update_env_vars({
  "company_name": "ACME Corp.",
  "company_phone_number": "123-456-7890",
})
```

### Delete Environment Variables

```python
await api.delete_env_vars(["company_name", "company_phone_number"])
```
