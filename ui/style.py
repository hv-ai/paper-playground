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

CSS += """
<style>
.stApp{background:#f6f4ee;color:#172e40;}
.block-container{max-width:1120px;padding-top:2rem;padding-bottom:3rem;}
[data-testid="stSidebar"]{background:#eceee7;border-right:1px solid #dde2da;}
h1,h2,h3{color:#172e40;letter-spacing:-.025em;}
h1,h2{font-family:Georgia,serif;font-weight:400;}
.pp-hero-new{padding:45px 40px;margin-bottom:28px;border-radius:16px;color:#f5f8fb;background:radial-gradient(ellipse at 5% 110%,#215361 0,transparent 60%),radial-gradient(ellipse at 95% 0,#273c5c 0,transparent 60%),#0b192b;}
.pp-brand{font-family:Georgia,serif;font-size:1.3rem;color:#f5f8fb;}
.pp-eyebrow{text-transform:uppercase;letter-spacing:.17em;font-size:.72rem;color:#9dd9ce;margin:25px 0 12px;}
.pp-hero-new h1{font-size:3.5rem;line-height:1.05;color:#f5f8fb;margin:0 0 18px;}
.pp-hero-new h1 em{color:#9dd9ce;font-weight:400;}
.pp-hero-new p{color:#c3d0db;max-width:650px;margin:0;font-size:1.03rem;}
.pp-workspace-head{background:#0b192b;padding:17px 23px;border-radius:10px;margin-bottom:24px;display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;}
.pp-workspace-head span{color:#b7cbd5;font-size:.9rem;}
[data-testid="stFileUploader"]{background:#eef4f0;border-radius:9px;padding:14px;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:10px;flex-wrap:wrap;}
[data-testid="stTabs"] [data-baseweb="tab"]{color:#526b75;}
[data-testid="stTabs"] [aria-selected="true"]{color:#087f83;}
button[kind="primary"]{background:#087f83;border-color:#087f83;border-radius:8px;}
.pp-chip{background:#e2eee7;color:#285c54;padding:5px 12px;margin-bottom:8px;}
.pp-sub{color:#245b5c;font-size:1.05rem;margin-top:24px;}
.pp-note{color:#526974;}
.pp-steps{gap:20px;margin-top:28px;}
.pp-step{background:transparent;border:0;padding:0;}
.pp-step b{color:#173b49;}
.pp-step span.n,.pp-step.s2 span.n,.pp-step.s3 span.n{background:#087f83;}
.pp-num.c0,.pp-num.c1,.pp-num.c2,.pp-num.c3{background:#e0eee6;color:#245d54;}
.pp-dot.c0,.pp-dot.c1,.pp-dot.c2,.pp-dot.c3{color:#087f83;}
@media(max-width:640px){.block-container{padding:1rem;}.pp-hero-new{padding:28px 23px;}.pp-hero-new h1{font-size:2.5rem;}.pp-steps{grid-template-columns:1fr;}}
</style>
"""
HERO = """
<section class="pp-hero-new"><div class="pp-brand">Paper Playground 🤓</div>
<div class="pp-eyebrow">Your paper. Your level. Your tone.</div>
<h1>Understand the <em>research.</em></h1>
<p>Bring the paper you’re curious about. Choose how you want it explained, explore its findings, and make sense of the unfamiliar.</p></section>
"""
WORKSPACE_HEADER = """
<div class="pp-workspace-head"><div class="pp-brand">Paper Playground 🤓</div><span>Understand the research.</span></div>
"""
STEPS = """
<div class="pp-steps"><div class="pp-step"><b><span class="n">1</span>Your paper</b>Upload a public PDF or find it on arXiv.</div>
<div class="pp-step"><b><span class="n">2</span>Your preferences</b>Choose the level, tone, and length independently.</div>
<div class="pp-step"><b><span class="n">3</span>Your understanding</b>Explore the idea, findings, caveats, and key terms.</div></div>
"""

