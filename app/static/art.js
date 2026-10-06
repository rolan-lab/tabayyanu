// Decorative illustrations for the main learning paths and modules.
// Original line art drawn for Tabayyanu (no photos, no people or animals), in the site's gold.
// Purely decorative: aria-hidden, and animations stop under prefers-reduced-motion.

const ART = {
  // The Kaaba: a cube with the gold band (hizam) and the door, on a soft glow.
  kaaba: `
    <svg viewBox="0 0 120 120" class="art-svg art-kaaba">
      <ellipse class="art-glow" cx="60" cy="96" rx="44" ry="8"/>
      <path class="art-fill-dark" d="M28 44 L60 30 L92 44 L92 92 L60 104 L28 92 Z"/>
      <path class="art-line" d="M28 44 L60 58 L92 44 M60 58 L60 104"/>
      <path class="art-band" d="M28 52 L60 66 L92 52 L92 58 L60 72 L28 58 Z"/>
      <path class="art-line art-thin" d="M33 56 l6 2.6 M45 61 l6 2.6 M69 64 l6 -2.6 M81 59 l6 -2.6"/>
      <path class="art-door" d="M70 74 L80 70 L80 90 L70 94 Z"/>
    </svg>`,

  // A mihrab arch with a hanging lamp that sways.
  mihrab: `
    <svg viewBox="0 0 120 120" class="art-svg art-mihrab">
      <path class="art-line" d="M24 104 L24 54 Q24 22 60 14 Q96 22 96 54 L96 104"/>
      <path class="art-line art-thin" d="M34 104 L34 56 Q34 32 60 25 Q86 32 86 56 L86 104"/>
      <path class="art-line" d="M16 104 L104 104"/>
      <g class="art-sway">
        <path class="art-line art-thin" d="M60 25 L60 46"/>
        <path class="art-band" d="M52 46 L68 46 L65 60 Q60 66 55 60 Z"/>
        <circle class="art-glow" cx="60" cy="56" r="10"/>
      </g>
    </svg>`,

  // Water drops falling into a basin (wudu).
  water: `
    <svg viewBox="0 0 120 120" class="art-svg art-water">
      <path class="art-drop art-d1" d="M44 20 Q52 34 52 40 a8 8 0 0 1 -16 0 Q36 34 44 20 Z"/>
      <path class="art-drop art-d2" d="M66 30 Q74 44 74 50 a8 8 0 0 1 -16 0 Q58 44 66 30 Z"/>
      <path class="art-drop art-d3" d="M82 16 Q88 27 88 32 a6 6 0 0 1 -12 0 Q76 27 82 16 Z"/>
      <path class="art-line" d="M22 82 Q60 100 98 82"/>
      <path class="art-line art-thin art-ripple" d="M38 86 Q60 94 82 86"/>
      <ellipse class="art-glow" cx="60" cy="90" rx="36" ry="6"/>
    </svg>`,

  // A dome with a crescent finial and a minaret (Madinah), floating gently.
  dome: `
    <svg viewBox="0 0 120 120" class="art-svg art-dome">
      <g class="art-float">
        <path class="art-fill-green" d="M34 74 Q34 44 60 38 Q86 44 86 74 Z"/>
        <path class="art-line" d="M34 74 Q34 44 60 38 Q86 44 86 74"/>
        <path class="art-line art-thin" d="M60 38 L60 28"/>
        <path class="art-band" d="M60 20 a5 5 0 1 0 4 8 a4 4 0 1 1 -4 -8 Z"/>
        <path class="art-line" d="M26 74 L94 74 L94 102 L26 102 Z"/>
        <path class="art-line art-thin" d="M50 102 L50 86 Q60 78 70 86 L70 102"/>
        <path class="art-line" d="M100 102 L100 46 L106 46 L106 102 M98 46 L103 34 L108 46"/>
      </g>
    </svg>`,

  // An eight-pointed Islamic star (two overlapping squares) that turns slowly.
  star: `
    <svg viewBox="0 0 120 120" class="art-svg art-star">
      <circle class="art-glow" cx="60" cy="60" r="34"/>
      <g class="art-spin">
        <rect class="art-line" x="34" y="34" width="52" height="52"/>
        <rect class="art-line" x="34" y="34" width="52" height="52" transform="rotate(45 60 60)"/>
        <circle class="art-band" cx="60" cy="60" r="9"/>
      </g>
    </svg>`,

  // An open book with a crescent above it.
  book: `
    <svg viewBox="0 0 120 120" class="art-svg art-book">
      <g class="art-float">
        <path class="art-band" d="M60 14 a10 10 0 1 0 8 16 a8 8 0 1 1 -8 -16 Z"/>
        <path class="art-line" d="M60 50 Q42 40 18 44 L18 92 Q42 88 60 98 Q78 88 102 92 L102 44 Q78 40 60 50 Z"/>
        <path class="art-line art-thin" d="M60 50 L60 98"/>
        <path class="art-line art-thin" d="M28 58 Q42 55 52 60 M28 68 Q42 65 52 70 M28 78 Q42 75 52 80
                                         M68 60 Q78 55 92 58 M68 70 Q78 65 92 68 M68 80 Q78 75 92 78"/>
      </g>
    </svg>`,
};

function artNode(key, size = "md") {
  const svg = ART[key];
  if (!svg) return null;
  const wrap = document.createElement("div");
  wrap.className = `art art-${size}`;
  wrap.setAttribute("aria-hidden", "true");
  wrap.innerHTML = svg;  // static markup defined above, never user content
  return wrap;
}
