# API

> This is documentation for how to interface with the Reportobello API directly.
> If you want to use Reportobello with a programming language like JavaScript or C#,
> refer to the [client libraries](./libraries) page.

## Authentication

Almost all API endpoints require an API key to function.

To get an API key, navigate to the [login page](https://reportobello.com/login) and login with your GitHub account.
We use GitHub to make the login experience quicker, and reduce the likelihood for spam and abuse.

You can also quickly spin-up your own [self hosted Reportobello instance](./self-hosting.md).

> The [reportobello.com](https://reportobello.com) site is currently being used for demo purposes, and is periodically reset.
> It should only be used for testing and *should not* be used for production!

Once you get an API key, make sure to set the `Authorization` header like so:

```
Authorization: Bearer rpbl_YOUR_API_KEY_HERE
```

All API keys start with `rpbl_` to indicate that it is a Reportobello API key.

## Endpoints

Refer to the [Swager Docs](/swagger) for a list of all the available endpoints,
their purpose, and examples.

## Rate Limits

By default, API endpoints are rate limited to 5 requests/second.
Certain endpoints have stricter rate limiting, while others have no rate limits.
Refer to the Swagger documentation to see what the rate limit is for a given endpoint.

Undocumented API endpoints (for example, in the UI) have different rate limits,
and are subject to change without notice.
Do not rely on them!

For self-hosted instances you can set the `REPORTOBELLO_RATE_LIMIT_DISABLED` env var to `1` to remove
all API rate limits.

> Currently there is no way to change rate limits for specific endpoints without modifying the code directly.
