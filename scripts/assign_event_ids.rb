require 'yaml'
require 'date'
require 'securerandom'
require_relative 'validate_event_data'

def assign_event_ids(text)
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
    next unless event['id'].nil?
    mapping = sequence.children.fetch(index)
    raise ArgumentError, "#{event['name']}: expected a mapping" unless mapping.is_a?(Psych::Nodes::Mapping)
    id = SecureRandom.uuid
    if mapping.style == Psych::Nodes::Mapping::FLOW
      offset = offsets.fetch(mapping.end_line) + mapping.end_column - 1
      raise ArgumentError, "#{event['name']}: invalid flow mapping boundary" unless text[offset] == '}'
      separator = text[0...offset].rstrip.end_with?(',') ? '' : ','
      edits << [offset, "#{separator} id: #{id}"]
    else
      offset = offsets.fetch(mapping.end_line, text.length)
      prefix = offset == text.length && !text.end_with?("\n") ? "\n" : ''
      edits << [offset, "#{prefix}#{' ' * mapping.start_column}id: #{id}\n"]
    end
  end
  output = text.dup
  edits.sort_by(&:first).reverse_each { |offset, insertion| output.insert(offset, insertion) }
  records = YAML.safe_load(output, permitted_classes: [Date, Time])
  errors = validate_events(records)
  raise ArgumentError, errors.join("\n") unless errors.empty?
  raise ArgumentError, 'record count changed during assignment' unless records.size == input.size
  without_ids = ->(entries) { entries.map { |event| event.reject { |key, _| key == 'id' } } }
  raise ArgumentError, 'event metadata changed during assignment' unless without_ids.call(records) == without_ids.call(input)
  [output, edits.size, records.size]
end

if $PROGRAM_NAME == __FILE__
  path = ARGV.fetch(0, '_data/special_events.yml')
  begin
    output, assigned, total = assign_event_ids(File.read(path))
    File.write(path, output) if assigned.positive?
    puts "Assigned #{assigned} IDs; #{total} distinct events"
  rescue Psych::Exception, ArgumentError => error
    warn error.message
    exit 1
  end
end
