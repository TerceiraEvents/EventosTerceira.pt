#!/usr/bin/env ruby
# Walks `_site/` after `jekyll build` and asserts the invariants the
# rest of the site depends on for SEO, structured data, and link
# previews. Designed to be run from the repo root in CI.
#
# Each assertion is one of the bugs we already shipped a fix for —
# these tests pin those fixes so a regression fails CI loudly instead
# of silently downgrading search/share quality on production.

require "json"
require "rexml/document"

SITE = "_site"
abort "missing #{SITE}/ — run `bundle exec jekyll build` first" unless Dir.exist?(SITE)

errors = []
warnings = []

def err(errors, msg); errors << msg; end
def warn_(warnings, msg); warnings << msg; end

# ─────────────────────────────────────────────────────────────────────
# 1. Per-page meta tags + JSON-LD validity
# ─────────────────────────────────────────────────────────────────────
# Catches:
#   - Silent og:image regression (PR #115 — jekyll-seo-tag dropped
#     URL-encoded Wikipedia path without erroring at build time).
#   - Missing canonical / og:title / og:description if jekyll-seo-tag
#     ever stops emitting them.
#   - Malformed JSON-LD (the bug pattern PR #111 fixed, except where
#     the broken file fails the build entirely; this catches the more
#     subtle case where a render produces invalid JSON that still
#     parses through Liquid).

REQUIRED_META = %w[og:title og:description og:url og:image og:site_name og:type]

html_pages = Dir.glob("#{SITE}/**/*.html")
puts "Found #{html_pages.size} HTML page(s) under #{SITE}/"

