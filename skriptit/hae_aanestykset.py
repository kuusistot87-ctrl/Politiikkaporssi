#!/usr/bin/env python3
"""
hae_aanestykset.py — Hakee kansanedustajien äänestyshistorian
eduskunnan avoimesta datasta ja tallentaa JSON-tiedostoihin.

API-sarakkeet: EdustajaId, AanestysId, EdustajaEtunimi, EdustajaSukunimi,
               EdustajaHenkiloNumero, EdustajaRyhmaLyhenne, EdustajaAanestys

Haku: EdustajaHenkiloNumero (löytyy index.json:n eduskunta-linkistä)
Ajo:  python skriptit/hae_aanestykset.py
"""

import json, os, re, time, urllib.request, urllib.parse
from datetime import datetime

API_BASE   = "https://avoindata.eduskunta.fi/api/v1/tables"
ROOT       = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR    = os.path.join(ROOT, "aanestykset_json")
INDEX_FILE = os.path.join(ROOT, "edustajat_json", "index.json")

PER_SIVU = 100
SIVUJA   = 3      # 300 viimeisintä äänestystä
VIIVE    = 0.35

def hae_json(url):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Politiikkaporssi/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:150]
        print(f"  VIRHE {e.code}: {body}")
        return None
    except Exception as e:
        print(f"  VIRHE: {e}")
        return None

def ascii_slug(nimi):
    """Muuntaa nimen ASCII-tiedostonimeksi: skandit korvataan, välilyönnit alaviivaksi."""
    korvaukset = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    s = ''.join(korvaukset.get(c, c) for c in nimi)
    return s.replace(' ', '_')

def henkilo_numero(eduskunta_url):
    """Poimii henkilönumeron eduskunta.fi-URL:sta, esim. /1234567.aspx → 1234567"""
    m = re.search(r"/(\d+)\.aspx", eduskunta_url or "")
    return m.group(1) if m else None

def hae_aanestykset(henkilonro):
    """Hakee äänestykset EdustajaHenkiloNumero-sarakkeella."""
    kaikki, sarakkeet = [], []
    for sivu in range(SIVUJA):
        url = (f"{API_BASE}/SaliDBAanestysEdustaja/rows"
               f"?columnName=EdustajaHenkiloNumero"
               f"&columnValue={henkilonro}"
               f"&page={sivu}&perPage={PER_SIVU}")
        data = hae_json(url)
        if not data:
            break
        if not sarakkeet:
            sarakkeet = data.get("columnNames", [])
        rivit = data.get("rowData", [])
        kaikki.extend(rivit)
        if len(rivit) < PER_SIVU:
            break
        time.sleep(VIIVE)
    return sarakkeet, kaikki

def laske_yhteenveto(sarakkeet, rivit):
    if not sarakkeet or not rivit:
        return {"jaa": 0, "ei": 0, "tyhjaa": 0, "poissa": 0, "yhteensa": 0}
    idx = sarakkeet.index("EdustajaAanestys") if "EdustajaAanestys" in sarakkeet else -1
    if idx < 0:
        return {"jaa": 0, "ei": 0, "tyhjaa": 0, "poissa": 0, "yhteensa": len(rivit)}
    laskurit = {"Jaa": 0, "Ei": 0, "Tyhjää": 0, "Poissa": 0}
    for rivi in rivit:
        a = (rivi[idx] or "Poissa").strip()
        laskurit[a] = laskurit.get(a, 0) + 1
    return {
        "jaa":      laskurit.get("Jaa", 0),
        "ei":       laskurit.get("Ei", 0),
        "tyhjaa":   laskurit.get("Tyhjää", 0),
        "poissa":   laskurit.get("Poissa", 0),
        "yhteensa": len(rivit)
    }

def muodosta_lista(sarakkeet, rivit, max_n=50):
    if not sarakkeet or not rivit:
        return []
    def g(rivi, nimi):
        i = sarakkeet.index(nimi) if nimi in sarakkeet else -1
        return (rivi[i] or "").strip() if i >= 0 and i < len(rivi) else ""

    lista = []
    for rivi in rivit[:max_n]:
        aani   = g(rivi, "EdustajaAanestys") or "Poissa"
        aan_id = g(rivi, "AanestysId")
        lista.append({
            "id":      aan_id,
            "otsikko": f"Äänestys {aan_id}",
            "aani":    aani,
            "pvm":     ""
        })
    return lista

