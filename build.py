#!/usr/bin/env python3
"""Genera le pagine del corso da content/*.html.

Scorciatoie nei contenuti:
  [[fig nome | didascalia]]                 foto con dati di scatto
  [[fig nome | didascalia | wide]]          foto larga
  [[pair a | didascalia || b | didascalia]] due foto affiancate
  [[grid a b c d | didascalia]]             piccola serie in griglia
  IMGDIR/nome.webp                          percorso immagine grande
"""
import json, os, re, html
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
EXIF = json.load(open(os.path.join(ROOT, "data/exif.json")))
WEBDIR = os.path.join(ROOT, "img/web")
EXT = ".jpg" if os.path.exists(os.path.join(WEBDIR, "dsc04882.jpg")) else ".webp"

LEVELS = [
    ("Le basi tecniche", "Livello 1. Come funziona la fotocamera."),
    ("Vedere", "Livello 2. Luce, composizione, momento."),
    ("I generi", "Livello 3. Dove la tecnica incontra il soggetto."),
    ("Avanzato", "Livello 4. Controllo totale e progetto."),
]

# numero, slug, titolo, livello, foto di testata, alt testata, sottotitolo
MODULES = [
    ("0", "prima-di-iniziare", "Prima di iniziare", 0, "dsc04657", "Sentiero che sale tra i prati verso le montagne", "Come usare il corso, cosa serve e come impostare la fotocamera prima del primo scatto."),
    ("1", "fotocamera", "Come funziona una fotocamera", 0, "dsc04717", "Il disco arancione del sole, parzialmente coperto, su un fondo rosso", "Luce, obiettivo, sensore. Tre pezzi, un solo lavoro: trasformare la luce in un'immagine."),
    ("2", "esposizione", "L'esposizione", 0, "dsc04838", "Lago di montagna al crepuscolo, ultima luce sull'orizzonte", "Tre controlli decidono quanta luce arriva al sensore. Impararli bene vuol dire smettere di subire la fotocamera."),
    ("3", "messa-a-fuoco", "Messa a fuoco e nitidezza", 0, "dsc01488", "Lorichetto arcobaleno tra fiori gialli, sfondo sfocato", "Dove mettere il fuoco, quanto deve essere profondo e perché una foto a fuoco può sembrare comunque morbida."),
    ("4", "obiettivi", "Obiettivi e focali", 0, "dsc02133", "Vista aerea di un'isola verde in una baia", "La focale decide quanto mondo entra nella foto. La distanza decide come appare."),
    ("5", "colore-e-file", "Colore e file", 0, "img_2051", "Sagoma di un albero di acacia contro un cielo rosa e viola", "Bilanciamento del bianco, RAW e JPEG, gamma dinamica e spazi colore."),
    ("6", "luce", "Leggere la luce", 1, "dsc04857", "Le Tre Cime avvolte da nuvole bianche contro il cielo azzurro", "Qualità, direzione, colore. Imparare a vedere la luce prima di guardare il soggetto."),
    ("7", "composizione", "Composizione", 1, "dsc03272", "Tetto bianco a punte di un edificio contro un cielo di nuvole", "Come organizzare quello che c'è nel fotogramma. Regole utili e quando superarle."),
    ("8", "momento", "Il momento", 1, "img_2117", "Un uccello posato in cima a un tronco secco contro il cielo", "Anticipare, aspettare, scattare. Il tempo giusto vale più della fotocamera giusta."),
    ("9", "paesaggio", "Paesaggio e montagna", 2, "dsc04869", "Le Tre Cime di Lavaredo con un piccolo lago in primo piano", "Pianificare la luce, leggere il meteo, raccontare la scala. Dalla montagna al bosco, dall'acqua alla notte."),
    ("10", "street", "Street", 2, "dsc02714", "Tram giallo tra gli alberi di un viale cittadino", "La città come palcoscenico. Approccio, luce urbana, geometrie e rispetto delle persone."),
    ("11", "viaggio", "Viaggio", 2, "dsc02984", "I tetti di Roma visti dall'alto fino all'orizzonte", "Raccontare un luogo, non collezionare cartoline."),
    ("12", "animali", "Animali, ambiente per ambiente", 2, "img_2506", "Un elefante tra gli arbusti della savana", "Dal cane di casa alla savana. Tecnica, pazienza ed etica in ogni ambiente."),
    ("13", "ritratto", "Ritratto", 2, "dsc03287", "Cucciolo di bracco ungherese che guarda in macchina", "Luce sul volto, posa e relazione. Un ritratto è una conversazione."),
    ("14", "altri-generi", "Macro, sport, architettura", 2, "dsc02010", "Ragno al centro della sua tela, sfondo sfocato", "Tre generi con regole proprie. Il molto piccolo, il molto veloce, il molto grande."),
    ("15", "luce-artificiale", "Luce artificiale", 3, "dsc02325", "Edifici illuminati di notte visti dal basso", "Flash, luce continua e luci della città. Quando la luce la porti o la scegli tu."),
    ("16", "tecniche-avanzate", "Tecniche avanzate di ripresa", 3, "dsc04853", "Montagne in bianco e nero con il sole tra le nuvole", "ETTR, bracketing, focus stacking, panoramiche, lunghe esposizioni e time-lapse."),
    ("17", "post-produzione", "Post-produzione", 3, "dark-mood", "Lago glaciale con montagne, versione cupa e fredda", "Dal file grezzo alla foto finita. Un metodo che vale in Lightroom, Luminar o qualsiasi altro programma."),
    ("18", "progetto", "Dalla foto al progetto", 3, "dsc03184", "La torre della televisione di Berlino contro il cielo", "Scegliere, mettere in sequenza, costruire una serie. E portarla su carta."),
    ("+", "intelligenza-artificiale", "Fotografia e intelligenza artificiale", 3, "dsc01931", "Primo piano di un koala con il naso scuro e gli occhi aperti", "Strumenti che aiutano, strumenti che inventano. E come restare credibili."),
]

