// Read Typst template docs at: https://typst.app/docs/reference

#import "@rpbl/util:0.0.1": *

#set page(paper: "us-letter", margin: (x: 0.75in, y: 0.5in))
#set text(font: "DejaVu Sans")

= Invoice

#table(
  columns: (1fr, auto, auto),
  inset: (x: 0pt, y: 4pt),
  stroke: none,

  [#data.company.name],
  table.cell(inset: (right: 12pt))[*Invoice \#:*],
  table.cell(align: right)[*#data.invoice*],

  [#data.company.address_line_1],
  table.cell(inset: (right: 12pt))[*Start Date:*],
  table.cell(align: right)[#data.start_date],

  [#data.company.address_line_2],
  table.cell(inset: (right: 12pt))[*End Date:*],
  table.cell(align: right)[#data.end_date],

  table.cell(colspan: 3)[#data.company.phone_number],
)

#linebreak()

== Bill To

#data.client.name \
#data.client.billing_address_line_1 \
#data.client.billing_address_line_2 \
#data.client.phone_number

#let format_row(row) = {
  let (line_item, description, hours, rate, total) = row

  (
    table.cell(inset: (x: 8pt))[#line_item],
    table.cell(inset: (x: 8pt))[#description],
    table.cell(align: center, inset: (x: 8pt))[#hours],
    table.cell(align: center, inset: (x: 8pt))[#rate],
    table.cell(align: right, inset: (x: 8pt))[#total],
  )
}

#linebreak()
#linebreak()

#show table.cell.where(y: 0): strong

#table(
  columns: (auto, 1fr, auto, auto, auto),
  fill: (x, y) =>
    if (y == 0) { luma(200) }
    else if (y > 0 and calc.even(y) and y < data.rows.len() + 1) { luma(220) }
    else if (x != 0 and y >= data.rows.len() + 1) { luma(240) }
    else { white },
  table.header(
    repeat: false,
    table.cell(align: center)[*Item*],
    table.cell(align: center)[*Description*],
    table.cell(align: center)[*Hours*],
    table.cell(align: center)[*Rate*],
    table.cell(align: center)[*Total*],
  ),
  ..data.rows.map(format_row).flatten(),

  table.footer(
    repeat: false,
    table.cell(colspan: 3, rowspan: 4, stroke: (bottom: none, x: none), inset: 16pt)[Make checks payable to *#data.company.name*],
    table.cell(align: right)[Subtotal],
    table.cell(align: right, inset: (x: 8pt))[#data.subtotal],

    table.cell(align: right)[Tax Rate],
    table.cell(align: right, inset: (x: 8pt))[#data.tax_rate],

    table.cell(align: right)[Taxes],
    table.cell(align: right, inset: (x: 8pt))[#data.taxes],

    table.cell(align: right)[Total],
    table.cell(align: right, inset: (x: 8pt))[*#data.total*],
  )
)
