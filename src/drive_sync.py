"""Synchronise les fichiers sources (Réalisé / EF) depuis Google Drive vers
sources/, en utilisant un compte de service Google Cloud (lecture seule).

Ce script est conçu pour tourner dans GitHub Actions (voir
.github/workflows/drive-sync.yml) : il lit la clé JSON du compte de service
depuis la variable d'environnement GDRIVE_SA_KEY (un secret GitHub Actions),
parcourt récursivement le(s) dossier(s) Drive configurés pour chaque
concessionnaire, et télécharge tout fichier .xlsx / .xlsm nouveau ou modifié
dans sources/. Un fichier .drive_manifest.json (dans sources/) garde la trace
de ce qui a déjà été synchronisé (par id Drive + date de modification) pour
éviter de retélécharger inutilement.

Le nom du concessionnaire n'a pas besoin d'être deviné à partir du nom de
fichier : extract.py identifie déjà chaque dépôt à partir du nom de la
compagnie contenu DANS le fichier (voir canonicalize_dealer). Ce script se
contente donc de garder sources/ à jour ; l'extraction et la reconstruction
du tableau de bord restent gérées par le pipeline existant
(update-dashboard.yml, déclenché automatiquement par le push sur sources/**).
"""

import io
import json
import os
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Adresse d'un utilisateur interne (Google Workspace) que le compte de
# service va "impersonater" grâce à la délégation à l'échelle du domaine
# (Admin Console > Sécurité > Contrôles des API > Délégation à l'échelle du
# domaine). Cet utilisateur a déjà accès en lecture à tous les dossiers
# Drive des concessionnaires, donc aucun partage individuel n'est requis.
IMPERSONATE_USER = "mallard@groupeautomax.com"

SOURCES_DIR = "sources"
MANIFEST_PATH = os.path.join(SOURCES_DIR, ".drive_manifest.json")

# Extensions/mimetypes qu'on accepte de télécharger -- ce sont les seuls
# formats que extract.py sait lire (voir extract_any_file).
ACCEPTED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel.sheet.macroenabled.12": "xlsm",
}

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# Un dossier Drive racine par concessionnaire. Chaque racine est parcourue
# récursivement (sous-dossiers compris, ex: BMW/STM organisent leurs
# "Réalisé" par année) jusqu'à MAX_DEPTH niveaux, pour éviter de partir dans
# des arborescences sans fin si un dossier partagé est trop large.
#
# Pour ajouter/corriger un concessionnaire : mettre à jour "roots" avec l'ID
# du dossier Drive à surveiller (visible dans l'URL du dossier :
# https://drive.google.com/drive/folders/<ID>). Le dossier doit être partagé
# en Lecteur avec l'adresse du compte de service (voir README du secret
# GDRIVE_SA_KEY).
DEALER_SOURCES = [
    {
        "key": "bmw",
        "label": "BMW Sherbrooke",
        "roots": ["1CVp1bMr8TP_XTCxKPLVTlSVq2VAYjbZh"],  # a) Réalisé (BMW)
    },
    {
        "key": "stm",
        "label": "STM (Ste-Marie Auto)",
        "roots": [
            "1SSfs-x-9Cmrtw075Qsbzgm7J-Uq0TyHu",  # a) Réalisé (STM)
            "1ui-xvQYYO-dAWFaBnfhh2J4Qs05n7K4z",  # États financiers GM (STM) : 2025/, 2026/
        ],
    },
    {
        "key": "hawks",
        "label": "HAWKS",
        "roots": [
            "1F8C7xbjash5b4j53lcCH-Sw15TicrkQ3",  # 2026_EF_HAWKS
            "1-LMakwOxmlqn0IJCWoI_SL4Wpc8gJheB",  # 2025_EF_HAWKS
        ],
    },
    {
        "key": "vw",
        "label": "Volkswagen Brossard",
        "roots": ["0AMpyfj_TcWfvUk9PVA"],  # Drive partagé "VW Brossard"
    },
    {
        "key": "hyundai",
        "label": "Hyundai Longueuil",
        # Réalisés et états financiers Hyundai Canada (HYUNDAILONGUEUIL<MM><AAAA>.xlsm)
        "roots": ["0AP3GdpOFlum2Uk9PVA"],  # Drive partagé "Hyundai Longueuil"
    },
]

MAX_DEPTH = 5

# Sous-dossiers de brouillons à ne jamais synchroniser (ex. « Version
# incomplète » dans les états financiers de STM).
SKIP_FOLDER_RE = re.compile(r"version incompl|brouillon", re.IGNORECASE)


def is_lock_file(name):
    """Fichiers de verrouillage d'Office (« ~$classeur.xlsx ») et de
    LibreOffice (« .~lock… ») : quelques octets sans données. Leur nom
    nettoyé est identique à celui du vrai classeur, ils l'écrasaient donc dans
    sources/ (ex. Réalisés Hyundai d'avril, mai et juillet 2026)."""
    return name.startswith("~$") or name.startswith(".~lock")


def is_valid_workbook(path):
    import zipfile
    return os.path.exists(path) and zipfile.is_zipfile(path)


