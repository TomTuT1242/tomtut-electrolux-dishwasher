# Electrolux/AEG Smart Appliance Communication Research

> Stand: 2026-04-02 | Fokus: AEG 8000 Series Dishwasher (z.B. FSE84708P / GI8700B2SC)

---

## 1. Kommunikationsprotokoll-Uebersicht

### Cloud-Kommunikation (aktuell genutzt)
- **REST API** (OCP): `https://api.ocp.electrolux.one` -- Hauptkommunikation
- **WebSocket** (OCP): `wss://ws.ocp.electrolux.one` -- Echtzeit-Updates
- **Regionale Endpunkte**: `https://api.eu.ocp.electrolux.one`, `wss://ws.eu.ocp.electrolux.one`

### Historisch (veraltet, nicht mehr funktionsfaehig)
- **ECP (Electrolux Connectivity Platform)**: `https://api.emea.ecp.electrolux.com` -- ABGESCHALTET
- **MQTT Broker (IBM)**: `4r8kqw.messaging.internetofthings.ibmcloud.com:8883` -- ABGESCHALTET
- **MQTT Topics**: `iot-2/cmd/live_stream/fmt/+`, `iot-2/cmd/feature_stream/fmt/+`

### Lokal (potenziell vorhanden, aber nicht dokumentiert)
- **AllJoyn**: Electrolux war Premier Member der AllSeen Alliance. Aeltere Geraete (ca. 2016) nutzen AllJoyn. Windows IoT Explorer kann AllJoyn-Werte lesen. UNKLAR ob neuere 8000er Geraete noch AllJoyn unterstuetzen.
- **Port 443 (HTTPS)**: Bei vergleichbaren BSH/HomeConnect-Spuelmaschinen wurde NUR Port 443 offen gefunden (TLS-PSK). Electrolux-spezifische Port-Scans sind noch noetig.

---

## 2. Lokale Kommunikation -- Status der Erkenntnisse

### Was bekannt ist
- Electrolux-Geraete verbinden sich per WiFi (2.4 GHz) mit dem Heimnetzwerk
- Sie kommunizieren primaer ueber die Cloud (OCP API)
- Auf dem HA Community Forum hat NIEMAND eine funktionierende lokale Kommunikation nachgewiesen
- AllJoyn wurde auf aelteren Geraeten erkannt (Windows IoT Explorer), aber keine praktische Integration daraus gebaut

### Was zu testen ist (sobald IP verfuegbar)
1. **nmap Full Port Scan**: `nmap -sS -sU -p- <IP>` -- alle TCP/UDP Ports
2. **mDNS/Bonjour Discovery**: `avahi-browse -a` oder `dns-sd -B _services._dns-sd._udp`
3. **AllJoyn Discovery**: AllJoyn Router/Browser testen (Port 9955/9956 UDP)
4. **HTTPS Probe**: `curl -kv https://<IP>:443/` und `openssl s_client -connect <IP>:443`
5. **UPnP/SSDP Discovery**: `gssdp-discover` oder manuell auf 239.255.255.250:1900
6. **Traffic Capture**: Wireshark/tcpdump waehrend die Spuelmaschine mit der Cloud kommuniziert

