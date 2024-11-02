using Microsoft.AspNetCore.Components;
using System.Text.Json;

namespace Reportobello.Blazor.Demo.Components.Pages;

public partial class Home
{
    [Inject]
    public ReportobelloApi ReportobelloApi { get; set; } = default!;

    [Inject]
    public ReportobelloUtil Util { get; set; } = default!;

    public ElementReference IframeRef { get; set; } = default!;

    private string JsonData = JsonSerializer.Serialize(Placeholder, JsonOptions);
    private string TypstData = """
#let data = json("data.json")

= Q#data.quarter Earnings Report

Generated: #datetime.today().display()

Earnings: $#data.earnings
""".Trim();

    private string DisplayMethod = "";
    private string? DownloadAsName = null;
    private string? TabDownloadAsName = null;

    private static readonly QuarterlyReport Placeholder = new(quarter: 1, earnings: 123_456);
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private List<string> Logs = [];

    private async Task UploadTemplate()
    {
        await ReportobelloApi.UploadTemplate<QuarterlyReport>(TypstData);
    }

    private async Task BuildPdf()
    {
        QuarterlyReport data;

        try
        {
            data = JsonSerializer.Deserialize<QuarterlyReport>(JsonData)!;
        }
        catch (JsonException ex)
        {
            Logs.Insert(0, ex.Message);
            return;
        }

        Uri url;

        try
        {
            url = await ReportobelloApi.RunReport(data);
        }
        catch (ReportobelloException ex)
        {
            Logs.Insert(0, ex.Message);
            return;
        }

        if (DisplayMethod == "iframe")
        {
            await Util.OpenInIframe(url, IframeRef);
        }
        else if (DisplayMethod == "tab")
        {
            await Util.OpenInNewTab(url, DownloadAsName);
        }
        else if (DisplayMethod == "download")
        {
            await Util.Download(url, TabDownloadAsName ?? "report.pdf");
        }
    }

    [TemplateName("quarterly_report")]
    record QuarterlyReport(int quarter, decimal earnings);
}
