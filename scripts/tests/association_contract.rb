# Shared contract for the /.well-known/ platform association files.
# Used by test_associations.rb (source + built output) and
# test_live_site.rb (deployed endpoints) so both enforce the same
# single verified-publisher contract.

require "json"

module AssociationContract
  AASA_APP_ID = "9R3942X8JM.com.terceiraevents.app"
  ANDROID_PACKAGE = "com.terceiraevents.app"
  ANDROID_CERT = "FD:23:49:C0:4B:57:A5:D2:AF:BE:62:93:D7:92:72:14:29:C4:72:93:" \
                 "60:D5:1E:E5:14:74:D2:66:FF:6A:C4:3A"
  ANDROID_RELATION = "delegate_permission/common.handle_all_urls"

  # The exact public routes the native build declares for OS association.
  EXPECTED_PATHS = %w[
    /events /events/ /weekly /weekly/ /special /special/
    /pt/events /pt/events/ /pt/weekly /pt/weekly/ /pt/special /pt/special/
  ].freeze

  FORBIDDEN_PATHS = %w[
    /saved /pt/saved /venues /venues/ /pt/venues /pt/venues/
    /blog /pt/blog /contribute /pt/contribute /resources /pt/resources
    /calendar /pt/calendar /archive /pt/archive /suggest /pt/suggest
    / /pt /privacy /pt/privacy /events-other /pt/events-other
  ].freeze

  def self.parse_json(raw, label, errors)
    JSON.parse(raw)
  rescue JSON::ParserError => e
    errors << "#{label}: invalid JSON — #{e.message[0, 80]}"
    nil
  end

  def self.check_assetlinks_doc(doc, label, errors)
    errors << "#{label}: top level must be a JSON array" and return unless doc.is_a?(Array)
    unless doc.size == 1
      errors << "#{label}: must contain exactly one statement (found #{doc.size})"
    end
    doc.each_with_index do |entry, i|
      l = "#{label}[#{i}]"
      unless entry.is_a?(Hash)
        errors << "#{l}: statement must be an object"
        next
      end
      errors << "#{l}: relation must be exactly [\"#{ANDROID_RELATION}\"]" unless entry["relation"] == [ANDROID_RELATION]
      target = entry["target"]
      unless target.is_a?(Hash)
        errors << "#{l}: target must be an object"
        next
      end
      errors << "#{l}: namespace must be android_app" unless target["namespace"] == "android_app"
      errors << "#{l}: package_name must be #{ANDROID_PACKAGE}" unless target["package_name"] == ANDROID_PACKAGE
      unless target["sha256_cert_fingerprints"] == [ANDROID_CERT]
        errors << "#{l}: sha256_cert_fingerprints must be exactly the verified Play app-signing certificate"
      end
    end
  end

  def self.check_aasa_doc(doc, label, errors)
    errors << "#{label}: top level must be an object" and return unless doc.is_a?(Hash)
    extra = doc.keys - %w[applinks]
    errors << "#{label}: unexpected top-level service(s) #{extra.join(', ')}" unless extra.empty?

    applinks = doc["applinks"]
    errors << "#{label}: missing applinks object" and return unless applinks.is_a?(Hash)
    unless applinks["apps"] == []
      errors << "#{label}: applinks.apps must stay empty (details carry the appID)"
    end

    details = applinks["details"]
    errors << "#{label}: applinks.details must be an array" and return unless details.is_a?(Array)
    unless details.size == 1
      errors << "#{label}: exactly one app detail is allowed (found #{details.size})"
    end
    details.each_with_index do |detail, i|
      l = "#{label}.details[#{i}]"
      unless detail.is_a?(Hash)
        errors << "#{l}: detail must be an object"
        next
      end
      if detail.key?("appIDs") || detail.key?("components")
        errors << "#{l}: legacy appID/paths must not mix with appIDs/components"
      end
      errors << "#{l}: appID must be #{AASA_APP_ID}" unless detail["appID"] == AASA_APP_ID
      paths = detail["paths"]
      errors << "#{l}: paths must be an array" and next unless paths.is_a?(Array)
      errors << "#{l}: paths mismatch; got #{paths.sort.inspect}" unless paths.sort == EXPECTED_PATHS.sort
      paths.each do |p|
        errors << "#{l}: wildcard/non-literal path #{p} would associate unrelated routes" if p.match?(/[*?]|NOT /)
      end
      FORBIDDEN_PATHS.each do |forbidden|
        errors << "#{l}: must not associate #{forbidden}" if paths.include?(forbidden)
      end
    end
  end

  # Deployed-endpoint contract: direct 200 with no redirects, and the
  # exact document contract. AASA's served MIME is reported by the
  # caller, not asserted — Pages serves extensionless files as
  # application/octet-stream and OS acceptance is an Apple-CDN check.
  def self.check_association_response(code, content_type, body, label, require_json_mime, errors)
    errors << "#{label}: expected direct HTTP 200 with no redirects, got #{code}" and return unless code == "200"
    mime_type = content_type.to_s.split(";", 2).first.to_s.strip.downcase
    if require_json_mime && mime_type != "application/json"
      errors << "#{label}: Content-Type '#{content_type}' must be application/json"
    end
    doc = parse_json(body, label, errors)
    label.include?("assetlinks") ? check_assetlinks_doc(doc, label, errors) : check_aasa_doc(doc, label, errors)
  end
end
