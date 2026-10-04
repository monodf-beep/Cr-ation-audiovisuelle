"""Compose index.html (HyperFrames) du reel « Terra Madre et Sagre » et son habillage sonore.
Tout est cale sur les mots de la voix montee (data/sous-titres.json) : si la voix change, on relance.
Entrees : montage-recit.json, data/sous-titres.json, compositions/carte.json, assets/plans/*, assets/face-recit.mp4.
Sorties : index.html, assets/habillage.m4a (musique + effets, sous la voix).
Usage (dans 12_terra-madre/) : python3 tools/composer.py <dossier des sons (Mixkit)>"""
import html, json, os, subprocess, sys

SONS = sys.argv[1] if len(sys.argv) > 1 else "assets/sons"
M = json.load(open("montage-recit.json"))
ST = json.load(open("data/sous-titres.json"))
CARTE = json.load(open("compositions/carte.json"))
V = M["vitesse"]

# ------------------------------------------------------------------ Ancres
SEQ = {}
for m in M["morceaux"]:
    s = SEQ.setdefault(m["sequence"], [m["t"] / V, 0])
    s[1] = (m["t"] + m["b"] - m["a"]) / V
S = {k: round(v[0], 3) for k, v in SEQ.items()}
E = {k: round(v[1], 3) for k, v in SEQ.items()}
FIN_VOIX = round(M["duree"], 3)
CARTON = 3.8
DUREE = round(FIN_VOIX + CARTON, 3)


def W(texte, apres=0.0):
    """Debut du premier groupe de sous-titres qui contient `texte`, apres `apres`."""
    for g in ST:
        if g["debut"] >= apres - 0.01 and texte.lower() in " ".join(g["mots"]).lower():
            return round(g["debut"], 3)
    raise SystemExit(f"mot introuvable dans la voix : {texte!r} apres {apres}")


# ------------------------------------------------------------------ Plans (images par-dessus le face camera)
# (debut, fin, media, effet) ; effet : pousse (poussee lente), drapeau-oc / drapeau-pie (le drapeau flotte), plat
PLANS = [
    (0.0, W("ce sont") + 0.95, "parapluies", "pousse"),
    (W("dans les villages") - 0.1, W("pour célébrer"), "village", "pousse"),
    (W("pour célébrer"), W("Les produits"), "marche", "pousse"),
    (W("Les produits"), E["sagre"], "chocolats", "pousse"),
    (W("des nouveaux"), W("et surtout") + 0.6, "patisseries", "pousse"),
    (W("uniquement"), W("On y mange", 24), "palais", "drapeau-pie"),
    (W("On y mange", 24), E["piemont"], "tables-mole", "pousse"),
    (W("pour Terra Madre") + 0.15, W("le terroir", 33) + 0.3, "san-carlo", "pousse"),
    (W("le terroir", 33) + 0.3, W("piémontais", 38) - 0.2, "terra-madre", "pousse"),
    (W("piémontais", 38) - 0.2, E["turin"], "escargot", "pousse"),
    (E["turin"], E["viaroma"], "via-roma", "plat"),
    (W("et là j'étais", 50), E["vallees"], "vignes", "drapeau-oc"),
    (W("c'est un petit"), W("Sagra dei Funghi"), "giaveno", "pousse"),
    (W("Sagra dei Funghi"), E["giaveno"], "sagra", "pousse"),
    (E["giaveno"], E["plats"] + 0.2, "menu-fond", "plat"),
    (E["cumiana"], W("le bulbe"), "clocher", "pousse"),
    (E["francois"], W("regorgent"), "baroque", "pousse"),
    (W("regorgent"), E["baroque"] + 0.15, "eglise-rue", "pousse"),
]
CARTES = [  # (debut, fin, scene)
    (E["sieste"], W("pour Terra Madre") + 0.15, "turin"),
    (W("dans le Piémont", 44), W("et là j'étais", 50), "vallees"),
    (E["vallees"], W("c'est un petit"), "giaveno"),
    (E["influenceur"], E["cumiana"], "cumiana"),
]
# Face camera serre (punch-in) : (instant, echelle) ; 1 = plan large
PUNCHS = [(0, 1.0), (W("ce sont") + 0.95, 1.08), (S["gouter"], 1.0), (W("de goûter"), 1.2), (W("C'est ça"), 1.0),
          (S["sieste"], 1.0), (W("des siestes"), 1.24), (S["influenceur"], 1.0), (W("influenceur"), 1.2),
          (W("pas encore"), 1.0), (W("confiance"), 1.16), (W("mais là non"), 1.22), (S["fin"], 1.0), (W("abastou"), 1.18)]
# Flash blanc sur les grands changements
FLASHS = [W("ce sont") + 0.95, E["sieste"], E["turin"], E["viaroma"], E["vallees"], E["giaveno"], E["influenceur"],
          E["cumiana"], E["bulbe"], FIN_VOIX]
# Pas de sous-titres pendant un titre qui dit la meme chose
SANS_ST = [(W("le bulbe"), E["bulbe"]), (0, W("ce sont") + 0.95), (W("la gastronomie"), E["sagre"]), (E["giaveno"], E["plats"] + 0.2), (FIN_VOIX, DUREE)]
# Plans clairs : sous-titres en encre
CLAIRS = [(a, b) for a, b, _ in CARTES]

