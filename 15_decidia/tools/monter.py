"""Écrit le montage HyperFrames (index.html) et sa feuille de temps (plan.json, lue par tools/bande-son.py).

Style « Reportage Franck » (styles/reportage-franck.md et 04_montage/BONNES-PRATIQUES.md, branche HyperFrames),
repris de 10_cern/index.html : bleu Savoie seul accent, Semplicità Pro, Cormorant Garamond pour les titres de lieu
et le remerciement, sous-titres par groupes avec un mot-clé en bloc bleu et un petit « pop », flash blanc,
punch-in, poussée lente, cercle qui se dessine, bandeau nom.

Tous les temps viennent de la voix : les mots-ancres sont donnés en secondes de la prise (rushes/15_oct.__15.18.aac),
convertis en temps du montage par voix-montee.json (tools/couper-voix.py) puis divisés par la vitesse (montage.json).
Usage (dans 15_decidia/) : python3 tools/monter.py"""
import json
from html import escape

VOIX = json.load(open("voix-montee.json"))
VITESSE = json.load(open("montage.json"))["vitesse"]
DUREES = json.load(open("assets/durees.json"))
PH = {p["id"]: p for p in VOIX["phrases"]}

def montage(s):
    """Temps de la prise -> temps de la voix montée (avant accélération)."""
    coupes = VOIX["coupes"]
    for c in coupes:
        (x, y), (m, _) = c["source"], c["montage"]
        if s <= y: return m + max(0.0, s - x)
    return coupes[-1]["montage"][1]

# ---------------------------------------------------------------- feuille de temps (secondes de la vidéo)
HOOK = 1.90                                  # accroche sur l'accueil exposants
DUO = DUREES["duo"]                          # le duo salue, son direct
VA = HOOK + DUO                              # début de la voix off (phrases 1 à 5)
fin_a = PH["cycle"]["fin"] / VITESSE         # fin de la phrase 5 dans la voix accélérée
debut_b, fin_b = PH["merci"]["debut"] / VITESSE, PH["merci"]["fin"] / VITESSE

def t(s):
    """Mot-ancre (secondes de la prise, phrases 1 à 5) -> temps de la vidéo."""
    return round(VA + montage(s) / VITESSE, 3)

RIOULE = round(VA + fin_a + 0.35, 3)
R1, R2, R3 = DUREES["rioule-1"], DUREES["rioule-2"], DUREES["rioule-3"]
MERCI = round(RIOULE + R1 + R2 + R3, 3)
VB = round(MERCI + 0.35, 3)                  # « Grant-marci a Rony é a tô »
BIENTOT = round(VB + (fin_b - debut_b) + 0.45, 3)
FIN = round(BIENTOT + DUREES["bientot"], 3)
TOTAL = round(FIN + 4.2, 3)

def tb(s):
    """Mot-ancre de la phrase 6 (merci) -> temps de la vidéo."""
    return round(VB + montage(s) / VITESSE - debut_b, 3)

# Plans : (id, début, fin). Une coupe, un zoom ou un titre toutes les 1 à 3 s : c'est le rythme demandé.
P = {
    "hook": (0.0, HOOK),
    "duo": (HOOK, VA),
    "allee": (VA, t(3.42)),                  # « Aujourd'hui, j'étais au salon »
    "accueil": (t(3.42), t(4.86)),           # « Dècidia » : les comptoirs aux couleurs du salon
    "frenchtech": (t(4.86), t(5.80)),        # « avec la French Tech »
    "savoyia": (t(5.80), t(7.20)),           # « et Savoy IA »
    "affiche": (t(7.20), t(8.72)),           # « pour une conférence »
    "salle": (t(8.72), t(11.02)),            # « sur l'intelligence artificielle »
    "entreprises": (t(11.02), t(12.95)),     # « adaptée » : le stand du club de handball
    "cabine": (t(12.95), t(15.40)),          # « à l'entreprise »
    "stand": (t(15.40), t(16.80)),           # « c'est utiliser la capacité »
    "scene": (t(16.80), t(18.40)),           # « les compétences métiers avant tout »
    "couches": (t(18.40), t(26.05)),         # « et ajouter l'IA en plus, pour une couche supplémentaire »
    "public": (t(26.05), t(28.36)),          # « nous avons parlé »
    "cycle": (t(28.36), RIOULE),             # « de tout le cycle, marketing et communication »
    "rioule": (RIOULE, MERCI),
    "merci": (MERCI, BIENTOT),
    "bientot": (BIENTOT, FIN),
    "fin": (FIN, TOTAL),
}

for k, (a, b) in P.items():   # un plan filmé ne doit pas durer plus que son extrait (image figée sinon)
    if k in DUREES and b - a > DUREES[k] + 0.02:
        raise SystemExit(f"plan « {k} » : {b - a:.2f} s à l'écran pour {DUREES[k]:.2f} s d'extrait (preparer-medias.py)")

