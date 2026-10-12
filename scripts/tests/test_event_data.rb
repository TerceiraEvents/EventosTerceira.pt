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

def validate_fixture_events(data)
  records = data.is_a?(Array) ? data.each_with_index.map { |event, i| { 'id' => "fixture-#{i}" }.merge(event) } : data
  validate_events(records)
end

@failed = 0
puts "event data validation"

assert_eq validate_fixture_events(
  [{ "name" => "Expo", "date" => Date.new(2026, 10, 1), "end_date" => Date.new(2026, 10, 5) }]
), [], "valid range passes"

assert_eq validate_fixture_events(
  [{ "name" => "One Night", "date" => Date.new(2026, 10, 4) }]
), [], "single-day record passes"

quoted = validate_fixture_events(
  [{ "name" => "Quoted", "date" => Date.new(2026, 10, 4), "end_date" => "2026-10-05" }]
)
assert_eq quoted.size, 1, "quoted end_date fails"
assert_eq quoted.first.include?("end_date"), true, "quoted end_date error names the field"

reversed = validate_fixture_events(
  [{ "name" => "Backwards", "date" => Date.new(2026, 10, 5), "end_date" => Date.new(2026, 10, 1) }]
)
assert_eq reversed.size, 1, "reversed end fails"
assert_eq reversed.first.include?("Backwards"), true, "reversed end error names the event"

assert_eq validate_fixture_events(
  [{ "name" => "Dateless" }]
).size, 1, "missing date still fails"

assert_eq validate_fixture_events(
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
  errors = validate_fixture_events([event])
  assert_eq errors.empty?, !should_fail, name
  assert_eq errors.all? { |error| error.include?(event["name"]) }, true,
            "#{name} errors name the record" if should_fail
end

assert_eq validate_fixture_events("nope").size, 1, "non-list top level fails"

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

assert_eq push_paths.include?('scripts/assign_event_ids.rb'), true, 'assignment changes run publication gate'
assert_eq pr_paths.include?('scripts/tests/test_event_identity.rb'), true, 'identity test changes run publication gate'
assert_eq workflow.fetch('jobs').fetch('validate').fetch('steps').any? { |step| step['run'] == 'ruby scripts/tests/test_event_identity.rb' }, true, 'identity suite is wired into publication workflow'

puts "published browser-source records"
special = YAML.safe_load(File.read("_data/special_events.yml"), permitted_classes: [Date])
castanha = special.find { |event| event["name"] == "Festas da Castanha — Terra Chã" }
assert_eq castanha.fetch("source_url"),
          "https://www.facebook.com/photo/?fbid=1783816519984160&set=a.609332960765861",
          "Castanha cites the official programme"
assert_eq [castanha["date"], castanha["end_date"]],
          [Date.new(2026, 10, 30), Date.new(2026, 10, 31)], "Castanha preserves both days"
assert_eq castanha["time"], nil, "different daily openings are not one festival time"
%w[description description_pt].each do |field|
  %w[18:00 12:00 14:00 14:10 20:00 21:00 21:30 23:00].each do |time|
    assert_eq castanha.fetch(field).include?(time), true, "#{field} retains published #{time}"
  end
end
weekly = YAML.safe_load(File.read("_data/weekly.yml"))
nfl = weekly.find { |day| day["day"] == "Sunday" }.fetch("events").find { |event| event["name"] == "NFL Sundays" }
assert_eq nfl && nfl["time"], "17:00", "NFL lists the venue-advertised kickoff"
assert_eq nfl && nfl["source_url"], "https://www.instagram.com/thetexanbar/p/Ddqy2UfCY6S/",
          "NFL cites the venue announcement"
venues = YAML.safe_load(File.read("_data/venues.yml"))
texan = venues.find { |venue| venue["name"] == "The Texan / The Garden Club" }
assert_eq texan.fetch("weekly").any? { |entry| entry["day"] == "Sunday" && entry["name"].include?("NFL") },
          true, "Texan venue summary includes Sunday NFL"

puts "identity and locality publication rules"
identity_cases = [
  ['valid UUID', '11111111-1111-4111-8111-111111111111', nil, false],
  ['missing ID', nil, nil, true], ['integer ID', 12345, nil, true],
  ['false ID', false, nil, true], ['space ID', 'has space', nil, true],
  ['empty ID', '', nil, true], ['unknown locality', 'valid-id', 'Angra', true],
  ['false locality', 'valid-id', false, true], ['valid locality', 'valid-id', 'angra', false]
]
identity_cases.each do |label, id, locality, should_fail|
  event = { 'name' => "Identity #{label}", 'date' => Date.new(2026, 10, 12) }
  event['id'] = id unless id.nil?
  event['locality'] = locality unless locality.nil?
  errors = validate_events([event])
  assert_eq errors.empty?, !should_fail, label
  assert_eq errors.any? && errors.all? { |error| error.include?(event['name']) }, true, "#{label} names record" if should_fail
end
duplicates = [
  { 'name' => 'First identity', 'date' => Date.new(2026, 10, 12), 'id' => 'duplicate-id' },
  { 'name' => 'Second identity', 'date' => Date.new(2026, 10, 13), 'id' => 'duplicate-id' }
]
duplicate_errors = validate_events(duplicates)
assert_eq duplicate_errors.any? { |error| error.include?('Second identity') && error.include?('id') }, true, 'duplicate ID names offending record'

if @failed > 0
  puts "\nFAIL: #{@failed} assertion(s) failed"
  exit 1
end
puts "\nOK — event data validation"