CAMERA = {"ILCE-6700": "Sony A6700", "Canon EOS DIGITAL REBEL XSi": "Canon EOS 450D", "HERO7 Black": "GoPro HERO7"}

def comma(x):
    s = ("%g" % x)
    return s.replace(".", ",")

def exif_line(name):
    e = EXIF.get(name + ".jpg")
    if not e or not e.get("f"):
        return ""
    t = e["t"]
    ts = ("1/%d s" % round(1 / t)) if t < 0.3 else (comma(round(t, 1)) + " s")
    cam = CAMERA.get(e["camera"], e["camera"])
    parts = ["f/" + comma(e["f"]), ts, "ISO %d" % e["iso"]]
    if "iPhone" in cam or "GoPro" in cam:
        parts.append(cam)
    else:
        parts.append("%d mm" % round(e["mm"]))
        parts.append(cam)
    return ", ".join(parts)

_size = {}
def size(name):
    if name not in _size:
        p = os.path.join(WEBDIR, name + EXT)
        try:
            with Image.open(p) as im:
                _size[name] = im.size
        except Exception:
            _size[name] = (1600, 1067)
    return _size[name]

def img(name, alt, prefix, lazy=True):
    w, h = size(name)
    return '<img src="%simg/web/%s%s" alt="%s" width="%d" height="%d"%s>' % (
        prefix, name, EXT, html.escape(alt, quote=True), w, h, ' loading="lazy"' if lazy else "")

def figure(name, cap, prefix, cls=""):
    # la didascalia può iniziare con "alt::" per separare testo alternativo e didascalia
    alt, _, text = cap.partition("::") if "::" in cap else (cap, "", cap)
    alt, text = alt.strip(), text.strip()
    ex = exif_line(name)
    exs = '<span class="exif">%s</span>' % ex if ex else ""
    return '<figure%s>%s<figcaption>%s%s</figcaption></figure>' % (
        ' class="%s"' % cls if cls else "", img(name, alt, prefix), text, exs)

