#!/usr/bin/env ruby
# Validates _data/special_events.yml record shapes before the site build.
# Validates typed dates, inclusive ranges, listing kind, and paired EN/PT
# published visiting schedules.
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
    if !ending.nil? && !ending.is_a?(Date)
      errors << "#{name}: `end_date` must be an unquoted ISO date (YYYY-MM-DD), got #{ending.class}: #{ending.inspect}. " \
                "Do not wrap the date in quotes — YAML will parse it as a String and break range selection."
    elsif ending.is_a?(Date) && ending < date
      errors << "#{name}: `end_date` (#{ending}) is before `date` (#{date})"
    end

    kind = event["kind"]
    unless kind.nil? || %w[event exhibition].include?(kind)
      errors << "#{name}: `kind` must be `event` or `exhibition`, got #{kind.inspect}"
    end

    if event.key?('visiting_hours') != event.key?('visiting_hours_pt')
      errors << "#{name}: provide `visiting_hours` and `visiting_hours_pt` together"
    end
    %w[visiting_hours visiting_hours_pt].each do |field|
      value = event[field]
      if !value.nil? && (!value.is_a?(String) || value.strip.empty?)
        errors << "#{name}: `#{field}` must be a non-empty string"
      end
    end

    tags = event["tags"]
    tagged_exhibition = tags.is_a?(Array) && tags.include?("exhibition")
    if kind == "exhibition"
      errors << "#{name}: `kind: exhibition` requires a Date `end_date` strictly after `date`" unless ending.is_a?(Date) && ending > date
      errors << "#{name}: `kind: exhibition` requires the `exhibition` tag" unless tagged_exhibition
    elsif tagged_exhibition && ending.is_a?(Date) && ending > date && kind.nil?
      errors << "#{name}: multi-day record tagged `exhibition` must declare `kind` explicitly"
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