### Vergleich BSH/HomeConnect (Referenz-Architektur)
Bei Bosch/Siemens HomeConnect Spuelmaschinen (aehnliche Preisklasse):
- Port 443 offen (einziger offener Port)
- TLS mit Pre-Shared Key (PSK-CHACHA20)
- WebSocket-basierte Kommunikation nach TLS-Handshake
- PSK wird beim App-Pairing gespeichert und kann extrahiert werden
- Vollstaendig lokaler Betrieb moeglich nach initialem Setup
- Tool: `hc-login` von Trammell Hudson (https://trmm.net/homeconnect/)

---

## 3. Cloud-Plattform: Electrolux OCP (One Connected Platform)

### Authentifizierung (4-Schritt-Flow)

```
1. Client Credentials Login
   POST https://api.ocp.electrolux.one/one-account-authorization/api/v1/token
   Body: { grantType: "client_credentials", clientId, clientSecret, scope: "" }
   Header: x-api-key: <brand_api_key>

2. Identity Provider Discovery
   GET https://api.ocp.electrolux.one/one-account-user/api/v1/identity-providers?brand=AEG&countryCode=DE
   -> Liefert Gigya Domain + API Key

3. Gigya (SAP) Login
   a) POST https://socialize.eu1.gigya.com/socialize.getIDs  (gmid, ucid)
   b) POST https://accounts.eu1.gigya.com/accounts.login     (sessionToken, sessionSecret)
   c) POST https://accounts.eu1.gigya.com/accounts.getJWT    (OAuth1 HMAC-SHA1 signiert)
      -> Liefert JWT id_token mit country claim

4. Token Exchange
   POST https://api.ocp.electrolux.one/one-account-authorization/api/v1/token
   Body: { grantType: "urn:ietf:params:oauth:grant-type:token-exchange", idToken: <jwt> }
   Header: Origin-Country-Code: <aus JWT>
   -> Liefert accessToken + refreshToken
```

### API Endpunkte

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/appliance/api/v2/appliances` | GET | Alle Geraete auflisten |
| `/appliance/api/v2/appliances/{id}` | GET | Einzelnes Geraet |
| `/appliance/api/v2/appliances/{id}/capabilities` | GET | Faehigkeiten/Optionen |
| `/appliance/api/v2/appliances/{id}/command` | PUT | Befehl senden |
| `/appliance/api/v2/appliances/info` | POST | Info fuer mehrere Geraete |
| `/one-account-user/api/v1/users/current` | GET | Aktueller Benutzer |

### API Headers (authentifiziert)
```
Authorization: Bearer <accessToken>
x-api-key: <brand_api_key>
Content-Type: application/json
```

### WebSocket Verbindung
```
URL: wss://ws.ocp.electrolux.one  (oder wss://ws.eu.ocp.electrolux.one)
Headers:
  Authorization: Bearer <accessToken>
  x-api-key: <brand_api_key>
  appliances: [{"applianceId": "<id>"}, ...]
  version: 2
Heartbeat: alle 300 Sekunden (Ping)
```

### Hardcodierte Credentials (aus homeassistant-aeg Repo)

**AEG:**
- API Key: `PEdfAP7N7sUc95GJPePDU54e2Pybbt6DZtdww7dz`
- Client ID: `AEGOneApp`
- Client Secret: `G6PZWyneWAZH6kZePRjZAdBbyyIu3qUgDGUDkat7obfU9ByQSgJPNy8xRo99vzcgWExX9N48gMJo3GWaHbMJsohIYOQ54zH2Hid332UnRZdvWOCWvWNnMNLalHoyH7xU`

**Electrolux:**
- API Key: `2AMqwEV5MqVhTKrRCyYfVF8gmKrd2rAmp7cUsfky`
- Client ID: `ElxOneApp`
- Client Secret: `8UKrsKD7jH9zvTV7rz5HeCLkit67Mmj68FvRVTlYygwJYy4dW6KF2cVLPKeWzUQUd6KJMtTifFf4NkDnjI7ZLdfnwcPtTSNtYvbP7OzEkmQD9IjhMOf5e1zeAQYtt2yN`

### Historische ECP Credentials (veraltet)
- AEG Brand ID: `A426680A-45DC-4582-9555-519BE6B57CDF`
- Electrolux Brand ID: `E6EB88D2-BD0E-4C8A-8DB9-766C22FDB641`
- IBM Client ID: `2a94cd2e-4248-4113-ace9-93540b43b18f`

---

## 4. Appliance States und Commands (Dishwasher relevant)

### Geraete-Kategorie
- `DW` = Dishwasher

### Appliance States
- `OFF`, `IDLE`, `READY_TO_START`, `RUNNING`, `PAUSED`, `DELAYED_START`, `END_OF_CYCLE`, `ALARM`

### Commands
- `ON`, `OFF`, `START`, `PAUSE`, `RESUME`, `STOPRESET`

### Datenformat (HACL Parameter -- altes ECP System)
Format: `"module:hacl"` z.B. `"WD1:0x1C09"`
Werte: numerisch oder Container-Listen mit verschachtelten Parametern

---

## 5. MAC-Adresse 44:3E:07

- **Hersteller**: Electrolux (registriert bei IEEE)
- **Standort der Registrierung**: Corso Lino Zanussi 24, Porcia, Pordenone 33080, Italien
- **Typ**: MA-L (Mac Address Block Large)
- **Bereich**: 44:3E:07:00:00:00 bis 44:3E:07:FF:FF:FF (~16 Mio Adressen)
- **Registrierungsdatum**: 24. November 2018
- **WiFi Chip**: Hoechstwahrscheinlich **Qualcomm QCA4002 oder QCA4004**
  - Qualcomm hat diese Chips spezifisch fuer Haushaltsgeraete entwickelt
  - Integrierter Prozessor + 802.11n (2.4 GHz)
  - AllJoyn-Support eingebaut
  - SPI/UART Host-Interface zum Hauptcontroller der Spuelmaschine
  - Electrolux war AllSeen Alliance Premier Member (nutzte AllJoyn auf QCA400x)

---

## 6. Existierende Projekte und Integrationen

### Home Assistant Integrationen (alle Cloud-basiert)

| Projekt | Status | Basis |
|---------|--------|-------|
| [homeassistant-aeg](https://github.com/emanuelbesliu/homeassistant-aeg) | Aktiv | OCP Internal API (beste Option) |
| [homeassistant_electrolux_status](https://github.com/albaintor/homeassistant_electrolux_status) | Aktiv | OCP/Wellbeing API |
| [electrolux_status](https://github.com/sanchosk/electrolux_status) | Aktiv | ECP/OCP |
| [homeassistant-wellbeing](https://github.com/JohNan/homeassistant-wellbeing) | Veraltet | Wellbeing/Delta API |
| [electrolux2mqtt](https://github.com/franciscofsales/electrolux2mqtt) | Experimentell | OCP API -> MQTT Bridge (Node.js) |
| [electrolux_mqtt](https://github.com/dannyyy/electrolux_mqtt) | Veraltet | ECP MQTT |

### Bibliotheken

| Projekt | Sprache | Status |
|---------|---------|--------|
| [py-electrolux-ocp](https://github.com/Woyken/py-electrolux-ocp) | Python | ARCHIVIERT -- verweist auf offizielles SDK |
| [electrolux-ocp](https://github.com/mafredri/electrolux-ocp) | Go | Aktiv |
| [pyelectroluxconnect](https://github.com/tomeko12/pyelectroluxconnect) | Python | VERALTET -- ECP abgeschaltet |

### Offizielle Electrolux Ressourcen
- **Developer Portal**: https://developer.electrolux.one/
- **API Reference**: https://developer.electrolux.one/documentation/reference
- **Official SDK**: https://github.com/electrolux-oss/electrolux-group-developer-sdk
- **Open Source Repos**: https://github.com/electrolux-oss

### Andere Plattformen
- **Homey App**: [Electrolux/AEG OCP](https://homey.app/en-us/app/com.electrolux-aeg.ocp/Electrolux-AEG/) -- Cloud-basiert

---

## 7. Reverse Engineering Strategie fuer lokale Kommunikation

### Phase 1: Netzwerk-Reconnaissance (braucht IP der Spuelmaschine)
```bash
# Full TCP port scan
nmap -sS -p- -T4 <IP>

# UDP scan (wichtige Ports)
nmap -sU --top-ports 1000 <IP>

# Service/Version detection
nmap -sV -p <offene_ports> <IP>

# mDNS/Bonjour
avahi-browse -art

# UPnP/SSDP
python3 -c "
import socket, struct
SSDP_ADDR = '239.255.255.250'
SSDP_PORT = 1900
msg = 'M-SEARCH * HTTP/1.1\r\nHOST:239.255.255.250:1900\r\nMAN:\"ssdp:discover\"\r\nMX:2\r\nST:ssdp:all\r\n\r\n'
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(5)
s.sendto(msg.encode(), (SSDP_ADDR, SSDP_PORT))
while True:
    try:
        data, addr = s.recvfrom(4096)
        print(f'--- {addr} ---')
        print(data.decode())
    except socket.timeout:
        break
"
```

### Phase 2: AllJoyn Discovery
```bash
# AllJoyn uses UDP 9955/9956 for discovery
# Install alljoyn-daemon or use Windows IoT Explorer
# Check if device responds to AllJoyn Name Service (AJNS) queries

# On Windows: "IoT Explorer for AllJoyn" from Microsoft Store
# Alternative: alljoyn_about_client tool
```

### Phase 3: Traffic Analysis
```bash
# Capture all traffic from dishwasher IP
tcpdump -i <interface> host <IP> -w dishwasher_capture.pcap

# Analyse in Wireshark:
# - DNS queries (welche Hosts kontaktiert das Geraet?)
# - TLS SNI (Server Name Indication)
# - mDNS Announcements
# - AllJoyn Traffic (Port 9955/9956)
```

### Phase 4: App Reverse Engineering
```bash
# AEG App APK herunterladen und decompilieren
# Tools: jadx, apktool, frida
# Suche nach:
# - Lokale Discovery-Mechanismen
# - AllJoyn Service-Namen
# - PSK/Pairing-Keys
# - Lokale API-Endpunkte
```

---

## 8. Bewertung und Empfehlung

### Lokale Kommunikation: Machbarkeit
| Ansatz | Wahrscheinlichkeit | Aufwand | Bewertung |
|--------|-------------------|---------|-----------|
| AllJoyn (wenn verfuegbar) | Mittel | Hoch | Aeltere Geraete nutzen es, neuere unklar |
| HTTPS/TLS-PSK (wie HomeConnect) | Niedrig | Sehr hoch | Nicht dokumentiert fuer Electrolux |
| Proprietaeres Protokoll | Moeglich | Sehr hoch | Komplett eigenes Reverse Engineering |
| Cloud-API lokal abfangen (MITM) | Hoch | Mittel | Braucht DNS/Proxy Manipulation |

### Empfohlener Ansatz
1. **Sofort**: Port-Scan + Traffic-Analyse sobald IP verfuegbar
2. **Parallel**: Cloud-basierte Integration (homeassistant-aeg) als Fallback aufsetzen
3. **Danach**: Basierend auf Scan-Ergebnissen entscheiden ob lokales RE machbar ist
4. **Plan B**: Wenn kein lokaler Zugang moeglich, Cloud-API nutzen aber lokal cachen

### Wichtigste Erkenntnis
Bisher hat NIEMAND in der Community eine funktionierende lokale Kommunikation mit Electrolux/AEG Geraeten dokumentiert. Alle existierenden Integrationen sind Cloud-basiert. Das macht dieses Projekt potenziell einzigartig -- aber auch riskant.

---

## 9. Argo Firmware Platform -- Neue Erkenntnisse (2026-04-02)

### Was ist "Argo"?

**"Argo" ist der interne Codename fuer die aktuelle NIU (Network Interface Unit) Firmware-Plattform von Electrolux.** Dies wurde durch Analyse der offiziellen Test-Daten im [electrolux-group-developer-sdk](https://github.com/electrolux-oss/electrolux-group-developer-sdk) bestaetigt.

Das Feld `networkInterface.swVersion` in der OCP API gibt die NIU-Firmware-Version zurueck. Der Suffix `_argo` identifiziert die Plattform-Generation.

### Firmware-Versionen aller Geraetetypen (aus offizieller SDK)

| Geraetetyp | Kuerzel | swVersion | niuSwUpdateCurrentDescription | swAncAndRevision |
|------------|---------|-----------|-------------------------------|------------------|
| **Dishwasher** | DW | `v4.0.0S_argo` | `A23642205A-S00008458A` | `S00008458A` |
| Washing Machine | WM | `v3.0.0S_argo` | `A23642201A-S00007645A` | `S00007645A` |
| Tumble Dryer | TD | `v3.0.0S_argo` | `A23642201A-S00007645A` | `S00007645A` |
| Washer-Dryer | WD | `v3.0.0S_argo` | `A23642201A-S00007645A` | `S00007645A` |
| Air Conditioner | AC | `v3.0.0_argo` | `A21023902A-S00007029A` | `S00007029A` |
| Hob | HB | `v3.0.0Src7_argo` | `A23642201A-S00007644G` | `S00007644G` |
| Hood (test) | HD | `v4.0.0S_0tst` | `A23642205A-S00000TSTC` | `S00000TSTC` |
| Steam Oven | SO | `v1.9.1_hacl` | `A16323310A-S00006777A` | `S00006777A` |
| Dehumidifier | DH | `v1.9.1_srac` | `A16323311A-S00006778A` | `S00006778A` |
| Combi Refrigerator | CR | `v5.4.2` | `A07491702B-S00008607A` | `S00008607A` |

### Firmware-Plattform-Generationen

Es gibt mindestens **vier verschiedene NIU-Firmware-Plattformen**:

1. **`_argo`** (aktuell, v3.x/v4.x) -- Neueste Generation, verwendet auf DW, WM, TD, WD, AC, HB
2. **`_hacl`** (aelter, v1.9.x) -- Aeltere Generation, verwendet auf Steam Ovens (SO)
3. **`_srac`** (aelter, v1.9.x) -- Aeltere Generation, verwendet auf Dehumidifiers (DH)
4. **Ohne Suffix** (v5.4.2) -- Combi Refrigerator (CR), moeglicherweise separate Plattform (Frigidaire?)

**Der Dishwasher (DW) laeuft auf der neuesten Argo-Generation v4.0.0S.**

### Entschluesselung der Firmware-Identifikatoren

**`niuSwUpdateCurrentDescription`** Format: `AXXXXXXXXX-SXXXXXXXXX`
- Erster Teil (z.B. `A23642205A`): **NIU-Hardware/Anwendungs-Identifikator**
  - `A2364220_A` = NIUX-Modul-Familie (gemeinsam bei WM, TD, WD, HB, DW, HD)
  - Die letzte Ziffer vor dem Suffix variiert: `1` = Waschmaschinen/Trockner/Hob, `5` = Dishwasher/Hood
  - `A2102390_A` = AC-spezifisches Modul
  - `A1632331_A` = Aeltere Module (SO, DH)
  - `A0749170_B` = Frigidaire/CR Modul (Suffix B statt A)
- Zweiter Teil (z.B. `S00008458A`): **Software-ANC-Revision** (= `swAncAndRevision`)

**`swAncAndRevision`** = Software Article Number Code + Revision
- Format: `SXXXXXXXYA` wobei Y eine Versionsnummer und A ein Revisions-Buchstabe ist
- Identifiziert die spezifische Anwendungssoftware (nicht die Plattform-Firmware)

**`swVersion`** Format: `vX.Y.Z[S][suffix]`
- `v4.0.0S_argo`: Version 4.0.0, `S` = moeglicherweise "Secure" oder "Standard", `_argo` = Plattform
- `v3.0.0Src7_argo`: Version 3.0.0, `Src7` = Source-Revision 7

### WiFi-Chip-Generationen der NIU-Module

Electrolux hat **drei Generationen** von NIU-Modulen:

| Generation | FCC ID | Chipset | Datum | AllJoyn |
|------------|--------|---------|-------|---------|
| **NIU** (1. Gen) | 2ABHC-5430042 | Qualcomm QCA4002/4004 | 2014 | Ja (eingebaut) |
| **NIUX** (2. Gen) | 2AIBX-NIUXL | Qualcomm QCA4531 | 2017 | Ja (Linux/OpenWRT) |
| **NIU5** (3. Gen) | 2AIBX-NIU5L | Unbekannt (WiFi + BLE) | Neuer | Unbekannt |

**NIUX (QCA4531):**
- 650 MHz MIPS 24Kc CPU
- 64 MB DDR2 + 32 MB SPI NOR Flash
- 802.11b/g/n 2x2 (bis 300 Mbps)
- Interfaces: UART, I2C, GPIO, USB, Ethernet
- Laeuft OpenWRT Linux OS mit Open-Source WiFi-Treibern
- Qualcomm SDK (QSDK) mit AllJoyn-Integration
- Kann als AllJoyn IoE Hub fungieren

**Die NIUX-Module (A2364220xA) mit QCA4531 sind die wahrscheinliche Hardware in aktuellen Argo-Geraeten wie dem Dishwasher.**

### Lokale Protokoll-Analyse

**AllJoyn:**
- QCA4531 hat vollstaendige AllJoyn-Client- und Service-Implementierung eingebaut
- AllJoyn nutzt TCP Port 9955/9956 und UDP fuer Discovery
- Electrolux war AllSeen Alliance Premier Member
- OCF-zertifizierte Electrolux/AEG-Geraete: Ovens (Elux100), Washing Machines (v1, v2), Tumble Dryers (v2), Refrigerators (v2), AEG BSE999220B (Oven)
- **KEIN Dishwasher in OCF AllJoyn-Zertifizierungsliste gefunden**
- AllJoyn Discovery via Windows IoT Explorer oder dotMorten.AllJoyn.DeviceProviders moeglich

**HACL vs Argo:**
- `_hacl` Firmware (v1.9.x) laeuft auf aelteren Modulen (A16323311A) -- wahrscheinlich NIU 1. Gen mit QCA4002
- `_argo` Firmware (v3.x/v4.x) laeuft auf neueren Modulen (A23642201A/A23642205A) -- wahrscheinlich NIUX mit QCA4531
- NIU-HACL Boards werden als separate Produkte verkauft (Electrolux Part 922695, ~$113)
- "HACL" steht moeglicherweise fuer "Home Appliance Communication Layer"

**Potenzielle lokale Protokolle auf Argo-Geraeten:**
1. **AllJoyn** (TCP 9955/9956, UDP Discovery) -- Wahrscheinlich noch vorhanden da QCA4531 es eingebaut hat
2. **HTTP/HTTPS** (Port 80/443) -- OpenWRT-basiert, koennte Webserver haben
3. **mDNS/Bonjour** (UDP 5353) -- Standard fuer Service Discovery auf Linux
4. **MQTT** -- Moeglich als lokaler Broker, aber unwahrscheinlich
5. **CoAP** (UDP 5683) -- IoT-Standard, aber kein Hinweis auf Nutzung

### AEG Smart Oven Netzwerk-Verhalten (Referenz)

Ein Blog-Post dokumentiert folgendes Verhalten von AEG Smart Ovens (BSK798280B):
- Connectivity-Check alle 5 Minuten zu google.com, baidu.cn, yandex.ru
- Cloud-API fuer Steuerung (OCP)
- **Kein lokales Protokoll gefunden** -- Autor fordert explizit lokale REST/WebSocket API
- Falsches OTA-Update brickte 2022 AEG Mikrowellen (falsche Firmware fuer Steam Oven gesendet)

### Zusammenfassung: Argo-Platform

- "Argo" ist die **aktuelle Generation** der Electrolux NIU-Firmware
- Laeuft auf **QCA4531-basierten NIUX-Modulen** mit OpenWRT Linux
- **Dishwasher hat v4.0.0S_argo** -- neueste Version unter allen Geraetetypen
- Hardware-ID `A23642205A` identifiziert die **Dishwasher/Hood NIUX-Variante**
- AllJoyn ist auf der Hardware vorhanden, aber **unklar ob in Argo-Firmware aktiviert**
- **Keine oeffentliche Dokumentation** ueber lokale Schnittstellen der Argo-Plattform
- **Kein Community-Erfolg** mit lokaler Kommunikation bei Electrolux/AEG Geraeten dokumentiert

### Naechste Schritte fuer lokales RE

1. **Port-Scan** (nmap -sS -sU -p- gegen Dishwasher IP) -- hoechste Prioritaet
2. **AllJoyn Probe** (Port 9955/9956 TCP + UDP multicast) -- vielversprechend wegen QCA4531
3. **mDNS Query** (avahi-browse oder dns-sd) -- Standard auf OpenWRT
4. **Traffic Capture** (Wireshark) -- DNS-Queries zeigen welche Hosts kontaktiert werden
5. **Windows IoT Explorer fuer AllJoyn** -- wenn AllJoyn antwortet, kann Introspection XML gelesen werden

---

## Quellen

- [HA Community: Electrolux/AEG connected appliances](https://community.home-assistant.io/t/electrolux-aeg-connected-appliances-integration-anyone/217633)
- [homeassistant-aeg (OCP Integration)](https://github.com/emanuelbesliu/homeassistant-aeg)
- [electrolux-ocp (Go Library)](https://github.com/mafredri/electrolux-ocp)
- [py-electrolux-ocp (Python, archiviert)](https://github.com/Woyken/py-electrolux-ocp)
- [pyelectroluxconnect (ECP, veraltet)](https://github.com/tomeko12/pyelectroluxconnect)
- [electrolux2mqtt](https://github.com/franciscofsales/electrolux2mqtt)
- [Trammell Hudson: Hacking HomeConnect Dishwashers](https://trmm.net/homeconnect/)
- [Electrolux Developer Portal](https://developer.electrolux.one/)
- [Electrolux OSS GitHub](https://github.com/electrolux-oss)
- [Qualcomm QCA4002 IoT WiFi SoC](https://www.qualcomm.com/products/technology/wi-fi/qca4002)
- [Electrolux joins AllSeen Alliance](https://www.electroluxgroup.com/en/electrolux-joins-allseen-alliance-to-enable-seamlessly-connected-appliances-19555/)
- [MAC Lookup 44:3E:07](https://maclookup.app/search/result?mac=44:3e:07)
- [Homey: Electrolux/AEG OCP App](https://homey.app/en-us/app/com.electrolux-aeg.ocp/Electrolux-AEG/)
- [ioBroker: AEG AllJoyn Issue](https://github.com/ioBroker/AdapterRequests/issues/772)
- [OCF Certified: AEG BSE999220B (AllJoyn)](https://openconnectivity.org/product/alljoyn/10145/)
- [Electrolux Official SDK (Test Data mit Argo Firmware)](https://github.com/electrolux-oss/electrolux-group-developer-sdk/tree/main/tests/client/appliances/data/appliance)
- [Electrolux NIUX FCC Filing (QCA4531)](https://fccid.io/2AIBX-NIUXL)
- [Electrolux NIU5 FCC Filing (WiFi+BLE)](https://fccid.io/2AIBX-NIU5L)
- [NIUX User Manual (QCA4531 Specs)](https://usermanual.wiki/ELECTROLUX-ITALIA-S-p-A/NIUXL/html)
- [QCA4531 Product Brief (Qualcomm)](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qca4531-product-brief.pdf)
- [Electrolux Open Source Licenses (NIUM/NIUF)](https://emtech.delta.electrolux.com/license)
- [NIU-HACL WiFi Board (Part 922695)](https://kitchenrestock.com/products/electrolux-professional-922695-connectivity-wi-fi-board-niu-hacl)
- [Blog: Disconnect Smart Oven (AEG Netzwerk-Verhalten)](https://svrooij.io/2023/01/25/disconnect-your-smart-appliance/)
- [OCF Certified Electrolux Products](https://openconnectivity.org/certified-product/electrolux-connected-elux100-ovens/)
- [AllJoyn Discovery Tutorial (Hackster.io)](https://www.hackster.io/dotMorten/discovering-and-interacting-with-any-alljoyn-device-0dbd86)
- [openHAB Electrolux Binding (swAncAndRevision Referenz)](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.electroluxappliance)
- [TTLucian HA Electrolux (Firmware Entities)](https://github.com/TTLucian/ha-electrolux)
- [Homebridge Electrolux (Frigidaire JSON Daten)](https://github.com/asp55/homebridge-electrolux-group)