# Sous-titres de la voix off : traduction de Franck, par groupes de 1 à 3 mots (mot-clé entre crochets).
# Temps de début en secondes de la prise ; chaque groupe reste jusqu'au suivant (ou 0,6 s après une pause).
ST_VOIX = [
    ("Aujourd'hui", 1.31), ("j'étais au salon", 2.29), ("[Décidia]", 3.42), ("avec la French Tech", 4.90),
    ("et Savoy IA", 5.80), (None, 6.54),
    ("pour une conférence", 7.32), ("sur l'intelligence", 8.72), ("artificielle", 9.80), (None, 11.02),
    ("adaptée", 11.87), ("à [l'entreprise]", 12.95), (None, 14.18),
    # Phrase rapide (2,2 s) : deux groupes, sinon plus de 25 car./s. « utiliser la capacité » est resserré.
    ("Les [compétences métiers]", 15.52), ("avant tout", 16.95),
    (None, 17.96),
    ("et ajouter", 18.49), ("l'intelligence", 19.52), ("artificielle", 20.46), (None, 21.47),
    ("en plus", 22.00), ("pour une [couche]", 22.56), ("supplémentaire", 23.62), (None, 24.85),
    ("Nous avons parlé", 26.05), ("de tout le cycle", 28.36), (None, 29.84),
    # « marketing » et « communication » claquent au centre du cycle : pas de sous-titre qui répète.
]
# Plans en son direct (français) : temps dans le plan, depuis la transcription.
ST_DIRECT = [
    ("Alors Rony", RIOULE + 0.09), ("tu sais ce que", RIOULE + 0.77), ("ça veut dire la [rioule] ?", RIOULE + 1.39), ("C'est faire la fête", RIOULE + R1 + 0.08),
    ("la [bambouche] !", RIOULE + R1 + 1.18), ("Exactement, bravo !", RIOULE + R1 + R2 + 0.02),
    (None, MERCI),
    ("À bientôt !", BIENTOT + 1.15), (None, FIN),
]
CLAIRS = {"couches", "cycle"}   # plans clairs : texte sombre (BONNES-PRATIQUES, section 2)

def groupes():
    out, liste = [], [(txt, t(s)) for txt, s in ST_VOIX] + [(None, t(29.84) + 0.6)] + ST_DIRECT
    for i, (txt, a) in enumerate(liste):
        if txt is None: continue
        b = liste[i + 1][1] if i + 1 < len(liste) else a + 1.0
        b = min(b, a + 2.6)
        plan = next((k for k, (x, y) in P.items() if x - 1e-6 <= a < y), "")
        out.append((txt, round(a, 3), round(b - 0.02, 3), plan in CLAIRS))
    return out

def html_groupe(txt):
    parts, html = txt.replace("]", "[").split("["), []
    for k, p in enumerate(parts):
        if not p.strip(): continue
        cls = "m cle" if k % 2 else "m"
        html.append(f'<span class="{cls}">{escape(p.strip())}</span>')
    return " ".join(html)

ST_HTML = "\n".join(
    f'      <div class="st{" clair" if clair else ""}" data-a="{a}" data-b="{b}">{html_groupe(txt)}</div>'
    for txt, a, b, clair in groupes())

def media(id_, src, plan, media_start=0.0, cls="plein"):
    a, b = P[plan]
    return (f'<video id="{id_}" class="{cls}" src="{src}" muted playsinline data-start="{a}" '
            f'data-duration="{round(b - a, 3)}" data-media-start="{media_start}"></video>')

def img(id_, src, plan):
    a, b = P[plan]
    return (f'<img id="{id_}" class="clip photo" src="{src}" width="1440" height="1920" alt="" '
            f'data-start="{a}" data-duration="{round(b - a, 3)}" />')

r_a = P["rioule"][0]
TEMPS = {k: [round(a, 3), round(b, 3)] for k, (a, b) in P.items()}
plan_json = {
    "total": TOTAL, "plans": TEMPS,
    "voix": {"debut_a": VA, "fin_a": round(fin_a, 3), "debut_b_voix": round(debut_b, 3),
             "fin_b_voix": round(fin_b, 3), "debut_b": VB},
    "direct": {"duo": [HOOK, "assets/duo.wav"], "rioule-1": [r_a, "assets/rioule-1.wav"],
               "rioule-2": [round(r_a + R1, 3), "assets/rioule-2.wav"],
               "rioule-3": [round(r_a + R1 + R2, 3), "assets/rioule-3.wav"],
               "bientot": [BIENTOT, "assets/bientot.wav"]},
    "ancres": {"frenchtech_logo": t(4.95), "savoyia_logo": t(5.86), "carte_a": round(P["couches"][0] + 0.15, 3),
               "carte_b": t(19.52), "couche": t(22.56), "cycle": round(P["cycle"][0] + 0.05, 3),
               "marketing": t(30.68), "communication": t(31.66), "rioule": round(r_a + 1.71, 3)},
}
A = plan_json["ancres"]

