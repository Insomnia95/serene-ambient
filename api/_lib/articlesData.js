// Shared helper — small, surgical text edits to articles-data.js.
// Deliberately does NOT parse/re-serialize the whole file (that would risk
// reformatting or losing exact formatting the daily bot and hand edits rely
// on). Instead it does line-based insert/patch, the same convention the
// daily content-engine's own prompt already uses ("add new entries at TOP
// of ARTICLES array").

const ID_RE = /id:'([^']*)'/;
const PIN_FIELD_RE = /,\s*pinnedUntil:'[^']*'/;
const SPONSORED_FIELD_RE = /,\s*sponsored:(true|false)/;

// Insert a new entry line right after "const ARTICLES = [".
export function insertArticleEntry(content, entryLine) {
  const marker = 'const ARTICLES = [';
  const idx = content.indexOf(marker);
  if (idx === -1) throw new Error('Could not find "const ARTICLES = [" in articles-data.js');
  const insertAt = idx + marker.length;
  return content.slice(0, insertAt) + '\n  ' + entryLine + content.slice(insertAt);
}

// Sets pinnedUntil ('YYYY-MM-DD' or null to clear) and/or sponsored (bool) on
// the entry whose id matches targetId. Any OTHER entry currently pinned gets
// its pinnedUntil stripped, so only one article is ever pinned at a time.
// Returns { content, found }.
export function setArticleFlags(content, targetId, { pinnedUntil, sponsored } = {}) {
  const lines = content.split('\n');
  let found = false;
  const newLines = lines.map((line) => {
    const m = line.match(ID_RE);
    if (!m) return line;
    const lineId = m[1];
    let newLine = line;

    if (lineId === targetId) {
      found = true;
      if (pinnedUntil !== undefined) {
        newLine = newLine.replace(PIN_FIELD_RE, '');
        if (pinnedUntil) {
          newLine = newLine.replace(/ \}(,)?\s*$/, ` , pinnedUntil:'${pinnedUntil}' }$1`);
        }
      }
      if (sponsored !== undefined) {
        newLine = newLine.replace(SPONSORED_FIELD_RE, '');
        if (sponsored) {
          newLine = newLine.replace(/ \}(,)?\s*$/, ` , sponsored:true }$1`);
        }
      }
    } else if (pinnedUntil) {
      // Enforce a single active pin: clear any other entry's pin.
      newLine = newLine.replace(PIN_FIELD_RE, '');
    }
    return newLine;
  });
  return { content: newLines.join('\n'), found };
}
