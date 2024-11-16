# Self Hosting

This page is a breakdown of how to self-host your own Reportobello instance.

## Local Testing

To experiment with Reportobello locally, run the following Docker command:

```
$ docker run -it \
    --name reportobello \
    -p 8000:8000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp:/tmp \
    ghcr.io/reportobello/server

...

reportobello-1  |
reportobello-1  | "admin" API key: rpbl_8dCCwVD4kMtmk_s3qODaiaa9_6MVyHXnhTODuohdcZI
reportobello-1  |
reportobello-1  | 2024-10-20T01:22:27.952 INFO:     Started server process [1]
reportobello-1  | 2024-10-20T01:22:27.952 INFO:     Waiting for application startup.
reportobello-1  | 2024-10-20T01:22:27.952 INFO:     Application startup complete.
reportobello-1  | 2024-10-20T01:22:27.952 INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

To start using Reportobello:

* Copy the `rpbl_...` API key

* Navigate to [http://localhost:8000]()

* Log in using your API key

When you're done, type CTRL+C to stop the server.
Your data will be stored in the `reportobello` container, and will be kept across restarts since the `--rm` flag is not used.
To start, stop, or destroy you Reportobello instance, run the following commands:

```
# Start a previously stopped instance
$ docker start reportobello

# Stop the currently running instance
$ docker stop reportobello

# Destroy the instance
$ docker rm reportobello
```

## Production

To use Reportobello in a production environment, you will probably want to enable/disable some environment variables:

**General**

* `REPORTOBELLO_DOMAIN`: The domain that the Reportobello instance is hosted from. Not setting this can cause CSRF issues when generating PDF URLs.
* `REPORTOBELLO_RATE_LIMIT_DISABLED`: By default, API requests in Reportobello are rate-limited. To disable rate-limits, set this to `1`. Note that this is different than monthly rate limits, which do not apply to the admin API key.
* `REPORTOBELLO_ADMIN_API_KEY`: Hard-code the admin API key (by default a key is auto-generated once on initial boot). If provided, it must match the following regex: `^rpbl_[0-9A-Za-z_-]{43}$`

**GitHub**

> Note: This probably should not be enabled, as it allows anyone with a GitHub account to create an account on your Reportobello instance.

* `REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID`: If you want to enable GitHub OAuth support, set your OAuth client ID here.
* `REPORTOBELLO_GITHUB_OAUTH_CLIENT_SECRET`: Same as above, but for the OAuth client secret.

**Jaeger/OTEL**

> Note: This should probably not be set unless you need to debug Reportobello, or want to ingest it's telemetry data.

* `REPORTOBELLO_JAEGER_URL`: Frontend URL for a [Jaeger instance](https://www.jaegertracing.io/).
* `REPORTOBELLO_OTEL_TRACE_ENDPOINT`: HTTP URL for exporting [Open Telemetry](https://opentelemetry.io/) data.
