require 'minitest/autorun'
require_relative '../assign_event_localities'

class EventLocalitiesTest < Minitest::Test
  def setup
    @lookup = load_locality_lookup('_data/venue_localities.yml')
  end

  def test_exact_aliases_and_unknown_names
    assert_equal 'angra', @lookup['Centro Cultural e de Congressos de Angra do Heroísmo']
    assert_equal 'angra', @lookup['CCCAH (Centro Cultural e de Congressos)']
    assert_equal 'praia', @lookup['Auditório do Ramo Grande']
    ['Unknown venue in Angra', 'Museu de Angra do Heroísmo', 'Auditório do Ramo Grande — outside event', 'Recreio dos Artistas'.downcase, nil].each do |name|
      assert_nil @lookup[name]
    end
  end

  def test_curator_correction_and_unknown_are_preserved
    original = "# Curated records\n- name: Corrected title\n  date: 2026-10-12\n  id: event-one\n  venue: Recreio dos Artistas\n  locality: other\n- date: 2026-10-12\n  venue: Unknown Angra event\n"
    result, count = apply_event_localities(original, @lookup)
    assert_equal original, result
    assert_equal 0, count
  end

  def test_assignment_preserves_identity_source_comments_and_is_idempotent
    original = "# Venue event\n- name: Published title\n  date: 2026-10-12\n  id: permanent-id\n  venue: Auditório do Ramo Grande\n  source_uid: source-42\n"
    result, count = apply_event_localities(original, @lookup)
    assert_equal 1, count
    data = YAML.safe_load(result, permitted_classes: [Date]).first
    assert_equal 'praia', data['locality']
    assert_equal 'permanent-id', data['id']
    assert_equal 'source-42', data['source_uid']
    assert result.start_with?("# Venue event\n")
    repeated, count = apply_event_localities(result, @lookup)
    assert_equal result, repeated
    assert_equal 0, count
  end

  def test_curator_can_clear_locality_after_venue_correction
    original = "- date: 2026-10-12\n  id: permanent-id\n  venue: Recreio dos Artistas\n"
    result, count = apply_event_localities(original, @lookup)
    data = YAML.safe_load(result, permitted_classes: [Date]).first
    assert_equal 1, count
    assert_equal 'angra', data['locality']
    assert_equal 'permanent-id', data['id']
  end

  def test_published_subset_has_both_city_localities
    data = YAML.safe_load(File.read('_data/special_events.yml'), permitted_classes: [Date, Time])
    @lookup.each do |venue, locality|
      events = data.select { |event| event['venue'] == venue }
      refute_empty events, venue
      assert events.all? { |event| event.key?('locality') }, venue
      assert events.any? { |event| event['locality'] == locality }, venue
    end
    assert data.any? { |event| !event.key?('locality') }
  end
end
