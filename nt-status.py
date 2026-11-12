#!/usr/bin/env python3
"""Lager status.json for statussiden (github nt-anbud).
Leser tallene fra besvarelse/ (nyeste versjon) og fletter med nt-status-manuell.json.
Skriver bare når innholdet er endret. Rot kan overstyres med NT_ROT (maskinbytte)."""
import json, re, glob, os, sys, datetime

ROT = os.environ.get("NT_ROT") or os.path.join(
    os.path.expanduser("~"), "Page Black Dropbox", "Page Black Business", "20 Paperclip",
    "outputs", "tilbudsmotor", "konkurransegrunnlag-NT-26-0260")
BESV = os.path.join(ROT, "besvarelse")
UT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")


def les(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def versjoner():
    ns = []
    for p in glob.glob(os.path.join(BESV, "Bilag-2-NT-26-0260-v*.docx")):
        m = re.search(r"-v(\d+)\.docx$", p)
        if m:
            ns.append(int(m.group(1)))
    return sorted(ns, reverse=True)


def tekstfil(n):
    for navn in ("bilag2-v%d-tekst-full.md" % n, "bilag2-v%d-tekst.md" % n):
        p = os.path.join(BESV, "_bygg", "v%d" % n, navn)
        if os.path.exists(p):
            return p
    return None


def main():
    man = json.loads(les(os.path.join(ROT, "nt-status-manuell.json")))
    n = next((v for v in versjoner() if tekstfil(v)), None)
    if n is None:
        sys.exit("fant ingen versjon med tekstfil")
    t = les(tekstfil(n))
    krav = []
    for del_ in re.split(r"\n(?=## R0\d\d)", t):
        m = re.match(r"## (R0\d\d)", del_)
        if not m:
            continue
        kid = m.group(1)
        meta = man.get("krav", {}).get(kid, [kid, "", ""])
        krav.append({"id": kid, "tittel": meta[0], "hvem": meta[1], "tekst": meta[2],
                     "aapne": len(re.findall(r"\[MANGLER", del_)),
                     "bekreft": len(re.findall(r"\[bekreftes", del_))})
    aapne = sum(k["aapne"] for k in krav)
    bekreft = sum(k["bekreft"] for k in krav)
    selskap = []
    ml = os.path.join(BESV, "mangelliste-NT-v%d.md" % n)
    if os.path.exists(ml):
        mt = les(ml)
        m = re.search(r"\*\*(\d+) åpne punkter og (\d+) bekreftelser", mt)
        if m:
            aapne, bekreft = int(m.group(1)), int(m.group(2))
        for navn, a, b in re.findall(r"^\| ([A-ZÆØÅ][^|]*?) \| (\d+) \| (\d+) \|", mt, re.M):
            selskap.append([navn.strip(), int(a), int(b)])

    sensur = {"farge": "r", "tekst": "Ikke stemplet på v%d ennå." % n}
    for sp in (os.path.join(BESV, "_bygg", "v%d" % n, "bilag2-v%d-tekst.md.stempel.json" % n),
               ml + ".stempel.json"):
        if os.path.exists(sp):
            try:
                tid = json.loads(les(sp)).get("tid", "")
                sensur = {"farge": "g", "tekst": "Stemplet på v%d, %s. Ingen stopp." % (n, tid)}
                break
            except Exception:
                pass
    ff = sorted(glob.glob(os.path.join(BESV, "faktasjekk-NT-26-0260-v%d*.md" % n)), key=os.path.getmtime)
    if ff:
        ft = les(ff[-1])
        m = re.findall(r"^(?:Åpne:|\*\*)?\s*(\d+ FEIL[^\n*]*)", ft, re.M)
        selv = "ikke av fersk agent" in ft
        fakta = {"farge": "y" if selv else "g",
                 "tekst": "Kjørt på v%d%s. %s" % (n, " av Skriver selv, ikke uavhengig" if selv else " av fersk agent",
                                                   (m[-1].strip() + ".") if m else "")}
    else:
        fakta = {"farge": "y", "tekst": "Ikke kjørt på v%d ennå. Bestilt." % n}
    checks = []
    for c in man.get("checks", []):
        c = dict(c)
        if c.get("id") == "sensur":
            c.update(sensur)
        if c.get("id") == "fakta":
            c.update(fakta)
        c.pop("id", None)
        checks.append(c)

    D = {"versjon": "v%d" % n, "aapne": aapne, "bekreft": bekreft, "selskap": selskap,
         "ingress": man.get("ingress", ""), "frist": man.get("frist", ""),
         "fast": man.get("fast", []), "crit": man.get("crit", []), "parts": man.get("parts", []),
         "checks": checks, "krav": krav, "log": man.get("log", [])[:12]}
    gammel = {}
    if os.path.exists(UT):
        try:
            gammel = json.loads(les(UT))
        except Exception:
            gammel = {}
    if {k: v for k, v in gammel.items() if k != "oppdatert"} == D:
        return
    D["oppdatert"] = datetime.datetime.now().strftime("%d.%m.%Y kl. %H:%M")
    with open(UT + ".tmp", "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    os.replace(UT + ".tmp", UT)
    print("status.json oppdatert:", D["versjon"], aapne, bekreft)


if __name__ == "__main__":
    main()