# ------------------------------------------------------------------ HTML
h = []
add = h.append
add(f'''<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>Terra Madre et sagre du Piémont</title>
    <!-- Reel vertical de Franck Monod, style « Reportage Franck » (styles/reportage-franck.md, 04_montage/BONNES-PRATIQUES.md).
         Genere par tools/composer.py : ne pas editer a la main. Voix : tools/couper-recit.py ; sous-titres : tools/sous-titres.py. -->
    <script src="assets/vendor/gsap.min.js"></script>
    <link rel="stylesheet" href="assets/tokens.css" />
    <style>
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro.woff') format('woff'); font-weight: 400; }}
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro-Semibold.woff') format('woff'); font-weight: 600; }}
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro-Bold.woff') format('woff'); font-weight: 700; }}
      @font-face {{ font-family: 'Cormorant Garamond'; src: url('assets/fonts/CormorantGaramond-Medium.woff2') format('woff2'); font-weight: 500; }}
      @font-face {{ font-family: 'Cormorant Garamond'; src: url('assets/fonts/CormorantGaramond-Italic.woff2') format('woff2'); font-weight: 500; font-style: italic; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #000; font-family: var(--fm-font); color: var(--fm-ink-900); }}
      video.plein, img.plein {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      #face {{ transform-origin: 50% 30%; }}
      .plan {{ position: absolute; inset: 0; overflow: hidden; opacity: 0; }}
      .plan .cadre {{ position: absolute; inset: 0; transform-origin: 50% 45%; }}
      .vent {{ position: absolute; inset: 0; }}
      #flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; z-index: 40; }}

      /* Titres (zone sure : sous 280 px, au-dessus de 1440 px, a gauche de 940 px) */
      .hook {{ position: absolute; left: 80px; right: 160px; top: 300px; z-index: 20; opacity: 0; }}
      .hook .eyebrow {{ display: inline-block; font-size: 30px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: #fff; background: var(--fm-bleu-savoie); padding: 8px 16px; }}
      .hook h1 {{ margin-top: 20px; font-size: 168px; font-weight: 700; line-height: .92; letter-spacing: -.02em; color: #fff; text-shadow: 0 4px 30px rgba(0,0,0,.55); }}
      .hook h1 em {{ font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; }}
      .pastille {{ position: absolute; left: 70px; top: 300px; background: #fff; padding: 18px 26px; z-index: 20; opacity: 0; max-width: 780px; }}
      .pastille .k {{ font-size: 24px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .pastille .v {{ margin-top: 6px; font-size: 44px; font-weight: 700; line-height: 1.1; }}
      .credit {{ position: absolute; right: 24px; top: 262px; font-size: 18px; color: #fff; background: rgba(23,23,25,.75); padding: 4px 10px; z-index: 21; opacity: 0; }}
      .liste {{ position: absolute; left: 70px; top: 300px; z-index: 20; }}
      .liste div {{ display: table; margin-bottom: 14px; background: #fff; padding: 10px 24px 14px; font-size: 64px; font-weight: 700; opacity: 0; }}
      .liste div.cle {{ background: var(--fm-bleu-savoie); color: #fff; }}
      .lieu-fin {{ position: absolute; left: 80px; top: 300px; z-index: 20; color: #fff; font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; font-size: 120px; line-height: 1; text-shadow: 0 0 4px rgba(0,0,0,.7), 0 2px 24px rgba(0,0,0,.7); opacity: 0; }}
      .lieu-fin em {{ font-style: italic; border-bottom: 5px solid #fff; }}
      .bloc-nom {{ position: absolute; left: 60px; top: 1080px; background: var(--fm-bleu-savoie); color: #fff; padding: 22px 32px 24px; z-index: 20; opacity: 0; }}
      .bloc-nom .n {{ font-size: 54px; font-weight: 700; line-height: 1.1; }}
      .bloc-nom .r {{ margin-top: 8px; font-size: 26px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; }}

      /* Carte */
      .carte {{ position: absolute; inset: 0; background: #e9ecf3; opacity: 0; z-index: 10; overflow: hidden; }}
      .carte .cam {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 0 0; }}
      .carte .cam img {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
      .pin {{ position: absolute; width: 0; height: 0; opacity: 0; }}
      .pin i {{ position: absolute; left: -16px; top: -16px; width: 32px; height: 32px; border-radius: 50%; background: var(--fm-bleu-savoie); border: 6px solid #fff; box-shadow: 0 3px 10px rgba(0,0,0,.3); }}
      .pin b {{ position: absolute; left: 30px; top: -34px; white-space: nowrap; font-size: 52px; font-weight: 700; color: var(--fm-ink-900); text-shadow: 0 0 6px #fff, 0 0 12px #fff; }}
      .pin.gauche b {{ left: auto; right: 30px; }}
      .pin.petit i {{ background: #fff; border-color: var(--fm-ink-700); left: -11px; top: -11px; width: 22px; height: 22px; border-width: 5px; }}
      .pin.petit b {{ font-size: 38px; font-weight: 600; color: var(--fm-ink-700); }}
      .lueur {{ position: absolute; border-radius: 50%; filter: blur(40px); opacity: 0; }}
      .langue {{ position: absolute; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; font-size: 64px; line-height: 1; opacity: 0; text-shadow: 0 0 8px #fff, 0 0 16px #fff; }}
      .carte .titre {{ position: absolute; left: 70px; top: 290px; font-size: 26px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .trait {{ position: absolute; height: 0; border-top: 5px dashed var(--fm-bleu-savoie); transform-origin: 0 0; opacity: 0; }}

      /* Via Roma : plaque de rue */
      .plaque {{ position: absolute; left: 140px; top: 640px; width: 800px; padding: 42px 40px 46px; background: #f4f1ea; border: 8px solid #2b2b2e; outline: 3px solid #f4f1ea; text-align: center; z-index: 20; opacity: 0; box-shadow: 0 30px 70px rgba(0,0,0,.45); }}
      .plaque .ville {{ font-size: 30px; font-weight: 700; letter-spacing: .3em; text-transform: uppercase; color: #6b6b70; }}
      .plaque .nom {{ margin-top: 6px; font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; font-size: 150px; line-height: 1; letter-spacing: .04em; color: #1c1c1e; }}
      .tampon {{ position: absolute; left: 520px; top: 990px; background: var(--fm-bleu-savoie); color: #fff; font-size: 54px; font-weight: 700; padding: 12px 28px 16px; transform: rotate(-6deg); z-index: 21; opacity: 0; }}

      /* Menu de la sagra */
      .menu {{ position: absolute; left: 110px; top: 330px; width: 860px; background: #fbf8f1; padding: 50px 56px 60px; z-index: 20; opacity: 0; box-shadow: 0 30px 70px rgba(0,0,0,.4); }}
      .menu .eyebrow {{ font-size: 26px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .menu h2 {{ margin-top: 10px; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; font-size: 96px; line-height: 1; }}
      .menu .ligne {{ display: flex; align-items: baseline; gap: 18px; margin-top: 34px; font-size: 54px; font-weight: 700; opacity: 0; }}
      .menu .ligne span {{ flex: 1; border-bottom: 4px dotted #b9b9bf; transform: translateY(-12px); }}
      .menu .ligne small {{ font-size: 34px; font-weight: 600; color: var(--fm-ink-700); }}
      .etoiles {{ position: absolute; right: 60px; bottom: -46px; background: var(--fm-bleu-savoie); color: #fff; font-size: 46px; font-weight: 700; padding: 12px 26px 16px; transform: rotate(-5deg); opacity: 0; }}
      .pas-photo {{ position: absolute; left: 600px; top: 330px; width: 380px; z-index: 20; opacity: 0; }}

      /* Clocher demonte (plan d'architecte) */
      .plan-bleu {{ position: absolute; inset: 0; background: var(--fm-bleu-savoie); opacity: 0; z-index: 12; overflow: hidden; }}
      .plan-bleu .grille {{ position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,.08) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,.08) 2px, transparent 2px); background-size: 60px 60px; }}
      .plan-bleu svg {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: visible; }}
      .plan-bleu .t {{ stroke: #fff; stroke-width: 4; fill: rgba(255,255,255,.06); stroke-linejoin: round; }}
      .plan-bleu .fin {{ stroke: #fff; stroke-width: 2.5; fill: none; opacity: .8; }}
      .plan-bleu .bul {{ fill: rgba(255,255,255,.06); }}
      .plan-bleu .eti {{ font-family: 'Semplicita Pro', sans-serif; font-size: 36px; font-weight: 700; fill: #fff; letter-spacing: .04em; }}
      .plan-bleu .eti-l {{ stroke: #fff; stroke-width: 2; stroke-dasharray: 6 6; }}
      .plan-bleu .titre {{ position: absolute; left: 70px; top: 290px; font-size: 26px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: #fff; }}
      .plan-bleu .legende {{ font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-size: 72px; fill: #fff; }}

      /* Z de la sieste */
      .zzz {{ position: absolute; right: 120px; top: 360px; z-index: 20; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; color: #fff; text-shadow: 0 2px 18px rgba(0,0,0,.6); }}
      .zzz span {{ position: absolute; opacity: 0; }}

      /* Carton final */
      .final {{ position: absolute; inset: 0; background: #fff; z-index: 30; opacity: 0; }}
      .final .eyebrow {{ position: absolute; left: 90px; top: 330px; font-size: 28px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .final h2 {{ position: absolute; left: 90px; right: 150px; top: 390px; font-size: 104px; font-weight: 700; line-height: 1; letter-spacing: -.01em; }}
      .final .lieux {{ position: absolute; left: 90px; top: 760px; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-size: 64px; color: #1b2f6e; }}
      .final .sig {{ position: absolute; left: 90px; top: 1200px; font-size: 30px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--fm-ink-500); }}
      .final .abastou {{ position: absolute; left: 90px; top: 1250px; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; font-size: 120px; color: var(--fm-bleu-savoie); }}

      /* Sous-titres : groupes de 1 a 3 mots, mot-cle sur bloc bleu (zone sure Reels) */
      .st {{ position: absolute; left: 60px; right: 140px; bottom: 490px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 4px 18px; transform-origin: 50% 100%; z-index: 35; opacity: 0;
             font-size: 62px; font-weight: 700; line-height: 1.2; color: #fff; text-shadow: 0 0 8px rgba(0,0,0,.9), 0 3px 18px rgba(0,0,0,.6); }}
      .st .m {{ display: inline-block; white-space: nowrap; }}
      .st .m.cle {{ font-size: 1.3em; background: var(--fm-bleu-savoie); color: #fff; padding: 0 16px 4px; text-shadow: none; }}
      .st.clair {{ color: var(--fm-ink-900); text-shadow: 0 0 10px rgba(255,255,255,.95); }}
      .st.clair .m.cle {{ color: #fff; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUREE}" data-width="1080" data-height="1920">
      <!-- Le recit face camera, monte comme la voix (tools/couper-recit.py) -->
      <video id="face" class="plein" src="assets/face-recit.mp4" muted playsinline data-start="0" data-duration="{FIN_VOIX}" data-media-start="0" data-track-index="1"></video>
      <audio id="voix" src="assets/voix.m4a" data-start="0" data-duration="{FIN_VOIX}" data-track-index="10" data-volume="1"></audio>
      <audio id="habillage" src="assets/habillage.m4a" data-start="0" data-duration="{DUREE}" data-track-index="11" data-volume="1"></audio>
      <svg width="0" height="0" style="position:absolute">
        <!-- Le drapeau flotte : turbulence qui glisse (feOffset anime) et deplace les pixels du drapeau seulement -->
        <filter id="vent-oc" x="-20%" y="-10%" width="140%" height="120%" filterUnits="objectBoundingBox">
          <feTurbulence type="turbulence" baseFrequency="0.009 0.022" numOctaves="2" seed="4" result="t"/>
          <feOffset id="vent-oc-dx" in="t" dx="0" dy="0" result="t2"/>
          <feDisplacementMap in="SourceGraphic" in2="t2" scale="22" xChannelSelector="R" yChannelSelector="G"/>
        </filter>
        <filter id="vent-pie" x="-20%" y="-10%" width="140%" height="120%" filterUnits="objectBoundingBox">
          <feTurbulence type="turbulence" baseFrequency="0.011 0.02" numOctaves="2" seed="9" result="t"/>
          <feOffset id="vent-pie-dx" in="t" dx="0" dy="0" result="t2"/>
          <feDisplacementMap in="SourceGraphic" in2="t2" scale="20" xChannelSelector="R" yChannelSelector="G"/>
        </filter>
      </svg>
''')

