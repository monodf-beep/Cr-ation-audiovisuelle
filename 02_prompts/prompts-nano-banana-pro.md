# Prompts image — « CHAMPIONS 26 »

**Modèle :** `nano_banana_pro` (Google — Gemini 3 Pro Image), résolution `4k`
**Pourquoi celui-là :** meilleur rendu de texte et de logos du catalogue, accepte des images de référence, sort en 4K. C'est le seul qui tient une typo anguleuse comme `FORZAFC` ou `LAuRAFoot` sans la déformer.

## Médias de référence (uploadés dans Higgsfield)

| ID média | Contenu | Plans concernés |
|---|---|---|
| `f8e03a96-2678-42e2-9508-b4480207606d` | photo réelle — face à plat, vue d'ensemble | 01, 02, 04, 09 |
| `d5912c1c-7372-4f72-ac9f-fd0410192dd3` | photo réelle — macro FORZAFC + TARIM + écusson FC CLUSES 1961 | 03, 05, 08, 09 |
| `8fa95b82-f704-450c-b09d-3081f5a0f2af` | photo réelle — manche gauche : couronne + UNIS DANS TOUS NOS DÉFIS | 06, 09 |
| `f84a1157-adf4-4c6d-9753-7ae819044fdb` | photo réelle — manche droite : R2 LAuRAFoot + FORCE ROUGE ET NOIR | 07, 09 |
| `5e2237c9-50ac-40f9-b069-c1e32fd2439f` | photo réelle — dos : Croix de Savoie, FC CLUSA, CHAMPIONS, 26 | 04, 11, 12, 13, 15 |
| `f7fff009-c190-4417-9db2-9ab5fafc0066` | photo réelle — macro dos haut : Croix de Savoie + FC CLUSA | 13, 14, 15 |
| `6f8a23bc-1a1c-4216-8015-4acbb5955d94` | rendu Meta AI — face | éclairage seulement |
| `adc4d477-f649-4b25-a809-bbe2397fce89` | rendu Meta AI — dos | éclairage seulement |

Les deux rendus Meta AI ne servent que de référence d'ambiance lumineuse : leurs couleurs et leurs textes sont faux.

## Ratio : ne pas générer les plans larges en 9:16

Vérifié à la production : en `9:16`, le modèle remplit la largeur du cadre avec le buste et **éjecte systématiquement les manches hors champ** — la devise `UNIS DANS TOUS NOS DÉFIS` et le patch `R2` sont tronqués à chaque essai, quelle que soit la formulation du prompt.

- **Plans larges du maillot entier (04, 09)** → générer en `4:5`, recadrer en 9:16 au montage ou par outpaint.
- **Macros (01, 02, 03, 05, 06, 07, 08, 11, 12, 13, 14, 15)** → `9:16` sans problème, la zone remplit le cadre.

---

## BIBLE DE DÉTAILS (à coller en tête de CHAQUE prompt)

> Bloc verrouillé. Ne rien enlever, ne rien reformuler — c'est ce qui empêche la dérive d'un plan à l'autre.

