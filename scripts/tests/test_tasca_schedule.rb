#!/usr/bin/env ruby
require "minitest/autorun"
require "yaml"

class TascaScheduleTest < Minitest::Test
  ROOT = File.expand_path("../..", __dir__)

  def test_published_tasca_recurrences_are_karaoke_on_confirmed_days
    weekly = YAML.load_file(File.join(ROOT, "_data/weekly.yml"))
    tasca = weekly.flat_map { |day| day.fetch("events").filter_map { |event| [day.fetch("day"), event] if event["venue"] == "Tasca do Camões" } }
    assert_equal %w[Monday Wednesday Sunday], tasca.map(&:first)
    assert tasca.all? { |_, event| event["name"].include?("Karaoke") && event["name_pt"].include?("Karaoke") }
  end

  def test_bilingual_venue_schedule_matches_confirmed_days
    venue = YAML.load_file(File.join(ROOT, "_data/venues.yml")).find { |entry| entry["name"] == "Tasca do Camões" }
    assert_equal %w[Monday Wednesday Sunday], venue.fetch("weekly").map { |entry| entry.fetch("day") }
    %w[description description_pt].each { |field| refute_match(/Latin|latina/i, venue.fetch(field)) }
  end
end
