# Reportobello: Build Reports Rapidly

Reportobello is an API for building PDF reports. It's main goals are, in no particular order:

1. Simplicity: Building a report is as easy as sending JSON to a predefined template
2. Reliability: Build reports confidently, and diagnose issues quickly
3. Performance: Reports should be built almost instantly (sub 500ms for most PDFs)

Reportobello uses [Typst](https://typst.app) as the templating engine for making PDFs.
Building reports is as easy as:

1. Uploading your Typst files via our UI, [CLI](./cli.md), or [API](./api.md).
2. Send your data as JSON, get PDF output
3. Repeat steps 2-3

You can use our [API](./api.md) directly, or use one of our [SDKs](./libraries/README.md).
We currently have support for [Python](./libraries/python.md), [C#](./libraries/csharp.md), and [JavaScript/Typescript](./libraries/typescript.md).

Keep reading to see how you can integrate Reportobello into your workflow.
