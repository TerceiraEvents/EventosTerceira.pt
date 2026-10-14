#!/usr/bin/env ruby
# Validates the platform association files served from /.well-known/ for
# the native app's deep links:
#
#   .well-known/apple-app-site-association  (iOS Universal Links, AASA)
#   .well-known/assetlinks.json             (Android App Links, DAL)
#
# Two levels of checking in one script:
#
#   1. Source level — the files under `.well-known/` parse, carry the
#      exact verified production identities, associate only the public
#      routes the native build declares, and `_config.yml` actually
#      includes the dotfile directory so Jekyll copies it into `_site/`.
#      Runs anywhere (`ruby scripts/tests/test_associations.rb`).
#
#   2. Built level — when `_site/` exists (after `jekyll build`), the
#      emitted endpoints are present and byte-identical to the sources.
#      In CI this runs after `bundle exec jekyll build`; locally it is
#      skipped unless a build has already produced `_site/`.
#
require "json"
require "yaml"

ROOT = File.expand_path("../..", __dir__)
SITE = ENV.fetch("SITE", File.join(ROOT, "_site"))

# Verified production identities (Apple Developer + Play Console records).
AASA_APP_ID = "9R3942X8JM.com.terceiraevents.app"
ANDROID_PACKAGE = "com.terceiraevents.app"
ANDROID_CERT = "FD:23:49:C0:4B:57:A5:D2:AF:BE:62:93:D7:92:72:14:29:C4:72:93:" \
               "60:D5:1E:E5:14:74:D2:66:FF:6A:C4:3A"

# Exactly the public routes the native build declares for both hosts:
# canonical trailing-slash forms plus the bare spellings that redirect.
EXPECTED_PATHS = %w[
  /events /events/ /weekly /weekly/ /special /special/
  /pt/events /pt/events/ /pt/weekly /pt/weekly/ /pt/special /pt/special/
].freeze

# Public routes that must NOT be OS-associated.
FORBIDDEN_PATHS = %w[
  /saved /pt/saved /venues /venues/ /pt/venues /pt/venues/
  /blog /pt/blog /contribute /pt/contribute /resources /pt/resources
  /calendar /pt/calendar /archive /pt/archive /suggest /pt/suggest
  / /pt /privacy /pt/privacy /events-other /pt/events-other
].freeze

errors = []

def load_json_file(path, errors)
  errors << "#{path}: missing" unless File.exist?(path)
  return nil unless File.exist?(path)
  JSON.parse(File.read(path))
rescue JSON::ParserError => e
  errors << "#{path}: invalid JSON — #{e.message[0, 80]}"
  nil
end

# Resolve an AASA detail's associated paths from either documented
# schema: legacy `paths` entries or iOS-13+ `components` path items.
def aasa_paths(detail)
  return detail["paths"].sort if detail["paths"].is_a?(Array)

  paths = []
  Array(detail["components"]).each do |component|
    paths << component["/"] if component.is_a?(Hash) && component["/"].is_a?(String)
  end
  paths.sort
end

def check_assetlinks(path, errors)
  data = load_json_file(path, errors)
  return unless data

  errors << "#{path}: top level must be a JSON array" unless data.is_a?(Array)
  entries = Array(data)
  app_entries = entries.select do |entry|
    entry.dig("target", "package_name") == ANDROID_PACKAGE
  end
  errors << "#{path}: no android_app entry for #{ANDROID_PACKAGE}" if app_entries.empty?
  app_entries.each do |entry|
    unless entry["relation"] == ["delegate_permission/common.handle_all_urls"]
      errors << "#{path}: relation must be exactly delegate_permission/common.handle_all_urls"
    end
    target = entry["target"] || {}
    errors << "#{path}: namespace must be android_app" unless target["namespace"] == "android_app"
    unless target["sha256_cert_fingerprints"] == [ANDROID_CERT]
      errors << "#{path}: sha256_cert_fingerprints must be exactly the verified " \
                "Play app-signing certificate (no debug/upload/other certs)"
    end
  end
  # No entries may claim unrelated packages or other namespaces.
  entries.each do |entry|
    target = entry["target"] || {}
    if target["namespace"] == "android_app" && target["package_name"] != ANDROID_PACKAGE
      errors << "#{path}: unexpected package #{target['package_name']}"
    end
  end
end

def check_aasa(path, errors)
  data = load_json_file(path, errors)
  return unless data

  applinks = data["applinks"]
  errors << "#{path}: missing applinks object" and return unless applinks.is_a?(Hash)

  # Only Universal Links are declared — no shared credentials, Handoff,
  # or App Clips sections.
  data.each_key do |key|
    errors << "#{path}: unexpected top-level service #{key}" unless key == "applinks"
  end
  if applinks["apps"].is_a?(Array) && !applinks["apps"].empty?
    errors << "#{path}: applinks.apps must stay empty (details carry the appID)"
  end

  details = Array(applinks["details"])
  matching = details.select do |d|
    d["appID"] == AASA_APP_ID || d["appIDs"].to_a.include?(AASA_APP_ID)
  end
  errors << "#{path}: no detail for verified appID #{AASA_APP_ID}" if matching.empty?
  matching.each do |detail|
    paths = aasa_paths(detail)
    errors << "#{path}: associated paths mismatch; got #{paths.inspect}" unless paths == EXPECTED_PATHS.sort
    paths.each do |p|
      if p.include?("*") || p.include?("?") || p.include?("NOT")
        errors << "#{path}: wildcard path #{p} would associate unrelated routes"
      end
    end
  end
  FORBIDDEN_PATHS.each do |forbidden|
    matching.each do |detail|
      if aasa_paths(detail).include?(forbidden)
        errors << "#{path}: must not associate #{forbidden}"
      end
    end
  end
end

src_assetlinks = File.join(ROOT, ".well-known", "assetlinks.json")
src_aasa = File.join(ROOT, ".well-known", "apple-app-site-association")
check_assetlinks(src_assetlinks, errors)
check_aasa(src_aasa, errors)

config = YAML.safe_load(File.read(File.join(ROOT, "_config.yml")))
includes = Array(config["include"]).map { |i| i.to_s.sub(%r{/\z}, "") }
unless includes.include?(".well-known")
  errors << "_config.yml: `include:` must list .well-known so Jekyll emits it into _site/"
end

if Dir.exist?(SITE)
  { "assetlinks.json" => src_assetlinks, "apple-app-site-association" => src_aasa }.each do |name, src|
    built = File.join(SITE, ".well-known", name)
    errors << "#{built}: missing from built site" unless File.exist?(built)
    next unless File.exist?(built)
    errors << "#{built}: content diverges from source" unless File.read(built) == File.read(src)
  end
  check_assetlinks(File.join(SITE, ".well-known", "assetlinks.json"), errors)
  check_aasa(File.join(SITE, ".well-known", "apple-app-site-association"), errors)
  puts "Checked built output under #{SITE}/.well-known/"
else
  puts "No #{SITE}/ — source-level checks only (run `bundle exec jekyll build` for built checks)"
end

if errors.empty?
  puts "OK — association files match the verified identities and route contract"
  exit 0
end
puts "FAIL: #{errors.size} error(s):"
errors.each { |e| puts "  ✗ #{e}" }
exit 1
