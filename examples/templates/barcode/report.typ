#import "@preview/tiaoma:0.2.1" : *

#set text(font: "DejaVu Sans")

#show link: x => text(fill: blue)[#underline[#x]]

= Barcode Demo

Read the #link("https://raw.githubusercontent.com/typst/packages/main/packages/preview/tiaoma/0.2.1/manual.pdf")[tiaoma docs] for more details.

== QR Code
#qrcode("some-example-data")

== Micro QR Code
#micro-qr("1234567890")

== Code 128
#code128("1234567890")

== Code 39
#code39("1234567890")

== Code 39 (custom height)
#code39("1234567890", options: (height: 24.0))

== EAN (EAN 2/5/8/13/X)
#eanx("6975004310001")

== ISBN
#isbnx("9780441172719")

== Aztec Code
#aztec("1234567890")

== Aztec Rune
#azrune("123")
