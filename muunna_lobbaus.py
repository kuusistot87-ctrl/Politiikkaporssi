#!/usr/bin/env python3
"""
muunna_lobbaus.py
=================
Muuntaa avoimuusrekisterin Excel-tiedostot JSON-muotoon.

Aja: python muunna_lobbaus.py

Lukee kaikki avoimuusrekisteri*.xlsx tiedostot kansiosta
"Raportit avoimuusrekisterissä mainituista kohteista"
ja kirjoittaa JSON:t kansioon "lobbaus_json/".
"""

import pandas as pd, json, re, sys
from pathlib import Path
from collections import defaultdict

LAHDE  = Path("Raportit avoimuusrekisterissä mainituista kohteista")
KOHDE  = Path("lobbaus_json")

def parse_kausi(fname):
    m = re.search(r'ilmoituskausi-(\d{2})(\d{2})(\d{2})(\d{2})(\d{4})\.xlsx', fname)
    if not m: return None
    a_pv, a_kk, l_pv, l_kk, vuosi = m.groups()
    return {
        "id":       f"{vuosi}-{a_kk}",
        "label":    f"{a_pv}.{a_kk}–{l_pv}.{l_kk}.{vuosi}",
        "alku":     f"{vuosi}-{a_kk}-{a_pv}",
        "loppu":    f"{vuosi}-{l_kk}-{l_pv}",
        "tiedosto": f"{vuosi}-{a_kk}.json"
    }

def main():
    if not LAHDE.exists():
        print(f"VIRHE: Kansiota '{LAHDE}' ei löydy.", file=sys.stderr)
        sys.exit(1)

    KOHDE.mkdir(exist_ok=True)
    tiedostot = sorted(LAHDE.glob("avoimuusrekisteri*.xlsx"))
    if not tiedostot:
        print("VIRHE: Excel-tiedostoja ei löydy.", file=sys.stderr)
        sys.exit(1)

    print(f"Löydetty {len(tiedostot)} tiedostoa...")
    ke_aikasarja = defaultdict(list)
    kaudet = []

    for f in tiedostot:
        kausi = parse_kausi(f.name)
        if not kausi:
            print(f"  OHITETTU (ei tunnistettu kausi): {f.name}")
            continue

        df = pd.read_excel(f)
        df["Mainintojen määrä"] = pd.to_numeric(
            df["Mainintojen määrä"], errors="coerce"
        ).fillna(0).astype(int)

        # Kansanedustajat
        ke = df[df["Nimike"] == "Kansanedustaja"][["Nimi","Mainintojen määrä"]]
        ke_lista = sorted(
            [{"nimi": r["Nimi"], "maara": int(r["Mainintojen määrä"])} for _, r in ke.iterrows()],
            key=lambda x: -x["maara"]
        )

        # Organisaatiot (ryhmätason rivit)
        org_df = df[df["Nimike"] == "-"].groupby("Organisaatio")["Mainintojen määrä"].sum()
        org_lista = sorted(
            [{"org": k, "maara": int(v)} for k,v in org_df.items()],
            key=lambda x: -x["maara"]
        )[:20]

        # Per KE: organisaatiokohtaiset maininnat
        ke_org = {}
        for _, row in df[df["Nimike"] == "Kansanedustaja"].iterrows():
            nimi = row["Nimi"]
            org  = row["Organisaatio"]
            maara = int(row["Mainintojen määrä"])
            if nimi not in ke_org:
                ke_org[nimi] = []
            ke_org[nimi].append({"org": org, "maara": maara})

        kausi_json = {
            "kausi":           kausi,
            "kansanedustajat": ke_lista,
            "organisaatiot":   org_lista,
            "ke_org":          ke_org
        }

        out = KOHDE / kausi["tiedosto"]
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(kausi_json, fh, ensure_ascii=False, separators=(",",":"))

        for row in ke_lista:
            ke_aikasarja[row["nimi"]].append({
                "kausi_id":    kausi["id"],
                "kausi_label": kausi["label"],
                "maara":       row["maara"]
            })

        kaudet.append({
            **kausi,
            "ke_count":  len(ke_lista),
            "max_maara": max((x["maara"] for x in ke_lista), default=0)
        })
        print(f"  OK: {out.name} ({out.stat().st_size//1024}KB, {len(ke_lista)} edustajaa)")

    # Pääindeksi
    # Laske sijoitus viimeisimmässä kaudessa per KE
    viimeisin_kausi_id = max((k["id"] for k in kaudet), default="") if kaudet else ""
    viim_ke_jarjestys  = {}
    if viimeisin_kausi_id:
        viim_lista = sorted(
            [(nimi, next((k["maara"] for k in kl if k["kausi_id"]==viimeisin_kausi_id), 0))
             for nimi, kl in ke_aikasarja.items()],
            key=lambda x: -x[1]
        )
        viim_ke_jarjestys = {nimi: i+1 for i, (nimi,_) in enumerate(viim_lista) if _ > 0}
        viim_kausi_label  = next((k["label"] for k in kaudet if k["id"]==viimeisin_kausi_id), "")

    ke_yhteensa = {
        nimi: {
            "yhteensa":           sum(k["maara"] for k in kl),
            "kaudet":             sorted(kl, key=lambda x: x["kausi_id"]),
            "sijoitus_viimeisin": viim_ke_jarjestys.get(nimi),
            "sijoitus_kausi":     viim_kausi_label if nimi in viim_ke_jarjestys else ""
        }
        for nimi, kl in ke_aikasarja.items()
    }

    index_json = {
        "kaudet":          sorted(kaudet, key=lambda x: x["id"]),
        "kansanedustajat": ke_yhteensa
    }

    out_idx = KOHDE / "index.json"
    with open(out_idx, "w", encoding="utf-8") as f:
        json.dump(index_json, f, ensure_ascii=False, separators=(",",":"))

    print(f"\nValmis!")
    print(f"  Pääindeksi:  {out_idx}  ({out_idx.stat().st_size//1024}KB)")
    print(f"  Kaudet:      {[k['id'] for k in kaudet]}")
    print(f"  Edustajia:   {len(ke_yhteensa)}")

    top5 = sorted(ke_yhteensa.items(), key=lambda x: -x[1]["yhteensa"])[:5]
    print("\n  Top 5 (kaikki kaudet):")
    for nimi, d in top5:
        print(f"    {nimi}: {d['yhteensa']} mainintaa")

if __name__ == "__main__":
    main()
