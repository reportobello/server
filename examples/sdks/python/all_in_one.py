import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from reportobello import ReportobelloApi, ReportobelloReportBuildFailure, ReportobelloTemplateNotFound, Template


@dataclass
class QuarterlyReport(Template):
    name = "report"

    content = """
#let data = json("data.json")

= Q#data.quarter Earnings Report

#sys.inputs.ENV_VAR_EXAMPLE

Generated: #datetime.today().display()

Earnings: $#data.earnings
"""

    # Alternatively, store in a file
    # file = "report.typ"

    quarter: int
    earnings: float


api = ReportobelloApi(api_key=os.getenv("REPORTOBELLO_API_KEY"), host="https://reportobello.com")

# These are both equivalent to the above code:
# api = ReportobelloApi(host="https://reportobello.com")
# api = ReportobelloApi()


async def main():
    template = QuarterlyReport(quarter=1, earnings=123_456)

    # This only needs to be re-ran if the template changes
    print("Creating template")
    await api.create_or_update_template(template)

    print("Updating environment variables")
    await api.update_env_vars({"ENV_VAR_EXAMPLE": "This is an example environment variable"})

    # Use this to delete an env var
    # await api.delete_env_vars(["ENV_VAR_EXAMPLE"])

    print("Building template")
    pdf = await api.build_template(template)

    print(f"Downloading {pdf.url}")

    # Download the PDF and save to disk
    await pdf.save_to("output.pdf")

    # Or, download and store in-memory
    print("Re-downloading as a blob")
    blob = await pdf.as_blob()
    assert b"PDF" in blob

    # Get recent PDF builds
    reports = await api.get_recent_builds(template)
    print(f"Recent reports count: {len(reports)}")
    print(f"Most recent report: {reports[0]}")
    print()

    # Get recent PDF builds before a given date
    yesterday = datetime.now() - timedelta(days=1)
    reports = await api.get_recent_builds(template, before=yesterday)
    print(f"Report count since yesterday: {len(reports)}")

    templates = await api.get_template_versions(template)
    print(f"Template version count: {len(templates)}")
    print(f"Most recent template: {templates[0]}")
    print()

    # Delete environment variable to show failed report error message
    await api.delete_env_vars(["ENV_VAR_EXAMPLE"])

    try:
        print("Building a bad report to test report build failure")
        pdf = await api.build_template(template)

    except ReportobelloReportBuildFailure as ex:
        print(ex)
        print()

    print("Deleting template")
    await api.delete_template(template)

    try:
        print("Building a non-existent template")
        pdf = await api.build_template(template)

    except ReportobelloTemplateNotFound as ex:
        print(ex)
        print()

    print("Done!")

asyncio.run(main())