HTML = f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>Décidia 2026 : l'humain garde la main</title>
    <!-- Fichier écrit par tools/monter.py : modifier le script, pas ce fichier. -->
    <script src="assets/gsap.min.js"></script>
    <link rel="stylesheet" href="brand/tokens.css" />
    <style>
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro.woff') format('woff'); font-weight: 400; }}
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro-Semibold.woff') format('woff'); font-weight: 600; }}
      @font-face {{ font-family: 'Semplicita Pro'; src: url('assets/fonts/SemplicitaPro-Bold.woff') format('woff'); font-weight: 700; }}
      @font-face {{ font-family: 'Cormorant Garamond'; src: url('assets/fonts/CormorantGaramond-Medium.woff2') format('woff2'); font-weight: 500; font-style: normal; }}
      @font-face {{ font-family: 'Cormorant Garamond'; src: url('assets/fonts/CormorantGaramond-Italic.woff2') format('woff2'); font-weight: 500; font-style: italic; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #000; font-family: var(--fm-font); color: var(--fm-ink-900); }}
      .plan {{ position: absolute; inset: 0; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; }}
      video.plein {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      .cadre {{ overflow: hidden; }}
      img.photo {{ position: absolute; left: -180px; top: 0; width: 1440px; height: 1920px; inset: auto; }}

      /* Accroche : les mots claquent un a un (bibliotheque : hook-mots) */
      #voile-hook {{ position: absolute; left: 0; right: 0; top: 0; height: 900px; background: linear-gradient(rgba(10,14,30,0.72) 0%, rgba(10,14,30,0.5) 45%, rgba(10,14,30,0) 100%); }}
      .hook {{ position: absolute; left: 70px; right: 70px; top: 300px; font-size: 104px; font-weight: 700; line-height: 1.22; letter-spacing: -0.01em; color: #fff; text-shadow: 0 0 8px rgba(0,0,0,0.6), 0 4px 24px rgba(0,0,0,0.5); }}
      .hook .w {{ display: inline-block; }}
      .hook .b {{ background: var(--fm-bleu-savoie); padding: 0 16px; text-shadow: none; }}

      /* Bandeau nom (bibliotheque : bandeau-nom) */
      .bloc-nom {{ position: absolute; left: 60px; top: 270px; background: var(--fm-bleu-savoie); color: #fff; padding: 22px 32px 24px; }}
      .bloc-nom .n {{ font-size: 52px; font-weight: 700; line-height: 1.1; }}
      .bloc-nom .r {{ margin-top: 8px; font-size: 24px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; }}

      /* Pastille posee sur une image */
      .pastille {{ position: absolute; left: 60px; right: 200px; top: 280px; background: var(--fm-bg); padding: 22px 28px 26px; }}
      .pastille .k {{ font-size: 24px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .pastille .v {{ margin-top: 8px; font-size: 54px; font-weight: 700; line-height: 1.12; }}

      /* Logos des partenaires */
      .carte-logo {{ position: absolute; left: 270px; top: 560px; width: 540px; background: #fff; padding: 26px 30px 18px; box-shadow: 0 30px 70px rgba(0,0,0,0.35); }}
      .carte-logo img {{ display: block; width: 480px; height: auto; }}
      #p-savoyia {{ background: radial-gradient(circle at 50% 42%, #0b1a4a 0%, #05091f 55%, #020512 100%); }}
      #sia-anneau {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
      #sia-logo {{ position: absolute; left: 240px; top: 470px; width: 600px; height: 600px; }}

      /* Titre de lieu : serif fine, lignes qui montent */
      .lieu-fin {{ position: absolute; left: 80px; top: 300px; color: #fff; font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; font-size: 96px; line-height: 1.02; text-shadow: 0 0 4px rgba(0,0,0,0.75), 0 2px 24px rgba(0,0,0,0.75); }}
      .lieu-fin .l {{ display: block; overflow: hidden; padding-bottom: 6px; }}
      .lieu-fin .l > span {{ display: inline-block; }}
      .lieu-fin em {{ font-style: italic; }}
      #bague {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
      #bague circle {{ fill: none; stroke-linecap: round; }}

      /* La couche en plus : les competences metiers d'abord, l'IA posee dessus */
      #p-couches {{ background: var(--fm-bg-soft); perspective: 1800px; }}
      #couches-titre {{ position: absolute; left: 90px; top: 290px; font-size: 30px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      #pile {{ position: absolute; left: 140px; top: 640px; width: 800px; height: 560px; transform-style: preserve-3d; }}
      .couche {{ position: absolute; left: 0; width: 800px; height: 300px; padding: 40px 48px; display: flex; flex-direction: column; justify-content: center; }}
      .couche .k {{ font-size: 26px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; }}
      .couche .v {{ margin-top: 12px; font-size: 76px; font-weight: 700; line-height: 1.02; letter-spacing: -0.01em; }}
      #couche-metier {{ top: 260px; background: #fff; border: 3px solid var(--fm-ink-900); color: var(--fm-ink-900); }}
      #couche-metier .k {{ color: var(--fm-ink-500); }}
      #couche-ia {{ top: 0; background: var(--fm-bleu-savoie); color: #fff; box-shadow: 0 30px 60px rgba(10, 54, 175, 0.35); }}

      /* Tout le cycle, en motion design : l'anneau eclot ; les cinq etapes du cycle de vie client (d'apres
         clustdoc.com) claquent au centre, chacune avec son entree, puis volent a leur place sur l'anneau, une comete
         les suit ; « marketing » puis « communication » claquent ; le cycle file vers la camera. */
      #p-cycle {{ background: var(--fm-bg); }}
      #cycle-monde {{ position: absolute; inset: 0; transform-origin: 500px 860px; }}
      #cycle-svg {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: visible; }}
      #cycle-svg .anneau {{ fill: none; stroke: var(--fm-bleu-savoie); stroke-width: 16; stroke-linecap: round; }}
      #cycle-svg .fond {{ fill: none; stroke: #e6ebf7; stroke-width: 16; }}
      #cycle-svg .noeud {{ fill: var(--fm-bleu-savoie); stroke: #fff; stroke-width: 5; }}
      #cycle-svg .comete {{ fill: #fff; stroke: var(--fm-bleu-savoie); stroke-width: 7; }}
      #cycle-centre {{ position: absolute; left: 200px; width: 600px; top: 768px; text-align: center; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500; font-size: 96px; line-height: 0.96; color: var(--fm-ink-900); }}
      .etape {{ position: absolute; left: 500px; top: 860px; background: var(--fm-bleu-savoie); color: #fff; font-size: 100px; font-weight: 700; padding: 18px 44px 26px; white-space: nowrap; }}
      .slam {{ position: absolute; left: 500px; top: 925px; background: var(--fm-bleu-savoie); color: #fff; font-size: 66px; font-weight: 700; padding: 8px 28px 14px; white-space: nowrap; }}
      .credit-noir {{ position: absolute; right: 24px; top: 262px; font-size: 20px; color: var(--fm-ink-700); background: rgba(255,255,255,0.85); padding: 3px 8px; }}

      /* Remerciement en savoyard */
      .merci {{ position: absolute; left: 70px; right: 70px; top: 300px; background: rgba(255,255,255,0.93); padding: 40px 50px 46px; }}
      .merci .l {{ overflow: hidden; }}
      .merci .l > span {{ display: inline-block; font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; font-style: italic; font-size: 150px; line-height: 1.05; color: var(--fm-bleu-savoie); white-space: nowrap; }}
      .merci p {{ margin-top: 18px; font-size: 52px; font-weight: 700; line-height: 1.2; }}
      .merci .sav {{ margin-top: 10px; font-size: 26px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--fm-ink-500); }}

      /* Carton final */
      #p-final {{ background: var(--fm-bg); }}
      .relire {{ position: absolute; left: 90px; right: 150px; top: 300px; }}
      .relire .eyebrow {{ font-size: 28px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--fm-bleu-savoie); }}
      .relire h2 {{ margin-top: 16px; font-size: 80px; font-weight: 700; line-height: 1.04; letter-spacing: -0.01em; }}
      .relire h2 .l {{ display: block; overflow: hidden; padding-bottom: 6px; }}
      .relire h2 .l > span {{ display: inline-block; }}
      .relire h2 em {{ font-style: normal; color: var(--fm-bleu-savoie); }}
      .relire .date {{ margin-top: 20px; font-size: 34px; font-weight: 600; color: var(--fm-ink-700); }}
      .logos {{ position: absolute; left: 60px; right: 150px; top: 760px; display: flex; align-items: center; justify-content: space-between; }}
      .logos .ft {{ width: 480px; height: auto; display: block; }}
      .logos .sia {{ width: 340px; height: 340px; display: flex; align-items: center; justify-content: center; }}
      .logos .sia img {{ width: 300px; height: 300px; display: block; }}
      .bloc-final {{ position: absolute; left: 90px; top: 1190px; background: var(--fm-bleu-savoie); color: #fff; padding: 22px 34px 26px; }}
      .bloc-final .n {{ font-size: 48px; font-weight: 700; line-height: 1.1; }}
      .bloc-final .r {{ margin-top: 8px; font-size: 24px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; }}

      /* Sous-titres : groupes de 1 a 3 mots, au-dessus de l'interface des Reels (y < 1440, x < 940) */
      .st {{ position: absolute; left: 60px; right: 140px; bottom: 490px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 4px 18px; transform-origin: 50% 100%; opacity: 0; }}
      .st {{ font-size: 66px; font-weight: 700; line-height: 1.2; color: #fff; text-shadow: 0 0 8px rgba(0,0,0,0.9), 0 3px 18px rgba(0,0,0,0.6); }}
      .st.clair {{ color: var(--fm-ink-900); text-shadow: 0 0 10px rgba(255,255,255,0.9); }}
      .st .m {{ display: inline-block; white-space: nowrap; }}
      .st .m.cle {{ font-size: 1.3em; background: var(--fm-bleu-savoie); color: #fff; padding: 0 16px 4px; text-shadow: none; }}

      /* Flash blanc sur les changements de sequence (bibliotheque : flash-blanc) */
      #flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; pointer-events: none; z-index: 5; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">

      <!-- Bande-son mixee (tools/bande-son.py) : voix off, son direct, musique, ambiance du salon, effets -->
      <audio id="bande-son" src="assets/bande-son.wav" data-start="0" data-duration="{TOTAL}" data-volume="1"></audio>

      <!-- Accroche : l'accueil exposants de Decidia -->
      {media("v-hook", "assets/hook.mp4", "hook")}
      <div id="voile-hook"></div>
      <div class="hook" id="hook"><span class="w">L'IA ?</span> <span class="w">L'humain</span> <span class="w">garde</span> <span class="w">la</span> <span class="w b">main</span></div>

      <!-- Franck et Rony saluent (son direct) -->
      {media("v-duo", "assets/duo.mp4", "duo")}
      <div class="bloc-nom" id="nom"><div class="n">Franck Monod &amp; Rony Dray</div><div class="r">Atelier Décidia · 15 octobre 2026</div></div>

      <!-- Phrase 1 : le salon, la French Tech, Savoy IA -->
      {media("v-allee", "assets/allee.mp4", "allee")}
      {media("v-accueil", "assets/accueil.mp4", "accueil")}
      {media("v-frenchtech", "assets/frenchtech.mp4", "frenchtech")}
      <div class="carte-logo" id="logo-ft"><img src="assets/logos/french-tech-alpes.svg" width="480" height="393" alt="La French Tech Alpes" /></div>
      <div class="plan" id="p-savoyia">
        <svg id="sia-anneau" viewBox="0 0 1080 1920"><circle id="sia-onde" cx="540" cy="725" r="215" fill="none" stroke="#2f7bff" stroke-width="6" /></svg>
        <img id="sia-logo" src="assets/logos/savoy-ia-detoure.png" width="600" height="600" alt="Savoy IA" />
      </div>

      <!-- Phrase 2 : la conference, l'entreprise -->
      {media("v-affiche", "assets/affiche.mp4", "affiche")}
      {img("photo-salle", "assets/photo-6.jpg", "salle")}
      <div class="pastille" id="pastille-atelier"><div class="k">Atelier · salle Lamartine</div><div class="v">Vendre mieux avec l'IA : l'humain garde la main</div></div>
      {media("v-entreprises", "assets/entreprises.mp4", "entreprises")}
      <div class="pastille" id="pastille-club"><div class="k">Hall A · stand A84</div><div class="v">Chambéry Savoie Mont Blanc Handball</div></div>
      {media("v-cabine", "assets/cabine.mp4", "cabine")}
      <div class="pastille" id="pastille-cabine"><div class="k">Sur le salon</div><div class="v">Téléphérique du Salève</div></div>

      <!-- Phrase 3 : les competences metiers -->
      {media("v-stand", "assets/stand.mp4", "stand")}
      {img("photo-scene", "assets/photo-5.jpg", "scene")}

      <!-- Phrase 4 : l'IA, une couche en plus -->
      <div class="plan" id="p-couches">
        <div id="couches-titre">D'abord le métier</div>
        <div id="pile">
          <div class="couche" id="couche-metier"><div class="k">La base</div><div class="v">Compétences métiers</div></div>
          <div class="couche" id="couche-ia"><div class="k">La couche en plus</div><div class="v">Intelligence artificielle</div></div>
        </div>
      </div>

      <!-- Phrase 5 : tout le cycle, marketing et communication -->
      {img("photo-public", "assets/photo-9.jpg", "public")}
      <div class="plan" id="p-cycle" data-layout-allow-overlap>
        <div id="cycle-monde">
          <svg id="cycle-svg" viewBox="0 0 1080 1920">
            <circle class="fond" cx="500" cy="860" r="300" />
            <circle class="anneau" id="cycle-anneau" cx="500" cy="860" r="300" pathLength="1" transform="rotate(-90 500 860)" />
            <circle class="noeud" id="n0" cx="500" cy="560" r="0" />
            <circle class="noeud" id="n1" cx="785" cy="767" r="0" />
            <circle class="noeud" id="n2" cx="676" cy="1103" r="0" />
            <circle class="noeud" id="n3" cx="324" cy="1103" r="0" />
            <circle class="noeud" id="n4" cx="215" cy="767" r="0" />
            <circle class="comete" id="cycle-comete" cx="500" cy="560" r="16" />
          </svg>
          <div id="cycle-centre">Tout<br />le cycle</div>
          <div class="etape" id="e0">Attraction</div>
          <div class="etape" id="e1">Acquisition</div>
          <div class="etape" id="e2">Développement</div>
          <div class="etape" id="e3">Fidélisation</div>
          <div class="etape" id="e4">Réactivation</div>
          <div class="slam" id="slam-marketing">Marketing</div>
          <div class="slam" id="slam-communication">Communication</div>
        </div>
        <div class="credit-noir">Étapes du cycle de vie client d'après clustdoc.com</div>
      </div>

      <!-- Au detour d'un stand : la rioule (son direct) -->
      <video id="v-rioule-1" class="plein" src="assets/rioule-1.mp4" muted playsinline data-start="{r_a}" data-duration="{R1}" data-media-start="0"></video>
      <video id="v-rioule-2" class="plein" src="assets/rioule-2.mp4" muted playsinline data-start="{round(r_a + R1, 3)}" data-duration="{R2}" data-media-start="0"></video>
      <video id="v-rioule-3" class="plein" src="assets/rioule-3.mp4" muted playsinline data-start="{round(r_a + R1 + R2, 3)}" data-duration="{R3}" data-media-start="0"></video>
      <div class="lieu-fin" id="titre-stand"><span class="l"><span>Au détour</span></span><span class="l"><span>d'un <em>stand</em>…</span></span></div>
      <svg id="bague" viewBox="0 0 1080 1920"><circle class="b-fond" cx="790" cy="490" r="200" stroke="#ffffff" stroke-width="12" pathLength="1" /><circle class="b-trait" cx="790" cy="490" r="200" stroke="#0a36af" stroke-width="6" pathLength="1" /></svg>

      <!-- Grant-marci : la scene de l'atelier -->
      {img("photo-merci", "assets/photo-7.jpg", "merci")}
      <div class="plan" id="p-merci">
        <div class="merci">
          <div class="l"><span>Grant-marci</span></div>
          <p>à Rony et à tous !</p>
          <div class="sav">« Merci », en savoyard</div>
        </div>
      </div>

      <!-- A bientot (son direct) -->
      {media("v-bientot", "assets/bientot.mp4", "bientot")}

      <!-- Carton final -->
      <div class="plan" id="p-final">
        <div class="relire">
          <div class="eyebrow">Décidia 2026 · Savoiexpo, Chambéry</div>
          <h2><span class="l"><span>Vendre mieux</span></span><span class="l"><span>avec l'IA :</span></span><span class="l"><span>l'<em>humain</em> garde la main</span></span></h2>
          <div class="date">Atelier du 15 octobre 2026</div>
        </div>
        <div class="logos">
          <img class="ft" id="fin-ft" src="assets/logos/french-tech-alpes.svg" width="480" height="393" alt="La French Tech Alpes" />
          <div class="sia" id="fin-sia"><img src="assets/logos/savoy-ia-clair.png" width="330" height="330" alt="Savoy IA" /></div>
        </div>
        <div class="bloc-final" id="fin-nom"><div class="n">Franck Monod · Rony Dray</div><div class="r">avec la French Tech Alpes et Savoy IA</div></div>
      </div>

      <div id="flash"></div>

      <!-- Sous-titres (traduction de la voix off en savoyard ; son direct en français) -->
{ST_HTML}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      const P = {json.dumps(TEMPS)};
      const A = {json.dumps(A)};
      const montre = (sel, plan) => {{ tl.set(sel, {{ opacity: 1 }}, P[plan][0]); tl.set(sel, {{ opacity: 0 }}, P[plan][1]); }};
      const flash = (t) => {{
        tl.fromTo("#flash", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.07, ease: "none", immediateRender: false }}, t - 0.07);
        tl.to("#flash", {{ opacity: 0, duration: 0.35, ease: "power2.out" }}, t);
      }};
      gsap.set(["#pastille-club", "#pastille-cabine"], {{ opacity: 0 }});
      gsap.set(["#hook", "#voile-hook", "#nom", "#logo-ft", "#p-savoyia", "#pastille-atelier", "#p-couches", "#p-cycle", "#titre-stand",
                "#bague", "#p-merci", "#p-final"], {{ opacity: 0 }});

      // Accroche (0 - {HOOK} s) : les mots claquent un a un, poussee lente sur l'accueil.
      tl.set(["#hook", "#voile-hook"], {{ opacity: 1 }}, 0);
      tl.from("#hook .w", {{ scale: 0.6, opacity: 0, duration: 0.28, ease: "back.out(2.2)", stagger: 0.12 }}, 0.08);
      tl.fromTo("#v-hook", {{ scale: 1.0 }}, {{ scale: 1.08, duration: {HOOK}, ease: "none" }}, 0);
      tl.set(["#hook", "#voile-hook"], {{ opacity: 0 }}, {HOOK});

      // Le duo : bandeau nom de gauche a droite.
      gsap.set("#v-duo", {{ transformOrigin: "50% 30%" }});
      tl.fromTo("#v-duo", {{ scale: 1.0 }}, {{ scale: 1.05, duration: {DUO}, ease: "none" }}, P.duo[0]);
      tl.set("#nom", {{ opacity: 1 }}, P.duo[0] + 0.25);
      tl.fromTo("#nom", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "power3.inOut", immediateRender: false }}, P.duo[0] + 0.25);
      tl.set("#nom", {{ opacity: 0 }}, P.duo[1]);

      // Allee du salon, puis coupe sur « Decidia » : les comptoirs du salon.
      gsap.set(["#v-allee", "#v-accueil"], {{ transformOrigin: "50% 45%" }});
      tl.fromTo("#v-allee", {{ scale: 1.0 }}, {{ scale: 1.05, duration: P.allee[1] - P.allee[0], ease: "none" }}, P.allee[0]);
      tl.fromTo("#v-accueil", {{ scale: 1.14 }}, {{ scale: 1.06, duration: P.accueil[1] - P.accueil[0], ease: "none" }}, P.accueil[0]);

      // French Tech : le stand, puis le logo qui saute.
      gsap.set("#v-frenchtech", {{ transformOrigin: "45% 40%" }});
      tl.fromTo("#v-frenchtech", {{ scale: 1.25 }}, {{ scale: 1.32, duration: P.frenchtech[1] - P.frenchtech[0], ease: "none" }}, P.frenchtech[0]);
      tl.set("#logo-ft", {{ opacity: 1 }}, A.frenchtech_logo);
      tl.fromTo("#logo-ft", {{ scale: 0.6, y: 60 }}, {{ scale: 1, y: 0, duration: 0.35, ease: "back.out(2.2)", immediateRender: false }}, A.frenchtech_logo);
      tl.set("#logo-ft", {{ opacity: 0 }}, P.frenchtech[1]);

      // Savoy IA : la sphere arrive, une onde s'en echappe (le cercle du collectif).
      montre("#p-savoyia", "savoyia");
      tl.fromTo("#sia-logo", {{ scale: 0.55, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.8)", immediateRender: false }}, A.savoyia_logo);
      tl.fromTo("#sia-logo", {{ scale: 1 }}, {{ scale: 1.06, duration: P.savoyia[1] - A.savoyia_logo - 0.45, ease: "none", immediateRender: false }}, A.savoyia_logo + 0.45);
      gsap.set("#sia-onde", {{ transformOrigin: "540px 725px", opacity: 0 }});
      tl.fromTo("#sia-onde", {{ scale: 1, opacity: 0.9 }}, {{ scale: 2.6, opacity: 0, duration: 1.1, ease: "power2.out", immediateRender: false }}, A.savoyia_logo + 0.15);

      // Programme des conferences.
      gsap.set("#v-affiche", {{ transformOrigin: "60% 30%" }});
      tl.fromTo("#v-affiche", {{ scale: 1.12 }}, {{ scale: 1.2, duration: P.affiche[1] - P.affiche[0], ease: "none" }}, P.affiche[0]);

      // La salle : poussee lente, titre de l'atelier.
      tl.fromTo("#photo-salle", {{ scale: 1.0, x: 0 }}, {{ scale: 1.1, x: -40, duration: P.salle[1] - P.salle[0], ease: "none" }}, P.salle[0]);
      tl.set("#pastille-atelier", {{ opacity: 1 }}, P.salle[0] + 0.2);
      tl.fromTo("#pastille-atelier", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "power3.inOut", immediateRender: false }}, P.salle[0] + 0.2);
      tl.set("#pastille-atelier", {{ opacity: 0 }}, P.salle[1]);

      // Les entreprises du salon : un stand, puis la cabine du Teleferique du Saleve.
      gsap.set(["#v-entreprises", "#v-cabine"], {{ transformOrigin: "50% 45%" }});
      tl.fromTo("#v-entreprises", {{ scale: 1.0 }}, {{ scale: 1.06, duration: P.entreprises[1] - P.entreprises[0], ease: "none" }}, P.entreprises[0]);
      tl.fromTo("#v-cabine", {{ scale: 1.12 }}, {{ scale: 1.04, duration: P.cabine[1] - P.cabine[0], ease: "none" }}, P.cabine[0]);
      // Les deux stands nommes : pastille de gauche a droite, le temps du plan.
      [["#pastille-club", "entreprises"], ["#pastille-cabine", "cabine"]].forEach(([sel, plan]) => {{
        tl.set(sel, {{ opacity: 1 }}, P[plan][0] + 0.1);
        tl.fromTo(sel, {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.5, ease: "power3.inOut", immediateRender: false }}, P[plan][0] + 0.1);
        tl.set(sel, {{ opacity: 0 }}, P[plan][1]);
      }});

      // Le stand du traiteur, puis la scene de l'atelier.
      tl.fromTo("#v-stand", {{ scale: 1.0 }}, {{ scale: 1.06, duration: P.stand[1] - P.stand[0], ease: "none" }}, P.stand[0]);
      gsap.set("#photo-scene", {{ transformOrigin: "35% 45%" }});
      tl.fromTo("#photo-scene", {{ scale: 1.15, x: 120 }}, {{ scale: 1.24, x: 120, duration: P.scene[1] - P.scene[0], ease: "none" }}, P.scene[0]);

      // La couche en plus : le metier d'abord, l'IA se pose dessus, puis la pile s'ouvre.
      montre("#p-couches", "couches");
      tl.from("#couches-titre", {{ y: 14, opacity: 0, duration: 0.5, ease: "power3.out" }}, A.carte_a);
      tl.from("#couche-metier", {{ y: 120, opacity: 0, duration: 0.55, ease: "power3.out" }}, A.carte_a + 0.1);
      gsap.set("#couche-ia", {{ opacity: 0 }});
      tl.fromTo("#couche-ia", {{ y: -360, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.45, ease: "power3.in", immediateRender: false }}, A.carte_b - 0.45);
      tl.fromTo("#pile", {{ y: 0 }}, {{ y: 14, duration: 0.12, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }}, A.carte_b);
      tl.to("#pile", {{ rotationX: 52, rotationZ: -28, y: -40, duration: 0.35, ease: "power3.out" }}, A.couche - 0.05);
      tl.to("#couche-ia", {{ z: 170, y: -40, duration: 0.35, ease: "power3.out" }}, A.couche - 0.05);
      // Punch-in sec sur « supplementaire » (rythme : un changement franc toutes les 2 a 4 s).
      gsap.set("#p-couches", {{ transformOrigin: "50% 15%" }});   // ancre en haut : le titre ne monte pas dans la zone masquee
      tl.set("#p-couches", {{ scale: 1.16 }}, {t(23.62)});

      // Le public, puis le cycle qui se dessine.
      tl.fromTo("#photo-public", {{ scale: 1.05, x: 60 }}, {{ scale: 1.15, x: -20, duration: P.public[1] - P.public[0], ease: "none" }}, P.public[0]);
      montre("#p-cycle", "cycle");
      const C = P.cycle[0], T0 = C + 0.62, PAS = 0.3;
      const NOEUDS = [[0, -300], [285, -93], [176, 243], [-176, 243], [-285, -93]];
      // 1. L'anneau eclot du centre et se trace d'un coup.
      gsap.set("#cycle-svg", {{ transformOrigin: "500px 860px" }});
      gsap.set("#cycle-anneau", {{ strokeDasharray: 1, strokeDashoffset: 1 }});
      tl.fromTo("#cycle-svg", {{ scale: 0.2 }}, {{ scale: 1, duration: 0.5, ease: "back.out(1.6)", immediateRender: false }}, C);
      tl.to("#cycle-anneau", {{ strokeDashoffset: 0, duration: 0.5, ease: "power2.out" }}, C + 0.02);
      gsap.set("#cycle-centre", {{ opacity: 0 }});
      tl.fromTo("#cycle-centre", {{ scale: 0.5, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2.2)", immediateRender: false }}, C + 0.1);
      tl.to("#cycle-centre", {{ scale: 0.6, opacity: 0, duration: 0.14, ease: "power2.in" }}, T0 - 0.14);
      // 2. Les cinq etapes : chacune claque au centre avec sa propre entree, puis vole a sa place sur l'anneau.
      const ENTREES = [{{ scale: 2.2, filter: "blur(14px)" }}, {{ x: -560 }}, {{ x: 560 }}, {{ y: 380, rotation: 8 }}, {{ y: -380, rotation: -8 }}];
      gsap.set(".etape", {{ xPercent: -50, yPercent: -50, opacity: 0 }});
      NOEUDS.forEach(([dx, dy], k) => {{
        const t = T0 + k * PAS, el = "#e" + k;
        tl.set(el, {{ opacity: 1 }}, t);
        tl.fromTo(el, {{ x: 0, y: 0, scale: 1, rotation: 0, filter: "blur(0px)", ...ENTREES[k] }},
          {{ x: 0, y: 0, scale: 1, rotation: 0, filter: "blur(0px)", duration: 0.16, ease: "power3.out", immediateRender: false }}, t);
        tl.to(el, {{ x: dx, y: dy, scale: 0.44, duration: 0.24, ease: "power3.inOut" }}, t + 0.2);
        tl.fromTo("#n" + k, {{ attr: {{ r: 0 }} }}, {{ attr: {{ r: 14 }}, duration: 0.25, ease: "back.out(3)", immediateRender: false }}, t + 0.4);
      }});
      // La comete fait le tour avec elles, arrive sur chaque noeud quand l'etape s'y pose, puis accelere.
      gsap.set("#cycle-comete", {{ svgOrigin: "500 860", opacity: 0 }});
      tl.set("#cycle-comete", {{ opacity: 1 }}, T0 + 0.44);
      tl.fromTo("#cycle-comete", {{ rotation: 0 }}, {{ rotation: 288, duration: 4 * PAS, ease: "none", immediateRender: false }}, T0 + 0.44);
      tl.to("#cycle-comete", {{ rotation: 1008, duration: P.cycle[1] - (T0 + 0.44 + 4 * PAS), ease: "power1.in" }}, T0 + 0.44 + 4 * PAS);
      // 3. « marketing » puis « communication » claquent sous le centre ; l'anneau accuse chaque coup.
      gsap.set(".slam", {{ xPercent: -50, yPercent: -50, opacity: 0 }});
      tl.set("#slam-marketing", {{ opacity: 1 }}, A.marketing);
      tl.fromTo("#slam-marketing", {{ scale: 1.9 }}, {{ scale: 1, duration: 0.22, ease: "back.out(2)", immediateRender: false }}, A.marketing);
      tl.to("#slam-marketing", {{ y: -52, duration: 0.22, ease: "power3.out" }}, A.communication);
      tl.set("#slam-communication", {{ opacity: 1 }}, A.communication);
      tl.fromTo("#slam-communication", {{ y: 52, scale: 1.9 }}, {{ y: 52, scale: 1, duration: 0.22, ease: "back.out(2)", immediateRender: false }}, A.communication);
      [A.marketing, A.communication].forEach((t) => {{
        tl.fromTo("#cycle-svg", {{ scale: 1 }}, {{ scale: 1.06, duration: 0.1, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }}, t);
      }});
      // 4. Sortie : le cycle tourne et file vers la camera, juste avant le flash.
      tl.to("#cycle-monde", {{ scale: 2.8, rotation: 30, duration: 0.42, ease: "power3.in" }}, P.cycle[1] - 0.42);
      tl.to("#cycle-monde", {{ opacity: 0, duration: 0.18, ease: "power1.in" }}, P.cycle[1] - 0.4);   // invisible avant les bords du cadre
      tl.from("#p-cycle .credit-noir", {{ opacity: 0, duration: 0.4 }}, C + 0.6);

      // La rioule : titre de lieu, cercle autour de l'enseigne, punch-in a chaque coupe.
      tl.set("#titre-stand", {{ opacity: 1 }}, P.rioule[0] + 0.05);
      tl.from("#titre-stand .l > span", {{ yPercent: 110, duration: 0.7, ease: "power4.out", stagger: 0.12 }}, P.rioule[0] + 0.05);
      tl.to("#titre-stand", {{ opacity: 0, duration: 0.3 }}, A.rioule - 0.35);
      gsap.set(["#bague .b-fond", "#bague .b-trait"], {{ strokeDasharray: 1, strokeDashoffset: 1 }});
      tl.set("#bague", {{ opacity: 1 }}, A.rioule - 0.1);
      tl.to(["#bague .b-fond", "#bague .b-trait"], {{ strokeDashoffset: 0, duration: 0.7, ease: "power2.inOut" }}, A.rioule - 0.1);
      tl.set("#bague", {{ opacity: 0 }}, P.rioule[0] + {R1});
      gsap.set(["#v-rioule-1", "#v-rioule-2", "#v-rioule-3"], {{ transformOrigin: "50% 40%" }});
      tl.fromTo("#v-rioule-1", {{ scale: 1.0 }}, {{ scale: 1.05, duration: {R1}, ease: "none" }}, P.rioule[0]);
      tl.fromTo("#v-rioule-2", {{ scale: 1.16 }}, {{ scale: 1.2, duration: {R2}, ease: "none" }}, P.rioule[0] + {R1});
      tl.fromTo("#v-rioule-3", {{ scale: 1.0 }}, {{ scale: 1.04, duration: {R3}, ease: "none" }}, P.rioule[0] + {round(R1 + R2, 3)});

      // Grant-marci.
      montre("#p-merci", "merci");
      gsap.set("#photo-merci", {{ transformOrigin: "40% 45%" }});
      tl.fromTo("#photo-merci", {{ scale: 1.1 }}, {{ scale: 1.18, duration: P.merci[1] - P.merci[0], ease: "none" }}, P.merci[0]);
      tl.from(".merci", {{ y: 30, opacity: 0, duration: 0.5, ease: "power3.out" }}, P.merci[0] + 0.05);
      tl.from(".merci .l > span", {{ yPercent: 110, duration: 0.8, ease: "power4.out" }}, P.merci[0] + 0.2);
      tl.from(".merci p", {{ y: 14, opacity: 0, duration: 0.45, ease: "power3.out" }}, {tb(34.94)});
      tl.from(".merci .sav", {{ opacity: 0, duration: 0.4 }}, {tb(34.94)} + 0.4);

      // A bientot : punch-in sur la main levee.
      gsap.set("#v-bientot", {{ transformOrigin: "50% 35%" }});
      tl.fromTo("#v-bientot", {{ scale: 1.0 }}, {{ scale: 1.03, duration: 1.1, ease: "none" }}, P.bientot[0]);
      tl.fromTo("#v-bientot", {{ scale: 1.15 }}, {{ scale: 1.18, duration: P.bientot[1] - P.bientot[0] - 1.1, ease: "none", immediateRender: false }}, P.bientot[0] + 1.1);

      // Carton final.
      montre("#p-final", "fin");
      tl.from(".relire .eyebrow", {{ y: 14, opacity: 0, duration: 0.5, ease: "power3.out" }}, P.fin[0] + 0.1);
      tl.from(".relire h2 .l > span", {{ yPercent: 110, duration: 0.8, ease: "power4.out", stagger: 0.15 }}, P.fin[0] + 0.2);
      tl.from(".relire .date", {{ y: 12, opacity: 0, duration: 0.5, ease: "power3.out" }}, P.fin[0] + 0.7);
      tl.from("#fin-ft", {{ scale: 0.6, opacity: 0, duration: 0.4, ease: "back.out(2.2)" }}, P.fin[0] + 1.0);
      tl.from("#fin-sia", {{ scale: 0.6, opacity: 0, duration: 0.4, ease: "back.out(2.2)" }}, P.fin[0] + 1.25);
      tl.fromTo("#fin-nom", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "power3.inOut" }}, P.fin[0] + 1.6);

      // Flash blanc sur les changements de sequence.
      [P.duo[0], P.savoyia[0], P.affiche[0], P.couches[0], P.cycle[0], P.rioule[0], P.merci[0], P.fin[0]].forEach(flash);

      // Sous-titres : chaque groupe apparait avec un petit pop.
      document.querySelectorAll(".st").forEach((st) => {{
        tl.set(st, {{ opacity: 1 }}, +st.dataset.a);
        tl.fromTo(st, {{ scale: 0.86 }}, {{ scale: 1, duration: 0.14, ease: "back.out(2.5)", immediateRender: false }}, +st.dataset.a);
        tl.set(st, {{ opacity: 0 }}, +st.dataset.b);
      }});

      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""

open("index.html", "w").write(HTML)
json.dump(plan_json, open("plan.json", "w"), ensure_ascii=False, indent=1)
print(f"index.html : {TOTAL:.2f} s")
for k, (a, b) in P.items(): print(f"  {k:<12} {a:6.2f} -> {b:6.2f}  ({b - a:4.2f} s)")
