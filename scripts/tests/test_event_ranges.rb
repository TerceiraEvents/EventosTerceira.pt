#!/usr/bin/env ruby
# Events with end_date stay listed while ongoing. Renders the actual
# production pages and card include with Liquid (Jekyll-only filters
# and include mechanics shimmed; template logic runs unmodified).
#
# Run from the repo root:
#   ruby -I/tmp/terceira-liquid-testgems/gems/liquid-4.0.4/lib scripts/tests/test_event_ranges.rb

require "liquid"
require "json"
require "date"

module JekyllFilters
  def push(arr, x); Array(arr) + [x]; end
  def jsonify(input); input.to_json; end
  def relative_url(input); "/" + input.to_s.sub(%r{\A/}, ""); end
  def absolute_url(input); "https://example.test" + relative_url(input); end
end
Liquid::Template.register_filter(JekyllFilters)

# Jekyll accepts bare partial names with dots; core Liquid wants quoted
# names resolved through a file system object. The rewrite below only
# quotes the partial name.
class IncludesDir
  def initialize(dir); @dir = dir; end

  def read_template_file(name)
    unless name =~ /\A[A-Za-z0-9_.-]+\.html\z/
      raise Liquid::FileSystemError, "blocked include: #{name}"
    end
    File.read(File.join(@dir, name))
  end
end
Liquid::Template.file_system = IncludesDir.new("_includes")