# Research-studio theme: one continuous canvas with calm, opaque reading surfaces.
CSS += """
<style>
.stApp{color:#e5eaf4;background:radial-gradient(ellipse at 0 35%,#253f50 0,transparent 55%),radial-gradient(ellipse at 100% 85%,#352a54 0,transparent 50%),repeating-linear-gradient(0deg,transparent 0,transparent 55px,#ffffff04 55px,#ffffff04 56px),#101b2d;background-attachment:fixed;}
[data-testid="stHeader"]{background:#101b2df0;}
[data-testid="stSidebar"]{background:#142137;border-right:1px solid #ffffff15;color:#dbe3f0;}
h1,h2,h3,[data-testid="stSidebar"] h3{color:#e5eaf4;}
.pp-hero-new{background:transparent;border-radius:0;padding:32px 5px 30px;margin-bottom:14px;}
.pp-brand{font-family:Arial,sans-serif;letter-spacing:-.04em;}
.pp-hero-new h1{font-size:3.7rem;max-width:700px;}
.pp-hero-new h1 em{color:#c0b2ff;}
.pp-eyebrow{color:#b9ade5;}
.pp-hero-new p{color:#bfcbdc;}
.pp-workspace-head{background:#17253c;border:1px solid #ffffff12;}
.st-key-paper_setup{background:#fbfbfd!important;color:#172e40!important;padding:25px;border:1px solid #ffffff40!important;border-radius:15px;box-shadow:0 20px 65px #0003;}
.st-key-reading_workspace{background:#fbfbfd;color:#172e40;padding:25px;border-radius:14px;box-shadow:0 14px 50px #0002;}
:is(.st-key-paper_setup,.st-key-reading_workspace) :is(h1,h2,h3,h4,h5,p,label,summary,[data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"]){color:#172e40;}
:is(.st-key-paper_setup,.st-key-reading_workspace) [data-testid="stCaptionContainer"] p{color:#586a79;}
:is(.st-key-paper_setup,.st-key-reading_workspace) [data-baseweb="input"]{background:#f2f2f8;}
:is(.st-key-paper_setup,.st-key-reading_workspace) input{color:#172e40!important;background:#f2f2f8!important;}
:is(.st-key-paper_setup,.st-key-reading_workspace) [data-baseweb="tab"]{color:#536178;}
:is(.st-key-paper_setup,.st-key-reading_workspace) [aria-selected="true"]{color:#6556b4;}
.st-key-paper_setup [data-testid="stFileUploader"],.st-key-paper_setup [data-testid="stFileUploaderDropzone"]{background:#eeecf8;color:#172e40;}
.st-key-paper_setup [data-testid="stFileUploaderDropzone"] small{color:#526477;}
:is(.st-key-paper_setup,.st-key-reading_workspace) button[kind="secondary"]{background:#eeedf6;color:#23394b;border-color:#d7d8e4;}
:is(.st-key-paper_setup,.st-key-reading_workspace) [data-testid="stChatMessage"]{background:#f0eff7;}
button[kind="primary"]{background:#6657b6;border-color:#6657b6;}
button[kind="primary"] p{color:#fff!important;}
.pp-chip{color:#594d8f;background:#ece8f7;}
.pp-num.c0,.pp-num.c1,.pp-num.c2,.pp-num.c3{color:#5c5196;background:#eae5f6;}
.pp-sub{color:#5c5196;}.pp-note{color:#596a78;}
.pp-step b{color:#e4e8f1;}.pp-step{color:#b7c4d4;}
.pp-step span.n{background:#67599d;}
@media(max-width:640px){.pp-hero-new h1{font-size:2.7rem;}.st-key-paper_setup,.st-key-reading_workspace{padding:16px;}}
</style>
"""

# Bundle the asset inside the repository so Streamlit Cloud can render it too.
from base64 import b64encode as _b64encode
from pathlib import Path as _Path
_RESEARCH_BACKGROUND = _Path(__file__).resolve().parents[1] / "assets" / "research-companion.png"
if _RESEARCH_BACKGROUND.is_file():
    _background_uri = "data:image/png;base64," + _b64encode(_RESEARCH_BACKGROUND.read_bytes()).decode("ascii")
    CSS += """
<style>
.stApp {background-image:linear-gradient(180deg,#0c172b9c,#111c30eb),url('ASSET_URI');background-size:cover;background-position:center top;background-attachment:fixed;}
.pp-hero-new {background-image:linear-gradient(90deg,#0a1527ef 0%,#0a1527bf 43%,#0a15271a 78%),url('ASSET_URI');background-size:cover;background-position:center right;border-radius:15px;padding:35px 32px;min-height:360px;border:1px solid #ffffff12;}
.pp-hero-new h1 {max-width:63%;font-size:3.25rem;}
.pp-hero-new p {max-width:55%;}
@media(max-width:640px){.pp-hero-new{padding:25px 22px;min-height:370px;background-position:65% center;}.pp-hero-new h1{font-size:2.5rem;max-width:100%;}.pp-hero-new p{max-width:100%;}.pp-hero-new{background-image:linear-gradient(90deg,#0a1527e8,#0a152791),url('ASSET_URI');}}
</style>
""".replace("ASSET_URI", _background_uri)

# Ensure native controls remain legible inside light panels under the dark app theme.
CSS += """
<style>
.st-key-paper_setup [data-testid="stCheckbox"]:has(input:not([role="switch"])) label > span + div {
 background:#fff!important;border:2px solid #64748b!important;border-radius:4px!important;
}
.st-key-paper_setup [data-testid="stCheckbox"]:has(input:checked:not([role="switch"])) label > span + div {
 background:#6657b6!important;border-color:#6657b6!important;color:#fff!important;
}
.st-key-paper_setup [data-testid="stCheckbox"]:has(input:focus-visible) label {outline:2px solid #6657b6;outline-offset:4px;}
:is(.st-key-reading_workspace,.st-key-paper_setup) [data-testid="stExpander"] details,
:is(.st-key-reading_workspace,.st-key-paper_setup) [data-testid="stExpander"] summary {
 background:#fff!important;color:#172e40!important;
}
:is(.st-key-reading_workspace,.st-key-paper_setup) [data-testid="stExpander"] summary:is(:hover,:focus-visible,:active),
:is(.st-key-reading_workspace,.st-key-paper_setup) [data-testid="stExpander"] details[open] > summary {
 background:#eeebf8!important;color:#172e40!important;
}
:is(.st-key-reading_workspace,.st-key-paper_setup) [data-testid="stExpander"] summary * {color:#172e40!important;}
</style>
"""
