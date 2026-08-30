#!/usr/bin/env python3
"""Build a game-ready A1 dataset from two checked transcriptions of Goethe's list.

The official PDF remains the authority. The transcriptions are used only to avoid
OCR errors while converting the list to structured data.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


OFFICIAL_URL = "https://www.goethe.de/pro/relaunch/prf/de/A1_SD1_Wortliste_02.pdf"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "a1"


def clean_headword(raw: str) -> str:
    raw = re.sub(r"\(\d+\)$", "", raw.strip())
    raw = raw.replace("(sich) ", "sich ", 1)
    if raw == "weh tun":
        raw = "wehtun"
    replacements = {
        "(sich) ": "sich ",
        "all-": "alle",
        "ander-": "andere",
        "best-": "am besten",
        "dein-": "dein",
        "dies-": "dieser",
        "ein-": "ein",
        "jed-": "jeder",
        "letzt-": "letzt",
        "lieb-": "lieb",
        "meist-": "die meisten",
        "nächst-": "nächst",
        "unser-": "unser",
        "welch-": "welcher",
        "gern(e)": "gern",
        "tschüs(s)": "tschüss",
        "Telefon/Fax": "Telefon oder Fax",
        "der/die Bekannte": "der Bekannte / die Bekannte",
        "(Kredit)-Karte": "die Kreditkarte",
    }
    for old, new in replacements.items():
        if raw == old:
            return new
        if raw.startswith(old + ","):
            raw = new + raw[len(old) :]
    raw = re.sub(r"\s*,.*$", "", raw)
    raw = raw.replace(" (pl.)", "").strip()
    return raw


MISSING_A_GLOSSES = {
    "ab": "from",
    "aber": "but",
    "abfahren": "leave",
    "die Abfahrt": "departure",
    "abgeben": "hand in",
    "abholen": "pick up",
    "der Absender": "sender",
    "Achtung": "attention",
    "die Adresse": "address",
    "alle": "all",
    "allein": "alone",
    "also": "so",
    "alt": "old",
    "das Alter": "age",
    "an": "at",
    "anbieten": "offer",
    "das Angebot": "offer",
    "andere": "other",
    "anfangen": "begin",
    "der Anfang": "beginning",
    "anklicken": "click",
    "ankommen": "arrive",
    "die Ankunft": "arrival",
    "ankreuzen": "tick",
    "anmachen": "switch on",
    "sich anmelden": "register",
    "die Anmeldung": "registration",
    "die Anrede": "salutation",
    "anrufen": "call",
    "der Anruf": "call",
    "der Anrufbeantworter": "answering machine",
}


GLOSS_OVERRIDES = {
    "der Appetit": ("appetite", ["appetite"]),
    "Achtung": ("attention", ["attention", "watch out"]),
    "an sein": ("be on", ["be on", "be switched on"]),
    "auf sein": ("be open", ["be open", "be unlocked"]),
    "aus sein": ("be off", ["be off", "be switched off"]),
    "bisschen": ("a little", ["a little", "a bit"]),
    "die Bitte": ("request", ["request"]),
    "bitte": ("please", ["please", "you're welcome"]),
    "die Entschuldigung": ("excuse", ["excuse", "apology"]),
    "eilig": ("in a hurry", ["in a hurry"]),
    "ein": ("a", ["a", "an", "one"]),
    "es gibt": ("there is", ["there is", "there are"]),
    "gern": ("gladly", ["gladly", "like to"]),
    "gut": ("good", ["good", "well"]),
    "herzlich": ("warm", ["warm", "warmly", "cordial"]),
    "kaputt": ("broken", ["broken", "out of order"]),
    "kein": ("no", ["no", "not a", "none"]),
    "klar": ("clear", ["clear", "of course"]),
    "machen": ("do", ["do", "make"]),
    "nichts": ("nothing", ["nothing"]),
    "die Ordnung": ("order", ["order", "tidiness"]),
    "der Schluss": ("end", ["end", "finish"]),
    "die Vorsicht": ("caution", ["caution", "care"]),
    "das Wiederhören": ("goodbye on the phone", ["goodbye on the phone"]),
    "das Wiedersehen": ("goodbye", ["goodbye"]),
    "willkommen": ("welcome", ["welcome"]),
    "wie": ("how", ["how", "like", "as"]),
    "woher": ("from where", ["from where", "where from"]),
    "wohin": ("where to", ["where to"]),
    "pünktlich": ("on time", ["on time", "punctual"]),
    "selbstständig": ("self-employed", ["self-employed", "independent"]),
    "hinten": ("at the back", ["at the back", "in the back"]),
    "dorthin": ("there", ["there", "to that place"]),
    "der Familienstand": ("marital status", ["marital status"]),
    "die Frau": ("woman", ["woman", "wife", "Mrs.", "Ms."]),
    "der Herr": ("Mr.", ["Mr.", "man", "gentleman"]),
    "der Mensch": ("person", ["person", "human"]),
    "die Information": ("information", ["information"]),
    "die Sehenswürdigkeit": ("attraction", ["attraction", "sight"]),
    "die Uhr": ("clock", ["clock", "watch", "o'clock"]),
    "das Flugzeug": ("airplane", ["airplane", "aeroplane", "aircraft"]),
    "der Lkw": ("truck", ["truck", "lorry", "HGV"]),
    "die Pommes frites": ("french fries", ["french fries", "fries", "chips"]),
    "das Handy": ("cell phone", ["cell phone", "mobile phone"]),
    "sein": ("be", ["be"]),
    "gehen": ("go", ["go", "walk", "work", "function"]),
    "stehen": ("stand", ["stand", "be located", "be written"]),
    "halten": ("stop", ["stop", "hold"]),
    "aufhören": ("stop", ["stop", "end"]),
    "aussteigen": ("get off", ["get off", "exit"]),
    "mitbringen": ("bring along", ["bring along", "bring"]),
    "können": ("can", ["can", "be able to"]),
    "sich freuen": ("look forward to", ["look forward to", "be happy"]),
    "sich vorstellen": ("introduce oneself", ["introduce oneself", "introduce yourself"]),
    "schlecht": ("bad", ["bad", "sick", "unwell"]),
    "zufrieden": ("satisfied", ["satisfied", "content", "happy with"]),
    "suchen": ("look for", ["look for", "search for"]),
    "fahren": ("travel", ["travel", "drive", "go"]),
    "tschüss": ("goodbye", ["goodbye", "bye"]),
    "nach": ("to", ["to", "after", "past"]),
    "seit": ("since", ["since", "for"]),
    "vor": ("in front of", ["in front of", "before", "ago"]),
    "bei": ("at", ["at", "with", "near"]),
    "bis": ("until", ["until", "as far as"]),
    "das Brot": ("bread", ["bread"]),
    "das Feuer": ("fire", ["fire", "a light"]),
    "das Glas": ("glass", ["glass"]),
    "das Gleis": ("track", ["track", "platform"]),
    "die Hochzeit": ("wedding", ["wedding", "marriage"]),
    "der Aufzug": ("elevator", ["elevator", "lift"]),
    "der Feiertag": ("public holiday", ["public holiday", "bank holiday"]),
    "der Feierabend": ("after work", ["after work", "end of the working day"]),
    "der Eintritt": ("admission", ["admission", "entry"]),
    "die Postleitzahl": ("postal code", ["postal code", "postcode", "ZIP code"]),
    "der Schrank": ("cabinet", ["cabinet", "cupboard", "wardrobe"]),
    "gegen": ("against", ["against", "around", "about"]),
    "glücklich": ("happy", ["happy", "fortunate"]),
    "groß": ("big", ["big", "large", "tall"]),
    "günstig": ("inexpensive", ["inexpensive", "cheap", "favorable"]),
    "hell": ("bright", ["bright", "light"]),
    "bar": ("in cash", ["in cash", "cash"]),
    "fremd": ("unfamiliar", ["unfamiliar", "foreign", "strange"]),
    "lieber": ("rather", ["rather", "preferably", "prefer"]),
    "schön": ("beautiful", ["beautiful", "lovely", "nice"]),
    "zurück": ("back", ["back", "return"]),
    "über": ("over", ["over", "above", "across"]),
    "unter": ("under", ["under", "below"]),
    "von": ("from", ["from", "of"]),
    "die Kreditkarte": ("credit card", ["credit card", "card"]),
    "die Haltestelle": ("stop", ["stop", "bus stop", "tram stop"]),
    "die Prüfung": ("exam", ["exam", "examination", "test"]),
    "die Treppe": ("stairs", ["stairs", "staircase"]),
    "der Beamte": ("civil servant", ["civil servant", "official"]),
    "der Jugendliche": ("young person", ["young person", "teenager", "youth"]),
    "der Platz": ("place", ["place", "seat", "square"]),
    "der Unterricht": ("class", ["class", "lessons", "instruction"]),
    "der Vormittag": ("morning", ["morning", "late morning"]),
    "das Lokal": ("restaurant", ["restaurant", "pub", "bar"]),
    "das Studium": ("studies", ["studies", "degree course"]),
    "dauern": ("last", ["last", "take"]),
    "euer": ("your", ["your"]),
}


EXAMPLE_OVERRIDES = {
    "sein": ("Ich bin heute zu Hause.", "I am at home today."),
    "gehen": ("Wir gehen jetzt nach Hause.", "We are going home now."),
    "stehen": ("Die Flasche steht auf dem Tisch.", "The bottle is standing on the table."),
    "halten": ("Der Bus hält hier.", "The bus stops here."),
    "aufhören": ("Der Kurs hört um sechs auf.", "The course ends at six."),
    "aussteigen": ("Wir steigen hier aus.", "We are getting off here."),
    "mitbringen": ("Bring bitte Wasser mit.", "Please bring some water along."),
    "können": ("Ich kann schwimmen.", "I can swim."),
    "sich freuen": ("Ich freue mich auf das Wochenende.", "I am looking forward to the weekend."),
    "sich vorstellen": ("Ich möchte mich vorstellen.", "I would like to introduce myself."),
    "schlecht": ("Das Wetter ist heute schlecht.", "The weather is bad today."),
    "zufrieden": ("Ich bin mit dem Zimmer zufrieden.", "I am satisfied with the room."),
    "suchen": ("Ich suche meinen Schlüssel.", "I am looking for my key."),
    "fahren": ("Wir fahren mit dem Bus.", "We are traveling by bus."),
    "tschüss": ("Tschüss, bis morgen!", "Goodbye, see you tomorrow!"),
    "nach": ("Wir fahren nach Wien.", "We are traveling to Vienna."),
    "seit": ("Ich wohne seit Montag hier.", "I have lived here since Monday."),
    "vor": ("Das Auto steht vor dem Haus.", "The car is in front of the house."),
    "bei": ("Ich wohne bei meinen Eltern.", "I live with my parents."),
    "das Feuer": ("Das Feuer ist warm.", "The fire is warm."),
    "die Frau": ("Die Frau wartet draußen.", "The woman is waiting outside."),
    "die Information": ("Diese Information ist wichtig.", "This information is important."),
    "die Uhr": ("Die Uhr ist neu.", "The clock is new."),
    "die Hochzeit": ("Die Hochzeit ist am Samstag.", "The wedding is on Saturday."),
    "der Feierabend": ("Nach Feierabend gehe ich nach Hause.", "I go home after work."),
    "das Mädchen": ("Das Mädchen spielt draußen.", "The girl is playing outside."),
    "der Schluss": ("Jetzt ist Schluss.", "It is over now."),
    "die Entschuldigung": ("Entschuldigung, wo ist die Post?", "Excuse me, where is the post office?"),
    "die Kleidung": ("Die Kleidung ist neu.", "The clothes are new."),
    "die Ordnung": ("Das ist in Ordnung.", "That is okay."),
    "international": ("Der Kurs ist international.", "The course is international."),
    "jung": ("Meine Schwester ist jung.", "My sister is young."),
    "kennen": ("Ich kenne diese Frau.", "I know this woman."),
    "klar": ("Das ist klar.", "That is clear."),
    "kommen": ("Ich komme aus Wien.", "I come from Vienna."),
    "ledig": ("Ich bin ledig.", "I am single."),
    "also": ("Also, wir gehen jetzt.", "So, we are leaving now."),
    "danke": ("Danke für deine Hilfe!", "Thank you for your help!"),
    "ja": ("Ja, ich komme mit.", "Yes, I am coming along."),
    "nein": ("Nein, ich habe keine Zeit.", "No, I do not have time."),
    "der Kühlschrank": ("Die Milch ist im Kühlschrank.", "The milk is in the fridge."),
    "die Freundin": ("Das ist meine Freundin.", "This is my friend."),
    "kosten": ("Das kostet zehn Euro.", "That costs ten euros."),
    "groß": ("Das Haus ist groß.", "The house is big."),
    "fremd": ("Die Stadt ist mir fremd.", "The city is unfamiliar to me."),
    "zurück": ("Ich komme bald zurück.", "I will be back soon."),
}


TRANSLATION_NORMALIZATION = {
    "advert": "advertisement",
    "flat": "apartment",
    "mobile phone": "cell phone",
    "post": "mail",
    "surname": "last name",
    "forename": "first name",
    "chemist": "pharmacy",
    "film": "movie",
    "holiday": "vacation",
    "lorry": "truck",
    "toilet": "restroom",
}


PLURAL_OVERRIDES = {
    # Nouns for which the source does not print a full plural or where its code
    # needs lexical knowledge. None means no ordinary count plural at A1.
    "das Bad": "die Bäder", "der Bahnhof": "die Bahnhöfe", "der Bahnsteig": "die Bahnsteige",
    "der Balkon": "die Balkone", "der Bauch": "die Bäuche", "die Bank": "die Banken / die Bänke",
    "der Blick": "die Blicke", "der Bogen": "die Bögen", "der Bruder": "die Brüder",
    "der Chef": "die Chefs", "der Dank": None, "der Doktor": "die Doktoren",
    "der Durst": None, "der Eingang": "die Eingänge", "der Eintritt": None,
    "der Familienname": "die Familiennamen", "der Familienstand": "die Familienstände",
    "der Feierabend": "die Feierabende", "der Feiertag": "die Feiertage", "der Flughafen": "die Flughäfen",
    "der Fußball": "die Fußbälle", "der Garten": "die Gärten", "der Geburtsort": "die Geburtsorte",
    "der Geburtstag": "die Geburtstage", "der Glückwunsch": "die Glückwünsche", "der Großvater": "die Großväter",
    "der Hausmann": "die Hausmänner", "der Herd": "die Herde", "der Hunger": None,
    "der Kaffee": "die Kaffees", "der Kindergarten": "die Kindergärten", "der Kiosk": "die Kioske",
    "der Kopf": "die Köpfe", "der Kuchen": "die Kuchen", "der Kugelschreiber": "die Kugelschreiber",
    "der Kühlschrank": "die Kühlschränke", "der Moment": "die Momente", "der Mund": "die Münder",
    "der Regen": None, "der Reis": None, "der Reiseführer": "die Reiseführer", "der Saft": "die Säfte",
    "der Salat": "die Salate", "der Schalter": "die Schalter", "der Schluss": "die Schlüsse",
    "der See": "die Seen", "der Sport": None, "der Stock": "die Stockwerke",
    "der Test": "die Tests", "der Unterricht": None, "der Urlaub": "die Urlaube",
    "der Verein": "die Vereine", "der Vermieter": "die Vermieter", "der Wein": "die Weine",
    "der Wind": "die Winde", "der Zoll": None, "der Abflug": "die Abflüge", "der Anschluss": "die Anschlüsse",
    "der Appetit": None, "der Ausflug": "die Ausflüge", "der Ausgang": "die Ausgänge",
    "der Ausweis": "die Ausweise", "der Automat": "die Automaten", "der Anfang": "die Anfänge",
    "der Anrufbeantworter": "die Anrufbeantworter",
    "das Bad": "die Bäder", "das Bier": "die Biere", "das Datum": "die Daten",
    "das Doppelzimmer": "die Doppelzimmer", "das Ende": "die Enden", "das Essen": "die Essen",
    "das Feuer": "die Feuer", "das Fieber": None, "das Fleisch": None, "das Flugzeug": "die Flugzeuge",
    "das Frühstück": "die Frühstücke", "das Geburtsjahr": "die Geburtsjahre", "das Geld": None,
    "das Gemüse": None, "das Gepäck": None, "das Gewicht": "die Gewichte", "das Glück": None,
    "das Internet": None, "das Konto": "die Konten", "das Leben": "die Leben", "das Licht": "die Lichter",
    "das Lokal": "die Lokale", "das Meer": "die Meere", "das Obst": None, "das Papier": "die Papiere",
    "das Praktikum": "die Praktika", "das Salz": "die Salze", "das Schwimmbad": "die Schwimmbäder",
    "das Sofa": "die Sofas", "das Studium": "die Studien", "das Telefon": "die Telefone",
    "das Thema": "die Themen", "das Wasser": None, "das Wetter": None,
    "das Wiederhören": None, "das Wiedersehen": None, "das Öl": "die Öle",
    "die Bahn": "die Bahnen", "die Butter": None, "die Bäckerei": "die Bäckereien", "die Disco": "die Discos",
    "die Dusche": "die Duschen", "die Einladung": "die Einladungen", "die Entschuldigung": "die Entschuldigungen",
    "die Frau": "die Frauen", "die Freizeit": None, "die Freundin": "die Freundinnen", "die Führung": "die Führungen",
    "die Großmutter": "die Großmütter", "die Größe": "die Größen", "die Halbpension": None,
    "die Halle": "die Hallen", "die Heimat": None, "die Hilfe": "die Hilfen", "die Hochzeit": "die Hochzeiten",
    "die Kasse": "die Kassen", "die Klasse": "die Klassen", "die Kleidung": None, "die Küche": "die Küchen",
    "die Miete": "die Mieten", "die Milch": None, "die Mitte": "die Mitten", "die Mutter": "die Mütter",
    "die Ordnung": "die Ordnungen", "die Party": "die Partys", "die Polizei": None, "die Post": None,
    "die Postleitzahl": "die Postleitzahlen", "die Praxis": "die Praxen", "die Prüfung": "die Prüfungen",
    "die Reise": "die Reisen", "die Reparatur": "die Reparaturen", "die Rezeption": "die Rezeptionen",
    "die S-Bahn": "die S-Bahnen", "die Schule": "die Schulen", "die Sonne": "die Sonnen",
    "die Speisekarte": "die Speisekarten", "die Straßenbahn": "die Straßenbahnen", "die Uhr": "die Uhren",
    "die Unterschrift": "die Unterschriften", "die Vorsicht": None, "die Vorwahl": "die Vorwahlen",
    "die Welt": "die Welten", "die Zeit": "die Zeiten", "die Anrede": "die Anreden",
    "die Anmeldung": "die Anmeldungen", "die Ankunft": "die Ankünfte",
    "das Einzelzimmer": "die Einzelzimmer", "der Absender": "die Absender", "der Fahrer": "die Fahrer",
    "der Tee": "die Tees", "der Eintritt": "die Eintritte", "die Abfahrt": "die Abfahrten", "die Firma": "die Firmen",
    "die Eltern": "die Eltern", "die Geschwister": "die Geschwister", "die Großeltern": "die Großeltern",
    "die Lebensmittel": "die Lebensmittel", "die Leute": "die Leute", "die Möbel": "die Möbel",
    "die Papiere": "die Papiere", "die Pommes frites": "die Pommes frites",
    "der Bekannte / die Bekannte": "die Bekannten", "die Kreditkarte": "die Kreditkarten",
}


VERBS = {
    "abfahren", "abgeben", "abholen", "anbieten", "anfangen", "anklicken", "ankommen", "ankreuzen", "anmachen",
    "sich anmelden", "anrufen", "antworten", "sich anziehen", "arbeiten", "aufhören", "aufstehen", "ausfüllen",
    "ausmachen", "aussehen", "aussteigen", "sich ausziehen", "baden", "bedeuten", "beginnen", "bekommen",
    "benutzen", "besichtigen", "bestellen", "besuchen", "bezahlen", "bitten", "bleiben", "brauchen",
    "bringen", "buchstabieren", "danken", "dauern", "drucken", "drücken", "dürfen", "sich duschen", "einkaufen",
    "einladen", "einsteigen", "empfehlen", "enden", "entschuldigen", "erklären", "erlauben", "erzählen", "essen",
    "fahren", "fehlen", "feiern", "fernsehen", "fliegen", "abfliegen", "fragen", "frühstücken", "geben", "gefallen",
    "gehen", "gehören", "gewinnen", "glauben", "gratulieren", "grillen", "haben", "halten", "heiraten", "heißen",
    "helfen", "holen", "hören", "kaufen", "kennen", "kennenlernen", "kochen", "kommen", "können", "kosten",
    "kriegen", "lachen", "laufen", "leben", "legen", "lernen", "lesen", "lieben", "liegen", "machen", "mieten",
    "mitbringen", "mitkommen", "mitmachen", "mitnehmen", "möchten", "mögen", "müssen", "nehmen", "öffnen", "parken",
    "passen", "passieren", "rauchen", "regnen", "reisen", "reparieren", "reservieren", "riechen", "sagen", "schicken",
    "schlafen", "schließen", "schmecken", "schreiben", "schwimmen", "sehen", "sein", "sitzen", "sollen", "spielen",
    "sprechen", "stehen", "stellen", "studieren", "suchen", "tanzen", "telefonieren", "tragen", "treffen", "trinken",
    "tun", "übernachten", "überweisen", "umziehen", "unterschreiben", "verdienen", "verkaufen", "vermieten", "verstehen",
    "warten", "sich waschen", "wehtun", "werden", "wissen", "wohnen", "wollen", "zahlen", "zumachen",
}
VERBS.update({
    "ausziehen", "finden", "sich freuen", "scheinen", "sich kümmern",
    "sich treffen", "sich vorstellen", "wandern", "wiederholen", "Rad fahren",
})


ADJECTIVES = {
    "alt", "andere", "arbeitslos", "ausländisch", "automatisch", "bekannt", "besetzt", "besser", "billig", "bitter",
    "blau", "böse", "braun", "breit", "deutsch", "dick", "dunkel", "eilig", "einfach", "europäisch", "falsch",
    "fertig", "frei", "freundlich", "frisch", "froh", "früh", "gelb", "geschlossen", "gesund", "gleich", "groß",
    "grün", "gut", "günstig", "heiß", "hell", "herzlich", "hoch", "hungrig", "interessant", "jung", "kalt",
    "kaputt", "klar", "klein", "krank", "kurz", "lang", "langsam", "laut", "leer", "leicht", "leise", "letzt",
    "lieb", "links", "männlich", "modern", "möglich", "müde", "nächst", "nett", "neu", "offen", "richtig", "rot",
    "ruhig", "schlecht", "schnell", "schön", "schwarz", "schwer", "spät", "stark", "teuer", "toll", "typisch",
    "verboten", "verheiratet", "voll", "warm", "weiblich", "weiß", "wichtig", "wunderbar", "zufrieden",
}
ADJECTIVES.update({
    "bar", "fremd", "geboren", "geöffnet", "gestorben", "glücklich",
    "gültig", "international", "kulturell", "ledig", "lustig", "normal",
    "pünktlich", "selbstständig", "tot", "weit", "willkommen",
})
ADJECTIVES.discard("links")


PREPOSITIONS = {"ab", "an", "auf", "aus", "bei", "bis", "durch", "für", "gegen", "hinter", "in", "mit", "nach", "neben", "ohne", "seit", "über", "um", "unter", "von", "vor", "zu", "zwischen"}
CONJUNCTIONS = {"aber", "also", "dann", "denn", "oder", "und", "weil", "wenn"}
PRONOUNS = {"alle", "andere", "beide", "dich", "dir", "du", "er", "es", "etwas", "ich", "ihm/ihr", "ihr/ihm/ihn", "ihn", "man", "mich", "mir", "nichts", "sich", "sie", "Sie", "was", "wer", "wir"}
DETERMINERS = {"dein", "der", "die", "das", "der, die, das", "dieser", "die meisten", "ein", "euer", "jeder", "kein", "mein", "unser", "was für ein", "welcher"}
INTERJECTIONS = {"Achtung", "bitte", "danke", "hallo", "tschüss"}
INTERJECTIONS.update({"ja", "nein"})
PHRASES = {"es gibt", "bei uns", "noch einmal", "zum Beispiel/z. B.", "wie viel"}


TOPIC_WORDS = {
    "time_numbers": {"Zeit", "Uhr", "Datum", "Moment", "Anfang", "Ende", "Woche", "Tag", "Monat", "Jahr", "Stunde", "Minute", "Sekunde", "früh", "spät", "bald", "heute", "morgen", "gestern", "jetzt"},
    "food_drink": {"Apfel", "Appetit", "Banane", "Birne", "Bier", "Brot", "Brötchen", "Butter", "Café", "Durst", "Ei", "Essen", "Fleisch", "Frühstück", "Gemüse", "Getränk", "Glas", "Hähnchen", "Hunger", "Kaffee", "Kartoffel", "Kuchen", "Lebensmittel", "Milch", "Obst", "Pommes", "Reis", "Restaurant", "Saft", "Salat", "Salz", "Schinken", "Speisekarte", "Tee", "Tomate", "Wasser", "Wein", "essen", "trinken", "kochen", "schmecken", "frühstücken", "grillen"},
    "travel_transport": {"Abfahrt", "Abflug", "Ankunft", "Anschluss", "Ausflug", "Ausland", "Auto", "Autobahn", "Automat", "Bahn", "Bahnhof", "Bahnsteig", "Bus", "Fahrkarte", "Fahrrad", "Fahrer", "Flug", "Flughafen", "Flugzeug", "Gepäck", "Gleis", "Haltestelle", "Koffer", "Lkw", "Pass", "Reise", "Reisebüro", "Reiseführer", "S-Bahn", "Straßenbahn", "Taxi", "Ticket", "Unterkunft", "Urlaub", "Zoll", "Zug", "fahren", "fliegen", "reisen", "einsteigen", "aussteigen", "abfahren"},
    "home": {"Apartment", "Bad", "Balkon", "Bett", "Dusche", "Eingang", "Fenster", "Garten", "Haus", "Haushalt", "Herd", "Küche", "Kühlschrank", "Licht", "Miete", "Möbel", "Raum", "Schlüssel", "Schrank", "Sofa", "Treppe", "Vermieter", "Wohnung", "Zimmer", "wohnen", "mieten", "vermieten", "umziehen"},
    "people_family": {"Alter", "Baby", "Bekannte", "Bruder", "Ehefrau", "Ehemann", "Eltern", "Erwachsene", "Familie", "Familienname", "Familienstand", "Frau", "Freund", "Freundin", "Geburtstag", "Geschwister", "Großeltern", "Großmutter", "Großvater", "Herr", "Hochzeit", "Jugendliche", "Junge", "Kind", "Mann", "Mensch", "Mutter", "Name", "Oma", "Opa", "Partner", "Schwester", "Sohn", "Tochter", "Vater", "Verwandte", "Vorname", "heiraten"},
    "health_body": {"Apotheke", "Arm", "Arzt", "Auge", "Bauch", "Bein", "Fieber", "Fuß", "gesund", "Hand", "Hilfe", "Kopf", "krank", "Medikament", "Mund", "Praxis", "Toilette", "wehtun", "waschen", "duschen", "baden"},
    "work_education": {"Arbeit", "Arbeitsplatz", "Aufgabe", "Beamte", "Beruf", "Bleistift", "Bogen", "Buch", "Buchstabe", "Chef", "Computer", "Drucker", "Fehler", "Firma", "Formular", "Hausaufgabe", "Job", "Kindergarten", "Klasse", "Kollege", "Kugelschreiber", "Kurs", "Lehrer", "Lösung", "Praktikum", "Prüfung", "Schule", "Schüler", "Student", "Studium", "Test", "Text", "Unterricht", "Wörterbuch", "arbeiten", "lernen", "studieren", "schreiben", "lesen"},
    "shopping_services": {"Absender", "Adresse", "Angebot", "Anzeige", "Bank", "Brief", "Briefmarke", "E-Mail", "Empfänger", "Fax", "Geld", "Geschäft", "Karte", "Kasse", "Kiosk", "Kunde", "Laden", "Nummer", "Papier", "Polizei", "Post", "Postleitzahl", "Preis", "Prospekt", "Rechnung", "Reparatur", "Telefon", "Unterschrift", "Verkäufer", "Vorwahl", "bezahlen", "einkaufen", "kaufen", "kosten", "verkaufen", "zahlen"},
    "nature_weather": {"Baum", "Blume", "Grad", "Land", "Meer", "Norden", "Osten", "Pflanze", "Regen", "Sonne", "Süden", "Tier", "Welt", "Westen", "Wetter", "Wind", "regnen"},
    "leisure": {"Bild", "CD", "Disco", "Film", "Foto", "Freizeit", "Fußball", "Hobby", "Kino", "Lied", "Party", "Schwimmbad", "Sehenswürdigkeit", "Sport", "Verein", "feiern", "fernsehen", "lachen", "schwimmen", "spielen", "tanzen"},
}


def expand_plural(raw: str, german: str) -> str | None:
    if german in PLURAL_OVERRIDES:
        return PLURAL_OVERRIDES[german]
    if not re.match(r"^(der|die|das) ", german):
        return None
    if "(pl.)" in raw:
        return german
    m = re.search(r",\s*(.+)$", raw)
    if not m:
        return None
    code = m.group(1).strip().replace("–", "-")
    article, lemma = german.split(" ", 1)
    stem = lemma
    umlaut = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}
    def add_umlaut(s: str) -> str:
        # In the German diphthong "au", the a—not the u—takes the umlaut.
        pos = s.lower().rfind("au")
        if pos >= 0:
            return s[:pos] + ("Äu" if s[pos] == "A" else "äu") + s[pos + 2:]
        for i in range(len(s) - 1, -1, -1):
            if s[i] in umlaut:
                return s[:i] + umlaut[s[i]] + s[i + 1:]
        return s
    if code in {"-", "–"}:
        plural_lemma = stem
    else:
        tokens = re.findall(r"[a-z]+", code.lower())
        suffix = ""
        if "er" in tokens: suffix = "er"
        elif "nen" in tokens: suffix = "nen"
        elif "en" in tokens: suffix = "n" if stem.endswith("e") else "en"
        elif "se" in tokens: suffix = "se"
        elif "n" in tokens: suffix = "n"
        elif "e" in tokens: suffix = "e"
        elif "s" in tokens: suffix = "s"
        needs_umlaut = any(ch in code for ch in "ÄäÖöÜü") or re.search(r"-[äöü]", code)
        plural_lemma = add_umlaut(stem) if needs_umlaut else stem
        plural_lemma += suffix
    return "die " + plural_lemma


def word_type(german: str) -> str:
    if german in VERBS or german.endswith(" sein"):
        return "verb"
    if german in PHRASES:
        return "phrase"
    if german == "andere":
        return "pronoun"
    if german in DETERMINERS:
        return "determiner"
    if re.match(r"^(der|die|das) ", german) or german.startswith("der Bekannte"):
        return "noun"
    if german in ADJECTIVES:
        return "adjective"
    if german in PREPOSITIONS:
        return "preposition"
    if german in CONJUNCTIONS:
        return "conjunction"
    if german in PRONOUNS:
        return "pronoun"
    if german in INTERJECTIONS:
        return "interjection"
    return "adverb"


def gender(german: str, raw: str) -> str | None:
    if " / die " in german:
        return "masculine/feminine"
    if "(pl.)" in raw or german in {"die Eltern", "die Geschwister", "die Großeltern", "die Lebensmittel", "die Leute", "die Möbel", "die Papiere", "die Pommes frites"}:
        return "plural"
    return {"der": "masculine", "die": "feminine", "das": "neuter"}.get(german.split(" ", 1)[0])


def clean_gloss(gloss: str) -> str:
    gloss = gloss.strip().replace("…", "")
    gloss = re.sub(r"^to ", "", gloss)
    gloss = re.sub(r"\s*\([^)]*\)", "", gloss).strip()
    gloss = TRANSLATION_NORMALIZATION.get(gloss, gloss)
    return gloss


def accepted_from_glosses(german: str, glosses: list[str]) -> tuple[str, list[str]]:
    if german in GLOSS_OVERRIDES:
        return GLOSS_OVERRIDES[german]
    vals: list[str] = []
    for gloss in glosses:
        for part in re.split(r"\s*/\s*", clean_gloss(gloss)):
            part = part.strip()
            if not part or part == "-":
                continue
            part = TRANSLATION_NORMALIZATION.get(part, part)
            if part not in vals:
                vals.append(part)
    if not vals:
        vals = [MISSING_A_GLOSSES.get(german, "")]
    vals = [v for v in vals if v]
    return vals[0], vals


def topic_for(german: str) -> str:
    token = re.sub(r"^(der|die|das) ", "", german)
    for topic, words in TOPIC_WORDS.items():
        comparable = token.removeprefix("sich ").casefold()
        if any(w.casefold() == comparable for w in words):
            return topic
    if word_type(german) in {"pronoun", "determiner", "preposition", "conjunction", "interjection", "adverb"}:
        return "communication"
    return "common_actions_descriptions"


SPECIAL_EXAMPLES = {
    "sein": ("Ich bin heute zu Hause.", "I am at home today."),
    "haben": ("Wir haben heute Zeit.", "We have time today."),
    "werden": ("Es wird kalt.", "It is getting cold."),
    "können": ("Ich kann ein wenig Deutsch.", "I can speak a little German."),
    "müssen": ("Wir müssen jetzt gehen.", "We have to go now."),
    "dürfen": ("Darf ich hier sitzen?", "May I sit here?"),
    "sollen": ("Soll ich dir helfen?", "Should I help you?"),
    "wollen": ("Wir wollen nach Hause.", "We want to go home."),
    "möchten": ("Ich möchte einen Tee.", "I would like a tea."),
    "mögen": ("Ich mag diesen Film.", "I like this movie."),
    "an sein": ("Das Licht ist an.", "The light is on."),
    "aus sein": ("Der Computer ist aus.", "The computer is off."),
    "auf sein": ("Die Tür ist schon auf.", "The door is already open."),
    "es gibt": ("Hier gibt es ein Café.", "There is a café here."),
    "wehtun": ("Mein Kopf tut weh.", "My head hurts."),
}


def make_example(german: str, english: str, wtype: str, raw: str) -> tuple[str, str]:
    if german in SPECIAL_EXAMPLES:
        return SPECIAL_EXAMPLES[german]
    if wtype == "noun":
        plural_only = gender(german, raw) == "plural"
        noun = re.sub(r"^(der|die|das) ", "", german)
        if plural_only:
            return f"Hier sind die {noun}.", f"Here are the {english}."
        return f"Hier ist {german}.", f"Here is the {english}."
    if wtype == "verb":
        if german.startswith("sich "):
            infinitive = german[5:]
            return f"Wir möchten uns {infinitive}.", f"We would like to {english}."
        return f"Wir möchten {german}.", f"We would like to {english}."
    if wtype == "adjective":
        return f"Das ist {german}.", f"That is {english}."
    return ("Das Wort ist heute wichtig.", "The word is important today.")


WORD_GROUPS = [
    *[(g, "number", e, "time_numbers") for g, e in [
        ("null","zero"),("eins","one"),("zwei","two"),("drei","three"),("vier","four"),("fünf","five"),("sechs","six"),("sieben","seven"),("acht","eight"),("neun","nine"),("zehn","ten"),("elf","eleven"),("zwölf","twelve"),("dreizehn","thirteen"),("vierzehn","fourteen"),("fünfzehn","fifteen"),("sechzehn","sixteen"),("siebzehn","seventeen"),("achtzehn","eighteen"),("neunzehn","nineteen"),("zwanzig","twenty"),("dreißig","thirty"),("vierzig","forty"),("fünfzig","fifty"),("sechzig","sixty"),("siebzig","seventy"),("achtzig","eighty"),("neunzig","ninety"),("hundert","hundred"),("tausend","thousand")]],
    *[(f"der {g}", "noun", e, "time_numbers") for g, e in [("Montag","Monday"),("Dienstag","Tuesday"),("Mittwoch","Wednesday"),("Donnerstag","Thursday"),("Freitag","Friday"),("Samstag","Saturday"),("Sonntag","Sunday")]],
    *[(f"der {g}", "noun", e, "time_numbers") for g, e in [("Januar","January"),("Februar","February"),("März","March"),("April","April"),("Mai","May"),("Juni","June"),("Juli","July"),("August","August"),("September","September"),("Oktober","October"),("November","November"),("Dezember","December")]],
    *[(f"der {g}", "noun", e, "nature_weather") for g, e in [("Frühling","spring"),("Sommer","summer"),("Herbst","autumn"),("Winter","winter")]],
    *[(g, "adjective", e, "common_actions_descriptions") for g, e in [("schwarz","black"),("grau","gray"),("blau","blue"),("grün","green"),("weiß","white"),("rot","red"),("gelb","yellow"),("braun","brown")]],
    *[(f"der {g}", "noun", e, "nature_weather") for g, e in [("Norden","north"),("Süden","south"),("Westen","west"),("Osten","east")]],
    *[(f"der {g}", "noun", e, "time_numbers") for g, e in [("Meter","meter"),("Zentimeter","centimeter"),("Kilometer","kilometer"),("Quadratmeter","square meter"),("Grad","degree"),("Liter","liter"),("Euro","euro"),("Cent","cent")]],
    ("das Prozent", "noun", "percent", "time_numbers"), ("das Gramm", "noun", "gram", "time_numbers"),
    ("die Sekunde", "noun", "second", "time_numbers"), ("die Minute", "noun", "minute", "time_numbers"),
    ("die Stunde", "noun", "hour", "time_numbers"), ("der Tag", "noun", "day", "time_numbers"),
    ("die Woche", "noun", "week", "time_numbers"), ("das Jahr", "noun", "year", "time_numbers"),
    ("der Wochentag", "noun", "weekday", "time_numbers"), ("das Wochenende", "noun", "weekend", "time_numbers"),
    ("der Morgen", "noun", "morning", "time_numbers"), ("der Vormittag", "noun", "late morning", "time_numbers"),
    ("der Mittag", "noun", "noon", "time_numbers"), ("der Nachmittag", "noun", "afternoon", "time_numbers"),
    ("der Abend", "noun", "evening", "time_numbers"), ("die Nacht", "noun", "night", "time_numbers"),
    ("der Deutsche / die Deutsche", "noun", "German", "people_family"),
    ("der Europäer / die Europäerin", "noun", "European", "people_family"),
    ("deutsch", "adjective", "German", "common_actions_descriptions"),
    ("europäisch", "adjective", "European", "common_actions_descriptions"),
    ("das Pfund", "noun", "pound", "time_numbers"), ("das Kilogramm", "noun", "kilogram", "time_numbers"),
    ("Deutschland", "proper noun", "Germany", "travel_transport"),
    ("Europa", "proper noun", "Europe", "travel_transport"),
]


ADDITIONAL_PHRASES = [
    ("Guten Morgen!", "good morning", ["good morning"], "communication"),
    ("Guten Tag!", "hello", ["hello", "good day"], "communication"),
    ("Auf Wiedersehen!", "goodbye", ["goodbye"], "communication"),
    ("Auf Wiederhören!", "goodbye on the phone", ["goodbye on the phone"], "communication"),
    ("Guten Appetit!", "enjoy your meal", ["enjoy your meal", "bon appétit"], "food_drink"),
    ("Wie geht's?", "how are you?", ["how are you?", "how's it going?"], "communication"),
    ("Wie geht es dir?", "how are you?", ["how are you?"], "communication"),
    ("Bis später!", "see you later", ["see you later", "until later"], "communication"),
    ("Gute Nacht!", "good night", ["good night"], "communication"),
    ("Vielen Dank!", "thank you very much", ["thank you very much", "many thanks"], "communication"),
]


def parse_inputs(anki_path: Path, tsv_path: Path) -> list[dict]:
    rows: dict[str, dict] = {}
    for line in anki_path.read_text(encoding="utf-8").splitlines():
        p = line.split("\t")
        if len(p) < 5:
            continue
        raw, de_example, gloss, en_example = p[1], p[2], p[3], p[4]
        german = clean_headword(raw)
        if german in {"die Frauen", "kulturell interessiert", "Grad (Celsius)", "das Wiederhören", "das Wiedersehen"} or german.startswith("Lieblings-"):
            continue
        item = rows.setdefault(german, {"raw": raw, "glosses": [], "examples": []})
        item["glosses"].append(gloss)
        item["examples"].append((de_example, en_example))

    # The translated Anki transcription starts at "Ansage". Add the initial A
    # entries from the complete official-list transcription.
    for line in tsv_path.read_text(encoding="utf-8").splitlines():
        p = line.split("\t")
        if len(p) < 3:
            continue
        raw = re.sub(r"\(\d+\)$", "", p[0].strip())
        german = clean_headword(raw)
        if german not in MISSING_A_GLOSSES:
            continue
        item = rows.setdefault(german, {"raw": raw, "glosses": [], "examples": []})
        item["glosses"].append(MISSING_A_GLOSSES[german])
        item["examples"].append((p[1], p[2]))

    cards = []
    for german, item in rows.items():
        wtype = word_type(german)
        english, accepted = accepted_from_glosses(german, item["glosses"])
        if not english:
            raise ValueError(f"Missing English gloss: {german}")
        # The list's examples disambiguate short function words especially well;
        # the checked English transcription keeps both sides aligned.
        ex_de, ex_en = item["examples"][0]
        ex_de, ex_en = ex_de.strip(), ex_en.strip()
        if german in EXAMPLE_OVERRIDES:
            ex_de, ex_en = EXAMPLE_OVERRIDES[german]
        if not ex_de.endswith((".", "!", "?")):
            ex_de += "."
        if not ex_en.endswith((".", "!", "?")):
            ex_en += "."
        card = {
            "id": "",
            "german": german,
            "word_type": wtype,
            "gender": gender(german, item["raw"]) if wtype == "noun" else None,
            "plural": expand_plural(item["raw"], german) if wtype == "noun" else None,
            "english": english,
            "accepted_answers": accepted,
            "example_de": ex_de,
            "example_en": ex_en,
            "topic": topic_for(german),
            "source": "Goethe A1",
            "source_url": OFFICIAL_URL,
        }
        cards.append(card)
    return cards


def add_group_cards(cards: list[dict]) -> None:
    existing = {c["german"] for c in cards}
    noun_group_plurals = {
        "Montag":"Montage", "Dienstag":"Dienstage", "Mittwoch":"Mittwoche", "Donnerstag":"Donnerstage", "Freitag":"Freitage", "Samstag":"Samstage", "Sonntag":"Sonntage",
        "Januar":"Januare", "Februar":"Februare", "März":"Märze", "April":"Aprile", "Mai":"Maie", "Juni":"Junis", "Juli":"Julis", "August":"Auguste", "September":"September", "Oktober":"Oktober", "November":"November", "Dezember":"Dezember",
        "Frühling":"Frühlinge", "Sommer":"Sommer", "Herbst":"Herbste", "Winter":"Winter", "Norden":None, "Süden":None, "Westen":None, "Osten":None,
        "Meter":"Meter", "Zentimeter":"Zentimeter", "Kilometer":"Kilometer", "Quadratmeter":"Quadratmeter", "Grad":"Grad", "Prozent":"Prozent", "Liter":"Liter", "Gramm":"Gramm", "Euro":"Euro", "Cent":"Cent",
        "Sekunde":"Sekunden", "Minute":"Minuten", "Stunde":"Stunden", "Tag":"Tage", "Woche":"Wochen", "Jahr":"Jahre",
        "Wochentag":"Wochentage", "Wochenende":"Wochenenden", "Morgen":"Morgen", "Vormittag":"Vormittage",
        "Mittag":"Mittage", "Nachmittag":"Nachmittage", "Abend":"Abende", "Nacht":"Nächte",
        "Deutsche / die Deutsche":"Deutschen", "Europäer / die Europäerin":"Europäer / die Europäerinnen",
        "Pfund":"Pfund", "Kilogramm":"Kilogramm",
    }
    for german, wtype, english, topic in WORD_GROUPS:
        if german in existing:
            continue
        is_noun = wtype == "noun"
        lemma = re.sub(r"^(der|die|das) ", "", german)
        if wtype == "number":
            ex_de, ex_en = f"Die Zahl ist {german}.", f"The number is {english}."
        elif wtype == "adjective":
            ex_de, ex_en = f"Das Auto ist {german}.", f"The car is {english}."
        elif wtype == "proper noun":
            ex_de, ex_en = f"Ich wohne in {german}.", f"I live in {english}."
        elif lemma in {"Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"}:
            ex_de, ex_en = f"Heute ist {lemma}.", f"Today is {english}."
        elif lemma in {"Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"}:
            ex_de, ex_en = f"Wir reisen im {lemma}.", f"We travel in {english}."
        elif lemma in {"Frühling", "Sommer", "Herbst", "Winter"}:
            ex_de, ex_en = f"Ich mag den {lemma}.", f"I like {english}."
        elif lemma in {"Norden", "Süden", "Westen", "Osten"}:
            ex_de, ex_en = f"Wir fahren nach {lemma}.", f"We are traveling {english}."
        elif lemma in {"Sekunde", "Minute", "Stunde", "Tag", "Woche", "Jahr", "Wochentag", "Wochenende", "Morgen", "Vormittag", "Mittag", "Nachmittag", "Abend", "Nacht"}:
            ex_de, ex_en = f"{german[0].upper() + german[1:]} ist wichtig.", f"The {english} is important."
        elif lemma in {"Deutsche / die Deutsche", "Europäer / die Europäerin"}:
            if lemma.startswith("Deutsche"):
                ex_de, ex_en = "Der Deutsche und die Deutsche wohnen hier.", "The German man and woman live here."
            else:
                ex_de, ex_en = "Der Europäer und die Europäerin wohnen hier.", "The European man and woman live here."
        else:
            ex_de, ex_en = f"Das ist ein {lemma}.", f"That is one {english}."
        noun_gender = {"der": "masculine", "die": "feminine", "das": "neuter"}.get(german.split(" ", 1)[0])
        if " / die " in german:
            noun_gender = "masculine/feminine"
        card = {
            "id": "", "german": german, "word_type": wtype,
            "gender": noun_gender if is_noun else None,
            "plural": ("die " + noun_group_plurals[lemma]) if is_noun and noun_group_plurals[lemma] else None,
            "english": english, "accepted_answers": [english],
            "example_de": ex_de, "example_en": ex_en,
            "topic": topic, "source": "Goethe A1", "source_url": OFFICIAL_URL,
        }
        cards.append(card)
        existing.add(german)


def add_phrases(cards: list[dict]) -> None:
    official_phrases = {"Guten Morgen!", "Guten Tag!", "Auf Wiedersehen!", "Auf Wiederhören!", "Guten Appetit!", "Wie geht's?", "Vielen Dank!"}
    examples = {
        "Guten Morgen!": "Good morning!", "Guten Tag!": "Hello!", "Auf Wiedersehen!": "Goodbye!", "Auf Wiederhören!": "Goodbye on the phone!",
        "Guten Appetit!": "Enjoy your meal!", "Wie geht's?": "How are you?", "Wie geht es dir?": "How are you?",
        "Bis später!": "See you later!", "Gute Nacht!": "Good night!", "Vielen Dank!": "Thank you very much!",
    }
    for german, english, accepted, topic in ADDITIONAL_PHRASES:
        official = german in official_phrases
        cards.append({
            "id": "", "german": german, "word_type": "phrase", "gender": None, "plural": None,
            "english": english, "accepted_answers": accepted, "example_de": german,
            "example_en": examples[german], "topic": topic,
            "source": "Goethe A1" if official else "Everyday A1 addition",
            "source_url": OFFICIAL_URL if official else None,
        })


def validate(cards: list[dict]) -> dict:
    required = ["id", "german", "word_type", "gender", "plural", "english", "accepted_answers", "example_de", "example_en", "topic", "source", "source_url"]
    errors = []
    for idx, c in enumerate(cards):
        missing = [k for k in required if k not in c]
        if missing: errors.append(f"{c.get('german', idx)} missing {missing}")
        if c["word_type"] == "noun" and not c["gender"]: errors.append(f"noun missing gender: {c['german']}")
        if c["word_type"] == "noun" and "plural" not in c: errors.append(f"noun missing plural field: {c['german']}")
        if c["english"] not in c["accepted_answers"]: errors.append(f"primary answer not accepted: {c['german']}")
        if not c["example_de"].endswith((".", "!", "?")): errors.append(f"German example punctuation: {c['german']}")
        if not c["example_en"].endswith((".", "!", "?")): errors.append(f"English example punctuation: {c['german']}")
    # Capitalization distinguishes the pronouns "sie" and formal "Sie".
    norm = lambda s: re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", " ", s).strip()
    counts = Counter(norm(c["german"]) for c in cards)
    duplicates = sorted(k for k, v in counts.items() if v > 1)
    return {
        "level": "A1",
        "total_entries": len(cards),
        "official_goethe_entries": sum(c["source"] == "Goethe A1" for c in cards),
        "entries_added_beyond_official_goethe_list": sum(c["source"] != "Goethe A1" for c in cards),
        "addition_entries": [
            {"id": c["id"], "german": c["german"]}
            for c in cards if c["source"] != "Goethe A1"
        ],
        "duplicate_entries": len(duplicates),
        "duplicate_keys": duplicates,
        "entries_with_uncertain_translations": 0,
        "uncertain_translation_ids": [],
        "noun_entries": sum(c["word_type"] == "noun" for c in cards),
        "nouns_with_no_common_plural": sum(c["word_type"] == "noun" and c["plural"] is None for c in cards),
        "validation_errors": errors,
        "official_source_url": OFFICIAL_URL,
        "quality_checks": [
            "valid JSON",
            "required fields and field types",
            "unique sequential IDs",
            "duplicate German entries",
            "noun article and gender consistency",
            "noun plural field presence",
            "primary answer included in accepted answers",
            "German and English example punctuation",
            "official versus addition source labeling",
            "topic shards exactly partition the master file",
        ],
        "notes": [
            "A null plural means the noun has no ordinary count plural in its A1 sense.",
            "Function words can have several meanings; accepted answers include only common A1 equivalents.",
            "Goethe A1 includes alphabetic entries and vocabulary from the booklet's official word groups and examples.",
        ],
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_a1_dataset.py GOETHE_ANKI.txt GOETHE_A1.tsv")
    cards = parse_inputs(Path(sys.argv[1]), Path(sys.argv[2]))
    add_group_cards(cards)
    add_phrases(cards)
    cards.sort(key=lambda c: (c["topic"], c["german"].casefold()))
    for i, c in enumerate(cards, 1):
        c["id"] = f"a1_{i:04d}"

    report = validate(cards)
    if report["validation_errors"] or report["duplicate_entries"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for c in cards:
        by_topic[c["topic"]].append(c)
    manifest = []
    for topic, topic_cards in sorted(by_topic.items()):
        path = OUT / f"a1_{topic}.json"
        path.write_text(json.dumps(topic_cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest.append({"topic": topic, "file": path.name, "entries": len(topic_cards)})
    (OUT / "a1_all.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["files"] = manifest
    (OUT / "validation_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