# Zones des drapeaux sur les photos 1080x1920 (rognage autour du drapeau, mat exclu autant que possible)
ZONES = {"drapeau-oc": "inset(668px 108px 796px 846px)", "drapeau-pie": "inset(540px 868px 872px 0px)"}
anim = []   # lignes JS du minutage
for i, (a, b, media, effet) in enumerate(PLANS):
    a, b = round(a, 3), round(b, 3)
    pid = f"pl{i}"
    src = f"assets/plans/{media}." + ("jpg" if media in ("palais", "vignes") else "mp4")
    if src.endswith(".mp4"):
        add(f'      <div class="plan" id="{pid}"><div class="cadre"><video id="v-{pid}" class="plein" src="{src}" muted playsinline data-start="{a}" data-duration="{round(b - a, 3)}" data-media-start="0" data-track-index="{2 + i % 2}"></video></div></div>')
    else:
        vent = ""
        if effet in ZONES:
            fid = "vent-oc" if effet == "drapeau-oc" else "vent-pie"
            vent = f'<div class="vent" style="clip-path:{ZONES[effet]}"><img class="plein" src="{src}" alt="" style="filter:url(#{fid})" /></div>'
        add(f'      <div class="plan" id="{pid}"><div class="cadre"><img class="plein" src="{src}" alt="" />{vent}</div></div>')
    anim.append(f'tl.set("#{pid}", {{opacity: 1}}, {a}); tl.set("#{pid}", {{opacity: 0}}, {b});')
    if effet in ("pousse", "drapeau-oc", "drapeau-pie"):
        anim.append(f'tl.fromTo("#{pid} .cadre", {{scale: 1}}, {{scale: 1.06, duration: {round(b - a, 3)}, ease: "none"}}, {a});')
    if effet in ZONES:
        fid = "vent-oc" if effet == "drapeau-oc" else "vent-pie"
        anim.append(f'tl.fromTo("#{fid}-dx", {{attr: {{dx: 0, dy: 0}}}}, {{attr: {{dx: -260, dy: 30}}, duration: {round(b - a, 3)}, ease: "none"}}, {a});')
