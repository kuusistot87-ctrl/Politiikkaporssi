#!/usr/bin/env python3
"""
luo_hakemisto.py
================
Aja tämä skripti samassa kansiossa kuin index.html:

    python luo_hakemisto.py

Lukee kaikki JSON-tiedostot edustajat_json/-kansiosta
ja luo edustajat_json/index.json -hakemistotiedoston.
Merkitsee nykyiset 200 kansanedustajaa (2023-2027) oikein.
"""

import json, re, sys
from pathlib import Path

KANSIO = Path("edustajat_json")

# ── Nykyiset 200 kansanedustajaa (2023–2027) nimi → vaalipiiri ──
NYKYISET = {
    "Alviina Alametsä":"Helsinki","Eva Biaudet":"Helsinki","Maaret Castrén":"Helsinki",
    "Fatim Diarra":"Helsinki","Elisa Gebhard":"Helsinki","Tuula Haatainen":"Helsinki",
    "Jussi Halla-aho":"Helsinki","Timo Harakka":"Helsinki","Atte Harjanne":"Helsinki",
    "Eveliina Heinäluoma":"Helsinki","Mari Holopainen":"Helsinki","Veronika Honkasalo":"Helsinki",
    "Atte Kaleva":"Helsinki","Mai Kivelä":"Helsinki","Minja Koskela":"Helsinki",
    "Terhi Koulumies":"Helsinki","Jarmo Lindberg":"Helsinki","Mari Rantanen":"Helsinki",
    "Nasima Razmyar":"Helsinki","Wille Rydman":"Helsinki","Sari Sarkomaa":"Helsinki",
    "Elina Valtonen":"Helsinki","Ben Zyskowicz":"Helsinki",
    "Anders Adlercreutz":"Uusimaa","Otto Andersson":"Uusimaa","Tiina Elo":"Uusimaa",
    "Noora Fagerström":"Uusimaa","Harry Harkimo":"Uusimaa","Inka Hopsu":"Uusimaa",
    "Saara Hyrkkö":"Uusimaa","Arja Juvonen":"Uusimaa","Antti Kaikkonen":"Uusimaa",
    "Anette Karlsson":"Uusimaa","Pia Kauma":"Uusimaa","Teemu Keskisarja":"Uusimaa",
    "Pihla Keto-Huovinen":"Uusimaa","Kimmo Kiljunen":"Uusimaa","Ari Koponen":"Uusimaa",
    "Miapetra Kumpula-Natri":"Uusimaa","Johan Kvarnström":"Uusimaa","Mia Laiho":"Uusimaa",
    "Jarno Limnell":"Uusimaa","Antti Lindtman":"Uusimaa","Pia Lohikoski":"Uusimaa",
    "Helena Marttila":"Uusimaa","Leena Meri":"Uusimaa","Sari Multala":"Uusimaa",
    "Martin Paasi":"Uusimaa","Pinja Perholehto":"Uusimaa","Jorma Piisinen":"Uusimaa",
    "Mika Poutala":"Uusimaa","Riikka Purra":"Uusimaa","Susanne Päivärinta":"Uusimaa",
    "Onni Rostila":"Uusimaa","Joona Räsänen":"Uusimaa","Tere Sammallahti":"Uusimaa",
    "Heikki Vestman":"Uusimaa","Eerikki Viljanen":"Uusimaa","Henrik Vuornos":"Uusimaa",
    "Henrik Wickström":"Uusimaa",
    "Pauli Aalto-Setälä":"Varsinais-Suomi","Sandra Bergqvist":"Varsinais-Suomi",
    "Ritva Elomaa":"Varsinais-Suomi","Eeva-Johanna Eloranta":"Varsinais-Suomi",
    "Timo Furuholm":"Varsinais-Suomi","Vilhelm Junnila":"Varsinais-Suomi",
    "Mauri Kontu":"Varsinais-Suomi","Milla Lahdenperä":"Varsinais-Suomi",
    "Aki Lindén":"Varsinais-Suomi","Mikko Lundén":"Varsinais-Suomi",
    "Saku Nikkanen":"Varsinais-Suomi","Petteri Orpo":"Varsinais-Suomi",
    "Saara-Sofia Sirén":"Varsinais-Suomi","Ville Tavio":"Varsinais-Suomi",
    "Ville Valkonen":"Varsinais-Suomi","Sofia Virta":"Varsinais-Suomi",
    "Johannes Yrttiaho":"Varsinais-Suomi",
    "Laura Huhtasaari":"Satakunta","Petri Huru":"Satakunta","Eeva Kalli":"Satakunta",
    "Mari Kaunistola":"Satakunta","Krista Kiuru":"Satakunta","Jari Koskela":"Satakunta",
    "Matias Marttinen":"Satakunta","Juha Viitala":"Satakunta",
    "Tarja Filatov":"Häme","Sanni Grahn-Laasonen":"Häme","Timo Heinonen":"Häme",
    "Mika Kari":"Häme","Hilkka Kemppi":"Häme","Teemu Kinnari":"Häme",
    "Johannes Koskinen":"Häme","Rami Lehtinen":"Häme","Mira Nieminen":"Häme",
    "Aino-Kaisa Pekonen":"Häme","Lulu Ranne":"Häme","Jari Ronkainen":"Häme",
    "Päivi Räsänen":"Häme","Ville Skinnari":"Häme",
    "Marko Asell":"Pirkanmaa","Miko Bergbom":"Pirkanmaa","Lotta Hamari":"Pirkanmaa",
    "Anna-Kaisa Ikonen":"Pirkanmaa","Aleksi Jäntti":"Pirkanmaa","Pauli Kiuru":"Pirkanmaa",
    "Anna Kontula":"Pirkanmaa","Hanna Laine-Nousimaa":"Pirkanmaa","Lauri Lyly":"Pirkanmaa",
    "Ville Merinen":"Pirkanmaa","Veijo Niemi":"Pirkanmaa","Jouni Ovaska":"Pirkanmaa",
    "Sakari Puisto":"Pirkanmaa","Arto Satonen":"Pirkanmaa","Sami Savio":"Pirkanmaa",
    "Sari Tanus":"Pirkanmaa","Oras Tynkkynen":"Pirkanmaa","Joakim Vigelius":"Pirkanmaa",
    "Pia Viitanen":"Pirkanmaa","Sofia Vikman":"Pirkanmaa",
    "Juho Eerola":"Kaakkois-Suomi","Hanna Holopainen":"Kaakkois-Suomi",
    "Antti Häkkänen":"Kaakkois-Suomi","Vesa Kallio":"Kaakkois-Suomi",
    "Ville Kaunisto":"Kaakkois-Suomi","Jukka Kopra":"Kaakkois-Suomi",
    "Hanna Kosonen":"Kaakkois-Suomi","Suna Kymäläinen":"Kaakkois-Suomi",
    "Sheikki Laakso":"Kaakkois-Suomi","Niina Malm":"Kaakkois-Suomi",
    "Anna-Kristiina Mikkonen":"Kaakkois-Suomi","Jani Mäkelä":"Kaakkois-Suomi",
    "Jaana Strandman":"Kaakkois-Suomi","Oskari Valtola":"Kaakkois-Suomi",
    "Paula Werning":"Kaakkois-Suomi",
    "Sanna Antikainen":"Savo-Karjala","Markku Eestilä":"Savo-Karjala",
    "Seppo Eskelinen":"Savo-Karjala","Sari Essayah":"Savo-Karjala",
    "Hannu Hoskonen":"Savo-Karjala","Marko Kilpi":"Savo-Karjala",
    "Laura Meriluoto":"Savo-Karjala","Krista Mikkonen":"Savo-Karjala",
    "Karoliina Partanen":"Savo-Karjala","Minna Reijonen":"Savo-Karjala",
    "Hanna Räsänen":"Savo-Karjala","Markku Siponen":"Savo-Karjala",
    "Timo Suhonen":"Savo-Karjala","Timo Vornanen":"Savo-Karjala",
    "Tuula Väätäinen":"Savo-Karjala",
    "Kim Berg":"Vaasa","Christoffer Ingo":"Vaasa","Janne Jukkola":"Vaasa",
    "Antti Kurvinen":"Vaasa","Mika Lintilä":"Vaasa","Juha Mäenpää":"Vaasa",
    "Matias Mäkynen":"Vaasa","Anders Norrback":"Vaasa","Mikko Ollikainen":"Vaasa",
    "Mauri Peltokangas":"Vaasa","Anne Rintamäki":"Vaasa","Paula Risikko":"Vaasa",
    "Mikko Savola":"Vaasa","Pia Sillanpää":"Vaasa","Joakim Strand":"Vaasa",
    "Peter Östman":"Vaasa",
    "Bella Forsgrén":"Keski-Suomi","Kaisa Garedew":"Keski-Suomi",
    "Petri Honkonen":"Keski-Suomi","Tomi Immonen":"Keski-Suomi",
    "Riitta Kaarisalo":"Keski-Suomi","Anne Kalmari":"Keski-Suomi",
    "Jani Kokko":"Keski-Suomi","Piritta Rantanen":"Keski-Suomi",
    "Ville Väyrynen":"Keski-Suomi","Sinuhe Wallinheimo":"Keski-Suomi",
    "Pekka Aittakumpu":"Oulu","Janne Heikkinen":"Oulu","Pia Hiltunen":"Oulu",
    "Juha Hänninen":"Oulu","Jessi Jokelainen":"Oulu","Antti Kangas":"Oulu",
    "Tuomas Kettunen":"Oulu","Hanna-Leena Mattila":"Oulu","Timo Mehtälä":"Oulu",
    "Olga Oinas-Panuma":"Oulu","Jenni Pitko":"Oulu","Mikko Polvinen":"Oulu",
    "Merja Rasinkangas":"Oulu","Hanna Sarkkinen":"Oulu","Jenna Simula":"Oulu",
    "Mari-Leena Talvitie":"Oulu","Tytti Tuppurainen":"Oulu","Ville Vähämäki":"Oulu",
    "Heikki Autto":"Lappi","Kaisa Juuso":"Lappi","Markus Lohi":"Lappi",
    "Johanna Ojala-Niemelä":"Lappi","Mika Riipi":"Lappi","Sara Seppänen":"Lappi",
    "Mats Löfström":"Ahvenanmaa",
}

