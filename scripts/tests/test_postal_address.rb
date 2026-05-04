#!/usr/bin/env ruby
# Pure-Liquid unit tests for `_includes/postal_address.html`.
#
# This is the shared parser that both `_includes/special_event_card.html`
# (Event JSON-LD) and `venues.md` (LocalBusiness JSON-LD) call to turn
# a free-form Portuguese address string into a Schema.org PostalAddress
# object. PR #109 extracted it because the two callsites had diverged;
# regressions here would break structured data on every event and venue.
#
# These tests run without Jekyll — they parse the include directly with
# Liquid and the `jsonify` filter shimmed in. Fast (<1s) and runnable
# pre-build, so they catch parser bugs at PR time rather than after a
# Pages deploy.

require "liquid"
require "json"

module Shims
  def jsonify(input); input.to_json; end
end
Liquid::Template.register_filter(Shims)

INCLUDE = "_includes/postal_address.html"
abort "missing #{INCLUDE}" unless File.exist?(INCLUDE)

TEMPLATE = Liquid::Template.parse(File.read(INCLUDE))

def render(address)
  out = TEMPLATE.render("include" => { "address" => address })
  JSON.parse(out)
end

def assert_eq(actual, expected, name)
  if actual == expected
    puts "  ok  #{name}"
  else
    puts "  FAIL  #{name}"
    puts "    expected: #{expected.inspect}"
    puts "    actual:   #{actual.inspect}"
    @failed = (@failed || 0) + 1
  end
end

@failed = 0

puts "postal_address.html unit tests"

# Full address with 9700- postal code
r = render("Rua de São João 22-24, 9700-182 Angra do Heroísmo")
assert_eq r["@type"],            "PostalAddress",         "[9700-] @type"
assert_eq r["streetAddress"],    "Rua de São João 22-24", "[9700-] streetAddress"
assert_eq r["postalCode"],       "9700-182",              "[9700-] postalCode"
assert_eq r["addressLocality"],  "Angra do Heroísmo",     "[9700-] addressLocality"
assert_eq r["addressCountry"],   "PT",                    "[9700-] addressCountry"

# Full address with 9760- postal code (Praia da Vitória)
r = render("Canada do Saco, 9760-123 Praia da Vitória")
assert_eq r["postalCode"],      "9760-123",          "[9760-] postalCode"
assert_eq r["addressLocality"], "Praia da Vitória",  "[9760-] addressLocality"

# Address without a postal code: locality-only
r = render("Angra do Heroísmo")
assert_eq r["@type"],            "PostalAddress",      "[no-PC] @type"
assert_eq r["addressLocality"],  "Angra do Heroísmo",  "[no-PC] addressLocality is full string"
assert_eq r["streetAddress"],    nil,                  "[no-PC] no streetAddress"
assert_eq r["postalCode"],       nil,                  "[no-PC] no postalCode"
assert_eq r["addressCountry"],   "PT",                 "[no-PC] addressCountry still PT"

# Malformed postal code (digits-suffix not actually digits): fall back to locality
r = render("Rua Test, 9700-Foo Angra")
assert_eq r["postalCode"],   nil,                            "[malformed] no postalCode for non-digit suffix"
assert_eq r["streetAddress"], nil,                           "[malformed] no streetAddress when parse fails"

# Trailing-comma stripping on street part
r = render("Praça Velha, 9700-145 Angra do Heroísmo")
assert_eq r["streetAddress"],   "Praça Velha",     "[trailing comma] street has no trailing comma"

# Leading-comma stripping on locality
r = render("Rua X 1, 9700-100, Angra")
assert_eq r["addressLocality"], "Angra",           "[leading comma] locality has no leading comma"

# Empty input — degenerate case, should still emit valid JSON
r = render("")
assert_eq r["@type"],          "PostalAddress",   "[empty] @type"
assert_eq r["addressCountry"], "PT",              "[empty] addressCountry"
assert_eq r["postalCode"],     nil,               "[empty] no postalCode"

# Output must always be valid JSON (already implicitly tested above
# since render() does JSON.parse — but pin it)
out = TEMPLATE.render("include" => { "address" => "anything" })
begin
  JSON.parse(out)
  puts "  ok  output is always valid JSON"
rescue JSON::ParserError => e
  puts "  FAIL  output not valid JSON: #{e.message}"
  @failed += 1
end

if @failed > 0
  puts "\nFAIL: #{@failed} assertion(s) failed"
  exit 1
end
puts "\nOK — postal_address.html"