PLAN_DE = {media: (round(a, 3), round(b, 3), f"pl{i}") for i, (a, b, media, _) in enumerate(PLANS)}

# ------------------------------------------------------------------ Habillage graphique
def montre(sel, a, b, entree="fade", sortie=True):
    anim.append(f'tl.set("{sel}", {{opacity: 1}}, {round(a, 3)});')
    if entree == "monte":
        anim.append(f'tl.from("{sel}", {{y: 30, duration: 0.45, ease: "power3.out"}}, {round(a, 3)});')
    elif entree == "pop":
        anim.append(f'tl.from("{sel}", {{scale: 0.8, duration: 0.3, ease: "back.out(2.2)"}}, {round(a, 3)});')
    if sortie:
        anim.append(f'tl.to("{sel}", {{opacity: 0, duration: 0.2}}, {round(b - 0.2, 3)});')

# Accroche : « Les sagre » sur les parapluies de Giaveno
pa, pb, _ = PLAN_DE["parapluies"]
add('      <div class="hook" id="hook"><div class="eyebrow">Piémont · automne</div><h1>Les <em>sagre</em></h1></div>')
anim.append(f'tl.set("#hook", {{opacity: 1}}, 0); tl.from("#hook .eyebrow", {{y: 16, opacity: 0, duration: 0.35, ease: "power3.out"}}, 0.05);')
anim.append(f'tl.from("#hook h1", {{y: 40, opacity: 0, duration: 0.5, ease: "power3.out"}}, 0.12); tl.to("#hook", {{opacity: 0, duration: 0.2}}, {pb - 0.2});')
# Liste qui monte : gastronomie, terroir, Piemont
add('      <div class="liste" id="liste"><div>la gastronomie</div><div>le terroir</div><div class="cle">le Piémont</div></div>')
for k, mot in enumerate(["la gastronomie", "du terroir", "du Piémont"]):
    t = W(mot)
    anim.append(f'tl.set("#liste div:nth-child({k + 1})", {{opacity: 1}}, {t}); tl.from("#liste div:nth-child({k + 1})", {{x: -40, duration: 0.35, ease: "power3.out"}}, {t});')
anim.append(f'tl.to("#liste", {{opacity: 0, duration: 0.2}}, {E["sagre"] - 0.2});')
# 100 % piemontais
a, b, _ = PLAN_DE["palais"]
add('      <div class="pastille" id="pa-pie"><div class="k">Au menu des sagre</div><div class="v">100 % piémontais</div></div>')
montre("#pa-pie", W("piémontais", a - 0.5), b, "monte")
# Sieste
add('      <div class="zzz" id="zzz"><span style="right:0;top:120px;font-size:80px">z</span><span style="right:-60px;top:40px;font-size:110px">z</span><span style="right:-140px;top:-60px;font-size:150px">z</span></div>')
t = W("des siestes")
for k in range(3):
    anim.append(f'tl.fromTo("#zzz span:nth-child({k + 1})", {{opacity: 0, y: 20}}, {{opacity: 1, y: 0, duration: 0.3, ease: "power2.out", immediateRender: false}}, {t + 0.15 + 0.22 * k});')
