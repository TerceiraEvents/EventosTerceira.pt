#!/usr/bin/env ruby
# Post-deploy smoke test against the LIVE production site. Different
# failure mode from `test_built_site.rb` (which runs against `_site/`
# pre-merge): this one runs after the GitHub Pages deploy completes
# and curl-fetches the actual deployed HTML.
#
# Why both: PRs #114 and #116 both passed pre-merge build checks AND
# the Pages deploy job AND were merged green — but production was
# wrong because jekyll-seo-tag silently dropped fields based on
# config syntax. The pre-merge build doesn't reproduce a Pages-built
# site exactly (different gem set, different image_drop logic). This
# script catches "the build succeeded but production isn't what we
# expected" — a real-world failure mode we hit three times.

require "net/http"
require "uri"
require "json"

BASE = ENV.fetch("BASE_URL", "https://terceiraevents.github.io")
puts "Smoke-testing live site at #{BASE}"

errors = []

def fetch(url, redirects = 3)
  uri = URI(url)
  res = Net::HTTP.get_response(uri)
  case res
  when Net::HTTPSuccess
    res.body
  when Net::HTTPRedirection
    redirects > 0 ? fetch(res["location"], redirects - 1) : nil
  else
    nil
  end
end

# Pages we care about + their expected JSON-LD shape
PAGES = [
  { path: "/",                                       expect_jsonld: ["WebSite"] },
  { path: "/special/",                               expect_jsonld: ["WebPage", "Event"] },
  { path: "/calendar/",                              expect_jsonld: ["WebPage", "Event"] },
  { path: "/venues/",                                expect_jsonld: ["WebPage", "LocalBusiness"] },
  { path: "/blog/",                                  expect_jsonld: ["WebPage"] },
  { path: "/blog/2026/twins-temporarily-closed/",    expect_jsonld: ["BlogPosting"] },
  { path: "/weekly/",                                expect_jsonld: ["WebPage"] },
  { path: "/archive/",                               expect_jsonld: ["WebPage", "Event"] },
]

REQUIRED_META = %w[og:title og:description og:url og:image og:site_name og:type]

PAGES.each do |spec|
  path = spec[:path]
  url = "#{BASE}#{path}"
  html = fetch(url)
  unless html
    errors << "#{path}: HTTP fetch failed"
    next
  end

  # Per-page meta tags
  err_count = 0
  REQUIRED_META.each do |prop|
    has = html.match?(/<meta\s+property=["']#{Regexp.escape(prop)}["']\s+content=["'][^"']+["']/) ||
          html.match?(/<meta\s+content=["'][^"']+["']\s+property=["']#{Regexp.escape(prop)}["']/)
    unless has
      errors << "#{path}: missing <meta property=\"#{prop}\">"
      err_count += 1
    end
  end

  has_canonical = html.match?(/<link[^>]+rel=["']canonical["']/) || html.match?(/<link[^>]+href=["'][^"']+["'][^>]+rel=["']canonical["']/)
  errors << "#{path}: missing <link rel=\"canonical\">" unless has_canonical

  # JSON-LD blocks
  blocks = html.scan(/<script\s+type=["']application\/ld\+json["']>(.*?)<\/script>/m).map { |m| m[0] }
  parsed = []
  blocks.each_with_index do |b, i|
    begin
      parsed << JSON.parse(b)
    rescue JSON::ParserError => e
      errors << "#{path}: JSON-LD block #{i} doesn't parse — #{e.message[0, 80]}"
    end
  end

  # Each expected @type should appear at least once
  found_types = parsed.map { |p| p["@type"] }
  spec[:expect_jsonld].each do |t|
    unless found_types.include?(t)
      errors << "#{path}: expected JSON-LD @type=#{t}, found types: #{found_types.uniq.join(', ')}"
    end
  end

  status = err_count == 0 ? "OK" : "FAIL(#{err_count})"
  puts "  #{status}  #{path}  (#{blocks.size} JSON-LD)"
end

# ─────────────────────────────────────────────────────────────────────
# Sitemap + robots.txt
# ─────────────────────────────────────────────────────────────────────
sm = fetch("#{BASE}/sitemap.xml")
errors << "/sitemap.xml: HTTP fetch failed" unless sm
if sm
  %w[/ /weekly/ /special/ /calendar/ /venues/ /blog/ /archive/].each do |p|
    full = "#{BASE}#{p}"
    errors << "/sitemap.xml does not list #{full}" unless sm.include?("<loc>#{full}</loc>")
  end
end

robots = fetch("#{BASE}/robots.txt")
errors << "/robots.txt: HTTP fetch failed" unless robots
if robots
  errors << "/robots.txt missing 'Sitemap:' directive" unless robots.include?("Sitemap:")
  errors << "/robots.txt missing 'Allow: /'" unless robots.include?("Allow: /")
end

# ─────────────────────────────────────────────────────────────────────
# Asset existence: og:image actually returns 200 (not 404)
# ─────────────────────────────────────────────────────────────────────
# Specifically catches the failure mode where jekyll-seo-tag emits an
# og:image tag with a stale path. Pages might cache a 404. Spot-check
# the homepage's og:image URL.

home = fetch("#{BASE}/")
if home && (m = home.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/))
  og_image_url = m[1]
  uri = URI(og_image_url)
  res = Net::HTTP.get_response(uri)
  unless res.is_a?(Net::HTTPSuccess)
    errors << "og:image URL #{og_image_url} returned HTTP #{res.code}"
  end
end

if errors.empty?
  puts "\nOK — live site invariants hold (#{PAGES.size} pages checked)"
  exit 0
end

puts "\nFAIL: #{errors.size} error(s):"
errors.first(40).each { |e| puts "  ✗ #{e}" }
puts "  … (and #{errors.size - 40} more)" if errors.size > 40
exit 1
