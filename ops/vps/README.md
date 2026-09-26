# Studio vidéo sur le VPS

Le Studio HyperFrames et la page de voix off tournent sur le VPS, derrière une adresse en https
protégée par un mot de passe. Le code des montages vient de GitHub ; les médias (vidéos, images,
sons, polices, rendus, prises de voix off) vivent dans Google Drive.

| Où | Quoi |
|---|---|
| GitHub | les montages HTML, les scripts, la charte |
| Google Drive (`Videos/`) | les médias, rangés comme dans le dépôt : `Videos/10_cern/assets/exterieur.mp4` |
| VPS | le Studio (`https://<adresse>/`) et la voix off (`https://<adresse>/enregistrement/10_cern/enregistrer.html`) |

Toutes les 3 minutes, le VPS :
1. récupère le code depuis GitHub ;
2. copie les nouveaux médias du Drive vers le VPS ;
3. copie les rendus (`renders/`) et les prises de voix off (`voix-off/`) du VPS vers le Drive.

Rien n'est jamais supprimé automatiquement, d'un côté comme de l'autre.

## Installation (Ubuntu ou Debian, 4 Go de RAM conseillés)

```bash
curl -fsSL https://raw.githubusercontent.com/monodf-beep/cr-ation-audiovisuelle/claude/hyperframe-installation-o3hduz/ops/vps/installer.sh -o installer.sh
sudo MOT_DE_PASSE='choisir-un-mot-de-passe' bash installer.sh
```

L'adresse par défaut est `<ip-du-vps>.sslip.io` : elle pointe déjà vers le VPS, et le https est
obtenu automatiquement. Pour un sous-domaine à vous, le faire pointer vers l'IP du VPS, puis
relancer l'installation avec `DOMAINE=studio.exemple.eu` devant `bash`.

Autres réglages possibles devant `bash` : `UTILISATEUR=` (identifiant, `franck` par défaut),
`PROJET=` (projet ouvert dans le Studio), `DRIVE=` (dossier Drive, `drive:Videos` par défaut).

## Relier Google Drive (une seule fois)

Le VPS n'a pas de navigateur : on autorise Google depuis l'ordinateur.

1. Sur l'ordinateur, installer rclone. Sous Windows, dans PowerShell : `winget install Rclone.Rclone`.
2. Sur le VPS :
   ```bash
   sudo -u studio rclone config
   ```
   Répondre : `n` (nouveau), nom `drive`, type `drive`, laisser *client_id* et *client_secret* vides,
   *scope* `1` (accès complet), laisser le reste par défaut, puis **`n`** à « Use web browser to
   automatically authenticate ».
3. rclone affiche une commande `rclone authorize "drive" "…"`. La copier dans PowerShell sur
   l'ordinateur : le navigateur s'ouvre, choisir le compte Google et autoriser.
4. PowerShell affiche un code : le recopier dans le VPS, là où rclone l'attend, puis valider jusqu'à la fin.
5. Créer le dossier `Videos` dans Google Drive et y déposer les médias, rangés comme dans le dépôt
   (`Videos/10_cern/assets/…`, `Videos/10_cern/renders/…`).
6. Lancer une première synchronisation sans attendre : `sudo systemctl start studio-synchro`.

## Au quotidien

- **Changer de projet dans le Studio** : `sudo studio-projet 08_hyperframes`.
- **Forcer la synchronisation** : `sudo systemctl start studio-synchro`.
- **Voir ce qui se passe** : `journalctl -u studio-hf -u studio-enregistrement -u studio-synchro -f`.
- **Rendre une vidéo sur le VPS** : `sudo -u studio bash -c 'cd /srv/studio/depot/10_cern && npm run render'`
  (le MP4 part ensuite dans `Videos/10_cern/renders/`).
- **Voix off** : chaque prise est envoyée sur le serveur dès qu'on clique sur « Arrêter », puis
  copiée dans `Videos/10_cern/voix-off/`.