anim.append(f'tl.to("#zzz", {{opacity: 0, duration: 0.2}}, {E["sieste"] - 0.15});')
# Terra Madre
a, b, _ = PLAN_DE["terra-madre"]
add('      <div class="pastille" id="pa-tm"><div class="k">Turin · 27 septembre</div><div class="v">Terra Madre</div></div>')
montre("#pa-tm", a, b, "monte")
a, b, _ = PLAN_DE["escargot"]
add('      <div class="pastille" id="pa-sf"><div class="k">Slow Food</div><div class="v">le terroir à l\'honneur</div></div>')
montre("#pa-sf", a + 0.1, b, "monte")
# Via Roma : la plaque, puis « refaite »
a, b, _ = PLAN_DE["via-roma"]
add('      <div class="plaque" id="plaque"><div class="ville">Torino</div><div class="nom">Via Roma</div></div>')
add('      <div class="tampon" id="tampon">refaite</div>')
montre("#plaque", a + 0.05, b, "pop")
montre("#tampon", W("ils ont refait"), b, "pop")
# Vallee occitane
a, b, _ = PLAN_DE["vignes"]
add('      <div class="pastille" id="pa-oc"><div class="k">3 octobre</div><div class="v">Une vallée occitane</div></div>')
montre("#pa-oc", a + 0.1, b, "monte")
# Giaveno, Sagra dei Funghi
a, b, _ = PLAN_DE["giaveno"]
add('      <div class="pastille" id="pa-gi"><div class="k">4 octobre</div><div class="v">Giaveno</div></div>')
montre("#pa-gi", a + 0.05, b, "monte")
a, b, _ = PLAN_DE["sagra"]
add('      <div class="hook" id="sagra"><div class="eyebrow">Giaveno</div><h1 style="font-size:132px">Sagra <em>dei Funghi</em></h1></div>')
montre("#sagra", W("Sagra dei Funghi"), b, "monte")
# Le menu
a, b, _ = PLAN_DE["menu-fond"]
add('''      <div class="menu" id="menu"><div class="eyebrow">Sagra dei Funghi · Giaveno</div><h2>Au menu</h2>
        <div class="ligne" id="m1">Lasagne<span></span><small>aux champignons</small></div>
        <div class="ligne" id="m2">Salsiccia<span></span><small>la saucisse</small></div>
        <div class="etoiles" id="etoiles">exceptionnel ★★★</div></div>''')
montre("#menu", a + 0.05, b, "monte")
anim.append(f'tl.set("#m1", {{opacity: 1}}, {W("lasagne")}); tl.from("#m1", {{x: -30, duration: 0.3, ease: "power3.out"}}, {W("lasagne")});')
anim.append(f'tl.set("#m2", {{opacity: 1}}, {W("la salsiccia")}); tl.from("#m2", {{x: -30, duration: 0.3, ease: "power3.out"}}, {W("la salsiccia")});')
anim.append(f'tl.set("#etoiles", {{opacity: 1}}, {W("exceptionnel")}); tl.from("#etoiles", {{scale: 1.6, duration: 0.3, ease: "back.out(2)"}}, {W("exceptionnel")});')
# Pas de photo de plats : appareil barre
add('''      <svg class="pas-photo" id="pas-photo" viewBox="0 0 380 300"><rect x="20" y="70" width="340" height="210" rx="26" fill="#fff"/><rect x="120" y="36" width="120" height="50" rx="12" fill="#fff"/>
        <circle cx="190" cy="175" r="70" fill="none" stroke="#171719" stroke-width="16"/><circle cx="190" cy="175" r="30" fill="#171719"/>
        <line x1="40" y1="40" x2="340" y2="290" stroke="#0a36af" stroke-width="26" stroke-linecap="round"/></svg>''')
montre("#pas-photo", W("montrer des plats"), W("montrer des plats") + 1.6, "pop")
# Le vrai clocher
a, b, _ = PLAN_DE["clocher"]
add('      <div class="pastille" id="pa-cl"><div class="k">Cumiana</div><div class="v">le clocher</div></div>')
montre("#pa-cl", a + 0.05, b, "monte")
# Saint Francois de Sales
add('      <div class="plan" id="pl-francois"><div class="cadre"><img class="plein" src="assets/francois-de-sales.jpg" alt="" style="object-position:50% 20%" /></div></div>')
fa, fb = E["bulbe"], W("mais là non")
anim.append(f'tl.set("#pl-francois", {{opacity: 1}}, {fa}); tl.set("#pl-francois", {{opacity: 0}}, {fb}); tl.fromTo("#pl-francois .cadre", {{scale: 1.12}}, {{scale: 1.02, duration: {round(fb - fa, 3)}, ease: "none"}}, {fa});')
add('      <div class="bloc-nom" id="nom-fr"><div class="n">Saint François de Sales</div><div class="r">1567-1622 · patron des journalistes</div></div>')
add('      <div class="credit" id="credit-fr">Château de Bussy-Rabutin · domaine public</div>')
montre("#nom-fr", fa + 0.3, fb, "monte")
montre("#credit-fr", fa, fb)
add('      <div class="tampon" id="introuvable" style="left:300px;top:420px;font-size:64px">introuvable ici</div>')
montre("#introuvable", W("pas trouvé"), E["francois"], "pop")
# Le baroque
a, b, _ = PLAN_DE["baroque"]
add('      <div class="lieu-fin" id="baroque">l\'art<br><em>baroque</em></div>')
montre("#baroque", W("le baroque"), PLAN_DE["eglise-rue"][1], "monte")

# ------------------------------------------------------------------ Cartes
P = CARTE["pts"]
def cam(cx, cy, k):
    return {"x": round(540 - cx * k, 1), "y": round(960 - cy * k, 1), "scale": k}
