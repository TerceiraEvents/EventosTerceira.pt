#!/usr/bin/env ruby
# Validates _data/special_events.yml record shapes before the site build.
# Every event needs a Date-typed `date`; a present `end_date` must also be
# Date-typed and must not precede `date`. Mixed String/Date entries crash
# Liquid's `sort: "date"` with "comparison of Array with Array failed",
# and a quoted or reversed `end_date` silently breaks range selection.
# Run from the repo root:
#   ruby scripts/validate_event_data.rb _data/special_events.yml
require "yaml"
require "date"

def validate_events(data)
  errors = []
  unless data.is_a?(Array)
    return ["expected a top-level YAML list, got #{data.class}"]
  end

  # Every event must have a Date-typed `date` field: mixed String/Date
  # entries crash Liquid's `sort: "date"` with
  # "comparison of Array with Array failed".
  data.each_with_index do |event, i|
    name = event["name"] || "(unnamed ##{i})"
    date = event["date"]

    if date.nil?
      errors << "#{name}: missing `date` field"
      next
    end

    unless date.is_a?(Date)
      errors << "#{name}: `date` must be an unquoted ISO date (YYYY-MM-DD), got #{date.class}: #{date.inspect}. " \
                "Do not wrap the date in quotes — YAML will parse it as a String and break the site build."
      next
    end

    ending = event["end_date"]
    next if ending.nil?

    unless ending.is_a?(Date)
      errors << "#{name}: `end_date` must be an unquoted ISO date (YYYY-MM-DD), got #{ending.class}: #{ending.inspect}. " \
                "Do not wrap the date in quotes — YAML will parse it as a String and break range selection."
      next
    end

    if ending < date
      errors << "#{name}: `end_date` (#{ending}) is before `date` (#{date})"
    end
  end

  errors
end

if $PROGRAM_NAME == __FILE__
  path = ARGV[0] || "_data/special_events.yml"
  # Psych instantiates Date only with permitted_classes; the explicit
  # File.read form accepts that keyword across Ruby versions.
  data = YAML.safe_load(File.read(path), permitted_classes: [Date, Time])
  errors = validate_events(data)

  if errors.any?
    warn "event data validation failed:"
    errors.each { |e| warn "  - #{e}" }
    exit 1
  end

  puts "#{path}: OK (#{data.size} events, all dates are Date-typed)"
end
