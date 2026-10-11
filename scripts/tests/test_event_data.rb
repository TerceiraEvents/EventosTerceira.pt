#!/usr/bin/env ruby
# Unit tests for scripts/validate_event_data.rb, the _data/special_events.yml
# record gate. Run from the repo root:
#   ruby scripts/tests/test_event_data.rb

require_relative "../validate_event_data"
require "date"

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
puts "event data validation"

assert_eq validate_events(
  [{ "name" => "Expo", "date" => Date.new(2026, 10, 1), "end_date" => Date.new(2026, 10, 5) }]
), [], "valid range passes"

assert_eq validate_events(
  [{ "name" => "One Night", "date" => Date.new(2026, 10, 4) }]
), [], "single-day record passes"

quoted = validate_events(
  [{ "name" => "Quoted", "date" => Date.new(2026, 10, 4), "end_date" => "2026-10-05" }]
)
assert_eq quoted.size, 1, "quoted end_date fails"
assert_eq quoted.first.include?("end_date"), true, "quoted end_date error names the field"

reversed = validate_events(
  [{ "name" => "Backwards", "date" => Date.new(2026, 10, 5), "end_date" => Date.new(2026, 10, 1) }]
)
assert_eq reversed.size, 1, "reversed end fails"
assert_eq reversed.first.include?("Backwards"), true, "reversed end error names the event"

assert_eq validate_events(
  [{ "name" => "Dateless" }]
).size, 1, "missing date still fails"

assert_eq validate_events(
  [{ "name" => "Quoted Start", "date" => "2026-10-04" }]
).size, 1, "quoted date still fails"

puts "kind and visiting-hours schema"

kind_cases = [
  ["valid event", { "name" => "Event", "date" => Date.new(2026, 10, 1), "kind" => "event" }, false],
  ["valid exhibition", { "name" => "Exhibition", "date" => Date.new(2026, 10, 1),
                          "end_date" => Date.new(2026, 10, 2), "kind" => "exhibition",
                          "tags" => ["exhibition"] }, false],
  ["unknown kind", { "name" => "Unknown", "date" => Date.new(2026, 10, 1), "kind" => "concert" }, true],
  ["exhibition without end_date", { "name" => "No End", "date" => Date.new(2026, 10, 1),
                                    "kind" => "exhibition", "tags" => ["exhibition"] }, true],
  ["exhibition with end_date equal to date", { "name" => "Same Day", "date" => Date.new(2026, 10, 1),
                                                "end_date" => Date.new(2026, 10, 1),
                                                "kind" => "exhibition", "tags" => ["exhibition"] }, true],
  ["exhibition without tag", { "name" => "No Tag", "date" => Date.new(2026, 10, 1),
                                "end_date" => Date.new(2026, 10, 2), "kind" => "exhibition" }, true],
  ["exhibition-tagged range with no kind", { "name" => "Implicit Exhibition",
                                              "date" => Date.new(2026, 10, 1),
                                              "end_date" => Date.new(2026, 10, 2),
                                              "tags" => ["exhibition"] }, true],
  ["exhibition-tagged range with kind event", { "name" => "Multi-day Event",
                                                "date" => Date.new(2026, 10, 1),
                                                "end_date" => Date.new(2026, 10, 2),
                                                "kind" => "event", "tags" => ["exhibition"] }, false],
  ["single-day exhibition-tagged record with no kind", { "name" => "Opening",
                                                           "date" => Date.new(2026, 10, 1),
                                                           "tags" => ["exhibition"] }, false],
  ["empty visiting_hours", { "name" => "Empty Hours", "date" => Date.new(2026, 10, 1),
                              "visiting_hours" => " " }, true],
  ["empty visiting_hours_pt", { "name" => "Empty Hours PT", "date" => Date.new(2026, 10, 1),
                                 "visiting_hours_pt" => "" }, true]
]

kind_cases.each do |name, event, should_fail|
  errors = validate_events([event])
  assert_eq errors.empty?, !should_fail, name
  assert_eq errors.all? { |error| error.include?(event["name"]) }, true,
            "#{name} errors name the record" if should_fail
end

assert_eq validate_events("nope").size, 1, "non-list top level fails"

puts "validate-events workflow paths (actual parsed workflow)"

workflow = YAML.safe_load(File.read(".github/workflows/validate-events.yml"))
triggers = workflow[true] || workflow["on"]
push_paths = triggers["push"]["paths"]
pr_paths = triggers["pull_request"]["paths"]

assert_eq push_paths.include?("scripts/validate_event_data.rb"), true,
          "push paths run the data gate"
assert_eq push_paths.include?("scripts/tests/test_event_data.rb"), true,
          "push paths run the gate tests"
assert_eq pr_paths.include?("scripts/validate_event_data.rb"), true,
          "PR paths run the data gate"
assert_eq pr_paths.include?("scripts/tests/test_event_data.rb"), true,
          "PR paths run the gate tests"

if @failed > 0
  puts "\nFAIL: #{@failed} assertion(s) failed"
  exit 1
end
puts "\nOK — event data validation"