def shortcodes(s, prefix):
    def rep(m):
        kind, body = m.group(1), m.group(2).strip()
        if kind == "fig":
            parts = [p.strip() for p in body.split("|")]
            name, cap = parts[0], parts[1]
            cls = "wide" if len(parts) > 2 and parts[2] == "wide" else ""
            return figure(name, cap, prefix, cls)
        if kind == "pair":
            a, b = [x.strip() for x in body.split("||")]
            out = []
            for x in (a, b):
                n, c = [p.strip() for p in x.split("|", 1)]
                out.append(figure(n, c, prefix))
            return '<div class="pair wide">%s</div>' % "".join(out)
        if kind == "grid":
            names, cap = [p.strip() for p in body.split("|", 1)]
            imgs = "".join('<img src="%simg/thumb/%s.webp" alt="" loading="lazy">' % (prefix, n) for n in names.split())
            return '<figure class="wide"><div class="grid">%s</div><figcaption>%s</figcaption></figure>' % (imgs, cap)
        return m.group(0)
    s = re.sub(r"\[\[(fig|pair|grid)\s+(.*?)\]\]", rep, s, flags=re.S)
    s = s.replace("IMGDIR/", prefix + "img/web/").replace(".webp\"", "%s\"" % EXT)
    # le miniature restano webp
    s = s.replace("img/thumb/", "img/thumb/").replace("img/thumb/%s" % "", "img/thumb/")
    s = re.sub(r'(img/thumb/[\w-]+)\.jpg', r'\1.webp', s)
    return s

def toc(content):
    items = re.findall(r'<section id="([\w-]+)">\s*<h2>(.*?)</h2>', content)
    return "\n".join('        <li><a href="#%s">%s</a></li>' % (i, re.sub("<.*?>", "", t)) for i, t in items)

HEAD = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{p}assets/css/site.css">
</head>
<body>
"""

RIGHTS = "Tutte le fotografie di questo sito sono di Michele Sarzana, che ne detiene tutti i diritti. Non possono essere copiate, scaricate, modificate o pubblicate altrove senza la sua autorizzazione scritta. I testi del corso sono di Michele Sarzana."

FOOT = """<footer>
  <div class="wrap">
    <p class="rights">%s</p>
    <span>© 2026 Michele Sarzana</span>
  </div>
</footer>
""" % RIGHTS

def module_page(i):
    num, slug, title, lev, hero, halt, sub = MODULES[i]
    content = open(os.path.join(ROOT, "content", "%02d-%s.html" % (i, slug))).read()
    body = shortcodes(content, "../")
    label = "Extra" if num == "+" else "Modulo %s" % num
    prev = MODULES[i - 1] if i > 0 else None
    nxt = MODULES[i + 1] if i + 1 < len(MODULES) else None
    def nav(m, side):
        if not m:
            return '<span></span>'
        lab = "Extra" if m[0] == "+" else "Modulo %s" % m[0]
        return '<a class="%s" href="%s.html"><span class="meta">%s %s</span>%s</a>' % (
            side, m[1], "←" if side == "prev" else "", lab if side == "prev" else lab + " →", m[2])
    has_sim = 'class="sim' in body
    out = HEAD.format(title="%s | Corso di fotografia" % title, desc=html.escape(sub), p="../")
    out += """
<header class="bar over-hero">
  <a class="brand" href="../">Corso di fotografia</a>
  <nav aria-label="Principale">
    <a href="../#programma">Programma</a>
    <a href="../corso-di-fotografia.pdf">PDF</a>
  </nav>
</header>

<main>
  <header class="mod-head">
    %s
    <div class="hero-shade"></div>
    <div class="in">
      <p class="meta">%s, %s</p>
      <h1>%s</h1>
      <p class="lede">%s</p>
    </div>
  </header>

  <div class="lesson-layout">
    <nav class="toc" aria-label="Lezioni del modulo">
      <p>In questo modulo</p>
      <ol>
%s
      </ol>
      <p class="toc-back"><a href="../#programma">Tutto il programma</a></p>
    </nav>

    <article>
%s
      <nav class="next" aria-label="Moduli vicini">
        %s
        %s
      </nav>
    </article>
  </div>
</main>

