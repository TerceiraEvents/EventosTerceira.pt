require 'yaml'
require 'date'
require 'securerandom'

path = ARGV.fetch(0, '_data/special_events.yml')
text = File.read(path)
blocks = text.split(/(?=^- [a-zA-Z_]+:)/)
seen = {}
changed = 0
blocks.map! do |block|
  next block unless block.match?(/\A- [a-zA-Z_]+:/)
  record = YAML.safe_load(block, permitted_classes: [Date, Time]).first
  id = record['id']
  if id
    abort "Invalid or duplicate event ID: #{id}" unless id.match?(/\A[a-zA-Z0-9_-]+\z/) && !seen[id]
  else
    id = SecureRandom.uuid
    block = block.sub(/(^- [a-zA-Z_]+:[^\n]*\n)/, "\\1  id: #{id}\n")
    changed += 1
  end
  seen[id] = true
  block
end
File.write(path, blocks.join) if changed.positive?
puts "Assigned #{changed} IDs; #{seen.size} distinct events"