```
JERSEY SPEC — reproduce exactly, no invention:
Short-sleeve V-neck football jersey, perforated micro-mesh polyester with a visible
regular dot texture across the whole garment.
BODY COLOUR: very dark navy, almost black (#141726). NOT purple, NOT blue-violet.
GRAPHIC: torn dry-brush strokes in vivid red (#E01B33) sweeping diagonally from
lower-left to upper-right, with scattered splatter fragments; same pattern on front
and back. NOT pink, NOT magenta.
GOLD: matte antique bronze-gold (#C79A4B) throughout. NOT lemon yellow, NOT bright yellow.
COLLAR: V-neck in matte gold with a white mesh inner facing visible at the neckline.
CUFFS: one horizontal matte gold band near the hem of each short sleeve.

FRONT:
- Chest centre: "FORZAFC" — one word, all caps, matte gold, wide angular blocky
  sports lettering with squared-off terminals.
- Upper chest, viewer's left: sponsor "TARIM" in matte gold all caps, inside a thin
  gold rectangular outline.
- Upper chest, viewer's right: FC CLUSES crest — gold-outlined shield, "FC" above a
  short horizontal rule, "CLUSES" below it, a football and the year "1961" at the base.
- Viewer's right sleeve: red hexagonal patch with white "R2" over "LAuRAFoot"
  (capital L, capital A, lowercase u, capital RAF, lowercase oot); below the patch,
  red all-caps text "FORCE ROUGE ET NOIR".
- Viewer's left sleeve: gold line-art five-point crown outline; below it, gold all-caps
  text "UNIS DANS TOUS NOS DÉFIS".

BACK:
- Top centre: Savoy shield — a red shield bearing a full white cross (Croix de Savoie).
- Directly under the shield: "FC CLUSA" in matte gold angular caps.
- Across the shoulders: "CHAMPIONS" in matte gold angular caps with a thin outline.
- Centre back: large number "26" in matte gold, blocky angular sports numerals,
  the perforated mesh dots clearly readable inside the strokes.

FORBIDDEN: any sportswear brand mark or swoosh, any additional logo, any extra text,
any spelling variation of the listed words, any colour shift toward purple, violet,
magenta or lemon yellow.
```

---

## IMG-01 — Macro maille (plan 01)

```
[JERSEY SPEC]
Extreme macro photograph of the perforated mesh fabric of this jersey, filling the
frame. Near-total darkness; a single raking sliver of warm light catches one gold
thread at the edge of frame. Shallow depth of field, fine textile grain, dust motes.
Cinematic product photography, black background, 9:16.
```

## IMG-02 — Macro coup de pinceau rouge (plan 02)

```
[JERSEY SPEC]
Extreme macro of the torn edge of one red dry-brush stroke where it meets the dark
navy fabric. Hard raking side light from the left revealing the sublimation grain and
the mesh perforations through the red. Deep black surround, high contrast, 9:16.
```

## IMG-03 — Écusson FC CLUSES (plan 03)

```
[JERSEY SPEC]
Macro of the FC CLUSES crest on the chest of the jersey, shot at a slight angle with
raking light from the right. The gold shield outline, "FC", "CLUSES", the football and
"1961" are all sharp and fully legible. The rest of the garment falls into darkness.
Cinematic product photography, black background, 9:16.
```

## IMG-04 — Dos suspendu, quart de lumière (plan 04)

```
[JERSEY SPEC]
Full jersey seen from the BACK, hanging in a pitch-black studio, lit at one quarter
exposure by a single narrow light from the upper left. The number 26 and the word
CHAMPIONS are only just suggested out of the shadow, not fully readable. Fabric hangs
naturally with a slight drape. Wide product shot, deep black background, 9:16.
```

## IMG-05 — Sponsor TARIM (plan 05)

```
[JERSEY SPEC]
Macro of the "TARIM" sponsor mark on the upper chest — matte gold caps inside a thin
gold rectangular outline, perfectly legible. A red brush stroke crosses the lower part
of the frame. Raking light, shallow depth of field, black surround, 9:16.
```

## IMG-06 — Couronne + devise (plan 06)

```
[JERSEY SPEC]
Macro of the left sleeve of the jersey: the gold line-art five-point crown outline and,
below it, the gold all-caps text "UNIS DANS TOUS NOS DÉFIS", both fully sharp and
legible, with the perforated mesh texture visible inside the gold. Soft raking light
from above, black surround, 9:16.
```

## IMG-07 — Patch R2 LAuRAFoot (plan 07)

```
[JERSEY SPEC]
Macro of the right sleeve of the jersey: the red hexagonal patch with white "R2" over
"LAuRAFoot", and below it the red all-caps text "FORCE ROUGE ET NOIR". Both fully sharp
and legible. A gold cuff band runs across the bottom of the frame. Hard directional
light, black surround, 9:16.
```

## IMG-08 — FORZAFC plein cadre (plan 08)

```
[JERSEY SPEC]
The word "FORZAFC" in matte gold filling the width of the frame across the chest of the
jersey, shot straight on. Red dry-brush strokes cut diagonally behind and across the
lettering. Every letter sharp, squared-off and correctly spelled. Dramatic side light,
black background, 9:16.
```

