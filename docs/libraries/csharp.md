# C#

This guide shows you how to use Reportobello with C#, specifically for backend applications, and Blazor frontends.

The full source code for this demo can be viewed [here](https://github.com/reportobello/server/tree/master/examples/sdks/dotnet/Reportobello.Blazor.Demo/Reportobello.Blazor.Demo).

> Reportobello should work with other .NET languages like F# and VB, but has not been tested.

## Installing

Via the dotnet CLI:

```
$ dotnet add package Reportobello
$ dotnet add package Reportobello.Blazor
```

Or add the following `PackageReference` directly:

```xml
<!-- Replace Version with the latest version -->
<PackageReference Include="Reportobello" Version="1.0.1" />
<PackageReference Include="Reportobello.Blazor" Version="1.0.0" />
```

The `Reportobello` package provides the core SDK for the Reportobello API, and is a .NET Standard 2.0 package which can be used with most .NET projects.

The `Reportobello.Blazor` package provides browser-only utilities like opening PDFs in new tabs, and only supports Blazor.
Only install `Reportobello.Blazor` for Blazor projects!

## Configuring Reportobello

Add the following to your `Program.cs` file to setup dependency injection for Reportobello:

```csharp
using Reportobello;
using Reportobello.Blazor;

// ...

builder.Services
    // Reportobello API
    .AddSingleton(
        new ReportobelloApi(
            builder.Configuration.GetValue<string>("Reportobello:ApiKey"),
            builder.Configuration.GetValue<string>("Reportobello:Host")
        )
    )
    // Blazor Utils
    .AddScoped<ReportobelloUtil>();
```

Then, in your `appsettings.json`, add the following:

```json
{
  "Reportobello": {
    "ApiKey": "rpbl_YOUR_API_KEY_HERE",
    "Host": "https://reportobello.com"
  }
}
```

> If you are using a self-hosted version of Reportobello, change the `Host` field to the URL for your local instance.

Now you will be able to inject `Reportobello` or `ReportobelloUtil` into your code!

## Injecting Reportobello

To use Reportobello in you code, you need to inject 2 services:

* `ReportobelloApi`: The API instance for building the actual reports
* `ReportobelloUtil`: A helper class for displaying/handling PDFs in the browser

Add the following code to your Blazor component:

```csharp
[Inject]
public ReportobelloApi ReportobelloApi { get; set; } = default!;
[Inject]
public ReportobelloUtil Util { get; set; } = default!;
```

> Note: If you aren't using Blazor, inject the services using your typical dependency injection system.
> As mentioned previously, `ReportobelloUtil` can only be used in Blazor projects, while `ReportobelloApi`
> can be used with any .NET Standard 2.0 compatible project.

## Creating Templates

Before you can build a report, you need to upload it's template file.
You only need to upload a template when you first create it or when you modify it.
You can upload it using the user interface, or by using a code-first approach, which is discussed below.

Reportobello uses Typst as it's templating language.
Read the [Typst docs](https://typst.app/docs) for more info on how to make templates with Typst.

### Weakly Typed Templates

If you don't want to create a `record` or `class` for your template data, you can specify the template name and contents directly:

```csharp
await ReportobelloApi.UploadTemplate("quarterly_report", "// Template contents here");
```

While weakly typed templates are easier in to start out with,
as your template becomes more complex,
strong typing will make building reports easier and less error prone.

## Strongly Typed Templates

To strongly type your template data, create a `record` or `class` that represents the structure of your template data:

```csharp
record QuarterlyReport(int quarter, decimal total);
```

Then give a name to your template via the `TemplateName` attribute:

```csharp
[TemplateName("quarterly_report")]
record QuarterlyReport(int quarter, decimal total);
```

This gives you enough to upload the template:

```csharp
string templateContent = "// Template content here";

await ReportobelloApi.UploadTemplate<QuarterlyReport>(templateContent);
```

Optionally, you can specify the template file in the `record` itself.
If you already have a `.typ` template file in repository, add the `TemplateFile` attribute:

```csharp
[TemplateName("quarterly_report")]
[TemplateFile("reports/quarterly_report.typ")]
record QuarterlyReport(int quarter, decimal total);
```

You can also specify the template contents directly:

```csharp
[TemplateName("quarterly_report")]
[TemplateContent("""

// Template content here

""")]
record QuarterlyReport(int quarter, decimal total);
```

Then you can upload the template without specifying the content:

```csharp
await ReportobelloApi.UploadTemplate<QuarterlyReport>();
```

## Building Reports

To build a report, use the template we created above to build the report:

```csharp
private async Task GeneratePdf()
{
    // Build the report data
    var report = new QuarterlyReport(quarter: 1, total: 123_456_789);

    // Call the API, get resulting PDF url
    var url = await ReportobelloApi.RunReport(report);
}
```

If you are using weakly-typed templates, you will need to specify the name of the template:

```csharp
var url = await ReportobelloApi.RunReport("quarterly_report", report);
```

You don't have to use template objects with `RunReport`, any JSON serializable object will do:

```csharp
var report = new {quarter: 1, total: 123_456_789};

var url = await ReportobelloApi.RunReport("quarterly_report", report);
```

## Displaying the PDF

The rest of this page is for Blazor projects that want to display/download PDFs in a browser.

### Download Report PDF

Download the PDF directly, opening it in a new tab.

**Function signature:**

```csharp
public async Task Download(Uri url, string downloadAs="report.pdf")
public async Task Download(string url, string downloadAs="report.pdf")
```

**Arguments:**

* `url`: The PDF URL to download
* `downloadAs`: Changes the default filename of the PDF when downloaded via the browser

**Examples:**

```csharp
await Util.Download(url);
await Util.Download(url, downloadAs: "Earnings Report.pdf");
```

### Open Report in New Tab

Opens the PDF in a new tab.

**Function signature:**

```csharp
public async Task OpenInNewTab(Uri url, string? downloadAs=null, bool download=false)
public async Task OpenInNewTab(string url, string? downloadAs=null, bool download=false)
```

**Arguments:**

* `url`: The PDF URL to download
* `downloadAs`: Changes the default filename of the PDF when downloaded via the browser
* `download`: When `true`, download the file in addition to opening it in a new tab

**Examples:**

```csharp
await Util.OpenInNewTab(url);
await Util.OpenInNewTab(url, downloadAs: "Earnings Report.pdf");

// Equivalent to Download(url, name);
await Util.OpenInNewTab(url, downloadAs: "Earnings Report.pdf", download: true);
```

### Open PDF in Existing Iframe

Open the PDF in an existing `<iframe>`.

**Function signature:**

```csharp
public async Task OpenInIframe(Uri url, object elementRef, string? downloadAs=null)
public async Task OpenInIframe(string url, object elementRef, string? downloadAs=null)
```

**Arguments:**

* `url`: The PDF URL to download
* `elementRef`: A string CSS selector for the iframe, or an `ElementReference` to an iframe
* `downloadAs`: Changes the default filename of the PDF when downloaded via the browser

**Examples:**

```csharp
await Util.OpenInIframe(url, "#iframe");

// or, using `ElementReference`

public ElementReference Iframe { get; set; } = default!;

await Util.OpenInIframe(url, Iframe);
```
