#!/usr/bin/env ruby
# Validates _data/special_events.yml record shapes before the site build.
# Validates typed dates, inclusive ranges, listing kind, and paired EN/PT
# published visiting schedules.
# Run from the repo root:
#   ruby scripts/validate_event_data.rb _data/special_events.yml
require "yaml"
require "date"

def validate_events(data, require_ids: true)
  errors = []
  unless data.is_a?(Array)
    return ["expected a top-level YAML list, got #{data.class}"]
  end

  # Every event must have a Date-typed `date` field: mixed String/Date
  # entries crash Liquid's `sort: "date"` with
  # "comparison of Array with Array failed".
  seen_ids = {}
  data.each_with_index do |event, i|
    unless event.is_a?(Hash)
      errors << "record ##{i}: expected a YAML mapping, got #{event.class}"
      next
    end
    name = event["name"] || "(unnamed ##{i})"
    id = event["id"]
    if id.nil?
      errors << "#{name}: missing `id` — run ruby scripts/assign_event_ids.rb" if require_ids
    elsif !id.is_a?(String) || !id.match?(/\A[a-zA-Z0-9_-]+\z/)
      errors << "#{name}: invalid `id`"
    elsif seen_ids[id]
      errors << "#{name}: duplicate `id` #{id.inspect}, also held by #{seen_ids[id]}; retain the older persisted ID"
    else
      seen_ids[id] = name
    end
    if !event["locality"].nil? && !%w[angra praia other].include?(event["locality"])
      errors << "#{name}: `locality` must be angra, praia, or other"
    end
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

def yaml_mapping_errors(text)
  stream = Psych.parse_stream(text)
  errors = []
  errors << 'expected exactly one YAML document' unless stream.children.size == 1
  visit = lambda do |node, context|
    if node.is_a?(Psych::Nodes::Mapping)
      pairs = node.children.each_slice(2).to_a
      named = pairs.find { |key, value| key.is_a?(Psych::Nodes::Scalar) && key.value == 'name' && value.is_a?(Psych::Nodes::Scalar) }
      context = named ? named.last.value : context
      seen = {}
      pairs.each do |key, _|
        next unless key.is_a?(Psych::Nodes::Scalar)
        errors << "#{context}: duplicate YAML key `#{key.value}` at line #{key.start_line + 1}" if seen[key.value]
        seen[key.value] = true
      end
    end
    (node.children || []).each { |child| visit.call(child, context) } if node.respond_to?(:children)
  end
  visit.call(stream, 'event data')
  errors
end

def validate_event_yaml(text, require_ids: true)
  errors = yaml_mapping_errors(text)
  return errors unless errors.empty?
  data = YAML.safe_load(text, permitted_classes: [Date, Time])
  validate_events(data, require_ids: require_ids)
end

if $PROGRAM_NAME == __FILE__
  path = ARGV[0] || "_data/special_events.yml"
  # Psych instantiates Date only with permitted_classes; the explicit
  # File.read form accepts that keyword across Ruby versions.
  text = File.read(path, encoding: 'UTF-8')
  errors = validate_event_yaml(text)
  data = YAML.safe_load(text, permitted_classes: [Date, Time])

  if errors.any?
    warn "event data validation failed:"
    errors.each { |e| warn "  - #{e}" }
    exit 1
  end

  puts "#{path}: OK (#{data.size} events, all dates are Date-typed)"
end
