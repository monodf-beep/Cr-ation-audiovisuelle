#!/usr/bin/env python3
"""Regenere le storyboard a partir des images reelles du film monte."""

import base64, io, os, sys
import imageio.v2 as iio
from PIL import Image

REPO = "/home/user/Cr-ation-audiovisuelle"
FILM = os.path.join(REPO, "04_montage/champions-26.mp4")
OUT = "/tmp/claude-0/-home-user-Cr-ation-audiovisuelle/e3f72c30-c5c1-5be3-8f7a-91ef92a288ef/scratchpad/storyboard.html"
FPS = 24

# (t_debut, duree, video?, mot, description, mouvement)
ACTES = [
    ("L'objet", "Deux macros en lumière dure. On sait tout de suite que c'est un maillot de foot, et qu'il a servi.", [
        (0.0, 2.5, True, "R2 · FORCE ROUGE ET NOIR", "Le patch de la ligue sur la manche.", "Le tissu fléchit, bascule de netteté"),
        (2.5, 2.5, True, "FC CLUSES 1961", "L'écusson. La lumière le balaie et la date sort de l'ombre en dernier.", "Balayage de lumière"),
    ]),
    ("Le lieu", "Deux plans, pas un de plus. Assez pour savoir où on est.", [
        (5.0, 1.0, False, "", "Un mât de projecteurs dans le noir.", "Flash d'une seconde"),
        (6.0, 3.0, True, "", "Les crampons dans l'herbe. Le pied se lève et se repose.", "Caméra basse, push-in"),
    ]),
    ("Le maillot", "Le produit occupe le film. C'est une présentation de maillot, pas un reportage.", [
        (9.0, 3.0, True, "", "Le maillot déployé à bout de bras. Le tissu respire et ondule.", "Push-in lent"),
        (12.0, 1.5, True, "FORZAFC", "Le mot traverse le cadre et en sort.", "Travelling rapide"),
        (13.5, 1.5, True, "UNIS DANS TOUS NOS DÉFIS", "La couronne et la devise. La manche fléchit au mouvement du bras.", "Tilt descendant"),
        (15.0, 1.2, True, "R2 · LAuRAFoot", "Le patch, en gros. La poitrine se soulève.", "Push-in sec"),
        (16.2, 1.0, True, "", "Retour au maillot déployé, plus court et plus serré.", "Reprise, cadre resserré"),
        (17.2, 1.0, True, "", "Le drapeau du Faucigny claque sur le grillage.", "Caméra à l'épaule"),
    ]),
    ("La montée", "Un seul plan, et il ne montre pas le maillot : la tribune debout. Puis le noir.", [
        (18.2, 2.0, True, "", "Le noyau debout, bras levés, drapeaux.", "Caméra bousculée, coupe sèche"),
    ]),
    ("Le dos", "Le film n'a jamais montré le verso. Il se retourne.", [
        (20.7, 3.0, True, "CHAMPIONS · 26", "Il se retourne. Les épaules respirent, puis la caméra entre.", "Arrêt sec, puis push-in"),
        (23.6, 0.7, False, "26", "Le chiffre plein cadre.", "Flash"),
        (24.3, 0.7, False, "CHAMPIONS", "La lumière court sur l'or.", "Flash"),
        (25.0, 0.7, False, "FC CLUSA", "Le nom.", "Flash"),
        (25.7, 1.8, False, "FC CLUSA", "La Croix de Savoie et le nom ensemble.", "Fondu au noir"),
    ]),
]

SON = [
    ("0:00 → 0:05", "Un souffle bas de vallée et le ronflement des lampes à décharge. Une frappe sur chaque coupe."),
    ("0:05 → 0:09", "La pulsation entre, un coup par seconde. Une montée filtrée annonce le maillot."),
    ("0:09 → 0:18", "La pulsation double, puis quadruple. La rumeur de tribune monte, un tambour part."),
    ("0:18 → 0:20", "Tout est plein. Une dernière montée pousse vers le noir."),
    ("0:20 → 0:21", "Coupe totale. Une demi-seconde de rien pendant qu'il se retourne."),
    ("0:21 → 0:27", "Tout revient d'un coup, plein régime, et un accord se tient jusqu'au fondu."),
]