# ── Puolue Wikidata-ID → lyhenne ──
PUOLUEET = {
    # KOK
    "Q304191":"KOK",
    # PS
    "Q181858":"PS","Q327591":"PS",
    # SDP
    "Q170775":"SDP","Q499029":"SDP",
    # KESK
    "Q170750":"KESK","Q1752583":"KESK","Q3177095":"KESK",
    # VIHR
    "Q465955":"VIHR","Q170784":"VIHR",
    # VAS
    "Q170767":"VAS","Q385927":"VAS",
    # RKP
    "Q170782":"RKP","Q1092519":"RKP",
    # KD
    "Q965052":"KD","Q170781":"KD",
    # LIIK
    "Q3230391":"LIIK",
    # SIN
    "Q18678676":"SIN",
    # Historialliset puolueet
    "Q170778":"SKDL","Q1054366":"SKL","Q170779":"LKP",
    "Q504956":"SMP","Q170780":"TPSL","Q170783":"SPP",
    "Q2045396":"KP","Q505610":"ED","Q170777":"SKYP",
}

# ── Puolueen NIMI → lyhenne (vararatkaisu jos Q-koodi ei tunnistettu) ──
PUOLUE_NIMET = {
    "kokoomus":"KOK","samlingsparti":"KOK",
    "perussuomalais":"PS","sannfinländar":"PS",
    "sosialidemokraat":"SDP","socialdemokrat":"SDP",
    "keskusta":"KESK","centern":"KESK","maalaisliitto":"KESK",
    "agrarian":"KESK",
    "vihreä":"VIHR","gröna":"VIHR","vihreat":"VIHR",
    "vasemmistoliitto":"VAS","vänsterförbundet":"VAS",
    "svenska folkpartiet":"RKP","ruotsalainen":"RKP",
    "kristillisdemokraat":"KD","kristdemokrat":"KD",
    "liike nyt":"LIIK","rörelse":"LIIK",
    "sininen tulevaisuus":"SIN",
    "skdl":"SKDL","kansandemokraat":"SKDL",
    "suomen maaseudun puolue":"SMP",
}

