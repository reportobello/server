#let iso8601(s) = {
	// Hack to parse an ISO 8601 datetime using Typst's built-in TOML support.
	// Since Typst does not support timezones or sub-second percision we have to
	// strip off those characters (if they exist).
	let d = toml.decode("date = " + s.slice(0, calc.min(s.len(), 19))).date

	assert(type(d) == datetime, message: "Could not parse date `" + s + "`")

	return d
}

#let data = json.decode(sys.inputs.__RPBL_JSON_PAYLOAD)
