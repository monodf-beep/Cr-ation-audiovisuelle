"""Sous-titres du reportage, a partir des mots de la voix (voix-mots.json), ecrits dans index.html
entre <!-- st:start --> et <!-- st:end -->.
Regles des formats verticaux (Reels, TikTok, Shorts) :
- des groupes de 1 a 3 mots, une seule ligne, coupes aux pauses et a la ponctuation, jamais la phrase entiere ;
- un mot-cle au plus par groupe, mis en valeur (plus gros, bloc bleu Savoie) ; les expressions
  (Grand Genève, Pays de Gex...) restent d'un seul tenant ;
- le mot prononce s'allume ; chaque groupe apparait avec un petit « pop » (index.html) ;
- pas de ponctuation affichee sauf ? et ! ;
- texte sombre (.clair) sur les plans clairs, blanc sur les images.
Usage : python3 tools/sous-titres.py"""
import json, re

MOTS = json.load(open("voix-mots.json"))["mots"]
DEBUT = 5                 # les cinq premiers mots sont le titre du hook, deja a l'ecran
MAX_MOTS, MAX_CARS = 3, 20
# Plans clairs (texte sombre) : carte, affiche, liste de la culture, carte du Grand Genève, remerciement.
CLAIRS = [(2.0, 12.9), (19.9, 29.9), (42.1, 50.9), (70.9, 80.5)]
# Plans ou le bas du cadre porte deja du texte (affiche : bandeau Interreg) : sous-titres plus bas.
BAS = [(19.9, 29.9)]
# Changements de plan : un groupe ne les chevauche jamais.
PLANS = [2.0, 12.9, 19.9, 29.9, 35.9, 42.1, 50.9, 57.9, 63.0, 70.9, 75.0]
EXPRESSIONS = ["Grand Genève", "Pays de Gex", "Lengoua Savoyârda", "Cé qu'è lainô", "Laetitia Picard",
               "24 septembre", "bien commun", "culture commune", "langue commune", "projet culturel"]
# Mots-cles : peu nombreux, sinon plus rien ne ressort (un groupe sur trois environ). La liste de la
# culture (jazz, theatre...) est deja a l'ecran en grand : pas besoin de la souligner.
CLES = ["CERN", "Interreg", "Grand Genève", "Globe", "Pays de Gex", "Haute-Savoie", "Lengoua Savoyârda",
        "bien commun", "culture commune", "160", "140", "frontière", "savoyard", "Cé qu'è lainô",
        "langue commune", "Laetitia Picard", "24 septembre", "projet culturel"]
# Petits mots qui ne finissent pas un groupe : ils passent au debut du suivant.
OUTILS = {"de", "du", "la", "le", "les", "à", "et", "un", "une", "des", "en", "sur", "ce", "pour", "au", "aux", "d'"}

def nu(t):
    return re.sub(r"[,.;:]+$", "", t).replace(" ?", " ?").replace(" !", " !")

def cle(t):
    base = re.sub(r"[,.;:?! ]+$", "", t).replace("l'", "").replace("L'", "")
    return base in CLES or base.lower() in [c.lower() for c in CLES if c.islower()]

# 1. Unites : un mot, ou une expression gardee d'un seul tenant.
unites, i = [], DEBUT
while i < len(MOTS):
    for e in EXPRESSIONS:
        n = len(e.split())
        bloc = MOTS[i:i + n]
        if n > 1 and len(bloc) == n and re.sub(r"[,.;:?!]", "", " ".join(m[0] for m in bloc)) == e:
            unites.append([" ".join(m[0] for m in bloc), bloc[0][1], bloc[-1][2]]); i += n; break
    else:
        unites.append(list(MOTS[i])); i += 1

# 2. Groupes de 1 a 3 unites.
groupes, g = [], []
for k, u in enumerate(unites):
    if g:
        texte = " ".join(nu(x[0]) for x in g + [u])
        coupe = (len(g) >= MAX_MOTS or len(texte) > MAX_CARS
                 or re.search(r"[,.;:?!]$", g[-1][0])
                 or u[1] - g[-1][2] > 0.4
                 or any(g[0][1] < p <= u[1] + 0.05 for p in PLANS)
                 or (cle(u[0]) and any(cle(x[0]) for x in g)))
        if coupe:
            report = []
            while len(g) > 1 and g[-1][0] in OUTILS: report.insert(0, g.pop())
            groupes.append(g); g = report
    g.append(u)
groupes.append(g)

# 3. HTML.
lignes = []
for k, g in enumerate(groupes):
    a = g[0][1]
    fin_mots = g[-1][2] + 0.25
    b = min(fin_mots, groupes[k + 1][0][1]) if k + 1 < len(groupes) else fin_mots
    if k + 1 < len(groupes) and groupes[k + 1][0][1] - g[-1][2] < 0.6: b = groupes[k + 1][0][1]
    clair = any(x <= a < y for x, y in CLAIRS)
    bas = any(x <= a < y for x, y in BAS)
    spans = " ".join(f'<span class="m{" cle" if cle(u[0]) else ""}" data-a="{u[1]:.2f}" data-b="{u[2]:.2f}">{nu(u[0])}</span>' for u in g)
    lignes.append(f'      <div class="st{" clair" if clair else ""}{" bas" if bas else ""}" data-a="{a:.2f}" data-b="{b:.2f}">{spans}</div>')

html = open("index.html").read()
html, n = re.subn(r"<!-- st:start -->.*?<!-- st:end -->", lambda m: "<!-- st:start -->\n" + "\n".join(lignes) + "\n      <!-- st:end -->", html, flags=re.S)
assert n == 1, "marqueurs st:start / st:end introuvables dans index.html"
open("index.html", "w").write(html)
print(f"{len(groupes)} groupes")
for g in groupes: print(f"  {g[0][1]:6.2f}  " + " ".join(("[" + nu(u[0]) + "]") if cle(u[0]) else nu(u[0]) for u in g))
