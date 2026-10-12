require 'yaml'
require 'date'
require_relative 'validate_event_data'

def load_locality_lookup(path)
  venues = YAML.safe_load(File.read(path))
  lookup = {}
  venues.each do |venue|
    raise ArgumentError, "invalid locality for #{venue['key']}" unless %w[angra praia other].include?(venue['locality'])
    raise ArgumentError, "missing evidence for #{venue['key']}" unless venue['location_evidence'].is_a?(Array) && !venue['location_evidence'].empty?
    venue.fetch('aliases').each do |name|
      raise ArgumentError, "invalid or duplicate venue alias: #{name}" unless name.is_a?(String) && !name.empty? && !lookup.key?(name)
      lookup[name] = venue['locality']
    end
  end
  lookup
end

def apply_event_localities(text, lookup)
  input = YAML.safe_load(text, permitted_classes: [Date, Time])
  errors = validate_events(input, require_ids: false)
  raise ArgumentError, errors.join("\n") unless errors.empty?
  stream = Psych.parse_stream(text)
  raise ArgumentError, 'expected exactly one YAML document' unless stream.children.size == 1
  sequence = stream.children.first.root
  raise ArgumentError, 'expected a YAML sequence' unless sequence.is_a?(Psych::Nodes::Sequence)
  offsets = [0]
  text.each_line { |line| offsets << offsets.last + line.length }
  edits = []
  input.each_with_index do |event, index|
    next if event.key?('locality')
    locality = lookup[event['venue']]
    next unless locality
    mapping = sequence.children.fetch(index)
    if mapping.style == Psych::Nodes::Mapping::FLOW
      offset = offsets.fetch(mapping.end_line) + mapping.end_column - 1
      raise ArgumentError, "#{event['name']}: invalid flow boundary" unless text[offset] == '}'
      separator = text[0...offset].rstrip.end_with?(',') ? '' : ','
      edits << [offset, "#{separator} locality: #{locality}"]
    else
      offset = offsets.fetch(mapping.end_line, text.length)
      prefix = offset == text.length && !text.end_with?("\n") ? "\n" : ''
      edits << [offset, "#{prefix}#{' ' * mapping.start_column}locality: #{locality}\n"]
    end
  end
  output = text.dup
  edits.sort_by(&:first).reverse_each { |offset, insertion| output.insert(offset, insertion) }
  records = YAML.safe_load(output, permitted_classes: [Date, Time])
  errors = validate_events(records, require_ids: false)
  raise ArgumentError, errors.join("\n") unless errors.empty?
  without_locality = ->(events) { events.map { |event| event.reject { |key, _| key == 'locality' } } }
  raise ArgumentError, 'event metadata changed during locality assignment' unless without_locality.call(records) == without_locality.call(input)
  [output, edits.size]
end

if $PROGRAM_NAME == __FILE__
  path = ARGV.fetch(0, '_data/special_events.yml')
  lookup = load_locality_lookup(ARGV.fetch(1, '_data/venue_localities.yml'))
  result, assigned = apply_event_localities(File.read(path), lookup)
  File.write(path, result) if assigned.positive?
  puts "Assigned #{assigned} localities from #{lookup.size} exact venue aliases"
end
