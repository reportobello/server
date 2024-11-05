# Client Libraries

Reportobello has SDK support for the following languages:

* [C#](./csharp.md)
* [TypeScript/JavaScript](./typescript.md)
* [Python](./python.md)

## Feature Support Matrix

Reportobello is constantly adding new features, including upgrades to it's API.
While we try to keep the SDKs up to date with the latest changes,
they may fall behind when it comes to adding new features.

Here are all the supported API features and their SDK support.

| Feature                                                                               | C#           | JS           | Python       |
|---------------------------------------------------------------------------------------|--------------|--------------|--------------|
| Get all templates (`GET /api/v1/templates`)                                           | ❌           | ❌           | ✅           |
| Create/update template (`POST /api/v1/template/{name}`)                               | ✅           | ✅           | ✅           |
| Get template versions (`GET /api/v1/template/{name}`)                                 | ✅           | ✅           | ✅           |
| Delete template (`DELETE /api/v1/template/{name}`)                                    | ❌           | ✅           | ✅           |
| Build template (`POST /api/v1/template/{name}/build`)                                 | ✅           | ✅           | ✅           |
| \* Specify template version (`?version=N`)                                            | ❌&nbsp;[^1] | ❌&nbsp;[^1] | ❌&nbsp;[^1] |
| \* Download PDF as blob                                                               | ✅&nbsp;[^2] | ✅           | ✅&nbsp;[^2] |
| \* Download PDF as URL link (`?justUrl`)                                              | ✅           | ✅           | ✅           |
| \* Build pure PDF [^4] (`?isPure`)                                                    | ❌           | ✅           | ❌           |
| Get recently built reports (`GET /api/v1/template/{name}/recent`)                     | ❌           | ✅           | ✅           |
| \* Get reports build before a given date (`?before`)                                  | ❌           | ❌           | ✅           |
| Get previously built PDF by filename (`GET /api/v1/files/{filename}`)                 | ✅           | ✅           | ❌&nbsp;[^3] |
| \* Specify download name for PDF (`?downloadAs=NAME`)                                 | ✅           | ✅           | N/A          |
| \* Automatically download PDF (in browser) (`?download`)                              | ✅           | ✅           | N/A          |
| Get environment variables (`GET /api/v1/env`)                                         | ❌           | ❌           | ✅           |
| Set environment variables (`POST /api/v1/env`)                                        | ✅           | ✅           | ✅           |
| Delete environment variables (`DELETE /api/v1/env`)                                   | ✅           | ✅           | ✅           |
| Convert existing file to template (`POST /api/v1/convert/pdf`)                        | ❌           | ❌           | ❌           |
| Upload data files for templates (`POST /api/v1/template/{name}/files`)                | ❌           | ✅           | ✅           |
| Delete data files for templates (`DELETE /api/v1/template/{name}/file/{filename}`)    | ❌           | ❌           | ❌           |
| Get/download data files for templates (`GET /api/v1/template/{name}/file/{filename}`) | ❌           | ❌           | ❌           |

[^1]: Defaults to latest version
[^2]: PDF is not download directly as a blob, it grabs the URL then re-downloads it as a blob.
[^3]: This endpoint is indirectly called when building a report, but the SDK does not allow for re-downloading a PDF with just a URL yet.
[^4]: A "pure" PDF is a PDF built using only the JSON body, and doesn't use environment variables or non-deterministic side-effects like `datetime.today()`. This means that if the JSON is the same, a cached version can be returned instead.