def vignette(t, duree):
    """Une image prise au milieu du plan."""
    i = int((t + duree * 0.5) * FPS)
    im = Image.fromarray(FRAMES[min(i, len(FRAMES) - 1)]).convert("RGB")
    im.thumbnail((430, 430 * 16 // 9), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=74, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def tc(t):
    return f"{int(t)//60}:{int(t)%60:02d}" + f"{t%1:.1f}"[1:]


print("lecture du film…")
r = iio.get_reader(FILM)
FRAMES = [f for f in r]
r.close()
print(f"{len(FRAMES)} images")

TOTAL = 27.5
n = 0
sections = []
ruban = []

for titre, chapo, plans in ACTES:
    t0 = plans[0][0]
    t1 = plans[-1][0] + plans[-1][1]
    cartes = []
    for t, d, video, mot, desc, mouv in plans:
        n += 1
        badge = '<span class="vid">vidéo</span>' if video else '<span class="fix">image</span>'
        motligne = f'<p class="mot">{mot}</p>' if mot else ""
        cartes.append(f"""<figure class="plan">
  <div class="vue"><img src="{vignette(t, d)}" alt="Plan {n:02d} — {desc}" loading="lazy">
    <span class="num">{n:02d}</span>{badge}</div>
  <figcaption>
    <p class="tc">{tc(t)} <span class="dur">{d:.1f} s</span></p>
    {motligne}
    <p class="desc">{desc}</p>
    <p class="mouv">{mouv}</p>
  </figcaption>
</figure>""")
        ruban.append(f'<span class="bloc {"v" if video else "i"}" '
                     f'style="flex:{d:.2f}" title="Plan {n:02d} — {d:.1f} s"></span>')
        if abs(t + d - 20.2) < 0.01:
            ruban.append('<span class="bloc noir" style="flex:0.50" title="Silence — 0,5 s"></span>')
    sections.append(f"""<section class="acte">
  <header class="acte-tete">
    <h2>{titre}</h2>
    <p class="acte-tc">{tc(t0)} → {tc(t1)}</p>
    <p class="acte-chapo">{chapo}</p>
  </header>
  <div class="bande">{''.join(cartes)}</div>
</section>""")

son_lignes = "".join(
    f'<div class="son-ligne"><p class="son-tc">{a}</p><p class="son-txt">{b}</p></div>'
    for a, b in SON)

HTML = f"""<title>Champions 26</title>
<style>
:root{{
  --fond:#F2F0EC; --carte:#FFFFFF; --trait:#DCD7CE;
  --encre:#16181F; --gris:#5E6273;
  --marine:#141726; --or:#9A7532; --rouge:#C4152B;
  --pas:clamp(1rem,2.4vw,1.6rem);
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --fond:#0C0E15; --carte:#141726; --trait:#272B3D;
    --encre:#EDEAE3; --gris:#8A90A6;
    --marine:#0A0C13; --or:#C79A4B; --rouge:#E01B33;
  }}
}}
:root[data-theme="dark"]{{
  --fond:#0C0E15; --carte:#141726; --trait:#272B3D;
  --encre:#EDEAE3; --gris:#8A90A6;
  --marine:#0A0C13; --or:#C79A4B; --rouge:#E01B33;
}}
*{{box-sizing:border-box}}
body{{
  margin:0; background:var(--fond); color:var(--encre);
  font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
  font-size:16px; line-height:1.5; -webkit-font-smoothing:antialiased;
}}
.page{{max-width:1180px; margin:0 auto; padding:calc(var(--pas)*2) var(--pas) calc(var(--pas)*3)}}

/* --- entete --- */
.tete{{display:flex; flex-direction:column; gap:.9rem; padding-bottom:calc(var(--pas)*1.4);
      border-bottom:2px solid var(--encre)}}
.sur{{margin:0; font-size:.7rem; letter-spacing:.22em; text-transform:uppercase;
     color:var(--or); font-weight:700}}
h1{{margin:0; font-size:clamp(2.6rem,8vw,5.2rem); line-height:.92; letter-spacing:-.03em;
   font-weight:800; text-wrap:balance}}
h1 .b{{display:block; font-weight:200; color:var(--gris)}}
.chapo{{margin:0; max-width:60ch; font-size:1.02rem; color:var(--gris)}}
.chapo strong{{color:var(--encre); font-weight:600}}
.fiche{{display:flex; flex-wrap:wrap; gap:.45rem 1.6rem; margin-top:.5rem;
       font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:.74rem;
       letter-spacing:.04em; color:var(--gris); text-transform:uppercase}}
.fiche b{{color:var(--encre); font-weight:700}}

/* --- ruban de rythme --- */
.rythme{{margin:calc(var(--pas)*1.6) 0 0}}
.rythme h3, .son h3{{margin:0 0 .55rem; font-size:.7rem; letter-spacing:.2em;
                    text-transform:uppercase; color:var(--gris); font-weight:700}}
.ruban{{display:flex; gap:2px; height:30px; overflow:hidden}}
.bloc{{min-width:2px; border-radius:1px}}
.bloc.v{{background:var(--or)}}
.bloc.i{{background:var(--trait)}}
.bloc.noir{{background:var(--rouge)}}
.legende{{display:flex; flex-wrap:wrap; gap:1.1rem; margin-top:.5rem;
         font-size:.72rem; color:var(--gris)}}
.legende span{{display:inline-flex; align-items:center; gap:.4rem}}
.legende i{{width:14px; height:8px; display:inline-block; border-radius:1px}}

/* --- actes --- */
.acte{{margin-top:calc(var(--pas)*2.4)}}
.acte-tete{{display:grid; grid-template-columns:1fr auto; gap:.2rem 1rem;
           padding-bottom:.7rem; border-bottom:1px solid var(--trait)}}
.acte-tete h2{{margin:0; font-size:1.5rem; letter-spacing:-.02em; font-weight:700}}
.acte-tc{{margin:0; align-self:center; font-family:ui-monospace,Menlo,Consolas,monospace;
         font-size:.76rem; font-variant-numeric:tabular-nums; color:var(--or);
         letter-spacing:.06em}}
.acte-chapo{{grid-column:1/-1; margin:.2rem 0 0; max-width:62ch; font-size:.92rem; color:var(--gris)}}

.bande{{display:flex; gap:var(--pas); margin-top:var(--pas);
       overflow-x:auto; padding-bottom:.6rem; scroll-snap-type:x proximity}}
.plan{{margin:0; flex:0 0 232px; scroll-snap-align:start;
      display:flex; flex-direction:column; gap:.55rem}}
.vue{{position:relative; aspect-ratio:9/16; overflow:hidden; background:var(--marine)}}
.vue img{{width:100%; height:100%; object-fit:cover; display:block}}
.num{{position:absolute; left:0; bottom:0; background:var(--or); color:#0C0E15;
     font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.7rem; font-weight:700;
     letter-spacing:.06em; padding:3px 9px}}
.vid,.fix{{position:absolute; right:0; top:0;
          font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.6rem; font-weight:700;
          letter-spacing:.1em; text-transform:uppercase; padding:3px 8px}}
.vid{{background:var(--rouge); color:#fff}}
.fix{{background:var(--trait); color:var(--gris)}}
figcaption{{display:flex; flex-direction:column; gap:.28rem}}
.tc{{margin:0; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.72rem;
    font-variant-numeric:tabular-nums; letter-spacing:.05em; color:var(--or)}}
.tc .dur{{color:var(--gris)}}
.mot{{margin:0; font-size:.74rem; font-weight:700; letter-spacing:.08em;
     text-transform:uppercase; color:var(--encre)}}
.desc{{margin:0; font-size:.88rem; line-height:1.45}}
.mouv{{margin:0; font-size:.76rem; color:var(--gris); font-style:italic}}

/* --- son + notes --- */
.son{{margin-top:calc(var(--pas)*2.4); padding-top:var(--pas); border-top:2px solid var(--encre)}}
.son-ligne{{display:grid; grid-template-columns:11rem 1fr; gap:.4rem 1.2rem;
           padding:.6rem 0; border-bottom:1px solid var(--trait)}}
.son-tc{{margin:0; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.76rem;
        font-variant-numeric:tabular-nums; color:var(--or); letter-spacing:.05em}}
.son-txt{{margin:0; font-size:.92rem}}
.notes{{margin-top:calc(var(--pas)*2); display:grid; gap:var(--pas);
       grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}}
.note{{background:var(--carte); border:1px solid var(--trait); padding:1.1rem 1.2rem}}
.note h4{{margin:0 0 .5rem; font-size:.7rem; letter-spacing:.18em; text-transform:uppercase;
         color:var(--or); font-weight:700}}
.note p{{margin:0 0 .6rem; font-size:.9rem; color:var(--gris)}}
.note p:last-child{{margin-bottom:0}}
.note strong{{color:var(--encre); font-weight:600}}
@media (max-width:560px){{
  .son-ligne{{grid-template-columns:1fr}}
  .acte-tete{{grid-template-columns:1fr}}
}}
</style>

<div class="page">

<header class="tete">
  <p class="sur">Film publicitaire · maillot commémoratif</p>
  <h1>FC Clusa<span class="b">Champions 26</span></h1>
  <p class="chapo">
    Un film de présentation de maillot, à la grammaire équipementier :
    <strong>le produit occupe le film</strong>. Onze plans sur seize sont le maillot
    lui-même, cadrés serré, nets, tenus par une lumière dure.
  </p>
  <p class="chapo">
    <strong>Dix plans sur seize sont de la vraie vidéo.</strong> Il ne reste d'images
    que là où le plan dure moins d'une seconde — à cette durée, une image se lit comme
    un flash, pas comme un arrêt.
  </p>
  <p class="chapo">
    <strong>Et le verso n'apparaît jamais avant la vingtième seconde.</strong>
    Ni CHAMPIONS, ni le 26, ni FC CLUSA. Puis il se retourne, et le son coupe.
  </p>
  <div class="fiche">
    <span>Format <b>9:16</b></span>
    <span>Durée <b>27,5 s</b></span>
    <span>Plans <b>16</b></span>
    <span>Vidéo <b>10</b></span>
    <span>Voix off <b>aucune</b></span>
    <span>Règle <b>aucun visage</b></span>
  </div>
</header>

<div class="rythme">
  <h3>Le rythme, à l'échelle</h3>
  <div class="ruban">{''.join(ruban)}</div>
  <p class="legende">
    <span><i style="background:var(--or)"></i> plan vidéo</span>
    <span><i style="background:var(--trait)"></i> image</span>
    <span><i style="background:var(--rouge)"></i> le noir, avant le dos</span>
  </p>
</div>

{''.join(sections)}

<section class="son">
  <h3>Le son</h3>
  {son_lignes}
</section>

<div class="notes">
  <div class="note">
    <h4>D'où viennent les images</h4>
    <p><strong>Les macros sont le vrai maillot photographié</strong>, puis recadré.
    Aucun risque de dérive sur les flocages : ce sont les vrais.</p>
    <p><strong>Les plans vidéo partent de ces mêmes images déjà étalonnées</strong>, pas
    de zéro — le clip hérite du style au lieu de revenir à côté. Les flocages sont
    intacts sur les dix : R2 / LAuRAFoot, FORZAFC, TARIM, l'écusson, CHAMPIONS, 26,
    FC CLUSA, la croix.</p>
  </div>
  <div class="note">
    <h4>La texture</h4>
    <p>Le style tient à une lumière dure, une dominante sodium vert-orange, des lampes
    qui bavent et un grain fin — <strong>sur des images qui restent nettes</strong>.</p>
    <p><strong>Le film assume deux registres au lieu d'un.</strong> Le lieu descend vers
    la photo de téléphone poussée à bout. Le maillot monte vers l'image de campagne. Les
    rapprocher donnait deux qualités tièdes qui se lisaient comme une incohérence ; les
    éloigner en fait un parti pris.</p>
  </div>
  <div class="note">
    <h4>Le son</h4>
    <p>Aucun modèle de musique ou de bruitage n'étant disponible, la piste est
    <strong>synthétisée et calée sur le découpage à l'image près</strong> — une frappe
    sur chaque coupe, et le silence tombe exactement où il faut.</p>
    <p>Une courbe générale la fait partir à un tiers du volume et ne jouer plein que sur
    le dos. Sans elle, tout était présent dès la première seconde, donc rien n'arrivait
    jamais.</p>
  </div>
  <div class="note">
    <h4>Ce qui reste ouvert</h4>
    <p><strong>Le grillage</strong> est encore au premier plan du drapeau et de la
    tribune. Si ça gêne, on recadre plus haut.</p>
    <p><strong>Le plan des mâts</strong> est le plus faible du film — il est à une
    seconde, mais c'est le seul que je referais.</p>
    <p><strong>Trois photos réelles du stade</strong> sont de jour ; une reprise vers
    21 h 30 les rendrait utilisables telles quelles.</p>
  </div>
</div>

<p class="chapo" style="margin-top:calc(var(--pas)*2); font-size:.8rem">
  Carton de fin — FC Cluses 1961 · Champions R2 · LAuRAFoot 2026
</p>

</div>
"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"{OUT}  {len(HTML)/1024:.0f} Ko  {n} plans")