def rikasta_otsikot(lista):
    """Hakee äänestyksen otsikot SaliDBAanestys-taulusta (KieliId=1 = suomi)."""
    cache = {}
    for item in lista:
        aan_id = item.get("id", "")
        if not aan_id or aan_id in cache:
            continue
        # KieliId=1 = suomenkielinen rivi
        url = (f"{API_BASE}/SaliDBAanestys/rows"
               f"?columnName=AanestysId&columnValue={aan_id}&page=0&perPage=2")
        data = hae_json(url)
        if data:
            cols  = data.get("columnNames", [])
            rivit = data.get("rowData", [])
            # Etsi suomenkielinen rivi (KieliId=1)
            rivi_fi = None
            for r in rivit:
                if cols and "KieliId" in cols:
                    ki = cols.index("KieliId")
                    if ki < len(r) and str(r[ki]).strip() == "1":
                        rivi_fi = r
                        break
            if not rivi_fi and rivit:
                rivi_fi = rivit[0]
            if rivi_fi:
                def g(n):
                    i = cols.index(n) if n in cols else -1
                    return (rivi_fi[i] or "").strip() if i >= 0 and i < len(rivi_fi) else ""
                # Paras otsikko: KohtaOtsikko on lain nimi, AanestysOtsikko on äänestyksen tyyppi
                kohta   = g("KohtaOtsikko")
                aanots  = g("AanestysOtsikko")
                hevp    = g("AanestysValtiopaivaasia")   # esim. "HE 157/2025 vp"
                pvm     = g("IstuntoPvm")[:10] if g("IstuntoPvm") else ""
                # Yhdistä: "HE 157/2025 vp — Lain otsikko"
                if kohta and hevp:
                    otsikko = f"{hevp} — {kohta}"
                elif kohta:
                    otsikko = kohta
                elif aanots:
                    otsikko = aanots
                else:
                    otsikko = f"Äänestys {aan_id}"
                url_polku = g("Url")  # esim. /aanestystulos/1/25/2026
                cache[aan_id] = {"otsikko": otsikko[:140], "pvm": pvm, "url": url_polku}
        time.sleep(VIIVE)

    for item in lista:
        if item["id"] in cache:
            item["otsikko"] = cache[item["id"]]["otsikko"]
            item["pvm"]     = cache[item["id"]]["pvm"]
            item["url"]     = cache[item["id"]].get("url", "")
    return lista

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(INDEX_FILE):
        print(f"VIRHE: {INDEX_FILE} ei löydy.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        kaikki = json.load(f)

    nykyiset = [m for m in kaikki if m.get("nykyinen") and m.get("eduskunta")]
    print(f"Haetaan äänestysdata {len(nykyiset)} nykyiselle edustajalle...\n")

    onnistuneet, epaonnistuneet = 0, []

    for i, ed in enumerate(nykyiset, 1):
        nimi  = ed.get("nimi", "")
        slug  = ascii_slug(nimi)
        nro   = henkilo_numero(ed.get("eduskunta", ""))
        out   = os.path.join(OUT_DIR, f"{slug}.json")

        print(f"[{i:3}/{len(nykyiset)}] {nimi} (nro:{nro})...", end=" ", flush=True)

        if not nro:
            print("ei henkilönumeroa")
            epaonnistuneet.append(nimi)
            continue

        sarakkeet, rivit = hae_aanestykset(nro)

        if not rivit:
            print("ei dataa")
            epaonnistuneet.append(nimi)
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"nimi": nimi, "yhteenveto": {}, "aanestykset": [],
                           "paivitetty": datetime.now().strftime("%Y-%m-%d")}, f, ensure_ascii=False)
            continue

        yht   = laske_yhteenveto(sarakkeet, rivit)
        lista = muodosta_lista(sarakkeet, rivit)
        lista = rikasta_otsikot(lista)

        tulos = {"nimi": nimi, "yhteenveto": yht, "aanestykset": lista,
                 "paivitetty": datetime.now().strftime("%Y-%m-%d")}

        with open(out, "w", encoding="utf-8") as f:
            json.dump(tulos, f, ensure_ascii=False, indent=2)

        print(f"✓ {yht['yhteensa']} (Jaa:{yht['jaa']} Ei:{yht['ei']} Poissa:{yht['poissa']})")
        onnistuneet += 1
        time.sleep(VIIVE)

    with open(os.path.join(OUT_DIR, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"paivitetty": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "edustajia": onnistuneet, "epaonnistuneet": epaonnistuneet},
                  f, ensure_ascii=False, indent=2)

    print(f"\n✅ Valmis! {onnistuneet}/{len(nykyiset)} edustajaa haettu.")
    if epaonnistuneet:
        print(f"⚠️  Epäonnistuneet ({len(epaonnistuneet)}): {', '.join(epaonnistuneet[:5])}")

if __name__ == "__main__":
    main()
