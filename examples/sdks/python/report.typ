#let data = json("data.json")

= Q#data.quarter Earnings Report

#sys.inputs.ENV_VAR_EXAMPLE

Generated: #datetime.today().display()

Earnings: #data.earnings
