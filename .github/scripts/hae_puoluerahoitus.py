#!/usr/bin/env python3
"""
hae_puoluerahoitus.py — uusi versio
Lataa CSV-tiedostot suoraan vaalirahoitusvalvonta.fi:stä.
Paljon yksinkertaisempi kuin HTML-parsinta!
"""

import requests
import csv
import json
import os
import io
from datetime import datetime, timezone

BASE = "https://www.vaalirahoitusvalvonta.fi/fi/index/puoluerahoitus/haetietoailmoituksista/tietoaineistot"

# Vuodet joilta haetaan data
VUODET = list(range(2010, 2027))

# Tunnistetaan pääpuolueet nimen perusteella
PUOLUEET_MAP = {
    "Kansallinen Kokoomus r.p.":                    "KOK",
    "Perussuomalaiset r.p.":                        "PS",
    "Suomen Sosialidemokraattinen Puolue r.p.":     "SDP",
    "Suomen Keskusta r.p.":                         "KESK",
    "Vihreä liitto r.p.":                           "VIHR",
    "Vasemmistoliitto r.p.":                        "VAS",
    "Suomen ruotsalainen kansanpuolue r.p.":        "RKP",
    "Suomen Kristillisdemokraatit (KD) R.P.":       "KD",
    "Liike Nyt r.p.":                               "LIIK",
}

# Pääpuolueiden Y-tunnukset
PUOLUEET_YTUNNUS = {
    "KOK":  "0213498-5",
    "PS":   "0699608-4",
    "SDP":  "0117005-2",
    "KESK": "0179288-7",
    "VIHR": "0202918-5",
    "VAS":  "0802437-3",
    "RKP":  "0215325-4",
    "KD":   "0117098-5",
    "LIIK": "3046798-7",
}

