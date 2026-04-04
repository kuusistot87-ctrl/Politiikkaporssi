#!/usr/bin/env python3
"""
hae_puoluerahoitus.py
Hakee usealta vuodelta listaussivut ja parsii kaikki puolueet automaattisesti.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

# Tunnetut puolueet — Y-tunnukset täydennetään automaattisesti listaussivulta
PUOLUEET_NIMET = {
    "Kansallinen Kokoomus":                   {"lyhenne": "KOK",  "ytunnus": None},
    "Perussuomalaiset":                        {"lyhenne": "PS",   "ytunnus": None},
    "Suomen Sosialidemokraattinen Puolue":     {"lyhenne": "SDP",  "ytunnus": None},
    "Suomen Keskusta":                         {"lyhenne": "KESK", "ytunnus": None},
    "Vihreä liitto":                           {"lyhenne": "VIHR", "ytunnus": None},
    "Vasemmistoliitto":                        {"lyhenne": "VAS",  "ytunnus": None},
    "Suomen ruotsalainen kansanpuolue":        {"lyhenne": "RKP",  "ytunnus": None},
    "Kristillisdemokraatit":                   {"lyhenne": "KD",   "ytunnus": None},
    "Liike Nyt":                               {"lyhenne": "LIIK", "ytunnus": None},
}

# Tunnetut Y-tunnukset varmuuden vuoksi
TUNNETUT_YTUNNUKSET = {
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

BASE_URL = "https://www.vaalirahoitusvalvonta.fi"
LISTA_BASE = BASE_URL + "/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset/ajantasaisetilmoitukset.html"

def hae_sivu(url, timeout=20):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PolitiikkaporssiBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        print(f"  HTTP {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  Virhe: {e}")
        return None

def parsii_rahasumma(teksti):
    if not teksti or ',' not in teksti:
        return None
    puhdas = re.sub(r'[^\d,]', '', teksti.strip()).replace(',', '.')
    try:
        arvo = float(puhdas)
        if 1000 <= arvo <= 10_000_000:
            return arvo
        return None
    except ValueError:
        return None

def keraa_linkit_ja_ytunnukset(lista_soup):
    """Kerää kaikki P_AI linkit ja niiden Y-tunnukset listaussivulta."""
    linkit = []
    ytunnukset_puolueittain = {}

    for a in lista_soup.find_all("a", href=True):
        href = a["href"]
        if "/P_AI_" not in href:
            continue
        if href.startswith("/"):
            href = BASE_URL + href

        # Pura Y-tunnus URL:sta: .../ajantasaisetilmoitukset/VUOSI/YTUNNUS/...
        m = re.search(r'/ajantasaisetilmoitukset/\d{4}/([^/]+)/', href)
        if m:
            ytunnus = m.group(1)
            # Etsi puolueen nimi h4-otsikosta
            # Käytetään tunnettua listaa
            if ytunnus not in [v for v in TUNNETUT_YTUNNUKSET.values()]:
                ytunnukset_puolueittain[ytunnus] = ytunnus

            if href not in linkit:
                linkit.append(href)

    return linkit

def hae_ilmoituslinkit(lista_soup, ytunnus):
    linkit = []
    for a in lista_soup.find_all("a", href=True):
        href = a["href"]
        if f"/{ytunnus}/" in href and "/P_AI_" in href:
            if href.startswith("/"):
                href = BASE_URL + href
            if href not in linkit:
                linkit.append(href)
    return linkit

def parsii_ilmoitus(soup, url):
    tulos = {
        "url": url,
        "ilmoitusaika": None,
        "kuukausi": None,
        "vuosi": None,
        "ilmoittaja": None,
        "tuet": [],
        "summa_yhteensa": 0.0,
    }

    m = re.search(r'/P_AI_(\d{4})(\d{2})\.html', url)
    if m:
        tulos["vuosi"] = int(m.group(1))
        tulos["kuukausi"] = int(m.group(2))

    for teksti in soup.stripped_strings:
        if "saapumispäivä" in teksti.lower():
            dm = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', teksti)
            if dm:
                tulos["ilmoitusaika"] = dm.group(1)
            break

    for t in soup.find_all("table"):
        for r in t.find_all("tr"):
            solut = r.find_all("td")
            if solut:
                nimi = solut[0].get_text(strip=True)
                if len(nimi) > 5 and not any(x in nimi.lower() for x in
                        ["kuukausi", "vuosi", "yritys", "etunimi", "saadun", "tuen"]):
                    tulos["ilmoittaja"] = nimi[:200]
                    break
        if tulos["ilmoittaja"]:
            break

    # Kaikki tukijat: sarake 0=Nimi, 1=Y-tunnus, 2=Tuen määrä
    for rivi in soup.find_all("tr"):
        solut = rivi.find_all("td")
        if len(solut) < 3:
            continue
        nimi = solut[0].get_text(strip=True)
        if len(nimi) < 3:
            continue
        if any(x in nimi.lower() for x in ["yrityksen", "etunimet", "ilmoitus sisältää"]):
            continue
        ytunnus_teksti = solut[1].get_text(strip=True) if len(solut) > 1 else ""
        ytunnus_m = re.search(r'\d{7}-\d', ytunnus_teksti)
        summa_teksti = solut[2].get_text(strip=True) if len(solut) > 2 else ""
        summa = parsii_rahasumma(summa_teksti)
        if summa:
            tulos["tuet"].append({
                "nimi": nimi[:200],
                "ytunnus": ytunnus_m.group() if ytunnus_m else None,
                "maara": summa,
            })
            tulos["summa_yhteensa"] += summa

    return tulos if (tulos["kuukausi"] or tulos["tuet"]) else None

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vuosi_nyt = datetime.now(timezone.utc).year

    output = {"paivitetty": nyt, "lahde": "vaalirahoitusvalvonta.fi", "puolueet": []}

    # Kerää linkit sekä kuluvan että edellisen vuoden listaussivulta
    kaikki_linkit_per_ytunnus = {}

    for vuosi in [vuosi_nyt - 1, vuosi_nyt]:
        # Listaussivu näyttää oletuksena kuluvan vuoden — haetaan myös 2025
        url = LISTA_BASE if vuosi == vuosi_nyt else \
              f"{BASE_URL}/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset/ajantasaisetilmoitukset/{vuosi}.html"
        print(f"Haetaan {vuosi} listaussivu: {url}")
        soup = hae_sivu(url if vuosi == vuosi_nyt else LISTA_BASE)
        if not soup:
            continue

        for lyhenne, ytunnus in TUNNETUT_YTUNNUKSET.items():
            linkit = hae_ilmoituslinkit(soup, ytunnus)
            if ytunnus not in kaikki_linkit_per_ytunnus:
                kaikki_linkit_per_ytunnus[ytunnus] = []
            for l in linkit:
                if l not in kaikki_linkit_per_ytunnus[ytunnus]:
                    kaikki_linkit_per_ytunnus[ytunnus].append(l)

    # Hae myös edellisen vuoden data suoraan URL-rakenteella
    print(f"\nHaetaan {vuosi_nyt-1} ilmoitukset suoraan URL:eilla...")
    for lyhenne, ytunnus in TUNNETUT_YTUNNUKSET.items():
        for kk in range(1, 13):
            url = (f"{BASE_URL}/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset"
                   f"/ajantasaisetilmoitukset/{vuosi_nyt-1}/{ytunnus}"
                   f"/P_AI_{vuosi_nyt-1}{kk:02d}.html")
            if url not in kaikki_linkit_per_ytunnus.get(ytunnus, []):
                if ytunnus not in kaikki_linkit_per_ytunnus:
                    kaikki_linkit_per_ytunnus[ytunnus] = []
                kaikki_linkit_per_ytunnus[ytunnus].append(url)

    # Parsii kaikki ilmoitukset
    for nimi_fi, tiedot in PUOLUEET_NIMET.items():
        lyhenne = tiedot["lyhenne"]
        ytunnus = TUNNETUT_YTUNNUKSET[lyhenne]
        print(f"\n=== {lyhenne} ({ytunnus}) ===")

        puolue_data = {
            "nimi": nimi_fi,
            "lyhenne": lyhenne,
            "ytunnus": ytunnus,
            "ilmoitukset": [],
            "summa_per_vuosi": {}
        }

        linkit = kaikki_linkit_per_ytunnus.get(ytunnus, [])
        print(f"  {len(linkit)} linkkiä")

        vuosi_summat = {}
        for linkki in linkit[:48]:
            s = hae_sivu(linkki)
            if not s:
                continue
            ilm = parsii_ilmoitus(s, linkki)
            if ilm and (ilm["tuet"] or ilm["kuukausi"]):
                puolue_data["ilmoitukset"].append(ilm)
                v = str(ilm.get("vuosi", "?"))
                vuosi_summat[v] = vuosi_summat.get(v, 0) + ilm["summa_yhteensa"]
                if ilm["summa_yhteensa"] > 0:
                    print(f"    {ilm['kuukausi']:02d}/{ilm['vuosi']} {ilm['ilmoittaja']}: {ilm['summa_yhteensa']:,.0f} €")

        puolue_data["summa_per_vuosi"] = {k: round(v, 2) for k, v in vuosi_summat.items() if v > 0}
        output["puolueet"].append(puolue_data)

    os.makedirs("rahoitus_json", exist_ok=True)
    with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Valmis: rahoitus_json/puoluerahoitus.json")

if __name__ == "__main__":
    main()