def ecran(pt, cx, cy, k):
    return round(540 + (pt[0] - cx) * k, 1), round(960 + (pt[1] - cy) * k, 1)
SCENES = {
    "turin":   (P["Turin"][0], P["Turin"][1], 1.7, [("Turin", "")], "Piémont"),
    "vallees": (560, 990, 1.25, [], "Piémont · les vallées"),
    "giaveno": (640, 990, 3.2, [("Turin", "petit"), ("Giaveno", "gauche")], "Piémont"),
    "cumiana": (605, 1020, 4.2, [("Giaveno", "petit gauche"), ("Pinerolo", "petit gauche"), ("Cumiana", "")], "entre Giaveno et Pinerolo"),
}
for n, (a, b, sc) in enumerate(CARTES):
    cx, cy, k, pins, titre = SCENES[sc]
    cid = f"ca{n}"
    c = cam(cx, cy, k)
    elts = []
    for nom, cls in pins:
        x, y = ecran(P[nom], cx, cy, k)
        elts.append(f'<div class="pin {cls}" id="{cid}-{nom}" style="left:{x}px;top:{y}px"><i></i><b>{nom}</b></div>')
    if sc == "vallees":
        fx, fy = ecran(CARTE["fp"], cx, cy, k); ox, oy = ecran(CARTE["occ"], cx, cy, k); sx, sy = ecran(CARTE["savtxt"], cx, cy, k)
        elts.append(f'<div class="lueur" id="{cid}-l1" style="left:{fx - 170}px;top:{fy - 150}px;width:340px;height:300px;background:rgba(10,54,175,.55)"></div>')
        elts.append(f'<div class="lueur" id="{cid}-l2" style="left:{ox - 190}px;top:{oy - 170}px;width:380px;height:340px;background:rgba(214,40,40,.5)"></div>')
        elts.append(f'<div class="langue" id="{cid}-t1" style="left:{fx - 200}px;top:{fy - 40}px;color:#0a36af">vallées savoyardes</div>')
        elts.append(f'<div class="langue" id="{cid}-t2" style="left:{ox - 210}px;top:{oy - 30}px;color:#b01c1c">vallées occitanes</div>')
        elts.append(f'<div class="langue" id="{cid}-sav" style="left:{sx - 120}px;top:{sy - 30}px;color:#0a36af;font-size:56px;opacity:0">Savoie</div>')
        tx, ty = ecran(P["Turin"], cx, cy, k)
        elts.append(f'<div class="pin petit" id="{cid}-Turin" style="left:{tx}px;top:{ty}px"><i></i><b>Turin</b></div>')
    if sc == "cumiana":
        gx, gy = ecran(P["Giaveno"], cx, cy, k); px_, py_ = ecran(P["Pinerolo"], cx, cy, k)
        import math
        L = math.hypot(px_ - gx, py_ - gy); ang = math.degrees(math.atan2(py_ - gy, px_ - gx))
        elts.append(f'<div class="trait" id="{cid}-trait" style="left:{gx}px;top:{gy}px;width:{L:.0f}px;transform:rotate({ang:.1f}deg)"></div>')
    add(f'      <div class="carte" id="{cid}"><div class="cam" style="transform:translate({c["x"]}px,{c["y"]}px) scale({k})"><img src="assets/carte.svg" alt="" /></div>'
        f'<div class="titre">{html.escape(titre)}</div>{"".join(elts)}</div>')
    anim.append(f'tl.set("#{cid}", {{opacity: 1}}, {a}); tl.set("#{cid}", {{opacity: 0}}, {b});')
    anim.append(f'tl.fromTo("#{cid} .cam", {{scale: {k * 0.92}, x: {cam(cx, cy, k * 0.92)["x"]}, y: {cam(cx, cy, k * 0.92)["y"]}}}, {{scale: {k}, x: {c["x"]}, y: {c["y"]}, duration: 0.9, ease: "power2.out"}}, {a});')
    t0 = a + 0.35
    for j, (nom, cls) in enumerate(pins):
        t = t0 + 0.35 * j
        if sc == "cumiana" and nom == "Cumiana":
            t = W("Cumiana", 80)
        if sc == "giaveno" and nom == "Giaveno":
            t = max(t, W("à Giaveno") - 0.05)
        anim.append(f'tl.fromTo("#{cid}-{nom}", {{opacity: 0, scale: 0.4}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.4)", immediateRender: false}}, {round(t, 3)});')
    if sc == "vallees":
        anim.append(f'tl.fromTo("#{cid}-Turin", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {a + 0.3});')
        anim.append(f'tl.to("#{cid}-sav", {{opacity: 1, duration: 0.4}}, {a + 0.5});')
        anim.append(f'tl.to("#{cid}-l1", {{opacity: 1, duration: 0.6}}, {W("vallées savoyardes")}); tl.to("#{cid}-t1", {{opacity: 1, duration: 0.4}}, {W("vallées savoyardes")});')
        anim.append(f'tl.to("#{cid}-l2", {{opacity: 1, duration: 0.6}}, {W("vallées occitanes")}); tl.to("#{cid}-t2", {{opacity: 1, duration: 0.4}}, {W("vallées occitanes")});')
    if sc == "cumiana":
        anim.append(f'tl.fromTo("#{cid}-trait", {{opacity: 1, scaleX: 0}}, {{scaleX: 1, duration: 0.6, ease: "power2.inOut"}}, {W("Pinerolo") - 0.2});')
    if sc == "turin":
        add('      <div class="pastille" id="pa-turin" style="top:1120px"><div class="k">Le week-end dernier</div><div class="v">Terra Madre, Turin</div></div>')
        montre("#pa-turin", W("pour Terra Madre") - 0.05, b, "monte")

