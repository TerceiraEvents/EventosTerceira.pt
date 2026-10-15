#!/usr/bin/env ruby
# Regression for the BPARLSR "Biblioagenda October 2026" programme
# (https://bparlsr.azores.gov.pt/destaque/biblioagenda-outubro-2/):
# asserts the dated in-window items are present once each and that the
# printed Confluencia run is reflected on the existing record.
require "minitest/autorun"
require "yaml"
require "date"

class LibraryProgrammeTest < Minitest::Test
  DATA = YAML.safe_load(File.read("_data/special_events.yml"), permitted_classes: [Date, Time])

  def find_records(fragment, date: nil)
    DATA.select do |event|
      event.is_a?(Hash) && event["name"].to_s.include?(fragment) &&
        (date.nil? || event["date"] == date)
    end
  end

  def assert_single(fragment, date, time = nil)
    records = find_records(fragment, date: date)
    assert_equal 1, records.size, "expected exactly one #{fragment.inspect} on #{date}, found #{records.size}"
    assert_equal time, records.first["time"], "#{fragment} #{date} time" if time
    records.first
  end

  def test_confluencia_runs_to_printed_october_end
    record = DATA.find { |event| event["id"] == "ba658ad2-7d03-4c09-a9b2-7e1e2b1146f2" }
    refute_nil record, "existing Confluencia record must be preserved by id"
    assert_equal Date.new(2026, 6, 30), record["date"]
    assert_equal Date.new(2026, 10, 31), record["end_date"], "programme prints 30/06 - 31/10"
  end

  def test_october_book_presentations
    jazz = assert_single("Jazz, Golf and American Dream", Date.new(2026, 10, 15), "18:30")
    assert_equal "Biblioteca Pública e Arquivo Regional Luís da Silva Ribeiro", jazz["venue"]
    altar = assert_single("Altar ao Divino Espírito Santo", Date.new(2026, 10, 21), "18:30")
    assert_equal "Biblioteca Pública e Arquivo Regional Luís da Silva Ribeiro", altar["venue"]
  end

  def test_aventuras_fantasticas_in_window_wednesdays
    [14, 21, 28].each do |day|
      assert_single("Aventuras Fantásticas", Date.new(2026, 10, day), "15:00–17:00")
    end
  end

  def test_lanterna_magica_october_wednesdays
    [14, 21, 28].each do |day|
      assert_single("Pensar com a Caixa", Date.new(2026, 10, day), "15:30–18:00")
    end
  end

  def test_livro_assombrado_is_a_bounded_event_not_an_exhibition
    record = assert_single("Livro Assombrado", Date.new(2026, 10, 21))
    assert_equal "event", record["kind"]
    assert_equal Date.new(2026, 11, 7), record["end_date"]
    refute record.fetch("tags", []).include?("exhibition")
    assert record["visiting_hours"], "library opening hours must be stated, not a fixed daily time"
  end

  def test_nocturnos_de_angra_exhibition
    record = assert_single("Nocturnos de Angra", Date.new(2026, 10, 20))
    assert_equal "exhibition", record["kind"]
    assert_equal Date.new(2027, 1, 30), record["end_date"]
  end
end