def tunnista_puolue_nimella(party_id_raw: str) -> str:
    """Vararatkaisu: tunnistaa puolueen nimen perusteella."""
    low = party_id_raw.lower()
    for avain, lyhenne in PUOLUE_NIMET.items():
        if avain in low:
            return lyhenne
    return "–"

def tunnista_puolue(party_id: str) -> str:
    """Tunnistaa puolueen ensin Q-koodista, sitten nimen perusteella."""
    if not party_id:
        return "–"
    qid = party_id.split(":")[-1].split("/")[-1]
    if qid in PUOLUEET:
        return PUOLUEET[qid]
    return tunnista_puolue_nimella(party_id)

def kentta_id(data, avain):
    v = data.get(avain)
    if not v: return ""
    if isinstance(v, list): v = v[-1]
    return v.get("@id","") if isinstance(v,dict) else ""

def kentta_arvo(data, avain):
    v = data.get(avain)
    if not v: return ""
    if isinstance(v, list): v = v[0]
    return v.get("@value","") if isinstance(v,dict) else str(v)

def sama_as_lista(data):
    v = data.get("sch:sameAs",[])
    if isinstance(v,dict): v=[v]
    return v if isinstance(v,list) else []

def laske_vaalikaudet(data):
    rp = data.get("semparl:representative_period")
    return len(rp) if isinstance(rp,list) else (1 if rp else 0)

