#!/usr/bin/env ruby
# Validates the /.well-known/ platform association files (AASA +
# assetlinks.json) for the native app's deep links — source level
# always, built `_site/` level when a `jekyll build` output exists.

require "json"
require "yaml"
require_relative "association_contract"

C = AssociationContract
ROOT = File.expand_path("../..", __dir__)
SITE = ENV.fetch("SITE", File.join(ROOT, "_site"))
errors = []

def check_files(dir, errors)
  {
    "assetlinks.json" => ->(doc, l, e) { AssociationContract.check_assetlinks_doc(doc, l, e) },
    "apple-app-site-association" => ->(doc, l, e) { AssociationContract.check_aasa_doc(doc, l, e) },
  }.each do |name, check|
    path = File.join(dir, ".well-known", name)
    errors << "#{path}: missing" and next unless File.exist?(path)
    doc = AssociationContract.parse_json(File.read(path), path, errors)
    check.call(doc, path, errors)
  end
end

check_files(ROOT, errors)

config = YAML.safe_load(File.read(File.join(ROOT, "_config.yml")))
unless Array(config["include"]).map { |i| i.to_s.sub(%r{/\z}, "") }.include?(".well-known")
  errors << "_config.yml: `include:` must list .well-known so Jekyll emits it into _site/"
end

if Dir.exist?(SITE)
  check_files(SITE, errors)
  %w[assetlinks.json apple-app-site-association].each do |name|
    src = File.join(ROOT, ".well-known", name)
    built = File.join(SITE, ".well-known", name)
    if File.exist?(built) && File.exist?(src) && File.read(built) != File.read(src)
      errors << "#{built}: content diverges from source"
    end
  end
  puts "Checked built output under #{SITE}/.well-known/"
else
  puts "No #{SITE}/ — source-level checks only (run `bundle exec jekyll build` for built checks)"
end

# Every mutation below must produce at least one recorded error.
valid_al = [{ "relation" => [C::ANDROID_RELATION],
             "target" => { "namespace" => "android_app", "package_name" => C::ANDROID_PACKAGE,
                           "sha256_cert_fingerprints" => [C::ANDROID_CERT] } }]
valid_aasa = { "applinks" => { "apps" => [], "details" => [
               { "appID" => C::AASA_APP_ID, "paths" => C::EXPECTED_PATHS }] } }
mutations = {
  "extra android_app/web namespace entry" => ->(e) {
    C.check_assetlinks_doc(
      valid_al + [{ "relation" => [C::ANDROID_RELATION],
                    "target" => { "namespace" => "web", "site" => "https://unrelated.example" } }],
      "neg", e)
  },
  "extra AASA detail for another team/app" => ->(e) {
    doc = JSON.parse(JSON.generate(valid_aasa))
    doc["applinks"]["details"] << { "appID" => "OTHERTEAM.com.unrelated.app", "paths" => ["*"] }
    C.check_aasa_doc(doc, "neg", e)
  },
  "wrong signing certificate" => ->(e) {
    doc = JSON.parse(JSON.generate(valid_al))
    doc[0]["target"]["sha256_cert_fingerprints"] = ["AA:BB:CC"]
    C.check_assetlinks_doc(doc, "neg", e)
  },
  "extra unexpected path" => ->(e) {
    doc = JSON.parse(JSON.generate(valid_aasa))
    doc["applinks"]["details"][0]["paths"] << "/saved"
    C.check_aasa_doc(doc, "neg", e)
  },
  "invalid JSON" => ->(e) {
    C.parse_json("{ not json", "neg", e)
  },
  "redirect status" => ->(e) {
    C.check_association_response("301", "application/json", "[]", "neg assetlinks", true, e)
  },
  "non-JSON content-type on assetlinks" => ->(e) {
    C.check_association_response("200", "text/html", JSON.generate(valid_al), "neg assetlinks", true, e)
  },
  "JSON-like content-type on assetlinks" => ->(e) {
    C.check_association_response("200", "application/jsonp", JSON.generate(valid_al), "neg assetlinks", true, e)
  },
  "non-array legacy AASA apps" => ->(e) {
    doc = JSON.parse(JSON.generate(valid_aasa))
    doc["applinks"]["apps"] = false
    C.check_aasa_doc(doc, "neg", e)
  },
  "mixed legacy and modern AASA details" => ->(e) {
    doc = JSON.parse(JSON.generate(valid_aasa))
    doc["applinks"]["details"][0]["appIDs"] = ["OTHERTEAM.com.unrelated.app"]
    doc["applinks"]["details"][0]["components"] = [{ "/" => "*" }]
    C.check_aasa_doc(doc, "neg", e)
  },
}
%w[assetlinks aasa].product(%w[null false]).each do |document, literal|
  mutations["#{document} rejects JSON #{literal}"] = ->(e) {
    C.check_association_response("200", "application/json", literal, "neg #{document}", document == "assetlinks", e)
  }
end
C.check_association_response("200", "Application/JSON; charset=utf-8", JSON.generate(valid_al),
                             "valid assetlinks", true, errors)
mutations.each do |name, run|
  local = []
  run.call(local)
  puts "  negative case '#{name}': #{local.size} error(s) — #{local.first}" if local.any?
  errors << "negative case '#{name}' produced no errors" if local.empty?
end

if errors.empty?
  puts "OK — association files match the verified identities and route contract (#{mutations.size} negative cases verified)"
  exit 0
end
puts "FAIL: #{errors.size} error(s):"
errors.each { |e| puts "  ✗ #{e}" }
exit 1