def parse_production(path)
  src = File.read(path)
  src = src.sub(/\A---.*?---\n/m, "")
  src = src.gsub(/{%(-?)\s*include\s+(?!['"])([^\s%]+)/, '{%\1 include "\2"')
  Liquid::Template.parse(src)
end

T = Date.today
def iso(d); d.iso8601; end

def ev(name, start_d, end_d = nil)
  e = { "name" => name, "date" => iso(start_d), "venue" => "Auditório", "time" => "21:30" }
  e["end_date"] = iso(end_d) if end_d
  e
end

EVENTS = [
  ev("Ongoing Expo", T - 5, T + 5),
  ev("Ends Today", T - 3, T),
  ev("Ended Yesterday", T - 10, T - 1),
  ev("Single Today", T),
  ev("Single Past", T - 2),
  ev("Single Future", T + 2),
  ev("Far Future", T + 40, T + 45),
].freeze

def render_page(path, events, lang)
  parse_production(path).render(
    "site" => { "data" => { "special_events" => events, "event_tags" => [] }, "posts" => [] },
    "page" => { "lang" => lang }
  )
end

def render_card(event, lang)
  parse_production("_includes/special_event_card.html").render(
    "event" => event,
    "page" => { "lang" => lang },
    "site" => { "data" => { "event_tags" => [] }, "url" => "https://example.test", "baseurl" => "" }
  )
end

# Fixed Azores-winter offset (UTC-1). Real YAML dates arrive as Date
# objects, which Liquid formats at UTC midnight, while "now" passes
# through local midnight: under UTC-1 the two differ by an hour.
WINTER_TZ = "AZOT1"

def with_tz(zone)
  had = ENV.key?("TZ")
  old = ENV["TZ"]
  ENV["TZ"] = zone
  yield
ensure
  had ? ENV["TZ"] = old : ENV.delete("TZ")
end

def date_ev(name, start_d, end_d = nil)
  e = { "name" => name, "date" => start_d, "venue" => "Auditório", "time" => "21:30" }
  e["end_date"] = end_d if end_d
  e
end

def card_jsonld(html)
  m = html.match(%r{<script type="application/ld\+json">(.*?)</script>}m)
  raise "no JSON-LD block in card" unless m
  JSON.parse(m[1])
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
puts "event range selection (actual templates)"

{
  "special.md" => "en", "pt/special.md" => "pt",
  "calendar.md" => "en", "pt/calendar.md" => "pt",
}.each do |path, lang|
  out = render_page(path, EVENTS, lang)
  %w[Ongoing\ Expo Ends\ Today Single\ Today Single\ Future Far\ Future].each do |n|
    assert_eq out.include?(n), true, "[#{lang}] upcoming lists #{n} (#{path})"
  end
  %w[Ended\ Yesterday Single\ Past].each do |n|
    assert_eq out.include?(n), false, "[#{lang}] upcoming hides #{n} (#{path})"
  end
end

{
  "archive.md" => "en", "pt/archive.md" => "pt",
}.each do |path, lang|
  out = render_page(path, EVENTS, lang)
  %w[Ended\ Yesterday Single\ Past].each do |n|
    assert_eq out.include?(n), true, "[#{lang}] archive lists #{n} (#{path})"
  end
  %w[Ongoing\ Expo Ends\ Today Single\ Today Single\ Future Far\ Future].each do |n|
    assert_eq out.include?(n), false, "[#{lang}] archive hides #{n} (#{path})"
  end
end

# Archive and upcoming are disjoint over the full fixture set.
up = render_page("special.md", EVENTS, "en")
arch = render_page("archive.md", EVENTS, "en")
EVENTS.each do |e|
  assert_eq(up.include?(e["name"]) ^ arch.include?(e["name"]), true,
            "disjoint: #{e["name"]} on exactly one side")
end

# Home preview keeps ongoing exhibitions in its first-3 slice.
home = render_page("index.md", EVENTS, "en")
%w[Ongoing\ Expo Ends\ Today Single\ Today].each do |n|
  assert_eq home.include?(n), true, "[en] home preview lists #{n}"
end
assert_eq home.include?("Single Past"), false, "[en] home preview hides Single Past"
home_pt = render_page("pt/index.md", EVENTS, "pt")
assert_eq home_pt.include?("Ongoing Expo"), true, "[pt] home preview lists Ongoing Expo"

puts "winter UTC-1 selection with Date objects (actual templates)"

with_tz(WINTER_TZ) do
  today = Date.today
  dated = [
    date_ev("Ends Today", today - 3, today),
    date_ev("Single Today", today),
    date_ev("Ended Yesterday", today - 10, today - 1),
  ]
  {
    "special.md" => "en", "pt/special.md" => "pt",
  }.each do |path, lang|
    out = render_page(path, dated, lang)
    assert_eq out.include?("Ends Today"), true, "[#{lang}] UTC-1 upcoming lists Ends Today"
    assert_eq out.include?("Single Today"), true, "[#{lang}] UTC-1 upcoming lists Single Today"
    assert_eq out.include?("Ended Yesterday"), false, "[#{lang}] UTC-1 upcoming hides Ended Yesterday"
  end
  {
    "archive.md" => "en", "pt/archive.md" => "pt",
  }.each do |path, lang|
    out = render_page(path, dated, lang)
    assert_eq out.include?("Ended Yesterday"), true, "[#{lang}] UTC-1 archive lists Ended Yesterday"
    assert_eq out.include?("Ends Today"), false, "[#{lang}] UTC-1 archive hides Ends Today"
    assert_eq out.include?("Single Today"), false, "[#{lang}] UTC-1 archive hides Single Today"
  end
  {
    "calendar.md" => "en", "pt/calendar.md" => "pt",
  }.each do |path, lang|
    out = render_page(path, dated, lang)
    assert_eq out.include?("Ends Today"), true, "[#{lang}] UTC-1 calendar lists Ends Today"
    assert_eq out.include?("Single Today"), true, "[#{lang}] UTC-1 calendar lists Single Today"
    assert_eq out.include?("Ended Yesterday"), false, "[#{lang}] UTC-1 calendar hides Ended Yesterday"
  end
  {
    "index.md" => "en", "pt/index.md" => "pt",
  }.each do |path, lang|
    out = render_page(path, dated, lang)
    assert_eq out.include?("Ends Today"), true, "[#{lang}] UTC-1 home lists Ends Today"
    assert_eq out.include?("Single Today"), true, "[#{lang}] UTC-1 home lists Single Today"
    assert_eq out.include?("Ended Yesterday"), false, "[#{lang}] UTC-1 home hides Ended Yesterday"
  end
end

puts "card range label + JSON-LD (actual include)"

# Year-crossing range card, both languages.
range_year = { "name" => "Winter Show", "date" => "2026-12-30",
               "end_date" => "2027-01-02", "venue" => "Auditório", "time" => "21:30" }
en_card = render_card(range_year, "en")
assert_eq en_card.include?("30 Dec 2026 – 2 Jan 2027"), true, "[en] year-crossing label"
pt_card = render_card(range_year, "pt")
assert_eq pt_card.include?("30 Dez 2026 – 2 Jan 2027"), true, "[pt] year-crossing label"

# Month-crossing range card.
range_month = { "name" => "Autumn Show", "date" => "2026-09-30",
                "end_date" => "2026-10-02", "venue" => "Auditório" }
assert_eq render_card(range_month, "en").include?("30 Sep – 2 Oct 2026"), true,
          "[en] month-crossing label"
assert_eq render_card(range_month, "pt").include?("30 Set – 2 Out 2026"), true,
          "[pt] month-crossing label"

# Same-month range card.
range_same = { "name" => "Week Show", "date" => "2026-10-01",
               "end_date" => "2026-10-05", "venue" => "Auditório" }
assert_eq render_card(range_same, "en").include?("1 – 5 Oct 2026"), true,
          "[en] same-month label"

# JSON-LD uses the actual inclusive end date with no copied start time.
ld = card_jsonld(en_card)
assert_eq ld["startDate"], "2026-12-30T21:30:00", "JSON-LD startDate keeps time"
assert_eq ld["endDate"], "2027-01-02", "JSON-LD endDate is the inclusive end, date-only"

# Single-day behavior is intact: no range label, time on both ends.
single = { "name" => "One Night", "date" => "2026-10-04",
           "venue" => "Auditório", "time" => "21:30" }
single_card = render_card(single, "en")
assert_eq single_card.include?("event-date-range"), false, "single-day card has no range label"
ld_single = card_jsonld(single_card)
assert_eq ld_single["startDate"], "2026-10-04T21:30:00", "single startDate"
assert_eq ld_single["endDate"], "2026-10-04T21:30:00", "single endDate keeps time"

# Explicit end_date equal to date behaves as single-day.
single_explicit = { "name" => "One Night", "date" => "2026-10-04",
                    "end_date" => "2026-10-04", "venue" => "Auditório", "time" => "21:30" }
explicit_card = render_card(single_explicit, "en")
assert_eq explicit_card.include?("event-date-range"), false, "explicit same-day end has no range label"
ld_explicit = card_jsonld(explicit_card)
assert_eq ld_explicit["endDate"], "2026-10-04T21:30:00", "explicit same-day endDate keeps time"

# Card data attributes wire the client filter to the same period.
assert_eq render_card(range_same, "en").include?('data-event-end-date="2026-10-05"'), true,
          "ranged card wires data-event-end-date"
assert_eq single_card.include?('data-event-end-date="2026-10-04"'), true,
          "single card falls back to its start date"

# Ranged event without a time gets date-only start/end.
notimed = { "name" => "Expo", "date" => "2026-10-01",
            "end_date" => "2026-10-05", "venue" => "Museu" }
ld_notimed = card_jsonld(render_card(notimed, "en"))
assert_eq ld_notimed["startDate"], "2026-10-01", "timeless range startDate"
assert_eq ld_notimed["endDate"], "2026-10-05", "timeless range endDate"

if @failed > 0
  puts "\nFAIL: #{@failed} assertion(s) failed"
  exit 1
end
puts "\nOK — event ranges"
