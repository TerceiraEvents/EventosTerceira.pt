#!/usr/bin/env ruby
# Flags likely duplicate listings in `_data/special_events.yml`.
#
# The ingest scripts already skip close matches while adding new events;
# this test catches manual/social-scan duplicates that slip through with
# small title changes such as an added "Concerto:" prefix.

require "cgi"
require "date"
require "yaml"

EVENTS_PATH = "_data/special_events.yml"
STOPWORDS = %w[
  a o as os de do da dos das e em no na nos nas um uma
  the of and at in on for to with com
].freeze
PREFIX = /\A(?:concert|concerto|show|festival|espetaculo|espectaculo|cinema|exposicao|workshop)\s*[:-]\s*/.freeze

def normalize_name(name)
  text = name.to_s
  previous = nil
  until previous == text
    previous = text
    text = CGI.unescapeHTML(text)
  end
  text = text.unicode_normalize(:nfkd).gsub(/\p{Mn}/, "")
  text = text.downcase
  text = text.gsub(/[\u{00ab}\u{00bb}\u{2018}\u{2019}\u{201c}\u{201d}\u{2039}\u{203a}"']+/, '"')
  text = text.gsub(/[\u{2010}-\u{2015}\u{2212}-]+/, "-")
  text = text.gsub(PREFIX, "")
  text.gsub(/\s+/, " ").strip
end

def content_tokens(name)
  normalize_name(name)
    .scan(/[[:alnum:]]+/)
    .reject { |token| STOPWORDS.include?(token) }
    .uniq
end

def similar_name?(a, b)
  return true if normalize_name(a) == normalize_name(b)

  a_tokens = content_tokens(a)
  b_tokens = content_tokens(b)
  return false if a_tokens.size < 3 || b_tokens.size < 3

  shared = a_tokens & b_tokens
  return false if shared.size < 3

  union = a_tokens | b_tokens
  jaccard = shared.size.to_f / union.size
  overlap = shared.size.to_f / [a_tokens.size, b_tokens.size].min
  jaccard >= 0.6 || overlap >= 0.8
end

events = YAML.safe_load(
  File.read(EVENTS_PATH),
  permitted_classes: [Date, Time],
)

groups = Hash.new { |h, key| h[key] = [] }
events.each_with_index do |event, index|
  next unless event.is_a?(Hash)

  groups[[event["date"], event["time"].to_s, event["end_date"].to_s]] << [index, event]
end

errors = []
groups.each do |(date, time, end_date), entries|
  entries.combination(2) do |(a_index, a), (b_index, b)|
    next unless similar_name?(a["name"], b["name"])

    bucket = [date, time.empty? ? nil : time, end_date.empty? ? nil : "ends #{end_date}"].compact.join(" ")
    errors << "#{bucket}: ##{a_index + 1} #{a["name"].inspect} duplicates ##{b_index + 1} #{b["name"].inspect}"
  end
end

if errors.empty?
  puts "OK -- #{events.size} events, no likely duplicate special events"
  exit 0
end

puts "FAIL: #{errors.size} likely duplicate special event(s):"
errors.first(50).each { |error| puts "  - #{error}" }
puts "  ... (and #{errors.size - 50} more)" if errors.size > 50
exit 1