# ------------------------------------------------------------------ Le clocher demonte
X = 540
PIECES = [  # id, dessin SVG (centre x=540), deplacement quand il est demonte, etiquette, y de l'etiquette
    ("croix", '<line class="t" x1="540" y1="430" x2="540" y2="520"/><line class="t" x1="512" y1="458" x2="568" y2="458"/>', -210, "la croix", 470),
    ("lanterne", '<path class="t" d="M520 590 L520 540 Q540 516 560 540 L560 590 Z"/><line class="fin" x1="540" y1="548" x2="540" y2="580"/><path class="t" d="M532 516 Q540 500 548 516 Z"/>', -140, "le lanternon", 555),
    ("bulbe", '<path class="t bul" d="M452 790 C 400 740, 420 676, 486 640 C 516 622, 532 610, 540 590 C 548 610, 564 622, 594 640 C 660 676, 680 740, 628 790 Z"/><path class="fin" d="M496 790 C 470 740, 490 680, 540 600 M584 790 C 610 740, 590 680, 540 600"/>', -70, "le bulbe", 700),
    ("tambour", '<rect class="t" x="440" y="790" width="200" height="140"/><circle class="t" cx="540" cy="860" r="40"/><line class="fin" x1="540" y1="860" x2="540" y2="834"/><line class="fin" x1="540" y1="860" x2="560" y2="868"/><rect class="t" x="428" y="780" width="224" height="18"/>', 0, "l'horloge", 860),
    ("beffroi", '<rect class="t" x="420" y="930" width="240" height="250"/><path class="t" d="M490 1150 L490 1020 Q540 966 590 1020 L590 1150 Z"/><rect class="t" x="404" y="920" width="272" height="22"/><line class="fin" x1="430" y1="950" x2="430" y2="1170"/><line class="fin" x1="650" y1="950" x2="650" y2="1170"/>', 70, "les cloches", 1060),
    ("tour", '<rect class="t" x="430" y="1180" width="220" height="300"/><rect class="t" x="414" y="1170" width="252" height="20"/><rect class="fin" x="510" y="1260" width="60" height="110"/><line class="fin" x1="444" y1="1200" x2="444" y2="1470"/><line class="fin" x1="636" y1="1200" x2="636" y2="1470"/>', 140, "la tour", 1330),
]
svg = []
for pid, d, dy, lab, ly in PIECES:
    svg.append(f'<g id="cl-{pid}">{d}</g>')
    svg.append(f'<g id="et-{pid}" opacity="0"><line class="eti-l" x1="{700}" y1="{ly + dy}" x2="{800}" y2="{ly + dy}"/><text class="eti" x="812" y="{ly + dy + 12}">{html.escape(lab)}</text></g>')
# Comparaison : bulbe piemontais, bulbe savoyard
compar = ('<g id="cmp" opacity="0">'
          '<path class="t bul" d="M232 900 C 180 850, 200 786, 266 750 C 296 732, 312 720, 320 700 C 328 720, 344 732, 374 750 C 440 786, 460 850, 408 900 Z"/>'
          '<path class="t" d="M300 700 L300 660 Q320 640 340 660 L340 700 Z"/><line class="t" x1="320" y1="600" x2="320" y2="642"/>'
          '<text class="legende" x="320" y="1010" text-anchor="middle">Piémont</text>'
          '<path class="t bul" d="M660 900 C 640 860, 650 830, 700 812 C 728 802, 744 792, 760 770 C 776 792, 792 802, 820 812 C 870 830, 880 860, 860 900 Z"/>'
          '<rect class="t" x="738" y="728" width="44" height="42"/>'
          '<path class="t bul" d="M716 728 C 712 706, 730 694, 752 686 C 756 680, 758 676, 760 668 C 762 676, 764 680, 768 686 C 790 694, 808 706, 804 728 Z"/>'
          '<line class="t" x1="760" y1="610" x2="760" y2="668"/>'
          '<text class="legende" x="760" y="1010" text-anchor="middle">Savoie</text>'
          '<text class="legende" x="540" y="1180" text-anchor="middle" font-size="84">la même famille</text></g>')
add(f'      <div class="plan-bleu" id="clocher"><div class="grille"></div><div class="titre">Cumiana · le clocher, démonté</div>'
    f'<svg viewBox="0 0 1080 1920"><g transform="translate(135 260) scale(0.75)"><g id="cl-tout">{"".join(svg)}</g></g>{compar}</svg></div>')
ca, cb = W("le bulbe"), E["bulbe"]
cmp_t = W("la même famille") - 0.9
anim.append(f'tl.set("#clocher", {{opacity: 1}}, {ca}); tl.set("#clocher", {{opacity: 0}}, {cb});')
anim.append(f'tl.from("#cl-tout g[id^=cl-]", {{opacity: 0, y: 40, duration: 0.3, stagger: 0.06, ease: "power2.out"}}, {ca});')
for pid, d, dy, lab, ly in PIECES:
    anim.append(f'tl.to("#cl-{pid}", {{y: {dy}, duration: 0.7, ease: "power3.inOut"}}, {ca + 0.5});')
    anim.append(f'tl.to("#et-{pid}", {{opacity: 1, duration: 0.25}}, {ca + 1.0 + 0.08 * PIECES.index((pid, d, dy, lab, ly))});')
anim.append(f'tl.to("#cl-bulbe .bul", {{fill: "rgba(255,255,255,0.9)", duration: 0.4}}, {ca + 1.3});')
anim.append(f'tl.to("#cl-tout", {{opacity: 0, duration: 0.3}}, {cmp_t}); tl.to("#cmp", {{opacity: 1, duration: 0.4}}, {cmp_t + 0.2});')

# ------------------------------------------------------------------ Carton final
add(f'''      <div class="final" id="final"><div class="eyebrow">Weekends sagre</div><h2>Terra Madre et les sagre du Piémont</h2>
        <div class="lieux">Turin · Giaveno · Cumiana</div><div class="sig">Franck Monod</div><div class="abastou">abastou !</div></div>''')