html_pages.each do |path|
  rel = path.sub(%r{^#{SITE}/?}, "/")
  html = File.read(path)

  # Title
  err(errors, "#{rel}: missing <title>") unless html.match?(/<title>[^<]+<\/title>/)

  # Per-page meta — use a forgiving regex (jekyll-seo-tag emits in
  # property=… content=… order; some other tools use the reverse)
  REQUIRED_META.each do |prop|
    has = html.match?(/<meta\s+property=["']#{Regexp.escape(prop)}["']\s+content=["'][^"']+["']/) ||
          html.match?(/<meta\s+content=["'][^"']+["']\s+property=["']#{Regexp.escape(prop)}["']/)
    err(errors, "#{rel}: missing <meta property=\"#{prop}\">") unless has
  end

  # Canonical link
  has_canonical = html.match?(/<link[^>]+rel=["']canonical["'][^>]+href=["']\S+["']/) ||
                  html.match?(/<link[^>]+href=["']\S+["'][^>]+rel=["']canonical["']/)
  err(errors, "#{rel}: missing <link rel=\"canonical\">") unless has_canonical

  # Twitter Card
  err(errors, "#{rel}: missing twitter:card") unless html.match?(/<meta\s+(?:name|property)=["']twitter:card["']/)

  # JSON-LD blocks must all parse as JSON
  blocks = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m).map { |m| m[0] }
  blocks.each_with_index do |b, i|
    begin
      JSON.parse(b)
    rescue JSON::ParserError => e
      err(errors, "#{rel}: JSON-LD block #{i} is not valid JSON — #{e.message[0, 80]}")
    end
  end
end

# ─────────────────────────────────────────────────────────────────────
# 2. Blog posts have exactly one BlogPosting JSON-LD block
# ─────────────────────────────────────────────────────────────────────
# Catches: PR #112's fix regressing — i.e. someone re-introducing the
# manual BlogPosting block in `_layouts/post.html` without realising
# jekyll-seo-tag also emits one.

post_pages = Dir.glob("#{SITE}/blog/**/*.html").reject { |p| p.end_with?("/blog/index.html") || p.end_with?("blog.html") }
puts "Found #{post_pages.size} blog post page(s)"

post_pages.each do |path|
  rel = path.sub(%r{^#{SITE}/?}, "/")
  html = File.read(path)
  parsed = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m)
                .map { |m| JSON.parse(m[0]) rescue nil }
                .compact
  blogpostings = parsed.select { |b| b["@type"] == "BlogPosting" }
  err(errors, "#{rel}: expected exactly 1 BlogPosting JSON-LD block, found #{blogpostings.size}") unless blogpostings.size == 1
  next if blogpostings.empty?
  bp = blogpostings.first
  # Required for Article rich result. PR #116 set a site-wide default
  # `image` so this is always populated; if it ever shows up missing,
  # the URL likely got silently dropped by jekyll-seo-tag's image_drop
  # (PR #115's bug pattern).
  err(errors, "#{rel}: BlogPosting missing 'image' field — likely jekyll-seo-tag dropped the URL silently") unless bp["image"]
  err(errors, "#{rel}: BlogPosting missing 'url' field") unless bp["url"]
  err(errors, "#{rel}: BlogPosting missing 'headline' field") unless bp["headline"]
  err(errors, "#{rel}: BlogPosting missing 'datePublished' field") unless bp["datePublished"]
  err(errors, "#{rel}: BlogPosting missing 'publisher.logo'") unless bp.dig("publisher", "logo")
end

# ─────────────────────────────────────────────────────────────────────
# 3. Special events: every Event JSON-LD has required fields
# ─────────────────────────────────────────────────────────────────────
# Catches: regression in `_includes/special_event_card.html` that
# would silently produce Events missing fields Google's rich result
# requires.

REQUIRED_EVENT_FIELDS = %w[name startDate location eventStatus organizer]

events_pages = ["#{SITE}/special/index.html", "#{SITE}/calendar/index.html"]
events_pages.each do |path|
  next unless File.exist?(path)
  rel = path.sub(%r{^#{SITE}/?}, "/")
  html = File.read(path)
  blocks = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m).map { |m| JSON.parse(m[0]) rescue nil }
  events = blocks.compact.select { |b| b["@type"] == "Event" }
  err(errors, "#{rel}: expected at least 1 Event JSON-LD block, found 0") if events.empty?
  events.each_with_index do |ev, i|
    REQUIRED_EVENT_FIELDS.each do |f|
      err(errors, "#{rel}: Event[#{i}] (#{(ev["name"] || "?")[0, 40]}) missing required field '#{f}'") unless ev[f]
    end
    # Organizer should be Organization with logo (PR #109's fix)
    if ev["organizer"]
      err(errors, "#{rel}: Event[#{i}] organizer.@type should be Organization") unless ev.dig("organizer", "@type") == "Organization"
      warn_(warnings, "#{rel}: Event[#{i}] organizer missing logo (was added in PR #109)") unless ev.dig("organizer", "logo")
    end
    # eventStatus + eventAttendanceMode are recommended by Google
    warn_(warnings, "#{rel}: Event[#{i}] missing eventAttendanceMode") unless ev["eventAttendanceMode"]
  end
end

# ─────────────────────────────────────────────────────────────────────
# 4. Venues: every LocalBusiness has PostalAddress with addressCountry=PT
# ─────────────────────────────────────────────────────────────────────
# Catches: regression in `_includes/postal_address.html` that would
# silently degrade venue address structure.

venue_path = "#{SITE}/venues/index.html"
if File.exist?(venue_path)
  html = File.read(venue_path)
  blocks = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m).map { |m| JSON.parse(m[0]) rescue nil }
  venues = blocks.compact.select do |b|
    %w[LocalBusiness BarOrPub Restaurant PerformingArtsTheater MovieTheater Store StadiumOrArena GovernmentBuilding].include?(b["@type"])
  end
  err(errors, "/venues/: expected at least 1 LocalBusiness-typed JSON-LD block, found 0") if venues.empty?
  venues.each_with_index do |v, i|
    err(errors, "/venues/: venue[#{i}] (#{(v["name"] || "?")[0, 40]}) missing name") unless v["name"]
    addr = v["address"]
    err(errors, "/venues/: venue[#{i}] missing address") unless addr
    if addr
      err(errors, "/venues/: venue[#{i}] address.@type must be PostalAddress, got #{addr["@type"].inspect}") unless addr["@type"] == "PostalAddress"
      err(errors, "/venues/: venue[#{i}] addressCountry must be 'PT', got #{addr["addressCountry"].inspect}") unless addr["addressCountry"] == "PT"
    end
  end
end

# ─────────────────────────────────────────────────────────────────────
# 5. Event sort order on /special/ /calendar/ /archive/
# ─────────────────────────────────────────────────────────────────────
# Catches: regression of the very first PR in this lineage — events
# rendered in YAML order rather than date order. /special/ and
# /calendar/ should be ascending (soonest first); /archive/ should be
# descending (most recent past first).

def event_dates(html)
  html.scan(/data-event-date="([^"]+)"/).map { |m| m[0] }
end

[
  ["#{SITE}/special/index.html",  :asc],
  ["#{SITE}/calendar/index.html", :asc],
  ["#{SITE}/archive/index.html",  :desc],
].each do |path, direction|
  next unless File.exist?(path)
  rel = path.sub(%r{^#{SITE}/?}, "/")
  dates = event_dates(File.read(path))
  next if dates.size < 2
  expected = direction == :asc ? dates.sort : dates.sort.reverse
  unless dates == expected
    # Find the first divergence to make the error specific
    first_bad = dates.zip(expected).each_with_index.find { |(a, e), _| a != e }
    err(errors, "#{rel}: events not sorted #{direction} by date — at index #{first_bad[1]}, got #{first_bad[0][0]}, expected #{first_bad[0][1]}")
  end
end

# ─────────────────────────────────────────────────────────────────────
# 6. Sitemap contains the canonical pages
# ─────────────────────────────────────────────────────────────────────
sitemap_path = "#{SITE}/sitemap.xml"
if File.exist?(sitemap_path)
  sm = File.read(sitemap_path)
  %w[/ /weekly/ /special/ /calendar/ /venues/ /blog/ /archive/].each do |path|
    full = "https://eventosterceira.pt#{path}"
    err(errors, "sitemap.xml does not list #{full}") unless sm.include?("<loc>#{full}</loc>")
  end
else
  err(errors, "sitemap.xml is missing — jekyll-sitemap plugin not running?")
end

# ─────────────────────────────────────────────────────────────────────
# 6. robots.txt has Sitemap pointer
# ─────────────────────────────────────────────────────────────────────
robots_path = "#{SITE}/robots.txt"
if File.exist?(robots_path)
  rb = File.read(robots_path)
  err(errors, "robots.txt missing 'Sitemap:' directive") unless rb.include?("Sitemap:")
  err(errors, "robots.txt missing 'Allow: /' directive") unless rb.include?("Allow: /")
else
  err(errors, "robots.txt missing")
end

# ─────────────────────────────────────────────────────────────────────
# 7. Asset references resolve to real files
# ─────────────────────────────────────────────────────────────────────
# Catches: typos in `image:` config or `<img src=...>` paths that
# build cleanly (Jekyll just outputs the string) but produce 404s in
# the browser. Walks every HTML and CSS file under _site/ for
# `/assets/...` URLs and checks the file exists.

# Common URL-encoded chars we need to undo before checking the FS
def url_decode(s)
  s.gsub(/%([0-9A-Fa-f]{2})/) { [$1.hex].pack("C*").force_encoding("UTF-8") }
end

asset_refs = {} # path -> [referencing files]
text_files = Dir.glob("#{SITE}/**/*.html") + Dir.glob("#{SITE}/**/*.css")
text_files.each do |path|
  body = File.read(path)
  body.scan(%r{["'(\s](/assets/[^"'\s)?#]+)}).each do |match|
    asset = match[0]
    asset_refs[asset] ||= []
    asset_refs[asset] << path.sub(%r{^#{SITE}/?}, "/")
  end
end

asset_refs.each do |asset, referrers|
  decoded = url_decode(asset)
  fs_path = File.join(SITE, decoded.sub(%r{^/}, ""))
  unless File.exist?(fs_path)
    # Only show the first 2 referrers to keep error noise down
    refs_summary = referrers.first(2).join(", ")
    refs_summary += " (+#{referrers.size - 2} more)" if referrers.size > 2
    err(errors, "asset #{asset} referenced by #{refs_summary} does not exist")
  end
end

# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────
puts ""
if warnings.any?
  puts "WARNINGS (#{warnings.size}):"
  warnings.first(20).each { |w| puts "  • #{w}" }
  puts "  … (and #{warnings.size - 20} more)" if warnings.size > 20
  puts ""
end

if errors.any?
  puts "FAIL: #{errors.size} error(s):"
  errors.first(50).each { |e| puts "  ✗ #{e}" }
  puts "  … (and #{errors.size - 50} more)" if errors.size > 50
  exit 1
end

puts "OK — built site invariants hold (#{html_pages.size} pages checked)"
