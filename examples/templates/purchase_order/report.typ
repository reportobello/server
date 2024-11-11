#import "@rpbl/util:0.0.1": *

#set page(paper: "us-letter", margin: (x: 0.75in, y: 0.5in))
#set text(font: "DejaVu Sans")

= Purchase Order

#table(
  columns: (1fr, auto, auto),
  inset: (x: 0pt, y: 4pt),
  stroke: none,

  [#data.buyer.name],
  table.cell(inset: (right: 12pt))[*PO \#:*],
  table.cell(align: right)[*#data.po_number*],

  [#data.buyer.billing_address_line_1],
  table.cell(inset: (right: 12pt))[*Date:*],
  table.cell(align: right)[#data.date],

  [#data.buyer.billing_address_line_2],
  table.cell()[],
  table.cell()[],

  table.cell(colspan: 3)[#data.buyer.phone_number],
)

#linebreak()

#table(
  columns: (auto, 1fr, auto, 1fr),
  inset: (x: 8pt, y: 4pt),
  stroke: none,

  table.hline(),
  table.vline(),

  [*Vendor:*],
  [#data.vendor.name],
  [*Ship To:*],
  [#data.buyer.name],

  [],
  [#data.vendor.billing_address_line_1],
  [],
  [#data.buyer.billing_address_line_1],

  [],
  [#data.vendor.billing_address_line_2],
  [],
  [#data.buyer.billing_address_line_2],

  [],
  [#data.vendor.phone_number],
  [],
  [#data.buyer.phone_number],

  table.hline(),
  table.vline(),
)

#let format_row(row) = {
  (
    table.cell(inset: (x: 8pt), stroke: (y: none))[#row.item_number],
    table.cell(inset: (x: 8pt), stroke: (y: none))[#row.description],
    table.cell(align: center, inset: (x: 8pt), stroke: (y: none))[#row.quantity],
    table.cell(align: center, inset: (x: 8pt), stroke: (y: none))[#row.cost],
    table.cell(align: right, inset: (x: 8pt), stroke: (y: none))[#row.total],
  )
}

#linebreak()

#show table.cell.where(y: 0): strong

#table(
  columns: (auto, 1fr, auto, auto, auto),
  table.header(
    repeat: false,
    table.cell(align: center)[*Item \#*],
    table.cell(align: center)[*Description*],
    table.cell(align: center)[*Qty*],
    table.cell(align: center)[*Price*],
    table.cell(align: center)[*Total*],
  ),
  ..data.rows.map(format_row).flatten(),

  table.footer(
    repeat: false,
    table.cell(colspan: 3, rowspan: 4, stroke: (bottom: none, x: none), inset: 16pt)[
        #if data.notes.len() != 0 [
            *Notes:* #data.notes
        ]
    ],
    table.cell(align: right, stroke: (bottom: none, left: none))[Subtotal],
    table.cell(align: right, stroke: (y: none), inset: (x: 8pt))[#data.subtotal],

    table.cell(align: right, stroke: none)[Tax Rate],
    table.cell(align: right, stroke: (y: none), inset: (x: 8pt))[#data.tax_rate],

    table.cell(align: right, stroke: none)[Taxes],
    table.cell(align: right, stroke: (y: none), inset: (x: 8pt))[#data.taxes],

    table.cell(align: right, stroke: none)[Total],
    table.cell(align: right, stroke: (top: none), inset: (x: 8pt))[*#data.total*],
  )
)
