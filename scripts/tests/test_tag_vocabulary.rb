#!/usr/bin/env ruby
# Cross-checks tags used in `_data/special_events.yml` against the
# canonical vocabulary in `_data/event_tags.yml`. Catches typos
# (e.g. `kid_friendly` instead of `kid-friendly`) and accidental new
# slugs that won't render a tag pill on the site.
#
# Tags are also documented in the app (`TerceiraEventsApp`) and the
# event-submit-worker — divergence between those is out of scope here,
# but a regular reminder is in `_data/event_tags.yml`'s comment header.

require "yaml"
require "date"

vocab = YAML.safe_load(File.read("_data/event_tags.yml")).map { |t| t["slug"] }
events = YAML.safe_load(
  File.read("_data/special_events.yml"),
  permitted_classes: [Date, Time],
)

errors = []
unknown_tags = Hash.new(0)

events.each_with_index do |ev, i|
  name = ev["name"] || "(unnamed ##{i})"
  tags = ev["tags"]
  next if tags.nil?
  unless tags.is_a?(Array)
    errors << "#{name}: tags must be a YAML list, got #{tags.class}"
    next
  end
  tags.each do |t|
    unless t.is_a?(String)
      errors << "#{name}: tag entry must be a string, got #{t.class}: #{t.inspect}"
      next
    end
    unless vocab.include?(t)
      unknown_tags[t] += 1
      errors << "#{name}: tag '#{t}' is not in _data/event_tags.yml"
    end
  end
end

if errors.empty?
  puts "OK — #{events.size} events, all tags ∈ #{vocab.size}-slug vocabulary"
  exit 0
end

puts "FAIL: #{errors.size} tag-vocabulary issue(s):"
errors.first(50).each { |e| puts "  ✗ #{e}" }
puts "  … (and #{errors.size - 50} more)" if errors.size > 50

unless unknown_tags.empty?
  puts "\nUnique unknown tag slugs (with usage count):"
  unknown_tags.sort_by { |_, n| -n }.each { |t, n| puts "  • '#{t}'  ×#{n}" }
  puts "If any of these are real new categories, add them to _data/event_tags.yml."
end

exit 1