anim.append(f'tl.set("#final", {{opacity: 1}}, {FIN_VOIX}); tl.from("#final .eyebrow, #final h2, #final .lieux, #final .sig, #final .abastou", {{y: 26, opacity: 0, duration: 0.5, stagger: 0.12, ease: "power3.out"}}, {FIN_VOIX + 0.05});')

# ------------------------------------------------------------------ Sous-titres
def dans(t, zones):
    return any(a - 0.01 <= t < b for a, b in zones)
for n, g in enumerate(ST):
    if dans(g["debut"], SANS_ST):
        continue
    mots = " ".join(f'<span class="m{" cle" if g["cle"] == m else ""}">{html.escape(m)}</span>' for m in g["mots"])
    clair = " clair" if dans(g["debut"], CLAIRS) else ""
    add(f'      <div class="st{clair}" id="st{n}">{mots}</div>')
    anim.append(f'tl.set("#st{n}", {{opacity: 1}}, {g["debut"]}); tl.from("#st{n}", {{scale: 0.86, duration: 0.14, ease: "back.out(2)"}}, {g["debut"]}); tl.set("#st{n}", {{opacity: 0}}, {g["fin"]});')

add('      <div id="flash"></div>')
anim.insert(0, 'tl.set("#flash", {opacity: 0}, 0);')
for t in FLASHS:
    anim.append(f'tl.fromTo("#flash", {{opacity: 0}}, {{opacity: 0.9, duration: 0.07, ease: "none", immediateRender: false}}, {round(t - 0.07, 3)}); tl.to("#flash", {{opacity: 0, duration: 0.35, ease: "power1.out"}}, {round(t, 3)});')
for t, k in PUNCHS:
    anim.append(f'tl.set("#face", {{scale: {k}}}, {round(t, 3)});')
# poussee lente du face camera entre deux punchs
add('''      <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
''' + "\n".join("      " + l for l in anim) + f'''
      tl.set({{}}, {{}}, {DUREE});
      window.__timelines["main"] = tl;
      </script>
    </div>
  </body>
</html>
''')
open("index.html", "w").write("\n".join(h))

# ------------------------------------------------------------------ Habillage sonore (musique + effets)
EFFETS = [  # (instant, fichier, volume)
    (0.02, "pop.wav", 0.5), (S["turin"] - 0.6 if False else E["sieste"] - 0.05, "whoosh2.wav", 0.45),
    (W("pour Terra Madre") - 0.05, "pop.wav", 0.35), (E["turin"] + 0.05, "pop.wav", 0.4), (W("ils ont refait"), "papier.wav", 0.45),
    (W("dans le Piémont", 44) - 0.05, "whoosh2.wav", 0.45), (W("vallées occitanes"), "ping.wav", 0.25),
    (E["vallees"] - 0.05, "whoosh2.wav", 0.45), (W("à Giaveno") - 0.05, "ping.wav", 0.3),
    (E["giaveno"] + 0.02, "papier.wav", 0.55), (W("lasagne"), "pop.wav", 0.35), (W("la salsiccia"), "pop.wav", 0.35),
    (W("exceptionnel"), "pop.wav", 0.45), (W("montrer des plats"), "declencheur.wav", 0.6),
    (E["influenceur"] - 0.05, "whoosh2.wav", 0.45), (W("Cumiana", 80), "ping.wav", 0.3), (E["cumiana"], "declencheur.wav", 0.5),
    (W("le bulbe") + 0.5, "whoosh1.wav", 0.35), (E["bulbe"], "declencheur.wav", 0.55), (W("pas trouvé"), "pop.wav", 0.45),
    (FIN_VOIX - 2.4, "riser.wav", 0.35),
]
AMBIANCES = [(PLAN_DE["village"][0], PLAN_DE["marche"][1]), (PLAN_DE["giaveno"][0], PLAN_DE["sagra"][1])]
entrees = ["-i", os.path.join(SONS, "musique-wind-leaves.mp3"), "-i", os.path.join(SONS, "foule.wav")]
f = []
# Musique : environ 16 dB sous la voix, remonte sur le carton final
f.append(f"[0:a]atrim=0:{DUREE},asetpts=PTS-STARTPTS,volume='if(lt(t,{FIN_VOIX - 0.3}),0.09,0.09+min(1,(t-{FIN_VOIX - 0.3})/0.8)*0.33)':eval=frame,"
         f"afade=t=in:d=0.6,afade=t=out:st={DUREE - 1.4}:d=1.4[mus]")
amb = []
for i, (a, b) in enumerate(AMBIANCES):
    f.append(f"[1:a]atrim=5:{5 + b - a},asetpts=PTS-STARTPTS,volume=0.10,afade=t=in:d=0.3,afade=t=out:st={max(0, b - a - 0.4)}:d=0.4,adelay={int(a * 1000)}:all=1[amb{i}]")
    amb.append(f"[amb{i}]")
fx = []
for i, (t, fic, vol) in enumerate(EFFETS):
    entrees += ["-i", os.path.join(SONS, fic)]
    f.append(f"[{2 + i}:a]aresample=48000,volume={vol},adelay={int(max(0, t) * 1000)}:all=1[fx{i}]")
    fx.append(f"[fx{i}]")
tous = "[mus]" + "".join(amb) + "".join(fx)
f.append(f"{tous}amix=inputs={1 + len(amb) + len(fx)}:normalize=0:duration=first,atrim=0:{DUREE}[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", ";".join(f), "-map", "[out]", "-ar", "48000", "-ac", "2",
                "-c:a", "aac", "-b:a", "192k", "assets/habillage.m4a"], check=True)
print(f"index.html : {DUREE} s, {len(PLANS)} plans, {len(CARTES)} cartes, {len(ST)} groupes de sous-titres ; habillage {len(EFFETS)} effets")
