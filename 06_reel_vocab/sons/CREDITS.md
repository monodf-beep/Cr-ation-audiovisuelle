# Crédits sons — « Le rugby en savoyard »

Tous les sons viennent d'Openverse (api.openverse.org), filtre licence `cc0,by`.
Aucun son NC / ND. Tous ont été coupés (silence de tête retiré, fondu de fin),
normalisés à −1 dBTP et convertis en WAV 48 kHz.

## Inventaire

| Fichier | Rôle | Durée | Titre original | Auteur | Source | Licence |
|---|---|---|---|---|---|---|
| impact_1.wav | impact du mot (boom, transitoire franc) | 1,60 s | BOOM IMPACT 2 | XHALE303 | https://freesound.org/people/XHALE303/sounds/535592 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| impact_2.wav | impact cinéma (coup sec + queue grave) | 1,80 s | Cinematic Impact | Rizzard | https://freesound.org/people/Rizzard/sounds/559387 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| impact_3.wav | impact sub-grave (boom très bas) | 1,30 s | Bass Impact - Ki_01.mp3 | Kievinay | https://freesound.org/people/Kievinay/sounds/512389 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| whoosh_1.wav | whoosh plein (crête vers 0,25 s) | 0,58 s | Swoosh 3 | D4XX | https://freesound.org/people/D4XX/sounds/607250 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| whoosh_2.wav | whoosh clair, passage (crête vers 0,25 s) | 0,55 s | whoosh.wav | LloydEvans09 | https://freesound.org/people/LloydEvans09/sounds/332003 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| whoosh_3.wav | swipe rapide (attaque immédiate) | 0,40 s | Swipe Whoosh | qubodup | https://freesound.org/people/qubodup/sounds/60007 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| sifflet.wav | coup de sifflet d'arbitre (≈0,5 s + réverbération de salle) | 1,20 s | 218318 splicesound referee-whistle-blow-gymnasium | SpliceSound | https://commons.wikimedia.org/w/index.php?curid=116753044 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| sifflet_long.wav | coup de sifflet plus long (≈0,8 s) | 1,00 s | Whistle.WAV | 14FPanskaBubik_Lukas | https://freesound.org/people/14FPanskaBubik_Lukas/sounds/418564 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| clameur_1.wav | clameur de foule qui monte (−25 → −10 dB en 2 s) puis retombe | 12,0 s | crowd roar.WAV | jonsept | https://freesound.org/people/jonsept/sounds/449915 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| clameur_2.wav | rugissement + applaudissements (montée en 1,5 s, soutenu) | 12,0 s | S004_Crowd_Roar_Clapping_Mono.wav | Pól | https://freesound.org/people/P%C3%B3l/sounds/385920 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| montee.wav | montée de tension, crête sur la fin | 1,85 s | Riser | Rizzard | https://freesound.org/people/Rizzard/sounds/561207 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| musique.wav | musique : sport, énergique, batterie + claps + guitare, **120 BPM** | 50,0 s | Path To Victory (Upbeat, Energetic, Optimistic) | UNIVERSFIELD | https://freesound.org/people/UNIVERSFIELD/sounds/704530 | **CC BY 4.0** — https://creativecommons.org/licenses/by/4.0/ |
| musique_alt_cc0.wav | autre musique : boucle de batterie hip-hop, 90 BPM (titre de l'auteur) | 45,3 s | East Coast Drum Loop Tempo 90 - Nova Sound | NovaSoundTechnology | https://freesound.org/people/NovaSoundTechnology/sounds/118750 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| coup_de_pied.wav | coup de pied dans le ballon (bruit sourd) | 0,43 s | Ball Kick | Nicolas4677 | https://freesound.org/people/Nicolas4677/sounds/446639 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| foule_ohh.wav | « ohh » de foule déçue | 2,00 s | crowd `oh - - disappointed.mp3 | mrrap4food | https://freesound.org/people/mrrap4food/sounds/619007 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |
| tic_lettre.wav | frappe de machine à écrire (une touche) | 0,25 s | Typewriter - single key - type 2.wav | yottasounds | https://freesound.org/people/yottasounds/sounds/380137 | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ |

## Notes de montage

- `musique.wav` commence sur le premier temps fort (le morceau d'origine coupé à 0,548 s).
  Il est à 120 BPM : 1 temps = 0,5 s, 1 mesure = 2 s. Structure dans le fichier :
  couplet 0–16 s, refrain à pleine énergie ≈16–48 s, puis début du pont et fondu de 3 s jusqu'à 50 s.
  Les temps forts tombent sur 0, 2, 4, 6 s… (`debut_s` dans montage.json doit être un multiple de 2 s pour rester sur une mesure).
- Les sons `impact_*` et `whoosh_*` commencent à leur attaque (moins de 6 ms de silence).
  La montée commence très bas et finit sur sa crête, sans traîne : elle peut s'arrêter juste avant un impact.
- `reel.py` va chercher ses sons par préfixe : `impact`, `whoosh`, `montee`, `sifflet`, `clameur`, `musique`.
  C'est pour ça que les foules s'appellent `clameur_1/2`. Les sons `coup_de_pied`, `foule_ohh`
  et `tic_lettre` sont en plus. `reel.py` ne les charge pas tout seul.

## À coller dans la légende Instagram (seuls les sons CC BY sont obligatoires)

Si `musique.wav` est utilisée :

> Musique : « Path To Victory » par UNIVERSFIELD (freesound.org/s/704530), licence CC BY 4.0 (creativecommons.org/licenses/by/4.0)

Tout le reste est en CC0 : pas de crédit obligatoire. Une mention reste possible, par courtoisie :

> Sons : Freesound / Wikimedia Commons (CC0) — XHALE303, Rizzard, Kievinay, D4XX, LloydEvans09, qubodup, SpliceSound, 14FPanskaBubik_Lukas, jonsept, Pól, NovaSoundTechnology, Nicolas4677, mrrap4food, yottasounds