def build_drive_service():
    raw_key = os.environ.get("GDRIVE_SA_KEY")
    if not raw_key:
        print("ERREUR: la variable d'environnement GDRIVE_SA_KEY est vide ou absente.",
              file=sys.stderr)
        sys.exit(1)
    info = json.loads(raw_key)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    # Impersonation via la délégation à l'échelle du domaine : le compte de
    # service agit "comme si" c'était IMPERSONATE_USER, qui a déjà accès en
    # lecture à tous les dossiers Drive des concessionnaires. Ça évite
    # d'avoir à partager individuellement chaque dossier avec le compte de
    # service.
    creds = creds.with_subject(IMPERSONATE_USER)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_children(service, folder_id):
    """Liste tous les enfants (fichiers + dossiers) d'un dossier Drive,
    en gérant la pagination et les Drive partagés."""
    items = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            pageSize=200,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageToken=page_token,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def walk(service, folder_id, depth=0):
    """Parcourt récursivement folder_id et renvoie la liste des fichiers
    Excel/xlsm trouvés (dicts avec id/name/mimeType/modifiedTime)."""
    if depth > MAX_DEPTH:
        return []
    found = []
    for item in list_children(service, folder_id):
        if item["mimeType"] == FOLDER_MIME_TYPE:
            if SKIP_FOLDER_RE.search(item["name"]):
                continue
            found.extend(walk(service, item["id"], depth + 1))
        elif item["mimeType"] in ACCEPTED_MIME_TYPES and not is_lock_file(item["name"]):
            found.append(item)
    return found


def sanitize_filename(name):
    # Enlève les accents/caractères spéciaux pour un nom de fichier sûr en CI.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_")


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    os.makedirs(SOURCES_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)


def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    with open(dest_path, "wb") as f:
        f.write(buf.getvalue())


def main():
    service = build_drive_service()
    manifest = load_manifest()
    os.makedirs(SOURCES_DIR, exist_ok=True)

    # Nettoyage : on oublie les fichiers de verrouillage déjà synchronisés et
    # on supprime ceux qui n'avaient pas de vrai classeur au même chemin.
    lock_ids = [fid for fid, e in manifest.items() if is_lock_file(e.get("name", ""))]
    for fid in lock_ids:
        entry = manifest.pop(fid)
        lp = entry.get("local_path")
        still_used = any(e.get("local_path") == lp for e in manifest.values())
        if lp and not still_used and os.path.exists(lp):
            os.remove(lp)
            print(f"supprimé (fichier de verrouillage) : {lp}")

    # Plusieurs fichiers Drive qui partageaient le même chemin local (ancien
    # comportement) : le plus récent garde le chemin, les autres seront
    # retéléchargés sous un nom unique.
    by_path = {}
    for fid, e in manifest.items():
        if e.get("local_path"):
            by_path.setdefault(e["local_path"], []).append(fid)
    for lp, fids in by_path.items():
        if len(fids) < 2:
            continue
        fids.sort(key=lambda fid: manifest[fid].get("modifiedTime") or "", reverse=True)
        manifest[fids[0]]["modifiedTime"] = None  # contenu actuel incertain : on le retélécharge
        for fid in fids[1:]:
            manifest[fid]["local_path"] = None
            manifest[fid]["modifiedTime"] = None

    downloaded = []
    unchanged = 0
    errors = []

    for dealer in DEALER_SOURCES:
        for root_id in dealer["roots"]:
            try:
                files = walk(service, root_id)
            except Exception as exc:  # noqa: BLE001 - on veut logguer et continuer
                errors.append(f"{dealer['label']} (dossier {root_id}): {exc}")
                continue

            for f in files:
                file_id = f["id"]
                ext = ACCEPTED_MIME_TYPES[f["mimeType"]]
                entry = manifest.get(file_id)

                # Un fichier local corrompu (ex. écrasé par un fichier de
                # verrouillage) est retéléchargé même si Drive n'a pas changé.
                if entry and entry.get("modifiedTime") == f["modifiedTime"] \
                        and is_valid_workbook(entry.get("local_path", "")):
                    unchanged += 1
                    continue

                if entry and entry.get("local_path"):
                    local_path = entry["local_path"]  # même fichier Drive : même chemin
                else:
                    safe_name = sanitize_filename(f["name"])
                    local_path = os.path.join(
                        SOURCES_DIR, f"{dealer['key']}_{safe_name}"
                    )
                    if not local_path.lower().endswith("." + ext):
                        local_path += "." + ext
                    # Deux fichiers Drive différents ne partagent jamais le
                    # même chemin local.
                    taken = {e.get("local_path") for fid, e in manifest.items() if fid != file_id}
                    if local_path in taken:
                        root, extension = os.path.splitext(local_path)
                        local_path = f"{root}__{file_id[:8]}{extension}"

                try:
                    download_file(service, file_id, local_path)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{dealer['label']} / {f['name']}: {exc}")
                    continue

                manifest[file_id] = {
                    "dealer": dealer["key"],
                    "name": f["name"],
                    "modifiedTime": f["modifiedTime"],
                    "local_path": local_path,
                }
                downloaded.append(local_path)
                print(f"[{dealer['label']}] téléchargé/mis à jour: {local_path}")

    save_manifest(manifest)

    print("---")
    print(f"Fichiers téléchargés/mis à jour: {len(downloaded)}")
    print(f"Fichiers déjà à jour (ignorés): {unchanged}")
    if errors:
        print(f"Erreurs ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    # On ne fait jamais échouer le job pour une erreur ponctuelle sur un
    # concessionnaire (ex: dossier pas encore partagé) -- le but est de
    # synchroniser ce qui est disponible et de laisser une trace claire
    # dans les logs pour le reste.
    return 0


if __name__ == "__main__":
    sys.exit(main())
