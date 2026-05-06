#!/usr/bin/env ruby
# Validates the `lang:` front-matter on every file in `_posts/`.
#
# The blog ships each story as two parallel files: `slug.md` (English)
# and `slug-pt.md` (Portuguese). Both the website's bilingual permalinks
# and the mobile app's de-duplication logic
# (TerceiraEventsApp/src/utils/posts.js → groupPostsByLanguage) depend
# on `lang:` being a known value, and on the filename suffix matching
# the declared language. Curator typos like `lang: portugese` or a
# PT-content file accidentally named without the `-pt` suffix would
# silently break either side — this catches them at PR time.

require "yaml"
require "date"

ALLOWED_LANGS = %w[en pt].freeze

# Read the front-matter block of a Jekyll post. Returns the parsed
# hash, or nil when the file isn't a Jekyll-style post.
def read_front_matter(path)
  text = File.read(path)
  return nil unless text.start_with?("---")
  m = text.match(/\A---\r?\n(.*?)\r?\n---\r?\n/m)
  return nil unless m
  YAML.safe_load(m[1], permitted_classes: [Date, Time]) || {}
rescue Psych::SyntaxError => e
  { "__yaml_error" => e.message }
end

errors = []

posts = Dir["_posts/*.md"].sort
if posts.empty?
  warn "No posts found in _posts/. (test_post_lang itself isn't broken — there's just nothing to check.)"
  exit 0
end

posts.each do |path|
  name = File.basename(path)
  meta = read_front_matter(path)

  if meta.nil?
    errors << "#{name}: no Jekyll front matter found"
    next
  end

  if (yaml_err = meta["__yaml_error"])
    errors << "#{name}: invalid YAML in front matter — #{yaml_err}"
    next
  end

  lang = meta["lang"]
  unless lang
    errors << "#{name}: missing `lang:` front-matter field (must be one of #{ALLOWED_LANGS.join(", ")})"
    next
  end

  unless ALLOWED_LANGS.include?(lang)
    errors << "#{name}: `lang: #{lang.inspect}` is not allowed — must be one of #{ALLOWED_LANGS.join(", ")}"
    next
  end

  # Filename suffix must match the declared language. The mobile app
  # de-duplicates pairs by stripping a trailing `-pt` from the slug,
  # so an EN-content file named `*-pt.md` would collide with the
  # actual PT partner and one of them would lose.
  pt_suffix = name.sub(/\.md\z/, "").end_with?("-pt")

  if pt_suffix && lang != "pt"
    errors << "#{name}: filename ends with `-pt` but `lang: #{lang}` (filename suggests Portuguese)"
  elsif !pt_suffix && lang == "pt"
    errors << "#{name}: `lang: pt` but filename is missing the `-pt` suffix (rename to `*-pt.md` so the app's bilingual grouping picks it up)"
  end

  # PT posts must live under /pt/ on the website. Without an explicit
  # permalink Jekyll would expose them at the EN slug and clobber the
  # English partner.
  if lang == "pt"
    permalink = meta["permalink"]
    unless permalink.is_a?(String) && permalink.start_with?("/pt/")
      errors << "#{name}: `lang: pt` requires `permalink:` starting with `/pt/` (got #{permalink.inspect})"
    end
  end
end

if errors.empty?
  puts "OK: #{posts.size} post(s) checked, all `lang:` front-matter valid."
  exit 0
end

warn "Post `lang:` front-matter validation failed:"
errors.each { |e| warn "  - #{e}" }
warn ""
warn "Allowed values: #{ALLOWED_LANGS.join(", ")}. EN files = `slug.md`, PT files = `slug-pt.md` with `permalink: /pt/...`."
exit 1
