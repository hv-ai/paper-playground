"""All of the app's look lives here: static CSS and static HTML written by us.
Nothing in this file ever contains text from a paper or from the model."""

CSS = """
<style>
.pp-hero{display:flex;align-items:center;gap:18px;margin:6px 0 4px 0;}
.pp-mascot{width:92px;height:92px;flex:none;filter:drop-shadow(0 6px 10px rgba(124,92,255,.25));}
.pp-title{font-size:2.5rem;font-weight:800;line-height:1.05;
  background:linear-gradient(90deg,#7c5cff,#ff6b9d 60%,#ffb347);-webkit-background-clip:text;
  background-clip:text;color:transparent;}
.pp-tag{color:#5b5486;font-size:1.02rem;margin-top:4px;}
.pp-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0 8px 0;}
.pp-step{background:#fff;border:1px solid #e3d9ff;border-radius:16px;padding:14px 16px;}
.pp-step b{display:block;margin-bottom:2px;}
.pp-step span.n{display:inline-flex;width:26px;height:26px;border-radius:50%;align-items:center;
  justify-content:center;color:#fff;font-weight:700;margin-right:8px;background:#7c5cff;}
.pp-step.s2 span.n{background:#ff6b9d;} .pp-step.s3 span.n{background:#ffb347;}
.pp-sec{font-size:1.35rem;font-weight:800;margin:26px 0 10px 0;padding:8px 14px;border-radius:14px;
  display:inline-block;}
.pp-sec.a{background:#e9e2ff;} .pp-sec.b{background:#ffe3ee;} .pp-sec.c{background:#fff0d6;}
.pp-sub{font-size:1.08rem;font-weight:800;margin:18px 0 4px 0;color:#4a3aa8;}
.pp-note{color:#7a739f;font-size:.85rem;margin:-2px 0 6px 0;}
.pp-beyond{border:2px dashed #c9bdf5;border-radius:16px;padding:6px 16px 10px 16px;margin-top:14px;background:#faf7ff;}
.pp-chip{display:inline-block;padding:2px 11px;border-radius:999px;background:#efe9ff;color:#4a3aa8;
  font-size:.8rem;font-weight:600;margin-right:6px;}
.pp-badge{display:inline-block;padding:2px 10px;border-radius:999px;background:#e3f6ea;color:#17603a;
  font-size:.8rem;font-weight:700;}
.pp-badge.warn{background:#fff1da;color:#8a5200;}
.pp-num{display:inline-flex;width:30px;height:30px;border-radius:50%;align-items:center;
  justify-content:center;color:#fff;font-weight:800;}
.pp-num.c0{background:#7c5cff;} .pp-num.c1{background:#ff6b9d;}
.pp-num.c2{background:#ffb347;} .pp-num.c3{background:#2bb6a3;}
.pp-dot{font-size:1.25rem;font-weight:800;}
.pp-dot.c0{color:#7c5cff;} .pp-dot.c1{color:#ff6b9d;} .pp-dot.c2{color:#e69a22;} .pp-dot.c3{color:#2bb6a3;}
@media (max-width:640px){.pp-steps{grid-template-columns:1fr;}.pp-title{font-size:1.9rem;}}
</style>
"""

# An original mascot: a friendly round face with big glasses. Static SVG, drawn by us.
MASCOT = """
<svg class="pp-mascot" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Paper Playground mascot">
  <circle cx="60" cy="63" r="44" fill="#ffd166" stroke="#2b2350" stroke-width="3.5"/>
  <path d="M30 40 Q60 6 90 40" fill="#7c5cff" stroke="#2b2350" stroke-width="3.5" stroke-linejoin="round"/>
  <circle cx="42" cy="58" r="15" fill="#ffffff" stroke="#2b2350" stroke-width="4.5"/>
  <circle cx="78" cy="58" r="15" fill="#ffffff" stroke="#2b2350" stroke-width="4.5"/>
  <line x1="57" y1="58" x2="63" y2="58" stroke="#2b2350" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="27" y1="56" x2="19" y2="52" stroke="#2b2350" stroke-width="4" stroke-linecap="round"/>
  <line x1="93" y1="56" x2="101" y2="52" stroke="#2b2350" stroke-width="4" stroke-linecap="round"/>
  <circle cx="44" cy="60" r="5" fill="#2b2350"/><circle cx="80" cy="60" r="5" fill="#2b2350"/>
  <circle cx="46" cy="58" r="1.6" fill="#fff"/><circle cx="82" cy="58" r="1.6" fill="#fff"/>
  <path d="M44 84 Q60 99 76 84" fill="none" stroke="#2b2350" stroke-width="4" stroke-linecap="round"/>
  <circle cx="29" cy="78" r="6" fill="#ff9aa2" opacity=".6"/><circle cx="91" cy="78" r="6" fill="#ff9aa2" opacity=".6"/>
  <text x="96" y="24" font-size="16" fill="#ff6b9d">✦</text><text x="8" y="30" font-size="12" fill="#7c5cff">✦</text>
</svg>
"""

HERO = f"""
<div class="pp-hero">{MASCOT}
  <div><div class="pp-title">Paper Playground</div>
  <div class="pp-tag">Drop in a research paper. Get a lesson you can trust: every fact is checked against the paper.</div></div>
</div>
"""

STEPS = """
<div class="pp-steps">
  <div class="pp-step"><b><span class="n">1</span>Upload</b>A public research paper (PDF), from the sidebar.</div>
  <div class="pp-step s2"><b><span class="n">2</span>Choose your style</b>Pick your level, how long you want it, and the tone.</div>
  <div class="pp-step s3"><b><span class="n">3</span>Learn it</b>Get the story, the checked facts, and what to be careful about.</div>
</div>
"""


def section(letter: str, title: str) -> str:
    """letter is one of a, b, c; title is one of our own fixed headings."""
    assert letter in "abc" and title in {"📖 What this paper is", "🔎 Key facts", "💡 Key things to know"}
    return f'<div class="pp-sec {letter}">{title}</div>'


SUBHEADS = {"🌍 Why it matters and where it is used", "🧩 Example", "🔭 Beyond the paper"}
NOTES = {
    "🧩 Example": "Made up to help you understand the idea. It is not a result from the paper.",
    "🔭 Beyond the paper": "From the AI's general knowledge. Not checked against the paper, and may be out of date.",
}


def subhead(title: str) -> str:
    assert title in SUBHEADS
    return f'<div class="pp-sub">{title}</div>' + (f'<div class="pp-note">{NOTES[title]}</div>' if title in NOTES else "")
