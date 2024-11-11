# JavaScript/TypeScript

## Installing

To install, run:

```
$ npm i reportobello
```

## Configuring Reportobello

To use Reportobello, create a new API instance using your API key:

```javascript
import { Reportobello } from "reportobello";

const api = new Reportobello({apiKey: "rpbl_YOUR_API_KEY_HERE"});
```

> Never hard code API keys! This is only an example.
> In Node.js use `process.env.XYZ` to read sensitive data from environment variables.
> If you are using Reportobello from a browser, your API key will be available to anyone with the source code.
> We are working on fine-grained token permissions, which would allow you to expose read/write only API keys.

If you are using a self-hosted version of Reportobello, make sure to set the `host` option:

```javascript
const api = new Reportobello({apiKey: "rpbl_YOUR_API_KEY_HERE", host: "https://example.com"});
```

## Creating Templates

Before you can build a report, you need to upload it's template file:

```javascript
const template = `
#import "@rpbl/util:0.0.1": *

= Q#data.quarter Earnings Report

Generated: #datetime.today().display()

Earnings: $#data.earnings
`;

await api.createOrUpdateTemplate("quarterly_report", template);
```

> Refer to the [Typst docs](https://typst.app/docs) to learn how to create Typst templates.

## Building Reports

Once you have a template you can start building reports!

Use the `runReport` function to build a report:

```typescript
const url: URL = api.runReport(name, data);
```

This will return a `URL` object which you can use to display, render, or download the PDF.

All the examples below will use the following globals:

```javascript
const name = "quarterly_report";
const data = {"quarter": 1, "total": "123,456,678.00"};
```

### Download Report PDF

Download the PDF directly, opening it in a new tab.

**Function signature:**

```typescript
download(url: URL | string, downloadAs: string="report.pdf"): void;
```

**Arguments:**

* `downloadAs`: Changes the default filename of the PDF when downloaded via the browser.

**Examples:**

```javascript
api.runReport(name, data).then(download);

// or

api.runReport(name, data).then(x => download(x));
api.runReport(name, data).then(x => download(x, "customName.pdf"));

// or

const url = await api.runReport(name, data);
download(url);
download(url, "customName.pdf");
```

### Open Report in New Tab

Use the `openInNewTab()` function to open the PDF in a new tab.

**Function signature:**

```typescript
openInNewTab(url: URL | string, downloadAs?: string, download?: boolean=false): void;
```

**Arguments:**

* `downloadAs`: Changes the default filename of the PDF when downloaded via the browser.
* `download`: Set to `true` to download the file in addition to opening it in a new tab.

**Examples:**

```javascript
api.runReport(name, data).then(openInNewTab);

// or

api.runReport(name, data).then(x => openInNewTab(x));

// or

const url = await api.runReport(name, data);
openInNewTab(url);
```

### Open PDF in Existing Iframe

Use this to open the PDF in an existing iframe.

**Function signature:**

```typescript
openInIframe(url: URL | string, ref: string, downloadAs?: string): void;
```

**Arguments:**

* `ref`: The CSS selector for the iframe element
* `downloadAs`: Set the name of the PDF when downloaded through the iframe

**Examples:**

```javascript
api.runReport(name, data).then(x => openInIframe(x, "#id-of-iframe"));

// or

const url = api.runReport(name, data);
openInIframe(url, "#id-of-iframe");
```

### PDF Building Options

#### Pure PDFs

A "pure" PDF is a PDF built using only the JSON body, and doesn't use environment variables or non-deterministic side-effects like `datetime.today()`.
This means that if the JSON is the same, a cached version can be returned instead.

To use a cached PDF if one exists (or build one like normal if it doesnt exist), set the `pure` option:

```javascript
const url = await api.runReport(name, data, {pure: true})
```

## Uploading Data Files

If you have a template that requires custom fonts, images, or other data files (JSON, txt, csv, etc),
you can upload these files using the `uploadDataFiles()` method:

```typescript
const files = document.querySelector("input[type=file]").files

// Using `FileList` object (from `<input type="file">` elements)
await api.uploadDataFiles(name, files);

// Using array of `File` objects
await api.uploadDataFiles(name, [files[0]]);

// Using array of manually built file objects
await api.uploadDataFiles(name, [
  {
    name: "file.txt",
    blob: new Blob(["Hello world"], {type: "text/plain"}),
  }
]);
```

After uploading these files you will be able to use the files in your template:

```typst
= Example Image

#image("img.jpg")
```

> Note: Directories are stripped from filename when uploading.
> For example, if you upload `images/img.jpg`, the file will be uploaded as `img.jpg`.


## Deleting Templates

When you delete a template it will "soft-delete" it,
meaning you will not be able to access it,
but it will still exist in the system for billing purposes.

When you delete a template you will not be able to access report metadata for reports built for that template.
You will still be able to download PDFs if you have the direct URL.

```javascript
await api.deleteTemplate("quarterly_report");
```

## Get Recently Built Reports

To get a list of all the reports that have been built for a given template,
use the following:

```javascript
const reports = await api.getRecentReports("quarterly_report");
```

> Note: The API currently does not allow for sorting, searching, or pagination,
> all reports will be returned.
> In the future pagination might be added, so do not rely on all results being returned.

## Environment Variables

You can read more about environment variables in Reportobello [here](../concepts.md).

### Creating/Updating Environment Variables

```javascript
await api.updateEnvVars({
  companyName: "ACME Corp.",
  companyPhoneNumber: "123-456-7890",
});
```

### Delete Environment Variables

```javascript
await api.deleteEnvVars(["companyName", "companyPhoneNumber"]);
```

## Using with TypeScript

If you are using TypeScript, you can use the generic version of `runReport()` to type-check JSON data before it gets sent to Reportobello:

```typescript
interface QuarterlyReport {
  // ...
}

api.runReport<QuarterlyReport>(name, data).then(download);
```
