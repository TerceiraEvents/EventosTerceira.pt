require 'minitest/autorun'
require 'tmpdir'
require 'yaml'
require 'date'
require 'open3'

class EventIdentityTest < Minitest::Test
  def test_id_assignment_and_corrections
    Dir.mktmpdir do |dir|
      path = File.join(dir, 'events.yml')
      File.write(path, "- date: 2026-10-12\n  name: Same title\n- date: 2026-10-13\n  name: Same title\n")
      _, status = Open3.capture2('ruby', 'scripts/assign_event_ids.rb', path)
      assert status.success?
      data = YAML.safe_load(File.read(path), permitted_classes: [Date])
      assert_equal 2, data.map { |e| e['id'] }.uniq.length
      original = File.read(path)
      File.write(path, original.sub('Same title', 'Corrected title').sub('2026-10-12', '2026-10-14'))
      corrected = File.read(path)
      _, status = Open3.capture2('ruby', 'scripts/assign_event_ids.rb', path)
      assert status.success?
      assert_equal corrected, File.read(path)
    end
  end

  def test_published_ids_are_distinct
    data = YAML.safe_load(File.read('_data/special_events.yml'), permitted_classes: [Date, Time])
    ids = data.map { |e| e['id'] }
    assert ids.all? { |id| id && id.match?(/\A[a-zA-Z0-9_-]+\z/) }
    assert_equal ids.length, ids.uniq.length
  end
end

class EventIdentityTest
  def test_first_field_can_be_name
    Dir.mktmpdir do |dir|
      path = File.join(dir, 'events.yml')
      File.write(path, "- name: Example\n  date: 2026-10-12\n")
      _, status = Open3.capture2('ruby', 'scripts/assign_event_ids.rb', path)
      assert status.success?
      assert YAML.safe_load(File.read(path), permitted_classes: [Date]).first['id']
    end
  end
end
