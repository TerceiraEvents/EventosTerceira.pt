#!/usr/bin/env ruby
# Walks `_site/` after `jekyll build` and asserts the invariants the
# rest of the site depends on for SEO, structured data, and link
# previews. Designed to be run from the repo root in CI.
#
# Each assertion is one of the bugs we already shipped a fix for —
# these tests pin those fixes so a regression fails CI loudly instead
# of silently downgrading search/share quality on production.

require "json"
require "yaml"
require "date"
require "rexml/document"

SITE = ENV.fetch("SITE", "_site")
abort "missing #{SITE}/ — run `bundle exec jekyll build` first" unless Dir.exist?(SITE)

errors = []
warnings = []

def err(errors, msg); errors << msg; end
def warn_(warnings, msg); warnings << msg; end

if Dir.exist?(File.join(SITE, "scripts/tests/fixtures"))
  err(errors, "test fixtures must not be published in the built site")
end

# Pin the visitor-facing component behavior when the canonical fixture is
# classified as an exhibition in the data used for this build.
target_css = File.read(File.join(SITE, 'assets/css/style.css'))
nav_rule = target_css.match(/\.site-nav\s*\{([^}]+)\}/m)
err(errors, 'navbar requires its original horizontal scroll layout') unless nav_rule && nav_rule[1].match?(/overflow-x:\s*auto/)
err(errors, 'navbar row must not wrap into multiple rows') if target_css.match?(/\.site-nav \.container\s*\{[^}]*flex-wrap:\s*wrap/m)
%w[locale-other view-all standalone-link detail-link].each do |name|
  rule_body = target_css.scan(/\.#{name}\s*\{([^}]+)\}/m).last&.first
  valid = rule_body && %w[height width].all? { |axis| rule_body.match?(/min-#{axis}:\s*44px/) } && rule_body.match?(/display:\s*inline-flex/)
  err(errors, "standalone .#{name} requires 44px width and height in normal flow") unless valid
end
home_target_html = File.read(File.join(SITE, 'index.html'))
['index.html', 'pt/index.html'].each do |route|
  home_html = File.read(File.join(SITE, route))
  weekly_heading = route.start_with?('pt/') ? 'Eventos semanais' : 'Weekly events'
  err(errors, "#{route}: plain Weekly events homepage heading is absent") unless home_html.include?('<h2>' + weekly_heading + '</h2>')
  err(errors, "#{route}: homepage app CTA is absent") unless home_html.include?('id="get-the-app"') && home_html.include?('apps.apple.com') && home_html.include?('play.google.com')
end
err(errors, 'homepage standalone navigation requires target classes') unless home_target_html.scan('class="standalone-link"').length >= 4
detail_source = File.read(File.join(SITE, 'assets/js/event-details.js'))
err(errors, 'browser-saving bundle must not be published') if File.exist?(File.join(SITE, 'assets/js/plans.js'))
%w[assets/js/event-details.js assets/js/discovery.js].each do |asset|
  err(errors, "#{asset}: event browsing must not access browser storage or notifications") if File.read(File.join(SITE, asset)).match?(/localStorage|sessionStorage|Notification|serviceWorker/)
end
err(errors, 'detail back/explore links require standalone targets') unless detail_source.include?("a.className='detail-link'") && detail_source.include?("back.className='detail-link'")

special_path = "#{SITE}/special/index.html"
if File.exist?(special_path)
  special_html = File.read(special_path)
  err(errors, "/special/: missing Next 7 days range label") unless special_html.include?("Next 7 days</option>")
  events = YAML.safe_load(File.read('_data/special_events.yml'), permitted_classes: [Date, Time])
  localities = events.map { |event| event['locality'] }.compact.uniq
  err(errors, "/special/: locality control availability does not match curated metadata") unless special_html.include?('class="event-locality-filter"') == localities.any?
  %w[angra praia other].each do |locality|
    err(errors, "/special/: #{locality} option availability does not match curated metadata") unless special_html.include?(%(<option value="#{locality}">)) == localities.include?(locality)
  end
  title_target = special_html.match?(%r{<article[^>]*class="[^"]*event-summary[^"]*"[\s\S]*?<h3 class="event-name"><a href=})
  err(errors, '/special/: summary title anchor selector is absent') unless title_target
  css = File.read(File.join(SITE, 'assets/css/style.css'))
  title_rule = css.match(/\.event-summary \.event-name a\s*\{([^}]+)\}/m)
  title_height = title_rule && title_rule[1].match(/min-height:\s*(\d+)px/)
  err(errors, '/special/: primary title link requires a 44px normal-flow target') unless title_height && title_height[1].to_i >= 44 && title_rule[1].match?(/display:\s*(?:block|flex)/)
  exhibition_marker = 'data-event-kind="exhibition"'
  if special_html.include?(exhibition_marker) && special_html.include?("Milestones of Autonomy: from the Administrative Board to the First Regional Government")
    en_start = special_html.index(exhibition_marker)
    en_end = special_html.index('<script type="application/ld+json">', en_start)
    card = special_html[en_start...en_end]
    err(errors, "/special/: Marcos exhibition missing its English status") unless card.include?("Exhibition until 31 December")
    err(errors, "/special/: Marcos exhibition renders an attendance time") if card.include?('class="event-attendance"')
    jsonld_end = special_html.index("</script>", en_end)
    jsonld = special_html[en_end...jsonld_end]
    err(errors, "/special/: Marcos exhibition JSON-LD includes a time of day") if jsonld.match?(/"(?:startDate|endDate)":\s*"\d{4}-\d{2}-\d{2}T/)
  end
end

pt_special_path = "#{SITE}/pt/special/index.html"
if File.exist?(pt_special_path)
  pt_html = File.read(pt_special_path)
  if pt_html.include?('data-event-kind="exhibition"') && pt_html.include?("Milestones of Autonomy: from the Administrative Board to the First Regional Government")
    start = pt_html.index('data-event-kind="exhibition"')
    finish = pt_html.index('<script type="application/ld+json">', start)
    err(errors, "/pt/special/: Marcos exhibition missing its Portuguese status") unless pt_html[start...finish].include?("Exposição até 31 de dezembro")
  end
end

archive_path = "#{SITE}/archive/index.html"
if File.exist?(archive_path)
  archive_html = File.read(archive_path)
  err(errors, '/archive/: literal Events back link is absent') unless archive_html.include?('Back to Events</a>')
  err(errors, "/archive/: missing the English multi-day festival label") unless archive_html.include?("6–10 June · 5-day festival")
end

pt_archive_path = "#{SITE}/pt/archive/index.html"
if File.exist?(pt_archive_path)
  pt_archive_html = File.read(pt_archive_path)
  err(errors, '/pt/archive/: literal Eventos back link is absent') unless pt_archive_html.include?('Voltar a Eventos</a>')
  err(errors, "/pt/archive/: missing the Portuguese multi-day festival label") unless pt_archive_html.include?("6–10 de junho · festival de 5 dias")
end

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
  if ['/saved/index.html', '/pt/saved/index.html'].include?(rel)
    target = rel.start_with?('/pt/') ? '/pt/special/' : '/special/'
    err(errors, "#{rel}: bookmarked route must point to Events without a saving query") unless html.include?("content=\"0; url=#{target}\"") && !html.include?('saved=')
  end
  err(errors, "#{rel}: browser-saving UI or activation is present") if html.match?(/data-save-id|save-event|event-saved-filter|saved-unavailable|plans\.js|terceira-plans-v1/)
  if ['/index.html', '/pt/index.html'].include?(rel)
    labels = rel.start_with?('/pt/') ? ['Eventos', 'Obter a aplicação'] : ['Events', 'Get the app']
    labels.each { |label| err(errors, "#{rel}: homepage discovery/app label #{label} is absent") unless html.match?(/<a[^>]*>#{Regexp.escape(label)}<\/a>/) }
    exhibitions = rel.start_with?('/pt/') ? 'Exposições' : 'Exhibitions'
    err(errors, "#{rel}: homepage Exhibitions section is absent") unless html.include?('<h2>' + exhibitions + '</h2>')

  end
  navigation = html[/<nav class="site-nav"[^>]*>[\s\S]*?<\/nav>/]
  if navigation
    err(errors, "#{rel}: bookmark destination is absent from primary navigation") if navigation.match?(/<a (?!class="locale-other")[^>]*href="[^"]*\/saved\/"/)
    err(errors, "#{rel}: primary destinations must be visible without opening a menu") if navigation.match?(/<details|\bhidden\b|aria-hidden="true"/)
    prefix = rel.start_with?('/pt/') ? '/pt' : ''
    routes = ['/', '/weekly/', '/special/', '/venues/', '/blog/', '/contribute/', '/resources/']
    labels = prefix.empty? ? ['Home', 'Weekly', 'Events', 'Places', 'Blog', 'Contribute', 'Resources'] : ['Início', 'Semanal', 'Eventos', 'Locais', 'Blogue', 'Contribuir', 'Recursos']
    expected = routes.zip(labels).map { |route, label| [prefix + route, label] }
    err(errors, "#{rel}: original seven primary routes/order with plain Events/Places labels are required") unless navigation.scan(/<a href="([^"]*)">([^<]*)<\/a>/) == expected
    err(errors, "#{rel}: locale switcher is absent") unless navigation.include?('class="locale-other"')
  end
  footer = html[/<footer\b[^>]*>[\s\S]*?<\/footer>/]
  if footer
    prefix = rel.start_with?('/pt/') ? '/pt' : ''
    secondary = rel.start_with?('/pt/') ? [['/contribute/', 'Contribuir'], ['/#get-the-app', 'Obter a aplicação']] : [['/contribute/', 'Contribute'], ['/#get-the-app', 'Get the app']]
    secondary.each do |route, label|
      err(errors, "#{rel}: footer secondary link #{label} needs its destination and 44px target") unless footer.match?(/<a class="standalone-link" href="#{Regexp.escape(prefix + route)}">#{Regexp.escape(label)}<\/a>/)
    end
    privacy = footer[/<a\b[^>]*href="[^"]*\/privacy\/?"[^>]*>/]
    err(errors, "#{rel}: footer Privacy requires a standalone 44px target") unless privacy && privacy.match?(/class="[^"]*\bstandalone-link\b/)
  end

  if %w[/index.html /pt/index.html].include?(rel)
    main_end = html.index('</main>')
    banner = html.index('id="app-banner"')
    err(errors, "#{rel}: mobile app promotion must follow main content") unless main_end && banner && banner > main_end
  end

  %w[assets/js/discovery.js assets/js/event-details.js assets/css/style.css].each do |asset|
    err(errors, "#{rel}: unversioned first-party asset #{asset}") unless html.match?(%r{#{Regexp.escape(asset)}\?v=\d+})
  end

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

VENUE_SCHEMA_TYPES = %w[
  LocalBusiness BarOrPub NightClub Restaurant PerformingArtsTheater MovieTheater
  Store StadiumOrArena GovernmentBuilding Museum ArtGallery
  CommunityCenter ExerciseGym Campground Library
].freeze

venue_path = "#{SITE}/venues/index.html"
if File.exist?(venue_path)
  html = File.read(venue_path)
  blocks = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m).map { |m| JSON.parse(m[0]) rescue nil }
  venues = blocks.compact.select { |b| VENUE_SCHEMA_TYPES.include?(b["@type"]) }
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
# 4b. Venues page: every venue card sits under a category section
# ─────────────────────────────────────────────────────────────────────
# Sections live in `venues.md` / `pt/venues.md` and are driven by the
# `category:` field on each entry in `_data/venues.yml`. Pin the EN
# and PT labels so a typo or untranslated label fails CI loudly, and
# cross-check that the YAML categories actually surface on the page.

require "yaml"
venues_data = YAML.load_file("_data/venues.yml", permitted_classes: [Date, Time], aliases: true) rescue YAML.load_file("_data/venues.yml")
yaml_categories = venues_data.map { |v| v["category"] }.compact.uniq

EXPECTED_VENUE_CATEGORY_LABELS = {
  "#{SITE}/venues/index.html" => {
    "arts-culture"   => "Arts &amp; Culture",
    "food-drink"     => "Food &amp; Drink",
    "nightlife"      => "Bars &amp; Nightlife",
    "sports-outdoor" => "Sports &amp; Outdoor",
    "civic"          => "Civic",
    "other"          => "Other",
  },
  "#{SITE}/pt/venues/index.html" => {
    "arts-culture"   => "Arte e Cultura",
    "food-drink"     => "Comida e Bebida",
    "nightlife"      => "Bares e Vida Noturna",
    "sports-outdoor" => "Desporto e Ar Livre",
    "civic"          => "Cívico",
    "other"          => "Outros",
  },
}.freeze

EXPECTED_VENUE_CATEGORY_LABELS.each do |path, labels|
  next unless File.exist?(path)
  rel = path.sub(%r{^#{SITE}/?}, "/")
  html = File.read(path)
  # Each <h3 class="venue-category"> should match a category we have venues for.
  rendered_sections = html.scan(/<h3 class="venue-category" id="category-([^"]+)">([^<]+)<\/h3>/)
  rendered_slugs = rendered_sections.map(&:first)
  yaml_categories.each do |slug|
    err(errors, "#{rel}: venues data has category '#{slug}' but no <h3> section renders for it") unless rendered_slugs.include?(slug)
  end
  rendered_sections.each do |slug, label|
    expected = labels[slug]
    if expected.nil?
      err(errors, "#{rel}: venues page rendered an unknown category '#{slug}' — add it to EXPECTED_VENUE_CATEGORY_LABELS or remove from data")
    elsif label.strip != expected
      err(errors, "#{rel}: category '#{slug}' label mismatch — got #{label.strip.inspect}, expected #{expected.inspect}")
    end
  end
  # No venue card should appear before the first category header (every
  # venue must live under a section, including Arts & Culture which is
  # always first).
  if (h3_idx = html.index('<h3 class="venue-category"'))
    pre = html[0...h3_idx]
    err(errors, "#{rel}: venue-card appears before the first <h3 class=\"venue-category\"> header") if pre.include?('class="venue-card"')
  else
    err(errors, "#{rel}: no <h3 class=\"venue-category\"> sections rendered at all")
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
