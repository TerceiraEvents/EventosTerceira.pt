require "minitest/autorun"
require "yaml"
require "date"

class OctoberSocialScanTest < Minitest::Test
  EVENTS = YAML.safe_load(File.read("_data/special_events.yml"), permitted_classes: [Date, Time])

  def test_cine_atlantico_final_screening_time
    event = EVENTS.find { |item| item["id"] == "c822c56b-296e-4829-957f-916dfc769ddf" }
    refute_nil event
    assert_equal Date.new(2026, 10, 25), event["date"]
    assert_equal "21:00", event["time"]
  end

  def test_drawing_course_opening_is_a_free_trial
    event = EVENTS.find { |item| item["id"] == "fcbb190c-4f15-4fbc-b865-c7c673d215c7" }
    refute_nil event
    assert_includes event["tags"], "free"
    assert_match(/free trial/i, event["description"])
  end

  def test_halloween_midnight_screening_uses_following_calendar_day
    events = EVENTS.select { |item| item["name"].to_s.include?("Halloween Drive-In: Hokum") }
    assert_equal 1, events.length
    assert_equal Date.new(2026, 11, 1), events.first["date"]
    assert_equal "00:00", events.first["time"]
    assert_includes events.first["description"], "31 October at 24:00"
  end

  def test_entre_terra_exhibition_preserves_weekday_restriction
    event = EVENTS.find { |item| item["id"] == "717abb33-5352-48f7-a06b-1d971459881c" }
    refute_nil event
    assert_includes event["visiting_hours"], "Monday to Friday"
    assert_includes event["visiting_hours_pt"], "segunda a sexta-feira"
    assert_includes event["description"], "opening on October 11 at 16:00"
  end
end
