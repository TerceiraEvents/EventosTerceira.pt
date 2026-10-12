import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/** Return the WCAG relative-luminance contrast ratio for two six-digit sRGB colors. */
export function contrast(foreground, background) {
  const luminance = (hex) => {
    const channels = hex.slice(1).match(/../g).map((value) => parseInt(value, 16) / 255).map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  };
  const values = [luminance(foreground), luminance(background)].sort((a, b) => a - b);
  return (values[1] + 0.05) / (values[0] + 0.05);
}

/** Validate documented color values against source and the declared text contrast pairs. */
export function checkTokens(manifest, css, nativeTheme) {
  const source = { website: Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[\da-fA-F]{6})/g)].map((match) => [match[1], match[2]])) };
  if (nativeTheme !== undefined) source.native = Object.fromEntries([...nativeTheme.matchAll(/(\w+): '(#[\da-fA-F]{6})'/g)].map((match) => [match[1], match[2]]));
  for (const [platform, tokens] of Object.entries(source)) {
    assert.deepEqual(tokens, manifest[platform], `${platform} color inventory differs from its source`);
  }
  return manifest.contrast_pairs.map((pair) => {
    const ratio = contrast(manifest[pair.platform][pair.foreground], manifest[pair.platform][pair.background]);
    assert.ok(ratio >= pair.minimum, `${pair.platform} ${pair.foreground}/${pair.background}: ${ratio.toFixed(2)} is below ${pair.minimum}`);
    return { ...pair, ratio: Number(ratio.toFixed(2)) };
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const manifest = JSON.parse(readFileSync(new URL('../docs/discovery-tokens.json', import.meta.url), 'utf8'));
  const css = readFileSync(new URL('../assets/css/style.css', import.meta.url), 'utf8');
  const native = process.argv[2] ? readFileSync(process.argv[2], 'utf8') : undefined;
  console.log(JSON.stringify({ native_source_checked: native !== undefined, pairs: checkTokens(manifest, css, native) }, null, 2));
}
