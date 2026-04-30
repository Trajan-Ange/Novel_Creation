/** Shared utility functions */

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Escape a value for use inside an inline onclick handler's single-quoted JS string.
 *  E.g. onclick="handler('${escapeOnclick(name)}')"
 *  Must be separate from escapeHtml because &#39; is decoded by the HTML parser before JS runs. */
function escapeOnclick(text) {
  if (!text) return '';
  return escapeHtml(text).replace(/'/g, "\\'");
}