%s
""" % (img(hero, halt, "../", lazy=False), LEVELS[lev][1].split(".")[0], label, html.escape(title), html.escape(sub), toc(content), body, nav(prev, "prev"), nav(nxt, "nxt"), FOOT)
    if has_sim:
        out += '<script src="../assets/js/simulatore.js"></script>\n'
    out += '<script src="../assets/js/modulo.js"></script>\n</body>\n</html>\n'
    open(os.path.join(ROOT, "corso", slug + ".html"), "w").write(out)

def program_html(prefix="", link=True):
    out = ['      <ol class="levels">']
    for li, (lname, ldesc) in enumerate(LEVELS):
        out.append('        <li class="level">\n          <h3>%s</h3>\n          <span class="meta">%s</span>\n          <ul class="modules">' % (lname, ldesc))
        for m in MODULES:
            if m[3] != li:
                continue
            title = html.escape(m[2])
            t = '<a href="%scorso/%s.html">%s</a>' % (prefix, m[1], title) if link else title
            out.append('            <li><span class="n">%s</span><span>%s</span></li>' % (m[0], t))
        out.append("          </ul>\n        </li>")
    out.append("      </ol>")
    return "\n".join(out)

def home():
    p = os.path.join(ROOT, "index.html")
    s = open(p).read()
    s = re.sub(r'      <ol class="levels">.*?\n      </ol>', lambda m: program_html(), s, flags=re.S)
    s = re.sub(r'      <p class="status-note">.*?</p>\n', '      <p class="status-note">Tutti i moduli sono online. Puoi seguirli in ordine o saltare dove ti serve. C\'è anche la <a href="corso-di-fotografia.pdf">versione PDF</a> da leggere offline.</p>\n', s, flags=re.S)
    s = re.sub(r'img/web/(dsc04882)\.(webp|jpg)', r'img/web/\1' + EXT, s)
    s = s.replace('<a href="corso/esposizione.html">Modulo 2</a>', '<a href="corso/prima-di-iniziare.html">Inizia</a>')
    open(p, "w").write(s)

def print_book():
    """Una sola pagina con tutto il corso, pensata per la stampa in PDF."""
    parts = []
    for i, m in enumerate(MODULES):
        num, slug, title, lev, hero, halt, sub = m
        content = open(os.path.join(ROOT, "content", "%02d-%s.html" % (i, slug))).read()
        content = re.sub(r'<div class="sim[^"]*".*?</div>\s*</div>', '', content, flags=re.S)  # niente simulatore su carta
        content = re.sub(r'<p class="meta">È una simulazione.*?</p>', '', content, flags=re.S)
        content = content.replace("Prova qui sotto.", "Sul sito trovi un simulatore per provare.")
        body = shortcodes(content, "")
        # id unici nel libro
        body = re.sub(r'id="([\w-]+)"', lambda mm: 'id="%s-%s"' % (slug, mm.group(1)), body)
        label = "Extra" if num == "+" else "Modulo %s" % num
        parts.append('<section class="chapter" id="%s">\n<div class="chap-head">%s<p class="meta">%s, %s</p><h1>%s</h1><p class="lede">%s</p></div>\n%s\n</section>' % (
            slug, img(hero, halt, "", lazy=False), LEVELS[lev][1].split(".")[0], label, html.escape(title), html.escape(sub), body))
    toc_items = "\n".join('<li><a href="#%s"><span>%s</span>%s</a></li>' % (m[1], "Extra" if m[0] == "+" else m[0], html.escape(m[2])) for m in MODULES)
    out = HEAD.format(title="Corso di fotografia", desc="Versione da leggere offline", p="")
    out = out.replace('<link rel="stylesheet" href="assets/css/site.css">', '<link rel="stylesheet" href="assets/css/site.css">\n<link rel="stylesheet" href="assets/css/print.css">')
    out += """<div class="book">
<section class="cover">%s<div class="cover-text"><h1>Corso di fotografia</h1><p class="lede">Dalle basi tecniche alla pratica avanzata.</p><p class="meta">Michele Sarzana</p></div></section>
<section class="book-toc"><h2>Indice</h2><ol>%s</ol></section>
%s
<section class="colophon"><p>%s</p><p class="meta">Versione online: michelesarzana.github.io/corso-di-fotografia</p></section>
</div>
<script>
document.querySelectorAll('img[data-histo]').forEach(function(img){ var c=img.nextElementSibling; if(c&&c.tagName==='CANVAS') c.remove(); });
</script>
</body></html>""" % (img("dsc04882", "Le Tre Cime di Lavaredo viste da una grotta", "", lazy=False), toc_items, "\n".join(parts), RIGHTS)
    open(os.path.join(ROOT, "stampa.html"), "w").write(out)

if __name__ == "__main__":
    for i, m in enumerate(MODULES):
        if os.path.exists(os.path.join(ROOT, "content", "%02d-%s.html" % (i, m[1]))):
            module_page(i)
        else:
            print("manca", m[1])
    home()
    print_book()
    print("ok, estensione", EXT)
