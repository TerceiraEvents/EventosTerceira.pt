require 'yaml'
require 'date'

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
  assigned = 0
  blocks = text.split(/(?=^- [a-zA-Z_]+:)/)
  blocks.map! do |block|
    next block unless block.match?(/\A- [a-zA-Z_]+:/)
    event = YAML.safe_load(block, permitted_classes: [Date, Time]).first
    next block if event.key?('locality')
    locality = lookup[event['venue']]
    next block unless locality
    assigned += 1
    block.sub(/(^- [a-zA-Z_]+:[^\n]*\n)/, "\\1  locality: #{locality}\n")
  end
  [blocks.join, assigned]
end

if $PROGRAM_NAME == __FILE__
  path = ARGV.fetch(0, '_data/special_events.yml')
  lookup = load_locality_lookup(ARGV.fetch(1, '_data/venue_localities.yml'))
  result, assigned = apply_event_localities(File.read(path), lookup)
  File.write(path, result) if assigned.positive?
  puts "Assigned #{assigned} localities from #{lookup.size} exact venue aliases"
end