def parsi_nimi(data):
    label = kentta_arvo(data,"skos:prefLabel")
    m = re.match(r"^(.+?),\s*(.+?)\s*\(",label)
    if m: return f"{m.group(2).strip()} {m.group(1).strip()}"
    return re.sub(r"\s*\(\d{4}.*\)","",label).strip()

def parsi_edustaja(tiedosto):
    try:
        with open(tiedosto,encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  VIRHE {tiedosto.name}: {e}",file=sys.stderr)
        return None

    label        = kentta_arvo(data,"skos:prefLabel")
    nimi         = parsi_nimi(data)
    party_raw    = kentta_id(data,"semparl:party")
    party_qid    = party_raw.split(":")[-1].split("/")[-1]
    puolue       = tunnista_puolue(party_raw)

    # Jos puolue ei tunnistettu Q-koodista, kokeile NYKYISET-hakemistosta
    if puolue == "–" and nimi in NYKYISET:
        pass  # Jätetään "–", NYKYISET ei sisällä puoluetta
    # Jos puolue edelleen "–" mutta nimi on nykyisten listassa, tarkistetaan myöhemmin
    kotikunta    = kentta_arvo(data,"semparl:home_location_text")
    koulutus     = kentta_arvo(data,"semparl:occupation_text")
    syntymavuosi = next(iter(re.findall(r"\((\d{4})-",label)),None)
    kuolinvuosi  = next(iter(re.findall(r"-(\d{4})\)",label)),None)
    kuva         = kentta_id(data,"sch:image")
    eid          = kentta_arvo(data,"semparl:id") or kentta_id(data,"semparl:id")
    vaalikaudet  = laske_vaalikaudet(data)

    sa = sama_as_lista(data)
    wiki      = next((s.get("@id","") for s in sa if "fi.wikipedia.org" in s.get("@id","")), "")
    eduskunta = f"https://www.eduskunta.fi/FI/kansanedustajat/Sivut/{eid}.aspx" if eid else ""
    twitter   = next((s.get("@id","").replace("twitter:","")
                      for s in sa if s.get("@id","").startswith("twitter:")), "")

    # Nykyinen ja vaalipiiri NYKYISET-hakemistosta
    nykyinen  = nimi in NYKYISET
    vaalipiiri = NYKYISET.get(nimi, "")

    return {
        "tiedosto":tiedosto.name,"nimi":nimi,"puolue":puolue,
        "kotikunta":kotikunta,"vaalipiiri":vaalipiiri,"koulutus":koulutus,
        "syntymavuosi":syntymavuosi,"kuolinvuosi":kuolinvuosi,
        "kuva":kuva,"wiki":wiki,"eduskunta":eduskunta,"twitter":twitter,
        "vaalikaudet":vaalikaudet,"nykyinen":nykyinen,
    }

# ── Edustajat joita ei löydy JSON-kansiosta — lisätään käsin ──
PUUTTUVAT = [
    # SemParl-aineistosta puuttuvat uudet edustajat — lisätty käsin
    {"tiedosto":"","nimi":"Anette Karlsson","puolue":"SDP","kotikunta":"","vaalipiiri":"Uusimaa",
     "koulutus":"","syntymavuosi":None,"kuolinvuosi":None,"kuva":"","wiki":"",
     "eduskunta":"","twitter":"","vaalikaudet":1,"nykyinen":True},
    {"tiedosto":"","nimi":"Henrik Vuornos","puolue":"PS","kotikunta":"","vaalipiiri":"Uusimaa",
     "koulutus":"","syntymavuosi":None,"kuolinvuosi":None,"kuva":"","wiki":"",
     "eduskunta":"","twitter":"","vaalikaudet":1,"nykyinen":True},
    {"tiedosto":"","nimi":"Mauri Kontu","puolue":"KOK","kotikunta":"","vaalipiiri":"Varsinais-Suomi",
     "koulutus":"","syntymavuosi":None,"kuolinvuosi":None,"kuva":"","wiki":"",
     "eduskunta":"","twitter":"","vaalikaudet":1,"nykyinen":True},
    {"tiedosto":"","nimi":"Hanna Laine-Nousimaa","puolue":"SDP","kotikunta":"Kangasala","vaalipiiri":"Pirkanmaa",
     "koulutus":"yhteiskuntatieteiden maisteri","syntymavuosi":"1972","kuolinvuosi":None,
     "kuva":"","wiki":"https://fi.wikipedia.org/wiki/Hanna_Laine-Nousimaa",
     "eduskunta":"","twitter":"","vaalikaudet":1,"nykyinen":True},
    {"tiedosto":"","nimi":"Riitta Kaarisalo","puolue":"SDP","kotikunta":"Jyväskylä","vaalipiiri":"Keski-Suomi",
     "koulutus":"yhteiskuntatieteiden maisteri","syntymavuosi":"1979","kuolinvuosi":None,
     "kuva":"","wiki":"https://fi.wikipedia.org/wiki/Riitta_M%C3%A4kinen",
     "eduskunta":"","twitter":"","vaalikaudet":3,"nykyinen":True},
]

def main():
    if not KANSIO.exists():
        print(f"VIRHE: Kansiota '{KANSIO}' ei loydy.",file=sys.stderr); sys.exit(1)

    tiedostot = sorted(t for t in KANSIO.glob("*.json") if t.name != "index.json")
    print(f"Loydetty {len(tiedostot)} JSON-tiedostoa...")

    edustajat, virheet = [], 0
    for i,t in enumerate(tiedostot,1):
        e = parsi_edustaja(t)
        if e: edustajat.append(e)
        else: virheet += 1
        if i % 200 == 0: print(f"  {i}/{len(tiedostot)} kasitelty...")

    # Lisää käsin syötetyt puuttuvat edustajat
    olemassa = {e["nimi"] for e in edustajat}
    for p in PUUTTUVAT:
        if p["nimi"] not in olemassa:
            edustajat.append(p)

    edustajat.sort(key=lambda x: x["nimi"].split()[-1].lower() if x["nimi"] else "")

    kohde = KANSIO/"index.json"
    with open(kohde,"w",encoding="utf-8") as f:
        json.dump(edustajat,f,ensure_ascii=False,separators=(",",":"))

    koko     = kohde.stat().st_size
    nykyiset = sum(1 for e in edustajat if e["nykyinen"])
    loydetyt = sum(1 for e in edustajat if e["nimi"] in NYKYISET)

    print(f"\nValmis!")
    print(f"  Edustajia yhteensä: {len(edustajat)}")
    print(f"  Nykyisiä (2023-27): {nykyiset}")
    print(f"  Historiallisia:     {len(edustajat)-nykyiset}")
    print(f"  Virheitä:           {virheet}")
    # Raportoi tuntemattomat Q-koodit
    q_tuntematon = {}
    for e in edustajat:
        if e["puolue"] == "–" and e["nykyinen"]:
            q_tuntematon[e["nimi"]] = e.get("tiedosto","")
    if q_tuntematon:
        print(f"\n  HUOMIO: {len(q_tuntematon)} nykyistä edustajaa ilman puoluetta:")
        for n,t in list(q_tuntematon.items())[:10]:
            print(f"    - {n} ({t})")
    print(f"  Tiedosto:           {kohde}  ({koko/1024:.0f} KB)")

    # Varoita jos nykyisiä ei löydy kaikille
    puuttuvat = [n for n in NYKYISET if not any(e["nimi"]==n for e in edustajat)]
    if puuttuvat:
        print(f"\n  HUOMIO: {len(puuttuvat)} nykyistä edustajaa ei löydy JSON-kansiosta:")
        for n in puuttuvat[:10]: print(f"    - {n}")

if __name__ == "__main__":
    main()