## IMG-09 — Packshot face (plan 09)

```
[JERSEY SPEC]
The complete jersey seen from the FRONT, hanging on an invisible mount in a black studio,
arms slightly spread, fabric falling naturally. Two-point lighting: a key from the upper
left, a cold rim from the right separating the shoulders from the background. Every
element — FORZAFC, TARIM, the FC CLUSES crest, both sleeve marks — sharp and legible.
Hero product photograph, pure black background, 9:16.
```

## IMG-10 — Respiration montagne (plan 10)

```
Wide cinematic landscape of the Arve valley in Haute-Savoie around Cluses at blue hour:
steep dark limestone ridges, low mist lying in the valley floor, the last cold light on
the summits, a few scattered village lights far below. No text, no people, no jersey.
Desaturated blue-grey palette with one warm accent on the highest ridge. Anamorphic
wide shot, 9:16.
```
*(seul plan sans la bible de détails — il n'y a pas de maillot dedans)*

## IMG-11 — Le 26 (plan 11)

```
[JERSEY SPEC]
Macro of the number "26" on the BACK of the jersey, the two gold numerals filling most
of the frame, shot straight on. The perforated mesh dots are clearly readable inside the
gold strokes. Red brush strokes pass behind the numerals. Raking light from the left,
black surround, 9:16.
```

## IMG-12 — CHAMPIONS (plan 12)

```
[JERSEY SPEC]
The word "CHAMPIONS" in matte gold angular caps with a thin outline, running across the
shoulders on the BACK of the jersey, shot straight on and filling the frame width. Every
letter sharp and correctly spelled. The top of the number 26 is visible at the bottom
edge. Light running along the gold, black surround, 9:16.
```

## IMG-13 — FC CLUSA (plan 13)

```
[JERSEY SPEC]
Macro on the BACK of the jersey centred on "FC CLUSA" in matte gold angular caps,
perfectly sharp and filling the middle of the frame. The bottom of the red-and-white
Savoy shield is visible just above it, the top of "CHAMPIONS" just below. Everything
outside the lettering falls into deep shadow. Raking light, black surround, 9:16.
```

## IMG-14 — Croix de Savoie (plan 14)

```
[JERSEY SPEC]
Extreme close-up of the Savoy shield at the top back of the jersey: a red shield bearing
a full white cross, the arms of the cross reaching the edges of the shield. Sharp,
centred, filling the frame. The perforated mesh texture is visible through the white and
the red. This is the brightest point of the whole film — soft warm key light rising on
the shield, everything around it black. 9:16.
```

## IMG-15 — Plan de fin (plan 15)

```
[JERSEY SPEC]
Tight shot of the upper BACK of the jersey: the red-and-white Savoy shield and "FC CLUSA"
in gold directly below it, both sharp and legible together in the same frame. The
shoulders and the word CHAMPIONS fall away into pure black. Single soft key light on the
shield and the wordmark. Closing hero shot, black background, 9:16.
```

---

## Procédure de génération

1. **Uploader les 4 photos de référence** dans Higgsfield (widget d'upload — les pièces jointes du chat ne sont pas lisibles par l'outil).
2. Générer **IMG-09** en premier (packshot face) : c'est le plan le plus exigeant, il valide ou invalide la bible de détails avant de dépenser sur les 14 autres.
3. Contrôler caractère par caractère : `FORZAFC`, `TARIM`, `FC CLUSES`, `1961`, `R2`, `LAuRAFoot`, `FORCE ROUGE ET NOIR`, `UNIS DANS TOUS NOS DÉFIS`.
4. Puis **IMG-15** (plan de fin) pour valider le dos et la Croix de Savoie.
5. Une fois ces deux-là validés, lancer le reste par lots (`generate_image_batch`).
6. Ne jamais animer un plan dont un texte est faux : le modèle vidéo amplifiera le défaut.

## Réglages

| Paramètre | Valeur |
|---|---|
| `model` | `nano_banana_pro` |
| `resolution` | `4k` |
| `aspect_ratio` | `9:16` |
| `medias[].role` | `image` |
| variantes | `count: 3` par plan, on garde la meilleure |
