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
    # ENDELIG (12.11 18:40, Vegar: siden var ikke ajour etter kuttet). Finnes den endelige
    # teksten og er den nyere enn siste versjon, er det DEN som gjelder: kuttet har fjernet
    # alle markoerer, og tallene fra foer kuttet er ikke lenger sanne.
    END = os.path.join(BESV, "bilag2-endelig-tekst.md")
    endelig = os.path.exists(END) and os.path.getmtime(END) >= os.path.getmtime(tekstfil(n))
    if endelig:
        et = les(END)
        rest_a, rest_b = len(re.findall(r"\[MANGLER", et)), len(re.findall(r"\[bekreftes", et))
        krav = []
        for kid in sorted(man.get("krav", {})):
            meta = man["krav"][kid]
            # Vegar 18:46: groent maa ikke bety «sterkt». Det som ble stroeket ved kuttet
            # (MANGLER i siste versjon foer kuttet) koster poeng og vises gult.
            seksjon = re.search(r"## %s\b.*?(?=\n## R0|\Z)" % kid, t, re.S)
            krav.append({"id": kid, "tittel": meta[0], "hvem": meta[1], "tekst": meta[2],
                         "aapne": 0, "bekreft": 0,
                         "stroket": len(re.findall(r"\[MANGLER", seksjon.group(0))) if seksjon else 0})
        krav[0]["aapne"] += rest_a
        krav[0]["bekreft"] += rest_b
        t = ""
    else:
        krav = []
    for del_ in ([] if endelig else re.split(r"\n(?=## R0\d\d)", t)):
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
    if os.path.exists(ml) and not endelig:
        mt = les(ml)
        m = re.search(r"\*\*(\d+) åpne punkter og (\d+) bekreftelser", mt)
        if m:
            aapne, bekreft = int(m.group(1)), int(m.group(2))
        for navn, a, b in re.findall(r"^\| ([A-ZÆØÅ][^|]*?) \| (\d+) \| (\d+) \|", mt, re.M):
            selskap.append([navn.strip(), int(a), int(b)])

    sensur = {"farge": "r", "tekst": "Ikke stemplet på v%d ennå." % n}
    for sp in ([END + ".stempel.json"] if endelig else []) + [os.path.join(BESV, "_bygg", "v%d" % n, "bilag2-v%d-tekst.md.stempel.json" % n),
               ml + ".stempel.json"]:
        if os.path.exists(sp):
            try:
                tid = json.loads(les(sp)).get("tid", "")
                sensur = {"farge": "g", "tekst": ("Stemplet på den endelige teksten, %s. Ingen stopp." % tid) if endelig else ("Stemplet på v%d, %s. Ingen stopp." % (n, tid))}
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
            if endelig and c.get("tekst_endelig"):
                c.update(farge="g", tekst=c["tekst_endelig"])
        c.pop("tekst_endelig", None)
        c.pop("id", None)
        checks.append(c)

    # Fremdrift (Vegar 12.11 10:58: «hvor mange prosent»). Grunnlinje for bekreftelser = hoyeste antall sett.
    gl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grunnlinje.json")
    try:
        G = json.loads(les(gl))
    except Exception:
        G = {}
    G["bekreft_maks"] = max(G.get("bekreft_maks", 0), bekreft)
    with open(gl, "w") as f:
        json.dump(G, f)
    skrevet = sum(1 for k in krav if k["aapne"] == 0 and not k.get("stroket"))
    fylt = round(100 * bekreft / (aapne + bekreft)) if (aapne + bekreft) else 100
    bekreftet = G["bekreft_maks"] - bekreft
    fremdrift = {"krav_ferdig": skrevet, "krav_alle": len(krav), "fylt": fylt,
                 "bekreftet": bekreftet, "bekreft_alle": G["bekreft_maks"]}
    # Skriver-status fra Paperclip pa minien (tidsavbrudd 8 s; feiler stille).
    agent = {}
    try:
        import subprocess
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "vegarbakken@Vegars-Plex.local",
            "curl -s 'localhost:3100/api/companies/3a8fde13-e669-442b-97af-b072fbacf822/heartbeat-runs?agentId=8966cf73-8072-4db1-a1e8-aa8ed2589e83&limit=1'"],
            capture_output=True, text=True, timeout=8)
        d = json.loads(r.stdout)
        d = d.get("data", d) if isinstance(d, dict) else d
        if d:
            run = d[0]
            def kl(x):
                if not x: return ""
                t = datetime.datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone()
                return t.strftime("%H:%M")
            st = run.get("status")
            tekst = {"running": "jobber nå, startet kl. " + kl(run.get("startedAt")),
                     "queued": "står i kø",
                     "succeeded": "ferdig kl. " + kl(run.get("finishedAt")),
                     "failed": "stoppet med feil kl. " + kl(run.get("finishedAt")),
                     "cancelled": "avbrutt kl. " + kl(run.get("finishedAt"))}.get(st, st)
            agent = {"navn": "Skriver", "status": st, "tekst": tekst}
    except Exception:
        agent = G.get("agent_sist", {})
    if agent:
        G["agent_sist"] = agent
        with open(gl, "w") as f:
            json.dump(G, f)
    if endelig:
        fremdrift["bekreftet"] = fremdrift["bekreft_alle"]
    D = {"versjon": ("Endelig" if endelig else "v%d" % n), "aapne": aapne, "bekreft": bekreft, "selskap": selskap,
         "ingress": man.get("ingress", ""), "frist": man.get("frist", ""),
         "fast": man.get("fast", []), "crit": man.get("crit", []), "parts": man.get("parts", []),
         "checks": checks, "krav": krav, "fremdrift": fremdrift, "agent": agent, "log": man.get("log", [])[:12]}
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
