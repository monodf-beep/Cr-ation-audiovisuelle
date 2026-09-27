"""Sous-titres du reportage, a partir des mots de la voix (voix-mots.json), ecrits dans index.html
entre <!-- st:start --> et <!-- st:end -->.
Regles des formats verticaux (Reels, TikTok, Shorts) :
- des groupes de 1 a 3 mots, une seule ligne, coupes aux pauses et a la ponctuation, jamais la phrase entiere ;
- un mot-cle au plus par groupe, mis en valeur (plus gros, bloc bleu Savoie) ; les expressions
  (Grand Genève, Pays de Gex...) restent d'un seul tenant ;
- chaque groupe apparait avec un petit « pop » (index.html) ; pas de mot allume (ecarte par Franck) ;
- pas de ponctuation affichee sauf ? et ! ;
- texte sombre (.clair) sur les plans clairs, blanc sur les images.
Usage : python3 tools/sous-titres.py"""
import json, re

MOTS = json.load(open("voix-mots.json"))["mots"]
DEBUT = 5                 # les cinq premiers mots sont le titre du hook, deja a l'ecran
MAX_MOTS, MAX_CARS = 3, 20
# Plans clairs (texte sombre) : carte, affiche, liste de la culture, carte du Grand Genève, remerciement.
CLAIRS = [(2.0, 6.66), (8.6, 12.9), (19.9, 29.9), (42.1, 50.9), (70.9, 80.5)]
# Plans ou les sous-titres doivent se placer autrement (aucun depuis que le bandeau Interreg est en haut).
BAS = []
# Pas de sous-titres quand un titre a l'ecran dit deja la meme chose (citation « un bien commun, une culture commune »).
SANS = [(46.08, 50.9)]
# Changements de plan : un groupe ne les chevauche jamais.
# (62.9 et 74.9 : « Elle » et « Et je remercie » commencent juste avant le changement de plan depuis la coupe du
# premier « 140 » ; le groupe part avec eux au lieu de clignoter seul.)
PLANS = [2.0, 6.66, 8.6, 12.9, 19.9, 29.9, 35.9, 42.1, 46.08, 50.9, 57.9, 62.9, 70.9, 74.9]
EXPRESSIONS = ["Grand Genève", "Pays de Gex", "Lengoua Savoyârda", "Cé qu'è lainô", "Laetitia Picard",
               "24 septembre", "bien commun", "culture commune", "langue commune", "projet culturel"]
# Mots-cles : peu nombreux, sinon plus rien ne ressort (un groupe sur trois environ). La liste de la
# culture (jazz, theatre...) est deja a l'ecran en grand : pas besoin de la souligner.
CLES = ["CERN", "Interreg", "Grand Genève", "Pays de Gex", "Haute-Savoie", "Lengoua Savoyârda",
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

groupes = [g for g in groupes if not any(a <= g[0][1] < b for a, b in SANS)]

# 2 bis. Pas de groupe qui clignote : moins de 0,45 s a l'ecran (temps de la video acceleree, montage.json),
# il rejoint le suivant, ou a defaut le precedent, si la ligne reste courte et sans changement de plan.
VITESSE = json.load(open("montage.json"))["vitesse"]
MIN_ECRAN, MAX_FUSION, MAX_UNITES = 0.45, 24, 4
texte_de = lambda g: " ".join(nu(u[0]) for u in g)
coupe_plan = lambda g, h: any(g[0][1] < p <= h[0][1] + 0.05 for p in PLANS)
k = 0
while k < len(groupes):
    g = groupes[k]
    fin = groupes[k + 1][0][1] if k + 1 < len(groupes) else g[-1][2] + 0.25
    if (fin - g[0][1]) / VITESSE < MIN_ECRAN:
        if k + 1 < len(groupes) and len(g + groupes[k + 1]) <= MAX_UNITES and len(texte_de(g + groupes[k + 1])) <= MAX_FUSION and not coupe_plan(g, groupes[k + 1]) \
                and sum(cle(u[0]) for u in g + groupes[k + 1]) <= 1:
            groupes[k:k + 2] = [g + groupes[k + 1]]; continue
        if k > 0 and len(groupes[k - 1] + g) <= MAX_UNITES and len(texte_de(groupes[k - 1] + g)) <= MAX_FUSION and not coupe_plan(groupes[k - 1], g) \
                and sum(cle(u[0]) for u in groupes[k - 1] + g) <= 1:
            groupes[k - 1:k + 1] = [groupes[k - 1] + g]; k -= 1; continue
    k += 1

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
