"""All of the app's look lives here: static CSS and static HTML written by us.
Nothing in this file ever contains text from a paper or from the model."""

CSS = """
<style>
.stApp{background:linear-gradient(180deg,#f2fbfa 0%,#eaf3ff 100%);}
.pp-hero{display:flex;align-items:center;gap:18px;margin:6px 0 4px 0;}
.pp-welcome{font-size:1.35rem;font-weight:700;margin:18px 0 2px 0;}
.pp-welcome-sub{opacity:.75;margin:0 0 6px 0;}
.pp-mascot{width:92px;height:92px;flex:none;filter:drop-shadow(0 6px 10px rgba(14,165,164,.25));}
.pp-title{font-size:2.5rem;font-weight:800;line-height:1.05;
  background:linear-gradient(90deg,#0ea5a4,#2563eb 60%,#f59e0b);-webkit-background-clip:text;
  background-clip:text;color:transparent;}
.pp-tag{color:#4a6a80;font-size:1.02rem;margin-top:4px;}
.pp-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0 8px 0;}
.pp-step{background:#fff;border:1px solid #bfe6e3;border-radius:16px;padding:14px 16px;}
.pp-step b{display:block;margin-bottom:2px;}
.pp-step span.n{display:inline-flex;width:26px;height:26px;border-radius:50%;align-items:center;
  justify-content:center;color:#fff;font-weight:700;margin-right:8px;background:#0ea5a4;}
.pp-step.s2 span.n{background:#2563eb;} .pp-step.s3 span.n{background:#f59e0b;}
.pp-sec{font-size:1.35rem;font-weight:800;margin:26px 0 10px 0;padding:8px 14px;border-radius:14px;
  display:inline-block;}
.pp-sec.a{background:#d5f3f0;} .pp-sec.b{background:#dbe7ff;} .pp-sec.c{background:#fff0d6;}
.pp-sub{font-size:1.08rem;font-weight:800;margin:18px 0 4px 0;color:#0b6f6e;}
.pp-note{color:#6b8497;font-size:.85rem;margin:-2px 0 6px 0;}
.pp-beyond{border:2px dashed #9ed8d3;border-radius:16px;padding:6px 16px 10px 16px;margin-top:14px;background:#f3fcfb;}
.pp-chip{display:inline-block;padding:2px 11px;border-radius:999px;background:#dff3f1;color:#0b6f6e;
  font-size:.8rem;font-weight:600;margin-right:6px;}
.pp-badge{display:inline-block;padding:2px 10px;border-radius:999px;background:#e3f6ea;color:#17603a;
  font-size:.8rem;font-weight:700;}
.pp-badge.warn{background:#fff1da;color:#8a5200;}
.pp-num{display:inline-flex;width:30px;height:30px;border-radius:50%;align-items:center;
  justify-content:center;color:#fff;font-weight:800;}
.pp-num.c0{background:#0ea5a4;} .pp-num.c1{background:#2563eb;}
.pp-num.c2{background:#f59e0b;} .pp-num.c3{background:#fb7185;}
.pp-dot{font-size:1.25rem;font-weight:800;}
.pp-dot.c0{color:#0ea5a4;} .pp-dot.c1{color:#2563eb;} .pp-dot.c2{color:#d97706;} .pp-dot.c3{color:#fb7185;}
.pp-about{background:linear-gradient(135deg,#d5f3f0,#dbe7ff);border-radius:16px;padding:14px 16px;margin-bottom:10px;}
.pp-about h4{margin:0 0 6px 0;font-size:1.05rem;}
.pp-about p{margin:0 0 8px 0;font-size:.9rem;}
.pp-about ul{margin:0;padding-left:0;list-style:none;font-size:.88rem;}
.pp-about li{margin:5px 0;}
.pp-about .safe{margin-top:8px;padding-top:8px;border-top:1px dashed #9ed8d3;font-size:.82rem;color:#4a6a80;}
@media (max-width:640px){.pp-steps{grid-template-columns:1fr;}.pp-title{font-size:1.9rem;}}
</style>
"""

# An original mascot: a friendly round face with big glasses. Static SVG, drawn by us.
MASCOT = """
<svg class="pp-mascot" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Paper Playground mascot">
  <circle cx="60" cy="63" r="44" fill="#ffd166" stroke="#12324a" stroke-width="3.5"/>
  <path d="M30 40 Q60 6 90 40" fill="#0ea5a4" stroke="#12324a" stroke-width="3.5" stroke-linejoin="round"/>
  <circle cx="42" cy="58" r="15" fill="#ffffff" stroke="#12324a" stroke-width="4.5"/>
  <circle cx="78" cy="58" r="15" fill="#ffffff" stroke="#12324a" stroke-width="4.5"/>
  <line x1="57" y1="58" x2="63" y2="58" stroke="#12324a" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="27" y1="56" x2="19" y2="52" stroke="#12324a" stroke-width="4" stroke-linecap="round"/>
  <line x1="93" y1="56" x2="101" y2="52" stroke="#12324a" stroke-width="4" stroke-linecap="round"/>
  <circle cx="44" cy="60" r="5" fill="#12324a"/><circle cx="80" cy="60" r="5" fill="#12324a"/>
  <circle cx="46" cy="58" r="1.6" fill="#fff"/><circle cx="82" cy="58" r="1.6" fill="#fff"/>
  <path d="M44 84 Q60 99 76 84" fill="none" stroke="#12324a" stroke-width="4" stroke-linecap="round"/>
  <circle cx="29" cy="78" r="6" fill="#fda4af" opacity=".6"/><circle cx="91" cy="78" r="6" fill="#fda4af" opacity=".6"/>
  <text x="96" y="24" font-size="16" fill="#2563eb">✦</text><text x="8" y="30" font-size="12" fill="#0ea5a4">✦</text>
</svg>
"""

HERO = f"""
<div class="pp-hero">{MASCOT}
  <div><div class="pp-title">Paper Playground</div>
  <div class="pp-tag">Upload a research paper. Get a clear explanation with facts you can verify against the source.</div></div>
</div>
"""

ABOUT = """
<div class="pp-about">
  <h4>Welcome to Paper Playground</h4>
  <p>Upload a research paper and get a clear, structured explanation, written for your level.</p>
  <ul>
    <li>📖 <b>What this paper is:</b> the idea, in plain words</li>
    <li>🔎 <b>Key facts:</b> each with a page reference and a supporting quote</li>
    <li>💡 <b>Key things to know:</b> caveats, plus definitions of key terms</li>
  </ul>
  <div class="safe">🛡️ Your PDF is not stored, and hidden text inside files is ignored.</div>
</div>
"""

WELCOME = """
<div class="pp-welcome">Welcome. What research paper would you like to explore today? :)</div>
<div class="pp-welcome-sub">Choose a paper below, or open an example to see how it works.</div>
"""

STEPS = """
<div class="pp-steps">
  <div class="pp-step"><b><span class="n">1</span>Pick a paper</b>Upload a public PDF, or find one on arXiv.</div>
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