def hae_csv(vuosi):
    url = f"{BASE}/{vuosi}_ajantasaiset_ilmoitukset.csv"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PolitiikkaporssiBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  ✅ {vuosi}: {len(resp.content)} tavua")
            # CSV on UTF-8 tai latin-1
            try:
                return resp.content.decode("utf-8-sig")
            except:
                return resp.content.decode("latin-1")
        print(f"  ❌ {vuosi}: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"  ❌ {vuosi}: {e}")
        return None

def parsii_csv(teksti, vuosi):
    """Parsii CSV ja palauttaa rivit listana."""
    rivit = []
    reader = csv.reader(io.StringIO(teksti), delimiter=";")
    otsikkorivi = None
    for i, rivi in enumerate(reader):
        if i == 0:
            otsikkorivi = rivi
            continue
        if len(rivi) < 9:
            continue
        rivit.append(rivi)
    print(f"    {len(rivit)} datariviä")
    return rivit, otsikkorivi

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Kerää kaikki data
    kaikki_rivit = []
    for vuosi in VUODET:
        print(f"\nHaetaan {vuosi}...")
        teksti = hae_csv(vuosi)
        if not teksti:
            continue
        rivit, _ = parsii_csv(teksti, vuosi)
        for r in rivit:
            kaikki_rivit.append((vuosi, r))

    print(f"\nYhteensä {len(kaikki_rivit)} riviä")

    # Ryhmittele pääpuolueittain
    # CSV-sarakkeet: 0=saapumispvm, 2=ilmoittajan nimi, 3=rekisteritunnus,
    #                4=kuukausi, 5=vuosi, 6=tuen antajan nimi, 7=y-tunnus, 8=summa
    puolue_data = {}
    for lyhenne in PUOLUEET_YTUNNUS:
        puolue_data[lyhenne] = {
            "ilmoitukset": [],
            "tuet_per_vuosi": {},
            "tukijat": {}  # nimi -> kokonaissumma
        }

    for vuosi_csv, rivi in kaikki_rivit:
        ilmoittaja = rivi[2].strip() if len(rivi) > 2 else ""
        rekisteritunnus = rivi[3].strip() if len(rivi) > 3 else ""

        # Tunnista puolue nimen tai Y-tunnuksen perusteella
        lyhenne = None
        if ilmoittaja in PUOLUEET_MAP:
            lyhenne = PUOLUEET_MAP[ilmoittaja]
        else:
            for l, ytunnus in PUOLUEET_YTUNNUS.items():
                if rekisteritunnus == ytunnus:
                    lyhenne = l
                    break

        if not lyhenne:
            continue  # ei pääpuolue

        try:
            kuukausi = int(rivi[4]) if rivi[4].strip() else None
            vuosi = int(rivi[5]) if rivi[5].strip() else vuosi_csv
            tuen_antaja = rivi[6].strip() if len(rivi) > 6 else ""
            tuen_antaja_ytunnus = rivi[7].strip() if len(rivi) > 7 else ""
            summa_str = rivi[8].strip().replace(",", ".").replace(" ", "") if len(rivi) > 8 else ""
            summa = float(summa_str) if summa_str else 0.0
        except (ValueError, IndexError):
            continue

        if summa <= 0:
            continue

        v = str(vuosi)
        if v not in puolue_data[lyhenne]["tuet_per_vuosi"]:
            puolue_data[lyhenne]["tuet_per_vuosi"][v] = 0.0
        puolue_data[lyhenne]["tuet_per_vuosi"][v] += summa

        # Tukijatilasto
        if tuen_antaja:
            if tuen_antaja not in puolue_data[lyhenne]["tukijat"]:
                puolue_data[lyhenne]["tukijat"][tuen_antaja] = {"ytunnus": tuen_antaja_ytunnus, "summa": 0.0}
            puolue_data[lyhenne]["tukijat"][tuen_antaja]["summa"] += summa

        puolue_data[lyhenne]["ilmoitukset"].append({
            "saapunut": rivi[0].strip() if rivi[0].strip() else None,
            "kuukausi": kuukausi,
            "vuosi": vuosi,
            "tuen_antaja": tuen_antaja,
            "tuen_antaja_ytunnus": tuen_antaja_ytunnus,
            "summa": summa,
        })

    # Rakenna output
    output = {
        "paivitetty": nyt,
        "lahde": "vaalirahoitusvalvonta.fi — CSV-tietoaineistot",
        "vuodet": [str(v) for v in VUODET],
        "puolueet": []
    }

    for nimi_fi, lyhenne in [
        ("Kansallinen Kokoomus", "KOK"),
        ("Perussuomalaiset", "PS"),
        ("Suomen Sosialidemokraattinen Puolue", "SDP"),
        ("Suomen Keskusta", "KESK"),
        ("Vihreä liitto", "VIHR"),
        ("Vasemmistoliitto", "VAS"),
        ("Suomen ruotsalainen kansanpuolue", "RKP"),
        ("Kristillisdemokraatit", "KD"),
        ("Liike Nyt", "LIIK"),
    ]:
        d = puolue_data[lyhenne]
        # Top 10 tukijat
        top_tukijat = sorted(
            [{"nimi": k, **v} for k, v in d["tukijat"].items()],
            key=lambda x: x["summa"], reverse=True
        )[:20]

        output["puolueet"].append({
            "nimi": nimi_fi,
            "lyhenne": lyhenne,
            "ytunnus": PUOLUEET_YTUNNUS[lyhenne],
            "ilmoituksia": len(d["ilmoitukset"]),
            "tuet_per_vuosi": {k: round(v, 2) for k, v in sorted(d["tuet_per_vuosi"].items())},
            "top_tukijat": top_tukijat,
        })

        vuosi_str = ", ".join(f"{k}: {v/1000:.0f}k€" for k, v in sorted(d["tuet_per_vuosi"].items()))
        print(f"  {lyhenne}: {len(d['ilmoitukset'])} ilmoitusta | {vuosi_str}")

    os.makedirs("rahoitus_json", exist_ok=True)
    with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Tallennettu: rahoitus_json/puoluerahoitus.json")

if __name__ == "__main__":
    main()
