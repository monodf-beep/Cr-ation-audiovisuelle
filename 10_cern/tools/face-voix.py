"""Image de la prise filmee, montee exactement comme la voix (memes coupes que tools/couper-voix.py),
pour que les plans face camera restent synchrones avec la voix off.
Chaque morceau garde l'image jusqu'au morceau suivant : les respirations ajoutees au montage montrent
la suite naturelle de la prise, sans image figee. Image traitee comme ops/vps/traiter-prises.sh
(eclaircie, rechauffee, recadree en vertical 1080 x 1920, 30 images/s). Pas de son : il est dans voix-off.mp3.
Usage : python3 tools/face-voix.py <prise.webm> <voix-montee.json> <sortie.mp4>"""
import json, subprocess, sys

prise, table, sortie = sys.argv[1:4]
coupes = json.load(open(table))["coupes"]
duree = json.load(open(table))["duree"]

IMAGE = ("hqdn3d=3:3:4:4,eq=gamma=1.35:contrast=1.06:saturation=1.08:brightness=0.02,"
         "colortemperature=temperature=5200,crop=trunc(ih*9/16/2)*2:ih,scale=1080:1920:flags=lanczos,unsharp=5:5:0.6")

# La webm de la webcam a une base de temps de 1000 images/s : on repasse a 30 une fois, puis on coupe
# en numeros d'image, calcules sur le montage pour que les arrondis ne s'accumulent pas (synchro labiale).
filtres, entrees = [f"[0:v]fps=30,split={len(coupes)}" + "".join(f"[s{i}]" for i in range(len(coupes)))], []
for i, c in enumerate(coupes):
    x = c["source"][0]
    fin_montage = coupes[i + 1]["montage"][0] if i + 1 < len(coupes) else duree
    n = round(fin_montage * 30) - round(c["montage"][0] * 30)
    filtres.append(f"[s{i}]trim=start_frame={round(x * 30)}:end_frame={round(x * 30) + n},setpts=PTS-STARTPTS[v{i}]")
    entrees.append(f"[v{i}]")
filtres.append("".join(entrees) + f"concat=n={len(entrees)}:v=1:a=0,{IMAGE}[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", prise, "-filter_complex", ";".join(filtres), "-map", "[out]",
                "-an", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30",
                "-movflags", "+faststart", sortie], check=True)
print(f"face camera : {sortie} ({duree:.1f} s, {len(coupes)} morceaux)")
