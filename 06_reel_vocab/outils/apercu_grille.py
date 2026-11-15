# Aperçu « grille de profil » : recadrage 3:4 au centre + zones couvertes par Instagram
# (compteur de vues en bas à gauche, icône lecture en haut à droite)
import sys
from PIL import Image, ImageDraw
g = Image.open(sys.argv[1]).convert("RGB")
c = g.crop((0, 240, 1080, 1680))
d = ImageDraw.Draw(c, "RGBA")
d.rectangle((0, 1440 - 190, 1080, 1440), fill=(255, 0, 0, 70))      # bas : compteur de vues
d.rectangle((1080 - 170, 0, 1080, 170), fill=(255, 0, 0, 70))       # haut droit : icône lecture
d.text((20, 1440 - 60), "compteur de vues", fill=(255, 255, 255))
out = Image.new("RGB", (273 + 374, 485), "white")
out.paste(g.resize((273, 485)), (0, 0))
out.paste(c.resize((364, 485)), (283, 0))
out.save(sys.argv[2])
