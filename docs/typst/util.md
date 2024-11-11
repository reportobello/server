# The `@rpbl/util` Package

> Current package version: `0.0.1`

The `@rpbl/util` package is used by Reportobello to inject global variables and other helper functions which aren't provided natively in Typst.
Examples include ISO 8601 datetime parsing and automatically loading JSON data in the template.

## Globals

### `data`

This global variable stores the JSON payload passed to the report via the API (or CLI).

**Example Usage**:

```json
{
  "invoice": {
    "number": 1234,
    "rows": [
      {
        "item": "Widget",
        "cost": "$1"
      }
    ]
  }
}
```

```typst
#import "@rpbl/util:0.0.1": *

Invoice \#: #data.invoice.number

Invoice Row 1: #data.invoice.rows.at(0)

This is the full JSON payload: #data
```

## Functions

### `iso8601`

This function parses a string in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) datetime format and returns a [`datetime`](https://typst.app/docs/reference/foundations/datetime) object.

> Note: Typst does not support timezones or sub-second percision, so those values are stripped before parsing.
> This behaviour might change in the future.

**Example Usage**:

```typst
#import "@rpbl/util:0.0.1": *

#iso8601("2024-11-11T19:51:41.711304+00:00")
#iso8601("2024-11-11T19:51:41.711304")
#iso8601("2024-11-11T19:51:41")
#iso8601("2024-11-11")
```
