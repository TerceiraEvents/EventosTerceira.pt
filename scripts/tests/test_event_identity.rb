require 'minitest/autorun'
require 'tmpdir'
require 'yaml'
require 'date'
require 'open3'
require 'rbconfig'

class EventIdentityTest < Minitest::Test
  ROOT = File.expand_path('../..', __dir__)
  SCRIPT = File.join(ROOT, 'scripts/assign_event_ids.rb')
  VALIDATOR = File.join(ROOT, 'scripts/validate_event_data.rb')

  def assign(path, preload = nil)
    args = [RbConfig.ruby]
    args += ['-r', preload] if preload
    stdout, stderr, status = Open3.capture3(*args, SCRIPT, path)
    [stdout, stderr, status]
  end

  def test_supported_yaml_shapes_preserve_all_fields
    shapes = [
      "- name: |\n    Multi line title\n  date: 2026-10-12\n",
      "- name: >-\n    Multi line title\n  date: 2026-10-12\n",
      "- date: 2026-10-12\n  name: A\n- {date: 2026-10-13, name: B}\n",
      "- \"date\": 2026-10-12\n  name: Quoted\n",
      "- source-id: source-one\n  date: 2026-10-12\n  name: Hyphen\n",
      "- date: 2026-10-12\n  name: No final newline",
      "[{date: 2026-10-12, name: Música}, {date: 2026-10-13, name: B}]",
      "- date: 2026-10-12\n  description: |\n    Published programme\n"
    ]
    shapes.each do |source|
      Dir.mktmpdir do |dir|
        path = File.join(dir, 'events.yml')
        File.write(path, source)
        before = YAML.safe_load(source, permitted_classes: [Date])
        stdout, stderr, status = assign(path)
        assert status.success?, "#{source.inspect}: #{stderr}"
        records = YAML.safe_load(File.read(path), permitted_classes: [Date])
        assert_equal before, records.map { |event| event.reject { |key, _| key == 'id' } }, source.inspect
        assert_equal before.size, records.map { |event| event.fetch('id') }.uniq.size
        assert_includes stdout, "#{before.size} distinct events"
        _, stderr, status = Open3.capture3(RbConfig.ruby, VALIDATOR, path)
        assert status.success?, stderr
        assigned = File.read(path)
        assert_no_duplicate_keys(assigned)
        _, stderr, status = assign(path)
        assert status.success?, stderr
        assert_equal assigned, File.read(path)
      end
    end
  end

  def test_null_id_keys_are_rejected_without_writing
    ["id:", "id: ~", "\"id\": null"].each do |line|
      Dir.mktmpdir do |dir|
        path = File.join(dir, 'events.yml')
        original = "- date: 2026-10-12\n  #{line}\n  name: Null identity\n"
        File.write(path, original)
        _, stderr, status = assign(path)
        refute status.success?, line
        assert_includes stderr, 'Null identity'
        assert_equal original, File.read(path)
      end
    end
  end

  def assert_no_duplicate_keys(text)
    visit = lambda do |node|
      if node.is_a?(Psych::Nodes::Mapping)
        keys = node.children.each_slice(2).map { |key, _| key.value }
        assert_equal keys.uniq, keys, "duplicate keys at line #{node.start_line + 1}"
      end
      (node.children || []).each { |child| visit.call(child) } if node.respond_to?(:children)
    end
    visit.call(Psych.parse_stream(text))
  end

  def test_existing_ids_and_source_metadata_are_untouched_when_appending
    Dir.mktmpdir do |dir|
      path = File.join(dir, 'events.yml')
      source = "# Curated record\n- date: 2026-10-12\n  id: existing-id\n  name: Corrected title\n  venue: Corrected venue\n  source_uid: source-one\n"
      File.write(path, source)
      _, stderr, status = assign(path)
      assert status.success?, stderr
      assert_equal source, File.read(path)
      File.write(path, source + "- date: 2026-10-12\n  name: Corrected title\n  source_uid: source-two\n")
      _, stderr, status = assign(path)
      assert status.success?, stderr
      records = YAML.safe_load(File.read(path), permitted_classes: [Date])
      assert_equal 'existing-id', records.first['id']
      assert_equal 'source-one', records.first['source_uid']
      refute_equal 'existing-id', records.last['id']
      assert File.read(path).start_with?(source)
    end
  end

  def test_invalid_generated_id_cannot_be_written
    Dir.mktmpdir do |dir|
      path = File.join(dir, 'events.yml')
      original = "- date: 2026-10-12\n  name: Publication test\n"
      File.write(path, original)
      preload = File.join(dir, 'bad_uuid.rb')
      File.write(preload, "require 'securerandom'\nmodule SecureRandom\n def self.uuid; 'has space'; end\nend\n")
      _, stderr, status = assign(path, preload)
      refute status.success?
      assert_includes stderr, 'Publication test'
      assert_equal original, File.read(path)
    end
  end

  def test_multiple_documents_are_rejected_without_writing
    Dir.mktmpdir do |dir|
      path = File.join(dir, 'events.yml')
      original = "- date: 2026-10-12\n  name: First\n---\n- date: 2026-10-13\n  name: Second\n"
      File.write(path, original)
      _, stderr, status = assign(path)
      refute status.success?
      assert_includes stderr, 'exactly one YAML document'
      assert_equal original, File.read(path)
    end
  end

  def test_published_ids_are_distinct_and_named_errors_are_actionable
    data = YAML.safe_load(File.read(File.join(ROOT, '_data/special_events.yml')), permitted_classes: [Date, Time])
    invalid = data.select { |event| !event['id'].is_a?(String) || !event['id'].match?(/\A[a-zA-Z0-9_-]+\z/) }
    assert_empty invalid, "Invalid/missing IDs: #{invalid.map { |event| event['name'] }.join(', ')}; run ruby scripts/assign_event_ids.rb"
    groups = data.group_by { |event| event['id'] }.values.select { |events| events.size > 1 }
    assert_empty groups, "Duplicate IDs: #{groups.flatten.map { |event| event['name'] }.join(', ')}"
  end
end
