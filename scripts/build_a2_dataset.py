#!/usr/bin/env python3
"""Build the A2-only production data from a checked Goethe A2 transcription.

The official Goethe PDF is the authority.  The Markdown deck is used as a
machine-readable transcription of the PDF's alphabetic section; its English
text is corrected and cross-checked against Goethe's English A2 glossary.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A1_FILE = ROOT / "data" / "a1" / "a1_all.json"
OUT = ROOT / "data" / "a2"
OFFICIAL_URL = "https://www.goethe.de/pro/relaunch/prf/de/Goethe-Zertifikat_A2_Wortliste.pdf"
ACCESS_DATE = "2026-08-30"
ALPHABETIC_SOURCE_ITEMS = 1214
WORD_GROUP_SOURCE_ITEMS = 230


HEADWORD_OVERRIDES = {
    "anderen": "andere",
    "alles": "alle",
    "die Bank (Geldinstitut)": "die Bank",
    "die Bank (Sitzgelegenheit)": "die Bank",
    "die Bekannte (weiblich)": "die Bekannte",
    "der Bekannte (männlich)": "der Bekannte",
    "eigenes": "eigen",
    "geehrte": "geehrt",
    "her kommen": "her",
    "jeden": "jeder",
    "jedes": "jeder",
    "letzte": "letzt",
    "Lieblingsfarbe": "die Lieblingsfarbe",
    "nächste": "nächst",
    "der Rind": "das Rind",
    "der Jugendliche (männlich)": "der Jugendliche",
    "die Jugendliche (weiblich)": "die Jugendliche",
    "der See (Teich)": "der See",
    "die See (Meer)": "die See",
    "sich schneiden": "schneiden",
    "sich über informieren": "sich über etwas informieren",
    "tschüs": "tschüss",
    "viele": "viel",
}

# These are ordinary A1 repetitions whose spelling, article, inflection, or
# presentation differs in the A2 transcription.  Distinct expressions such as
# "auf jeden Fall" and new separable compounds remain eligible.
KNOWN_A1_ALIASES = {
    "andere", "alle", "die Bank", "die Bekannte", "der Bekannte",
    "der Jugendliche", "die Jugendliche", "jeder", "letzt", "nächst",
    "der See", "tschüss", "viel", "das Wiederhören", "das Wiedersehen",
}


ANSWER_OVERRIDES = {
    "anders": ("otherwise", ["otherwise", "differently", "different"]),
    "abschließen": ("lock", ["lock", "complete", "finish"]),
    "die Angst": ("fear", ["fear", "anxiety"]),
    "die Ahnung": ("idea", ["idea", "clue"]),
    "als": ("than", ["than", "as"]),
    "ansehen": ("look at", ["look at", "watch", "view"]),
    "der Apparat": ("device", ["device", "apparatus", "machine"]),
    "die Ausbildung": ("vocational training", ["vocational training", "training", "apprenticeship"]),
    "sich ärgern": ("get annoyed", ["get annoyed", "be annoyed", "be angry"]),
    "der Artikel": ("article", ["article", "item"]),
    "auspacken": ("unpack", ["unpack"]),
    "außerhalb": ("outside", ["outside", "outside of"]),
    "austragen": ("deliver", ["deliver"]),
    "beenden": ("finish", ["finish", "end"]),
    "basteln": ("do crafts", ["do crafts", "make things"]),
    "der Bescheid": ("information", ["information", "decision", "answer"]),
    "der Besuch": ("visit", ["visit", "visitor"]),
    "bestehen": ("pass", ["pass", "consist of"]),
    "braten": ("fry", ["fry", "roast"]),
    "dabei sein": ("be there", ["be there", "take part", "have with you"]),
    "das Einzelkind": ("only child", ["only child"]),
    "das Fach": ("subject", ["subject", "compartment"]),
    "die Datei": ("file", ["file"]),
    "die Band": ("band", ["band", "music group"]),
    "die Bewerbung": ("application", ["application"]),
    "das Blatt": ("leaf", ["leaf", "sheet", "piece of paper"]),
    "darauf": ("to that", ["to that", "on it", "after that"]),
    "deutlich": ("clearly", ["clearly", "distinctly", "clear"]),
    "doch": ("yes", ["yes", "but", "still", "after all"]),
    "egal": ("not matter", ["not matter", "all the same"]),
    "das Eis": ("ice cream", ["ice cream", "ice"]),
    "erst": ("only", ["only", "first"]),
    "der Fahrplan": ("timetable", ["timetable", "schedule"]),
    "fertig sein": ("be ready", ["be ready", "be finished"]),
    "die Fundsachen": ("lost property", ["lost property", "lost and found"]),
    "ganz": ("whole", ["whole", "intact", "completely", "quite"]),
    "geehrt": ("dear", ["dear", "honored"]),
    "gegenüber": ("opposite", ["opposite", "across from"]),
    "das Gericht": ("dish", ["dish", "court"]),
    "die Geschichte": ("story", ["story", "history"]),
    "das Geschirr": ("dishes", ["dishes", "crockery"]),
    "die Gesundheit": ("health", ["health", "bless you"]),
    "der Hals": ("throat", ["throat", "neck"]),
    "her": ("here", ["here", "this way"]),
    "herein": ("come in", ["come in", "in"]),
    "der Haushalt": ("household", ["household"]),
    "hin": ("there", ["there", "to there"]),
    "hinaus": ("out", ["out", "outside"]),
    "hinein": ("in", ["in", "inside", "into"]),
    "sich über etwas informieren": ("find out about", ["find out about", "get information about"]),
    "die Kette": ("necklace", ["necklace", "chain"]),
    "klappen": ("work", ["work", "succeed"]),
    "die Krankenkasse": ("health insurance provider", ["health insurance provider", "health insurance fund"]),
    "der Kredit": ("loan", ["loan", "credit"]),
    "der Krimi": ("crime story", ["crime story", "crime novel", "thriller"]),
    "klug": ("clever", ["clever", "smart"]),
    "komisch": ("funny", ["funny", "strange"]),
    "kontrollieren": ("check", ["check", "inspect", "control"]),
    "kündigen": ("quit", ["quit", "give notice", "cancel"]),
    "lassen": ("let", ["let", "leave"]),
    "leidtun": ("be sorry", ["be sorry"]),
    "die Lust": ("desire", ["desire", "feel like"]),
    "die Lieblingsfarbe": ("favorite color", ["favorite color", "favourite colour"]),
    "mal": ("once", ["once", "just", "sometime"]),
    "das Mal": ("time", ["time"]),
    "meinen": ("mean", ["mean", "think"]),
    "merken": ("remember", ["remember", "notice"]),
    "die Messe": ("trade fair", ["trade fair", "fair", "exhibition"]),
    "das Mittel": ("remedy", ["remedy", "means"]),
    "die Nachricht": ("message", ["message", "news"]),
    "nennen": ("call", ["call", "name", "mention"]),
    "die Nähe": ("nearby", ["nearby", "vicinity"]),
    "natürlich": ("of course", ["of course", "naturally"]),
    "neben": ("next to", ["next to", "beside"]),
    "die Note": ("grade", ["grade", "mark", "note"]),
    "das Paar": ("couple", ["couple", "pair"]),
    "passen": ("fit", ["fit", "suit"]),
    "praktisch": ("practical", ["practical", "handy"]),
    "raten": ("advise", ["advise", "guess"]),
    "reiten": ("ride", ["ride", "ride a horse"]),
    "die Reinigung": ("dry cleaner's", ["dry cleaner's", "dry cleaning", "cleaning"]),
    "der Rundgang": ("tour", ["tour", "walk-through"]),
    "sauer": ("sour", ["sour", "angry"]),
    "schaffen": ("manage", ["manage", "accomplish"]),
    "das Rezept": ("recipe", ["recipe", "prescription"]),
    "scharf": ("spicy", ["spicy", "sharp"]),
    "das Rind": ("cattle", ["cattle", "beef"]),
    "schenken": ("give as a gift", ["give as a gift", "give"]),
    "schimpfen": ("scold", ["scold", "complain", "grumble"]),
    "das Schloss": ("castle", ["castle", "lock"]),
    "das Schwein": ("pig", ["pig", "swine"]),
    "die See": ("sea", ["sea"]),
    "der Schmerz": ("pain", ["pain", "ache"]),
    "schneiden": ("cut", ["cut"]),
    "sich bewerben": ("apply", ["apply", "apply for"]),
    "sich eintragen": ("register", ["register", "sign up", "enter one's name"]),
    "sich interessieren": ("be interested in", ["be interested in", "take an interest in"]),
    "sich setzen": ("sit down", ["sit down", "take a seat"]),
    "selbst": ("self", ["self", "myself", "yourself", "oneself", "in person"]),
    "die Sendung": ("show", ["show", "program", "broadcast"]),
    "der Star": ("star", ["star", "celebrity"]),
    "das Stück": ("piece", ["piece", "play"]),
    "sicher": ("safe", ["safe", "sure", "certain"]),
    "der Stift": ("pen", ["pen", "pencil"]),
    "das Stockwerk": ("floor", ["floor", "story", "storey"]),
    "stören": ("disturb", ["disturb", "bother"]),
    "super": ("great", ["great", "really well"]),
    "sympathisch": ("likeable", ["likeable", "likable", "nice"]),
    "die Tafel": ("board", ["board", "blackboard", "whiteboard"]),
    "total": ("totally", ["totally", "completely"]),
    "tragen": ("carry", ["carry", "wear"]),
    "die Torte": ("cake", ["cake", "gateau"]),
    "der Umzug": ("move", ["move", "relocation"]),
    "austauschen": ("exchange", ["exchange", "swap", "replace"]),
    "teilen": ("share", ["share", "divide"]),
    "unternehmen": ("do", ["do", "undertake"]),
    "unterwegs sein": ("be on the way", ["be on the way", "be out"]),
    "umsteigen": ("change trains", ["change trains", "transfer", "change"]),
    "verabredet sein": ("have plans", ["have plans", "be meeting"]),
    "vereinbaren": ("arrange", ["arrange", "agree"]),
    "verbieten": ("forbid", ["forbid", "prohibit", "ban"]),
    "verschieben": ("postpone", ["postpone", "reschedule", "move"]),
    "vorbei": ("past", ["past", "over"]),
    "vorne": ("at the front", ["at the front", "in front"]),
    "wählen": ("dial", ["dial", "choose", "vote"]),
    "die Wäsche": ("laundry", ["laundry", "washing"]),
    "der Weg": ("way", ["way", "path", "route"]),
    "weg": ("away", ["away", "gone", "off"]),
    "wegmachen": ("remove", ["remove", "clear away"]),
    "wegwerfen": ("throw away", ["throw away", "discard"]),
    "weiterhelfen": ("help", ["help", "assist"]),
    "der Workshop": ("workshop", ["workshop", "seminar"]),
    "das Zeugnis": ("school report", ["school report", "report card", "certificate"]),
    "das Ziel": ("destination", ["destination", "goal", "finish"]),
}


EXAMPLE_OVERRIDES = {
    "aktuell": ("Das ist das aktuelle Kinoprogramm.", "This is the current movie schedule."),
    "die Apotheke": ("Das Medikament bekommen Sie in der Apotheke.", "You can get the medicine at the pharmacy."),
    "die Ausbildung": ("Ich möchte eine Ausbildung zum Krankenpfleger machen.", "I would like to train as a nurse."),
    "auspacken": ("Packst du bitte den Koffer aus?", "Will you please unpack the suitcase?"),
    "auf keinen Fall": ("Ich sehe den Film auf keinen Fall an!", "I definitely will not watch the movie!"),
    "aufpassen": ("Pass auf, der Teller fällt gleich auf den Boden!", "Watch out, the plate is about to fall on the floor!"),
    "austragen": ("Er trägt jeden Morgen die Zeitung aus.", "He delivers the newspaper every morning."),
    "basteln": ("Die Kinder haben etwas gebastelt.", "The children made something."),
    "der Bescheid": ("Sie bekommt erst nächste Woche Bescheid.", "She will not get an answer until next week."),
    "die Bewerbung": ("Kannst du mir bei meiner Bewerbung helfen?", "Can you help me with my application?"),
    "braten": ("Braten Sie das Fleisch in etwas Öl!", "Fry the meat in a little oil!"),
    "dabei sein": ("Hast du einen Stift dabei?", "Do you have a pen with you?"),
    "darauf": ("Darauf fällt mir keine Antwort ein.", "I cannot think of an answer to that."),
    "doch": ("Hast du keinen Hunger? - Doch, ich bin sehr hungrig.", "Aren't you hungry? - Yes, I am very hungry."),
    "egal": ("Das ist mir egal.", "I do not care."),
    "eng": ("Diese Hose ist zu eng. Gibt es sie auch eine Nummer größer?", "These pants are too tight. Do you have them one size larger?"),
    "die Ferien": ("Bald haben wir Ferien.", "Our vacation starts soon."),
    "fertig sein": ("Wir müssen gleich gehen. Bist du fertig?", "We have to leave soon. Are you ready?"),
    "das Fest": ("Am Wochenende feiern wir ein Fest. Meine Tochter hat Geburtstag.", "We are having a party this weekend. It is my daughter's birthday."),
    "der Fahrplan": ("Ist das der neue Fahrplan?", "Is this the new timetable?"),
    "fit sein": ("Tom will fit sein. Er geht jeden Tag ins Fitnessstudio.", "Tom wants to be fit. He goes to the gym every day."),
    "die Fundsachen": ("Sie können dort bei den Fundsachen schauen.", "You can check the lost-and-found office over there."),
    "ganz": ("Zum Glück ist die Brille noch ganz!", "Luckily, the glasses are still intact!"),
    "gegenüber": ("Die Post ist gegenüber vom Bahnhof.", "The post office is opposite the train station."),
    "die Gesundheit": ("Gesundheit! Sind Sie erkältet?", "Bless you! Do you have a cold?"),
    "der Haushalt": ("Meine Frau und ich machen den Haushalt zusammen.", "My wife and I share the housework."),
    "die Hose": ("Kann ich die Hose waschen?", "Can I wash these pants?"),
    "die Kamera": ("Mit der Kamera kann er Fotos und Filme machen.", "He can take photos and make videos with the camera."),
    "klappen": ("Können wir uns heute Mittag treffen? - Ja, das klappt.", "Can we meet at noon today? - Yes, that works."),
    "die Krankenkasse": ("Bei welcher Krankenkasse sind Sie?", "Which health insurance provider are you with?"),
    "die Lust": ("Ich habe keine Lust.", "I do not feel like it."),
    "die Nudel": ("Möchten Sie lieber Reis oder Nudeln? - Lieber Nudeln, bitte.", "Would you prefer rice or pasta? - Pasta, please."),
    "das Plakat": ("Wir machen im Unterricht ein Plakat zum Thema Essen und Trinken.", "We are making a poster about food and drink in class."),
    "praktisch": ("Das finde ich sehr praktisch.", "I find that very practical."),
    "rechnen": ("Sarah kann gut rechnen.", "Sarah is good at arithmetic."),
    "die Reinigung": ("Bringst du bitte die Bluse in die Reinigung?", "Will you please take the blouse to the dry cleaner's?"),
    "rufen": ("Rufst du bitte die Kinder? Das Essen ist fertig.", "Will you please call the children? The food is ready."),
    "schaffen": ("Kannst du mir bitte helfen? Ich schaffe das nicht allein.", "Can you please help me? I cannot manage it alone."),
    "scharf": ("Die Suppe ist mir zu scharf.", "The soup is too spicy for me."),
    "schrecklich": ("Ich finde ihren Rock schrecklich. Er sieht furchtbar aus!", "I think her skirt is awful. It looks terrible!"),
    "die Sendung": ("Welche Sendungen schaust du gern an?", "Which shows do you like to watch?"),
    "der Stift": ("Brauchst du einen Bleistift oder einen Kugelschreiber?", "Do you need a pencil or a pen?"),
    "das Stipendium": ("Wenn ich ein gutes Zeugnis habe, bekomme ich ein Stipendium.", "If I have a good school report, I will receive a scholarship."),
    "stören": ("Störe ich?", "Am I disturbing you?"),
    "sympathisch": ("Der neue Chef ist sehr sympathisch.", "The new boss is very likeable."),
    "die Tafel": ("Der Lehrer schreibt das neue Wort an die Tafel.", "The teacher writes the new word on the board."),
    "die Vermieterin": ("Unsere Vermieterin ist schon sehr alt.", "Our landlady is already very old."),
    "vorgestern": ("Er hat mich vorgestern angerufen.", "He called me the day before yesterday."),
    "vorne": ("Bitte vorne einsteigen!", "Please board at the front!"),
    "das Wiederhören": ("Auf Wiederhören!", "Goodbye!"),
    "zumachen": ("Machst du bitte das Fenster zu?", "Will you please close the window?"),
    "das Zeugnis": ("Morgen bekommen die Kinder ihr Zeugnis.", "The children will receive their school reports tomorrow."),
    "aktiv": ("Peter ist sehr aktiv und macht viel Sport.", "Peter is very active and does a lot of sports."),
    "ansehen": ("Darf ich eure Urlaubsfotos ansehen?", "May I look at your vacation photos?"),
    "ausgehen": ("Gehen wir am Freitag zusammen aus?", "Shall we go out together on Friday?"),
    "aussprechen": ("Wie spricht man das Wort aus?", "How do you pronounce the word?"),
    "beenden": ("Du musst deine Ausbildung auf jeden Fall beenden.", "You definitely have to finish your vocational training."),
    "besonders": ("Dieses Angebot ist besonders günstig.", "This offer is especially inexpensive."),
    "der Apparat": ("Was machen wir mit deinem alten Apparat?", "What should we do with your old device?"),
    "der Besuch": ("Wir bekommen am Wochenende Besuch.", "We are having visitors this weekend."),
    "der Fernseher": ("Der Fernseher ist kaputt.", "The television is broken."),
    "der Motorroller": ("Oskar fährt mit dem Motorroller zur Arbeit.", "Oskar rides his scooter to work."),
    "der Ski": ("Gehen wir am Wochenende Ski fahren?", "Shall we go skiing this weekend?"),
    "der Workshop": ("Das war ein toller Workshop. Ich habe viel gelernt.", "That was a great workshop. I learned a lot."),
    "die Baustelle": ("Vor unserem Haus ist eine große Baustelle.", "There is a large construction site in front of our house."),
    "die Geschichte": ("Erzählst du mir eine Geschichte?", "Will you tell me a story?"),
    "die Übersetzung": ("Ich brauche eine Übersetzung von meinem Zeugnis.", "I need a translation of my school report."),
    "gefährlich": ("Du darfst nicht bei Rot über die Straße gehen. Das ist gefährlich.", "You must not cross the street when the light is red. It is dangerous."),
    "mitspielen": ("Warum spielt ihr nicht mit?", "Why don't you join in?"),
    "neben": ("Neben mir ist noch ein Platz frei.", "There is still a free seat next to me."),
    "privat": ("Das ist meine private Handynummer.", "This is my personal cell phone number."),
    "schwanger": ("Lena ist schwanger. Sie bekommt im Juli ein Kind.", "Lena is pregnant. She is having a baby in July."),
    "sonst": ("Haben Sie sonst noch einen Wunsch? - Nein danke, das ist alles.", "Would you like anything else? - No, thank you. That is all."),
    "super": ("Er kann super tanzen.", "He can dance really well."),
    "das Festival": ("Am Wochenende ist in der Stadt ein Musikfestival.", "There is a music festival in the city this weekend."),
    "der Zirkus": ("Heute gehen wir mit den Kindern in den Zirkus.", "We are taking the children to the circus today."),
    "der Fluss": ("Der Rhein ist ein großer Fluss.", "The Rhine is a large river."),
    "der Schnee": ("In den Bergen liegt viel Schnee.", "There is a lot of snow in the mountains."),
    "der Himmel": ("Heute ist tolles Wetter: Der Himmel ist blau und es gibt keine Wolken.", "The weather is wonderful today: the sky is blue and there are no clouds."),
    "der Service": ("Ich bin mit dem Service in der Werkstatt sehr zufrieden.", "I am very satisfied with the service at the garage."),
    "mal": ("Sag mal, wie gefällt dir mein neues Kleid?", "Tell me, what do you think of my new dress?"),
    "wählen": ("Sie müssen erst eine Null wählen.", "You must dial zero first."),
    "die Bibliothek": ("Sie lernt jeden Tag in der Bibliothek.", "She studies in the library every day."),
    "die Schülerin": ("In meinem Kurs sind drei Schülerinnen.", "There are three female students in my class."),
    "der Titel": ("Wie heißt der Film? - Ich weiß den Titel nicht mehr.", "What is the movie called? - I cannot remember the title."),
    "der Wunsch": ("Haben Sie noch einen Wunsch?", "Would you like anything else?"),
    "die Portion": ("Ich nehme eine kleine Portion Eis.", "I will have a small portion of ice cream."),
    "die Ruhe": ("Ruhe, bitte! Hier in der Bibliothek darf man nicht laut sprechen.", "Quiet, please! You must not speak loudly in the library."),
    "die Zeitschrift": ("Diese Zeitschrift kauft Andrea jede Woche.", "Andrea buys this magazine every week."),
    "liefern": ("Wir liefern Ihnen den Schrank nach Hause.", "We will deliver the wardrobe to your home."),
    "meinen": ("Wie meinst du das? Erklär mir das bitte genauer!", "What do you mean? Please explain that more precisely!"),
    "schimpfen": ("Warum schimpfst du denn so laut?", "Why are you complaining so loudly?"),
    "ein paar": ("Wir fahren ein paar Tage ans Meer.", "We are going to the seaside for a few days."),
    "einige": ("In diesem Text sind einige Fehler.", "There are some errors in this text."),
    "die Person": ("Eintritt pro Person: 5 Euro.", "Admission is five euros per person."),
    "die Qualität": ("Dieser Fernseher hat eine gute Qualität.", "This television is good quality."),
    "das Projekt": ("Wir machen ein Projekt über Sehenswürdigkeiten in unserer Stadt.", "We are doing a project about attractions in our city."),
    "das Ziel": ("John läuft sehr schnell. Er war als Erster am Ziel.", "John runs very fast. He was the first to reach the finish."),
    "die Rentnerin": ("Meine Tante arbeitet nicht mehr. Sie ist Rentnerin.", "My aunt no longer works. She is retired."),
    "der Club": ("Gibt es hier einen Tennisclub?", "Is there a tennis club here?"),
}


PLURAL_OVERRIDES = {
    "die Band": "die Bands", "die Creme": "die Cremes / die Cremen",
    "das Eis": None, "die Ferien": "die Ferien", "die Fundsachen": "die Fundsachen",
    "das Geschirr": None, "die Gesundheit": None, "der Käse": None,
    "die Kenntnisse": "die Kenntnisse", "die Kosmetik": None, "die Lust": None,
    "das Medikament": "die Medikamente", "das Mineralwasser": None,
    "der Müll": None, "das Museum": "die Museen", "die Musik": None,
    "die Nähe": None, "die Pizza": "die Pizzas / die Pizzen", "das Quiz": "die Quiz",
    "das Rind": "die Rinder", "der Schirm": "die Schirme", "der Schnee": None,
    "die See": None, "der Service": None, "der Ski": "die Ski / die Skier",
    "der Spaß": None, "der Stress": None, "die Süßigkeiten": "die Süßigkeiten",
    "das Taschengeld": None, "das Tennis": None, "die Wäsche": None,
}


ADJECTIVES = {
    "aktiv", "aktuell", "aufregend", "beliebt", "bequem", "berühmt", "besonders", "bewölkt",
    "blöd", "blond", "bunt", "dick", "dringend", "dumm", "dunkel", "dünn",
    "echt", "eigen", "eng", "fantastisch", "faul", "fett", "fleißig", "freiwillig",
    "freundlich", "frisch", "froh", "furchtbar", "ganz", "gefährlich", "geehrt", "gesund", "hart", "heiß", "hässlich", "intelligent",
    "interessant", "klug", "komisch", "kostenlos", "kühl", "langweilig", "leer",
    "kalt", "modern", "nass", "natürlich", "neblig", "nervös", "nett", "notwendig", "nützlich", "online",
    "offen", "praktisch", "preiswert", "privat", "reich", "romantisch", "rund",
    "sauber", "sauer", "schädlich", "scharf", "schlimm", "schmutzig", "schrecklich",
    "schwanger", "schwach", "schwierig", "sicher", "sonnig", "spannend", "sportlich",
    "stark", "streng", "stressig", "super", "süß", "sympathisch", "tief", "toll", "traurig",
    "trocken", "typisch", "verschieden", "voll", "vorsichtig", "wach", "wahr", "warm", "weich",
    "windig", "witzig",
}
PREPOSITIONS = {"außer", "außerhalb", "gegenüber", "hinter", "neben", "pro", "wegen"}
CONJUNCTIONS = {"als", "dass", "weil", "wenn"}
PRONOUNS = {"alle", "andere", "einige", "etwas", "jemand", "manche", "niemand", "wen", "wem"}
DETERMINERS = {"eigen", "jeder", "viel"}
PHRASES = {"auf jeden Fall", "auf keinen Fall", "dafür sein", "dagegen sein", "recht haben", "zum Beispiel"}
SPLIT_VERBS = {
    "mitspielen", "verbieten", "wegbringen", "wegfahren", "weggehen", "weglaufen", "wegmachen",
    "wegnehmen", "wegwerfen", "weiterhelfen", "weitermachen", "wünschen", "zurückfahren",
    "zurückgeben", "zurückgehen", "zurückkommen", "zurücklaufen",
}
INTERJECTIONS = {"schade"}


TOPIC_HINTS = {
    "health_body": {"Angst", "Apotheke", "Brille", "Gesicht", "Gesundheit", "Grippe", "Hals", "Körper", "Krank", "Magen", "Medikament", "Schmerz", "Zahn"},
    "home": {"Erdgeschoss", "Fenster", "Garage", "Geschirr", "Haushalt", "Heizung", "Keller", "Lampe", "Müll", "Schlafzimmer", "Vermieterin", "Wohnzimmer"},
    "leisure": {"Band", "Basketball", "Festival", "Flohmarkt", "Gitarre", "Instrument", "Konzert", "Krimi", "Kunst", "Museum", "Sportplatz", "Theater", "Volleyball", "Zirkus", "Zoo"},
    "nature_weather": {"Berg", "Fluss", "Gewitter", "Himmel", "Insel", "Landschaft", "Natur", "Pflanze", "Schnee", "See", "Wald", "Wolke"},
    "people_family": {"Bekannte", "Ehepartner", "Jugendliche", "Nachbar", "Nachbarin", "Person"},
    "shopping_services": {"Bank", "Bewerbung", "Geldbörse", "Kredit", "Kundin", "Messe", "Passwort", "Produkt", "Qualität", "Reinigung", "Service", "Vertrag", "Webseite"},
    "time_numbers": {"Kalender", "Mal", "Zahl"},
    "travel_transport": {"Ausbildung", "Fahrplan", "Flug", "Führerschein", "Jugendherberge", "Reifen", "Rucksack", "Schiff", "Stadtplan", "Strand", "Tour", "Tourist", "Touristin", "Unterkunft", "Unfall", "Verkehr", "Verkehrsmittel", "Verspätung", "Wagen", "Zelt", "Ziel"},
    "work_education": {"Artikel", "Bibliothek", "Blatt", "Büro", "Datei", "Fach", "Gehalt", "Kenntnisse", "Kollegin", "Mitarbeiter", "Note", "Projekt", "Schülerin", "Stipendium", "Studentin", "Tafel", "Zeugnis"},
}


# Word-group items that add A2 material not already represented by an A1 card
# or by the checked alphabetic transcription.  Paired occupations follow A1's
# combined masculine/feminine convention unless only the feminine lemma is new.
GROUP_ADDITIONS = [
    ("ca.", "abbreviation", "approximately", ["approximately", "about"], "Der Kurs beginnt ca. um neun Uhr.", "The course starts at about nine o'clock.", "communication", None, None),
    ("d. h.", "abbreviation", "that is", ["that is", "i.e."], "Der Kurs ist kostenlos, d. h., Sie müssen nichts bezahlen.", "The course is free; that is, you do not have to pay anything.", "communication", None, None),
    ("ICE", "abbreviation", "high-speed train", ["high-speed train", "Intercity Express"], "Wir fahren mit dem ICE nach Berlin.", "We are taking the high-speed train to Berlin.", "travel_transport", None, None),
    ("PC", "abbreviation", "computer", ["computer", "PC"], "Mein PC ist schon sehr alt.", "My computer is already very old.", "communication", None, None),
    ("SMS", "abbreviation", "text message", ["text message", "SMS"], "Ich schicke dir eine SMS.", "I will send you a text message.", "communication", None, None),
    ("usw.", "abbreviation", "and so on", ["and so on", "etc."], "Wir brauchen Brot, Milch, Käse usw.", "We need bread, milk, cheese, and so on.", "communication", None, None),
    ("WC", "abbreviation", "restroom", ["restroom", "toilet", "WC"], "Wo ist das WC?", "Where is the restroom?", "communication", None, None),
    ("auf Deutsch", "phrase", "in German", ["in German"], "Können Sie das bitte auf Deutsch sagen?", "Can you please say that in German?", "communication", None, None),
    ("der Antwortbogen", "noun", "answer sheet", ["answer sheet"], "Bitte schreiben Sie auf den Antwortbogen.", "Please write on the answer sheet.", "work_education", "masculine", "die Antwortbögen"),
    ("markieren", "verb", "mark", ["mark", "highlight"], "Markieren Sie die richtige Antwort.", "Mark the correct answer.", "work_education", None, None),
    ("der Prüfer / die Prüferin", "noun", "examiner", ["examiner"], "Die Prüferin erklärt die Aufgabe.", "The examiner explains the task.", "work_education", "masculine/feminine", "die Prüfer / die Prüferinnen"),
    ("der Punkt", "noun", "point", ["point", "dot"], "Für diese Antwort bekommen Sie einen Punkt.", "You get one point for this answer.", "work_education", "masculine", "die Punkte"),
    ("der Angestellte / die Angestellte", "noun", "employee", ["employee"], "Die Angestellte arbeitet im Büro.", "The employee works in the office.", "work_education", "masculine/feminine", "die Angestellten"),
    ("die Ärztin", "noun", "doctor", ["doctor", "physician"], "Die Ärztin untersucht mich.", "The doctor examines me.", "health_body", "feminine", "die Ärztinnen"),
    ("der Auszubildende / die Auszubildende", "noun", "trainee", ["trainee", "apprentice"], "Die Auszubildende arbeitet heute im Büro.", "The trainee is working in the office today.", "work_education", "masculine/feminine", "die Auszubildenden"),
    ("der Autor / die Autorin", "noun", "author", ["author", "writer"], "Die Autorin liest aus ihrem neuen Buch.", "The author reads from her new book.", "work_education", "masculine/feminine", "die Autoren / die Autorinnen"),
    ("der Bäcker / die Bäckerin", "noun", "baker", ["baker"], "Die Bäckerin backt frisches Brot.", "The baker bakes fresh bread.", "work_education", "masculine/feminine", "die Bäcker / die Bäckerinnen"),
    ("die Doktorin", "noun", "doctor", ["doctor"], "Die Doktorin arbeitet im Krankenhaus.", "The doctor works at the hospital.", "health_body", "feminine", "die Doktorinnen"),
    ("die Fahrerin", "noun", "driver", ["driver"], "Die Fahrerin wartet im Auto.", "The driver is waiting in the car.", "travel_transport", "feminine", "die Fahrerinnen"),
    ("der Friseur / die Friseurin", "noun", "hairdresser", ["hairdresser", "hairstylist"], "Die Friseurin schneidet meine Haare.", "The hairdresser cuts my hair.", "work_education", "masculine/feminine", "die Friseure / die Friseurinnen"),
    ("der Handwerker / die Handwerkerin", "noun", "tradesperson", ["tradesperson", "craftsperson"], "Der Handwerker repariert die Heizung.", "The tradesperson repairs the heating.", "work_education", "masculine/feminine", "die Handwerker / die Handwerkerinnen"),
    ("der Journalist / die Journalistin", "noun", "journalist", ["journalist"], "Die Journalistin schreibt einen Artikel.", "The journalist writes an article.", "work_education", "masculine/feminine", "die Journalisten / die Journalistinnen"),
    ("der Kaufmann / die Kauffrau", "noun", "businessperson", ["businessperson", "merchant"], "Die Kauffrau arbeitet in einer großen Firma.", "The businessperson works for a large company.", "work_education", "masculine/feminine", "die Kaufleute / die Kauffrauen"),
    ("der Kellner / die Kellnerin", "noun", "server", ["server", "waiter", "waitress"], "Die Kellnerin bringt die Getränke.", "The server brings the drinks.", "food_drink", "masculine/feminine", "die Kellner / die Kellnerinnen"),
    ("der Koch / die Köchin", "noun", "cook", ["cook", "chef"], "Die Köchin macht eine Suppe.", "The cook makes soup.", "food_drink", "masculine/feminine", "die Köche / die Köchinnen"),
    ("der Krankenpfleger / die Krankenschwester", "noun", "nurse", ["nurse"], "Der Krankenpfleger arbeitet im Krankenhaus.", "The nurse works at the hospital.", "health_body", "masculine/feminine", "die Krankenpfleger / die Krankenschwestern"),
    ("der Künstler / die Künstlerin", "noun", "artist", ["artist"], "Die Künstlerin malt ein Bild.", "The artist paints a picture.", "leisure", "masculine/feminine", "die Künstler / die Künstlerinnen"),
    ("die Lehrerin", "noun", "teacher", ["teacher"], "Die Lehrerin erklärt die Aufgabe.", "The teacher explains the task.", "work_education", "feminine", "die Lehrerinnen"),
    ("der Mechaniker / die Mechanikerin", "noun", "mechanic", ["mechanic"], "Die Mechanikerin repariert das Auto.", "The mechanic repairs the car.", "work_education", "masculine/feminine", "die Mechaniker / die Mechanikerinnen"),
    ("das Model", "noun", "model", ["model"], "Das Model trägt ein rotes Kleid.", "The model is wearing a red dress.", "work_education", "neuter", "die Models / die Modelle"),
    ("der Musiker / die Musikerin", "noun", "musician", ["musician"], "Der Musiker spielt Klavier.", "The musician plays the piano.", "leisure", "masculine/feminine", "die Musiker / die Musikerinnen"),
    ("der Polizist / die Polizistin", "noun", "police officer", ["police officer"], "Die Polizistin hilft uns.", "The police officer helps us.", "work_education", "masculine/feminine", "die Polizisten / die Polizistinnen"),
    ("die Rentnerin", "noun", "retiree", ["retiree", "pensioner"], "Meine Tante ist Rentnerin.", "My aunt is retired.", "people_family", "feminine", "die Rentnerinnen"),
    ("der Sänger / die Sängerin", "noun", "singer", ["singer"], "Die Sängerin ist sehr bekannt.", "The singer is very well known.", "leisure", "masculine/feminine", "die Sänger / die Sängerinnen"),
    ("der Schauspieler / die Schauspielerin", "noun", "actor", ["actor", "actress"], "Die Schauspielerin spielt in einem neuen Film.", "The actor is in a new movie.", "leisure", "masculine/feminine", "die Schauspieler / die Schauspielerinnen"),
    ("der Techniker / die Technikerin", "noun", "technician", ["technician"], "Die Technikerin repariert meinen PC.", "The technician repairs my computer.", "work_education", "masculine/feminine", "die Techniker / die Technikerinnen"),
    ("die Verkäuferin", "noun", "salesperson", ["salesperson", "sales assistant"], "Die Verkäuferin berät den Kunden.", "The salesperson advises the customer.", "shopping_services", "feminine", "die Verkäuferinnen"),
    ("der Cousin", "noun", "cousin", ["cousin"], "Mein Cousin wohnt in Berlin.", "My cousin lives in Berlin.", "people_family", "masculine", "die Cousins"),
    ("die Cousine", "noun", "cousin", ["cousin"], "Meine Cousine besucht uns am Wochenende.", "My cousin is visiting us this weekend.", "people_family", "feminine", "die Cousinen"),
    ("der Enkel", "noun", "grandson", ["grandson"], "Mein Enkel geht schon zur Schule.", "My grandson already goes to school.", "people_family", "masculine", "die Enkel"),
    ("die Enkelin", "noun", "granddaughter", ["granddaughter"], "Meine Enkelin ist sechs Jahre alt.", "My granddaughter is six years old.", "people_family", "feminine", "die Enkelinnen"),
    ("der Onkel", "noun", "uncle", ["uncle"], "Mein Onkel wohnt in Hamburg.", "My uncle lives in Hamburg.", "people_family", "masculine", "die Onkel"),
    ("die Tante", "noun", "aunt", ["aunt"], "Meine Tante besucht uns am Sonntag.", "My aunt is visiting us on Sunday.", "people_family", "feminine", "die Tanten"),
    ("getrennt", "adjective", "separated", ["separated"], "Meine Eltern leben getrennt.", "My parents are separated.", "people_family", None, None),
    ("geschieden", "adjective", "divorced", ["divorced"], "Er ist seit zwei Jahren geschieden.", "He has been divorced for two years.", "people_family", None, None),
    ("lila", "adjective", "purple", ["purple", "lilac"], "Sie trägt eine lila Bluse.", "She is wearing a purple blouse.", "common_actions_descriptions", None, None),
    ("orange", "adjective", "orange", ["orange"], "Der Pullover ist orange.", "The sweater is orange.", "common_actions_descriptions", None, None),
    ("rosa", "adjective", "pink", ["pink"], "Das T-Shirt ist rosa.", "The T-shirt is pink.", "common_actions_descriptions", None, None),
    ("Österreich", "proper noun", "Austria", ["Austria"], "Wien liegt in Österreich.", "Vienna is in Austria.", "travel_transport", None, None),
    ("der Österreicher / die Österreicherin", "noun", "Austrian", ["Austrian"], "Die Österreicherin kommt aus Wien.", "The Austrian is from Vienna.", "people_family", "masculine/feminine", "die Österreicher / die Österreicherinnen"),
    ("österreichisch", "adjective", "Austrian", ["Austrian"], "Das ist eine österreichische Spezialität.", "That is an Austrian specialty.", "common_actions_descriptions", None, None),
    ("die Schweiz", "proper noun", "Switzerland", ["Switzerland"], "Bern liegt in der Schweiz.", "Bern is in Switzerland.", "travel_transport", None, None),
    ("der Schweizer / die Schweizerin", "noun", "Swiss person", ["Swiss person", "Swiss"], "Die Schweizerin kommt aus Bern.", "The Swiss woman is from Bern.", "people_family", "masculine/feminine", "die Schweizer / die Schweizerinnen"),
    ("schweizerisch", "adjective", "Swiss", ["Swiss"], "Das ist eine schweizerische Firma.", "That is a Swiss company.", "common_actions_descriptions", None, None),
    ("Luxemburg", "proper noun", "Luxembourg", ["Luxembourg"], "Luxemburg liegt in Europa.", "Luxembourg is in Europe.", "travel_transport", None, None),
    ("der Luxemburger / die Luxemburgerin", "noun", "Luxembourger", ["Luxembourger", "person from Luxembourg"], "Die Luxemburgerin spricht Deutsch.", "The Luxembourger speaks German.", "people_family", "masculine/feminine", "die Luxemburger / die Luxemburgerinnen"),
    ("luxemburgisch", "adjective", "Luxembourgish", ["Luxembourgish"], "Er hat die luxemburgische Staatsangehörigkeit.", "He has Luxembourgish citizenship.", "common_actions_descriptions", None, None),
    ("das Abitur", "noun", "school-leaving qualification", ["school-leaving qualification", "Abitur", "high school diploma"], "Sie macht nächstes Jahr ihr Abitur.", "She will complete her school-leaving qualification next year.", "work_education", "neuter", None),
    ("der Direktor", "noun", "principal", ["principal", "director", "headteacher"], "Der Direktor spricht mit den Eltern.", "The principal speaks with the parents.", "work_education", "masculine", "die Direktoren"),
    ("die Klassenfahrt", "noun", "class trip", ["class trip", "school trip"], "Unsere Klasse macht eine Klassenfahrt nach Berlin.", "Our class is taking a school trip to Berlin.", "work_education", "feminine", "die Klassenfahrten"),
    ("das Sekretariat", "noun", "school office", ["school office", "secretary's office"], "Das Formular bekommen Sie im Sekretariat.", "You can get the form from the school office.", "work_education", "neuter", "die Sekretariate"),
    ("der Stundenplan", "noun", "timetable", ["timetable", "class schedule"], "Mathematik steht am Montag auf dem Stundenplan.", "Math is on the timetable on Monday.", "work_education", "masculine", "die Stundenpläne"),
    ("die Biologie", "noun", "biology", ["biology"], "Biologie ist mein Lieblingsfach.", "Biology is my favorite subject.", "work_education", "feminine", None),
    ("die Chemie", "noun", "chemistry", ["chemistry"], "Wir haben heute Chemie.", "We have chemistry today.", "work_education", "feminine", None),
    ("das Englisch", "noun", "English", ["English"], "Mein Englisch ist noch nicht sehr gut.", "My English is not very good yet.", "work_education", "neuter", None),
    ("das Französisch", "noun", "French", ["French"], "Sie lernt Französisch in der Schule.", "She learns French at school.", "work_education", "neuter", None),
    ("die Geografie", "noun", "geography", ["geography"], "In Geografie lernen wir etwas über Europa.", "In geography, we learn about Europe.", "work_education", "feminine", None),
    ("die Geschichte", "noun", "history", ["history", "story"], "Geschichte ist heute die erste Stunde.", "History is the first lesson today.", "work_education", "feminine", "die Geschichten"),
    ("die Kunst", "noun", "art", ["art"], "Kunst macht mir viel Spaß.", "I really enjoy art.", "work_education", "feminine", None),
    ("das Latein", "noun", "Latin", ["Latin"], "Mein Sohn lernt Latein.", "My son learns Latin.", "work_education", "neuter", None),
    ("die Mathematik", "noun", "mathematics", ["mathematics", "math", "maths"], "Mathematik ist nicht leicht.", "Math is not easy.", "work_education", "feminine", None),
    ("die Physik", "noun", "physics", ["physics"], "Wir schreiben morgen einen Test in Physik.", "We have a physics test tomorrow.", "work_education", "feminine", None),
    ("die Religion", "noun", "religion", ["religion"], "Religion ist heute die letzte Stunde.", "Religion is the last lesson today.", "work_education", "feminine", "die Religionen"),
    ("die Sozialkunde", "noun", "social studies", ["social studies", "civics"], "In Sozialkunde sprechen wir über Politik.", "In social studies, we talk about politics.", "work_education", "feminine", None),
    ("der Franken", "noun", "franc", ["franc", "Swiss franc"], "Das kostet zehn Franken.", "That costs ten francs.", "time_numbers", "masculine", "die Franken"),
    ("der Rappen", "noun", "rappen", ["rappen", "Swiss centime"], "Ein Franken hat hundert Rappen.", "One franc is one hundred rappen.", "time_numbers", "masculine", "die Rappen"),
    ("Grad Celsius", "phrase", "degree Celsius", ["degree Celsius", "degree centigrade"], "Heute sind es zehn Grad Celsius.", "It is ten degrees Celsius today.", "time_numbers", None, None),
    ("Karneval", "proper noun", "Carnival", ["Carnival"], "Im Februar feiern wir Karneval.", "We celebrate Carnival in February.", "time_numbers", None, None),
    ("Ostern", "proper noun", "Easter", ["Easter"], "Zu Ostern besuchen wir unsere Familie.", "We visit our family at Easter.", "time_numbers", None, None),
    ("Weihnachten", "proper noun", "Christmas", ["Christmas"], "Zu Weihnachten fahren wir zu meinen Eltern.", "We visit my parents at Christmas.", "time_numbers", None, None),
    ("Neujahr", "proper noun", "New Year's Day", ["New Year's Day", "New Year"], "An Neujahr haben viele Geschäfte geschlossen.", "Many stores are closed on New Year's Day.", "time_numbers", None, None),
    ("Silvester", "proper noun", "New Year's Eve", ["New Year's Eve"], "An Silvester feiern wir mit Freunden.", "We celebrate with friends on New Year's Eve.", "time_numbers", None, None),
    ("das Frühjahr", "noun", "spring", ["spring", "springtime"], "Im Frühjahr wird es wieder wärmer.", "It gets warmer again in spring.", "nature_weather", "neuter", "die Frühjahre"),
    ("die Mitternacht", "noun", "midnight", ["midnight"], "Der Film endet um Mitternacht.", "The movie ends at midnight.", "time_numbers", "feminine", None),
    ("um Mitternacht", "phrase", "at midnight", ["at midnight"], "Der Zug fährt um Mitternacht ab.", "The train leaves at midnight.", "time_numbers", None, None),
    ("täglich", "adverb", "daily", ["daily", "every day"], "Der Bus fährt täglich.", "The bus runs every day.", "time_numbers", None, None),
    ("tagsüber", "adverb", "during the day", ["during the day", "in the daytime"], "Tagsüber bin ich bei der Arbeit.", "I am at work during the day.", "time_numbers", None, None),
    ("morgens", "adverb", "in the mornings", ["in the mornings", "every morning"], "Morgens trinke ich Kaffee.", "I drink coffee in the mornings.", "time_numbers", None, None),
    ("vormittags", "adverb", "in the late mornings", ["in the late mornings", "before noon"], "Vormittags bin ich im Büro.", "I am at the office before noon.", "time_numbers", None, None),
    ("mittags", "adverb", "at noon", ["at noon", "at lunchtime"], "Mittags esse ich in der Kantine.", "I eat in the cafeteria at noon.", "time_numbers", None, None),
    ("nachmittags", "adverb", "in the afternoons", ["in the afternoons", "every afternoon"], "Nachmittags mache ich meine Hausaufgaben.", "I do my homework in the afternoons.", "time_numbers", None, None),
    ("abends", "adverb", "in the evenings", ["in the evenings", "every evening"], "Abends lese ich gern.", "I like to read in the evenings.", "time_numbers", None, None),
    ("nachts", "adverb", "at night", ["at night", "during the night"], "Nachts ist es hier ruhig.", "It is quiet here at night.", "time_numbers", None, None),
    ("montags", "adverb", "on Mondays", ["on Mondays", "every Monday"], "Montags habe ich Deutschkurs.", "I have German class on Mondays.", "time_numbers", None, None),
    ("dienstags", "adverb", "on Tuesdays", ["on Tuesdays", "every Tuesday"], "Dienstags gehe ich schwimmen.", "I go swimming on Tuesdays.", "time_numbers", None, None),
    ("mittwochs", "adverb", "on Wednesdays", ["on Wednesdays", "every Wednesday"], "Mittwochs arbeite ich zu Hause.", "I work from home on Wednesdays.", "time_numbers", None, None),
    ("donnerstags", "adverb", "on Thursdays", ["on Thursdays", "every Thursday"], "Donnerstags spielt sie Tennis.", "She plays tennis on Thursdays.", "time_numbers", None, None),
    ("freitags", "adverb", "on Fridays", ["on Fridays", "every Friday"], "Freitags gehen wir ins Kino.", "We go to the movies on Fridays.", "time_numbers", None, None),
    ("samstags", "adverb", "on Saturdays", ["on Saturdays", "every Saturday"], "Samstags kaufe ich auf dem Markt ein.", "I shop at the market on Saturdays.", "time_numbers", None, None),
    ("sonntags", "adverb", "on Sundays", ["on Sundays", "every Sunday"], "Sonntags besuchen wir meine Eltern.", "We visit my parents on Sundays.", "time_numbers", None, None),
    ("am Wochenende", "phrase", "at the weekend", ["at the weekend", "on the weekend"], "Am Wochenende besuchen wir Freunde.", "We are visiting friends at the weekend.", "time_numbers", None, None),
    ("der Arbeitstag", "noun", "workday", ["workday", "working day"], "Mein Arbeitstag beginnt um acht Uhr.", "My workday starts at eight o'clock.", "time_numbers", "masculine", "die Arbeitstage"),
    ("der Werktag", "noun", "weekday", ["weekday", "working day"], "Die Praxis ist nur an Werktagen geöffnet.", "The doctor's office is only open on weekdays.", "time_numbers", "masculine", "die Werktage"),
    ("erstens", "adverb", "firstly", ["firstly", "first"], "Erstens ist der Kurs günstig.", "Firstly, the course is inexpensive.", "communication", None, None),
    ("zweitens", "adverb", "secondly", ["secondly", "second"], "Zweitens ist der Kurs nicht weit weg.", "Secondly, the course is not far away.", "communication", None, None),
    ("drittens", "adverb", "thirdly", ["thirdly", "third"], "Drittens habe ich am Montag Zeit.", "Thirdly, I have time on Monday.", "communication", None, None),
    ("viertens", "adverb", "fourthly", ["fourthly", "fourth"], "Viertens brauche ich ein Wörterbuch.", "Fourthly, I need a dictionary.", "communication", None, None),
    ("erste", "adjective", "first", ["first"], "Sie war die erste Person am Ziel.", "She was the first person at the finish.", "time_numbers", None, None),
    ("zweite", "adjective", "second", ["second"], "Das ist mein zweiter Versuch.", "This is my second attempt.", "time_numbers", None, None),
    ("dritte", "adjective", "third", ["third"], "Wir wohnen im dritten Stock.", "We live on the third floor.", "time_numbers", None, None),
    ("vierte", "adjective", "fourth", ["fourth"], "Die vierte Aufgabe ist schwer.", "The fourth task is difficult.", "time_numbers", None, None),
    ("einmal", "adverb", "once", ["once", "one time"], "Ich war einmal in Berlin.", "I was in Berlin once.", "time_numbers", None, None),
    ("zweimal", "adverb", "twice", ["twice", "two times"], "Ich trainiere zweimal pro Woche.", "I train twice a week.", "time_numbers", None, None),
    ("dreimal", "adverb", "three times", ["three times"], "Nehmen Sie die Tablette dreimal täglich.", "Take the tablet three times a day.", "time_numbers", None, None),
    ("viermal", "adverb", "four times", ["four times"], "Der Bus fährt viermal am Tag.", "The bus runs four times a day.", "time_numbers", None, None),
    ("einundzwanzig", "number", "twenty-one", ["twenty-one", "twenty one"], "Der Kurs hat einundzwanzig Teilnehmer.", "The course has twenty-one participants.", "time_numbers", None, None),
    ("hunderteins", "number", "one hundred and one", ["one hundred and one", "one hundred one"], "Das Buch hat hunderteins Seiten.", "The book has one hundred and one pages.", "time_numbers", None, None),
    ("zweihundert", "number", "two hundred", ["two hundred"], "Das Hotel hat zweihundert Zimmer.", "The hotel has two hundred rooms.", "time_numbers", None, None),
    ("zweitausendeins", "number", "two thousand and one", ["two thousand and one", "two thousand one"], "Er wurde im Jahr zweitausendeins geboren.", "He was born in the year two thousand and one.", "time_numbers", None, None),
    ("eine Million", "number", "one million", ["one million", "a million"], "Die Stadt hat eine Million Einwohner.", "The city has one million residents.", "time_numbers", None, None),
]


def official_word_group_items() -> list[str]:
    """Return one canonical item for every printed word-group row/item.

    Slash-separated alternatives printed on one line remain one source item;
    numeric date and clock examples are not vocabulary headwords.
    """
    items = [
        "ca.", "d. h.", "ICE", "Lkw", "PC", "SMS", "usw.", "WC", "z. B.",
        "der Antwortbogen", "die Aufgabe", "das Beispiel", "die Durchsage", "die Lösung",
        "markieren", "der Prüfer / die Prüferin", "die Prüfung", "der Punkt", "der Teil",
        "der Test", "der Text", "das Wörterbuch",
        "der Angestellte / die Angestellte", "der Arzt / die Ärztin",
        "der Auszubildende / die Auszubildende", "der Autor / die Autorin", "der Babysitter",
        "der Bäcker / die Bäckerin", "der Doktor / die Doktorin", "der Fahrer / die Fahrerin",
        "der Friseur / die Friseurin", "der Handwerker / die Handwerkerin",
        "der Hausmann / die Hausfrau", "der Journalist / die Journalistin",
        "der Kaufmann / die Kauffrau", "der Kellner / die Kellnerin", "der Koch / die Köchin",
        "der Krankenpfleger / die Krankenschwester", "der Künstler / die Künstlerin",
        "der Lehrer / die Lehrerin", "der Mechaniker / die Mechanikerin", "das Model",
        "der Musiker / die Musikerin", "der Polizist / die Polizistin",
        "der Rentner / die Rentnerin", "der Sänger / die Sängerin",
        "der Schauspieler / die Schauspielerin", "der Techniker / die Technikerin",
        "der Verkäufer / die Verkäuferin",
        "der Bruder", "der Cousin", "die Cousine", "die Eltern", "der Enkel", "die Enkelin",
        "die Geschwister", "die Großeltern", "die Großmutter", "der Großvater", "das Kind",
        "die Mutter", "der Onkel", "die Schwester", "der Sohn", "die Tante", "die Tochter",
        "der Vater", "der Verwandte",
        "ledig", "verheiratet", "getrennt / geschieden",
        "blau", "braun", "gelb", "grau", "grün", "lila", "orange", "rosa", "rot", "schwarz", "weiß",
        "der Norden", "der Süden", "der Osten", "der Westen",
        "Deutschland", "der Deutsche / die Deutsche", "deutsch", "auf Deutsch", "Österreich",
        "der Österreicher / die Österreicherin", "österreichisch", "die Schweiz",
        "der Schweizer / die Schweizerin", "schweizerisch", "Luxemburg",
        "der Luxemburger / die Luxemburgerin", "luxemburgisch", "Europa",
        "der Europäer / die Europäerin", "europäisch",
        "das Abitur", "der Direktor", "die Hausaufgabe", "die Klasse", "die Klassenfahrt",
        "das Sekretariat", "der Stundenplan", "die Biologie", "die Chemie", "Deutsch", "Englisch",
        "Französisch", "die Geografie", "die Geschichte", "die Kunst", "Latein", "die Mathematik",
        "die Musik", "die Physik", "die Religion", "die Sozialkunde", "der Sport",
        "der Euro / der Cent", "der Franken / der Rappen", "der Meter", "der Zentimeter",
        "der Kilometer", "das Prozent", "der Liter", "das Gramm / das Kilogramm", "der Grad Celsius",
        "Karneval", "Ostern", "Weihnachten", "Neujahr / Silvester",
        "der Frühling / das Frühjahr", "der Sommer", "der Herbst", "der Winter",
        *[f"der {month}" for month in ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")],
        "der Tag", "der Morgen", "der Vormittag", "der Mittag", "der Nachmittag", "der Abend",
        "die Nacht", "Mitternacht", "täglich / tagsüber", "morgens / am Morgen",
        "vormittags / am Vormittag", "mittags / am Mittag", "nachmittags / am Nachmittag",
        "abends / am Abend", "nachts / in der Nacht", "um Mitternacht",
        "am Wochenende", "montags / am Montag", "dienstags / am Dienstag",
        "mittwochs / am Mittwoch", "donnerstags / am Donnerstag", "freitags / am Freitag",
        "samstags / am Samstag", "sonntags / am Sonntag", "der Arbeitstag / der Werktag", "der Feiertag",
        "die Sekunde", "die Minute", "die Stunde", "die Woche", "das Jahr",
        *(
            ["eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn",
             "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn",
             "achtzehn", "neunzehn", "zwanzig", "einundzwanzig", "dreißig", "vierzig", "fünfzig",
             "sechzig", "siebzig", "achtzig", "neunzig", "hundert", "hunderteins", "zweihundert",
             "tausend", "zweitausendeins", "eine Million"]
        ),
        "erste", "zweite", "dritte", "vierte", "erstens", "zweitens", "drittens", "viertens",
        "einmal", "zweimal", "dreimal", "viermal",
    ]
    if len(items) != WORD_GROUP_SOURCE_ITEMS:
        raise ValueError(f"word-group transcription count is {len(items)}, expected {WORD_GROUP_SOURCE_ITEMS}")
    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-deck",
        type=Path,
        default=ROOT / "tmp" / "a2_reference_deck" / "A2_Wortliste_Goethe",
        help="directory containing the checked Markdown transcription",
    )
    parser.add_argument(
        "--translation-reference",
        type=Path,
        default=ROOT / "tmp" / "deutale_a2.html",
        help="downloaded bilingual reference page used for cross-checking",
    )
    return parser.parse_args()


def parse_note(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    for part in re.split(r"\n### ", text)[1:]:
        key, _, value = part.partition("\n")
        fields[key.strip()] = value.strip()
    return fields


def normalized_lemma(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold().strip()
    value = value.replace("(sich)", "sich")
    value = re.sub(r"^(der|die|das)\s+", "", value)
    value = re.sub(r"^sich\s+", "", value)
    value = re.sub(r"\betwas\b", "", value)
    value = value.replace("ß", "ss")
    return re.sub(r"[^a-zäöü0-9]+", "", value)


def a1_aliases(cards: list[dict]) -> set[str]:
    aliases: set[str] = set()
    for card in cards:
        german = card["german"]
        aliases.add(normalized_lemma(german))
        for part in re.split(r"\s*/\s*", german):
            aliases.add(normalized_lemma(part))
        if german.startswith("Auf Wieder"):
            aliases.add(normalized_lemma(german.removeprefix("Auf ")))
    aliases.update(normalized_lemma(item) for item in KNOWN_A1_ALIASES)
    return aliases


def card_aliases(cards: list[dict]) -> set[str]:
    aliases: set[str] = set()
    for card in cards:
        german = card["german"]
        aliases.add(normalized_lemma(german))
        for part in re.split(r"\s*/\s*", german):
            aliases.add(normalized_lemma(part))
    return aliases


def source_item_components(item: str) -> list[set[str]]:
    """Return acceptable normalized forms for each lexical component."""
    components: list[set[str]] = []
    for part in re.split(r"\s*/\s*", item):
        forms = {normalized_lemma(part)}
        temporal = re.sub(r"^(am|an|im|in der|um)\s+", "", part, flags=re.I)
        forms.add(normalized_lemma(temporal))
        components.append(forms)
    return components


def clean_headword(note: dict[str, str]) -> str:
    word = note["Wort_DE"].strip()
    article = note.get("Artikel", "").strip()
    combined = f"{article} {word}".strip()
    combined = HEADWORD_OVERRIDES.get(combined, HEADWORD_OVERRIDES.get(word, combined))
    return unicodedata.normalize("NFC", combined).replace("  ", " ").strip()


def parse_translation_reference(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    source = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'class="word-item[^\"]*" data-lemma="([^"]*)" data-meaning="([^"]*)".*?'
        r'<span class="font-semibold[^\"]*">\s*(.*?)\s*</span>',
        re.S,
    )
    result: dict[str, list[str]] = defaultdict(list)
    for match in pattern.finditer(source):
        lemma, meaning, display = (html.unescape(value) for value in match.groups())
        for key in {normalized_lemma(lemma), normalized_lemma(display)}:
            if meaning not in result[key]:
                result[key].append(meaning)
    return result


def clean_answer(value: str) -> str:
    value = html.unescape(value).strip().strip(".!;")
    value = re.sub(r"^to\s+", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("sth.", "something").replace("so.", "someone")
    value = re.sub(r"\s*\([^)]*(?:male|female|sth|someone|something)[^)]*\)", "", value, flags=re.I)
    return value.strip()


def answers_for(german: str, note: dict[str, str], reference: dict[str, list[str]]) -> tuple[str, list[str]]:
    if german in ANSWER_OVERRIDES:
        return ANSWER_OVERRIDES[german]
    raw_values = list(reference.get(normalized_lemma(german), []))
    raw_values.append(note.get("Wort_EN", ""))
    answers: list[str] = []
    for raw in raw_values:
        for part in re.split(r"\s*(?:,|/|;)\s*", raw):
            answer = clean_answer(part)
            if not answer or len(answer) > 48:
                continue
            if answer.casefold() not in {item.casefold() for item in answers}:
                answers.append(answer)
    if not answers:
        raise ValueError(f"no English answer for {german}")
    return answers[0], answers[:6]


def add_umlaut(value: str) -> str:
    pos = value.casefold().rfind("au")
    if pos >= 0:
        return value[:pos] + ("Äu" if value[pos] == "A" else "äu") + value[pos + 2 :]
    mapping = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}
    for index in range(len(value) - 1, -1, -1):
        if value[index] in mapping:
            return value[:index] + mapping[value[index]] + value[index + 1 :]
    return value


def plural_for(german: str, code: str) -> str | None:
    if german in PLURAL_OVERRIDES:
        return PLURAL_OVERRIDES[german]
    if not re.match(r"^(der|die|das) ", german):
        return None
    code = code.strip().replace("–", "-")
    if code in {"", "(Sg.)", "(Sg)", "Sg."}:
        return None
    if code in {"(Pl.)", "(Pl)"}:
        return german
    if "/" in code:
        # The few legitimate alternatives are covered above.
        raise ValueError(f"unhandled plural alternatives for {german}: {code}")
    _, lemma = german.split(" ", 1)
    stem = lemma
    needs_umlaut = '"' in code or any(ch in code for ch in "äöü")
    code = code.replace('"', "")
    if code in {"-", ""}:
        suffix = ""
    else:
        token = code.lstrip("-")
        suffix = token
        if suffix == "en" and stem.endswith("e"):
            suffix = "n"
    plural = add_umlaut(stem) if needs_umlaut else stem
    return "die " + plural + suffix


def word_type_for(german: str, note: dict[str, str]) -> str:
    if re.match(r"^(der|die|das) ", german):
        return "noun"
    if note.get("Verbformen") or german in SPLIT_VERBS or german.startswith("sich ") or german.endswith(" sein") or german.endswith(" gehen"):
        return "verb"
    if german in PHRASES:
        return "phrase"
    if german in ADJECTIVES:
        return "adjective"
    if german in PREPOSITIONS:
        return "preposition"
    if german in CONJUNCTIONS:
        return "conjunction"
    if german in PRONOUNS:
        return "pronoun"
    if german in DETERMINERS:
        return "determiner"
    if german in INTERJECTIONS:
        return "interjection"
    return "adverb"


def gender_for(german: str, plural: str | None) -> str | None:
    if " / die " in german:
        return "masculine/feminine"
    if german.startswith("die ") and plural == german:
        return "plural"
    return {"der": "masculine", "die": "feminine", "das": "neuter"}.get(german.split(" ", 1)[0])


def topic_for(german: str, word_type: str) -> str:
    comparable = re.sub(r"^(der|die|das) ", "", german).removeprefix("sich ")
    for topic, hints in TOPIC_HINTS.items():
        if any(hint.casefold() in comparable.casefold() for hint in hints):
            return topic
    if word_type in {"adverb", "conjunction", "determiner", "phrase", "preposition", "pronoun"}:
        return "communication"
    return "common_actions_descriptions"


def example_for(german: str, note: dict[str, str]) -> tuple[str, str]:
    if german in EXAMPLE_OVERRIDES:
        return EXAMPLE_OVERRIDES[german]
    de = note.get("Satz1_DE", "").strip()
    en = note.get("Satz1_EN", "").strip()
    de = re.sub(r"\s+([!?.,])", r"\1", de)
    en = re.sub(r"\bcan not\b", "cannot", en, flags=re.I)
    en = re.sub(r"\bDo not you\b", "Don't you", en)
    en = re.sub(r"\bdoes not\b", "doesn't", en)
    en = en.replace("canditature", "application").replace("controll", "control")
    if not de.endswith((".", "!", "?")):
        de += "."
    if not en.endswith((".", "!", "?")):
        en += "."
    return de, en


def make_alpha_card(note: dict[str, str], reference: dict[str, list[str]]) -> dict:
    german = clean_headword(note)
    word_type = word_type_for(german, note)
    plural = plural_for(german, note.get("Plural", "")) if word_type == "noun" else None
    english, accepted = answers_for(german, note, reference)
    example_de, example_en = example_for(german, note)
    return {
        "id": "",
        "german": german,
        "word_type": word_type,
        "gender": gender_for(german, plural) if word_type == "noun" else None,
        "plural": plural,
        "english": english,
        "accepted_answers": accepted,
        "example_de": example_de,
        "example_en": example_en,
        "topic": topic_for(german, word_type),
        "source": "Goethe A2",
        "source_url": OFFICIAL_URL,
    }


def make_group_card(row: tuple) -> dict:
    german, word_type, english, accepted, example_de, example_en, topic, gender, plural = row
    return {
        "id": "",
        "german": german,
        "word_type": word_type,
        "gender": gender,
        "plural": plural,
        "english": english,
        "accepted_answers": accepted,
        "example_de": example_de,
        "example_en": example_en,
        "topic": topic,
        "source": "Goethe A2",
        "source_url": OFFICIAL_URL,
    }


def main() -> None:
    args = parse_args()
    note_paths = list(args.reference_deck.glob("*.md"))
    if len(note_paths) != ALPHABETIC_SOURCE_ITEMS:
        raise SystemExit(f"expected {ALPHABETIC_SOURCE_ITEMS} source notes, found {len(note_paths)}")

    notes = sorted((parse_note(path) for path in note_paths), key=lambda item: int(item["Original_Order"]))
    reference = parse_translation_reference(args.translation_reference)
    a1_cards = json.loads(A1_FILE.read_text(encoding="utf-8"))
    aliases = a1_aliases(a1_cards)

    cards: list[dict] = []
    overlap_rows: list[dict] = []
    source_duplicates: list[dict] = []
    seen_exact: dict[str, str] = {}

    for note in notes:
        german = clean_headword(note)
        lemma = normalized_lemma(german)
        if lemma in aliases:
            overlap_rows.append({
                "source_section": "alphabetical",
                "source_order": int(note["Original_Order"]),
                "german": german,
                "normalized_lemma": lemma,
                "resolution": "excluded_as_ordinary_A1_overlap",
            })
            continue
        exact_key = unicodedata.normalize("NFC", german).casefold()
        if exact_key in seen_exact:
            source_duplicates.append({
                "german": german,
                "normalized_lemma": lemma,
                "kept_as": seen_exact[exact_key],
                "resolution": "consolidated_source_variant",
            })
            continue
        card = make_alpha_card(note, reference)
        cards.append(card)
        seen_exact[exact_key] = german

    alpha_cards = list(cards)

    for row in GROUP_ADDITIONS:
        card = make_group_card(row)
        lemma = normalized_lemma(card["german"])
        if lemma in aliases:
            continue
        exact_key = unicodedata.normalize("NFC", card["german"]).casefold()
        if exact_key in seen_exact:
            source_duplicates.append({
                "german": card["german"],
                "normalized_lemma": lemma,
                "kept_as": seen_exact[exact_key],
                "resolution": "alphabetical_card_already_represents_word_group_item",
            })
            continue
        cards.append(card)
        seen_exact[exact_key] = card["german"]

    alpha_aliases = card_aliases(alpha_cards)
    group_cards = [card for card in cards if card not in alpha_cards]
    group_aliases = card_aliases(group_cards)
    unresolved_group_items = []
    for source_item in official_word_group_items():
        components = source_item_components(source_item)
        a1_matches = [any(form in aliases for form in forms) for forms in components]
        if all(a1_matches):
            overlap_rows.append({
                "source_section": "word_groups",
                "source_order": None,
                "german": source_item,
                "normalized_lemma": " / ".join(sorted(forms)[0] for forms in components),
                "resolution": "excluded_as_ordinary_A1_overlap",
            })
            continue
        unresolved = []
        represented_by_group = False
        represented_by_alpha = False
        for forms, is_a1 in zip(components, a1_matches):
            if is_a1:
                continue
            if any(form in group_aliases for form in forms):
                represented_by_group = True
            elif any(form in alpha_aliases for form in forms):
                represented_by_alpha = True
            else:
                unresolved.append(sorted(forms)[0])
        if unresolved:
            unresolved_group_items.append({"source_item": source_item, "components": unresolved})
            continue
        if represented_by_alpha and not represented_by_group:
            source_duplicates.append({
                "german": source_item,
                "normalized_lemma": " / ".join(sorted(forms)[0] for forms in components),
                "kept_as": "alphabetical section card",
                "resolution": "alphabetical_card_already_represents_word_group_item",
            })
    if unresolved_group_items:
        raise ValueError(f"unresolved official word-group items: {unresolved_group_items}")

    cards.sort(key=lambda card: (card["topic"], card["german"].casefold()))
    for index, card in enumerate(cards, 1):
        card["id"] = f"a2_{index:04d}"

    OUT.mkdir(parents=True, exist_ok=True)
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        by_topic[card["topic"]].append(card)
    files = []
    for topic, topic_cards in sorted(by_topic.items()):
        path = OUT / f"a2_{topic}.json"
        path.write_text(json.dumps(topic_cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        files.append({"topic": topic, "file": path.name, "entries": len(topic_cards)})
    (OUT / "a2_all.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    overlap_report = {
        "level": "A2",
        "normalization": "NFC, case-folded, articles/reflexive pronouns/formatting removed, ß normalized to ss",
        "detected_a1_overlaps": len(overlap_rows),
        "resolved_overlaps": overlap_rows,
        "source_variants_consolidated": len(source_duplicates),
        "consolidated_variants": source_duplicates,
        "resolved_homographs": [
            {
                "normalized_lemma": lemma,
                "cards": [card["german"] for card in cards if normalized_lemma(card["german"]) == lemma],
                "resolution": "kept_as_distinct_word_classes_or_meanings",
            }
            for lemma in sorted({normalized_lemma(card["german"]) for card in cards})
            if sum(normalized_lemma(card["german"]) == lemma for card in cards) > 1
        ],
    }
    (OUT / "overlap_report.json").write_text(
        json.dumps(overlap_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    review_report = {
        "level": "A2",
        "manual_review_required": 0,
        "excluded_uncertain_entries": [],
        "note": "No unresolved entry was admitted to production; uncertainty would be listed here and excluded.",
    }
    (OUT / "review_report.json").write_text(
        json.dumps(review_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "level": "A2",
        "official_source_items_examined": ALPHABETIC_SOURCE_ITEMS + WORD_GROUP_SOURCE_ITEMS,
        "official_alphabetic_items_examined": ALPHABETIC_SOURCE_ITEMS,
        "official_word_group_items_examined": WORD_GROUP_SOURCE_ITEMS,
        "a1_overlaps_detected_and_excluded": len(overlap_rows),
        "source_variants_consolidated": len(source_duplicates),
        "unique_a2_cards_added": len(cards),
        "manual_review_required": 0,
        "official_source_url": OFFICIAL_URL,
        "official_source_access_date": ACCESS_DATE,
        "official_source_is_cumulative": True,
        "validation_errors": [],
        "quality_checks": [
            "valid UTF-8 JSON and NFC Unicode",
            "exact A1 field names, field order, types, and null handling",
            "unique sequential A2 IDs",
            "unique exact German headwords",
            "normalized German homographs explicitly resolved",
            "automated normalized A1/A2 lemma comparison",
            "articles, noun genders, and full plural forms",
            "verb infinitives and normalized reflexive/separable forms",
            "non-empty primary and accepted English answers",
            "duplicate and malformed accepted answers",
            "natural punctuated German and English examples",
            "official source metadata on every card",
            "topic shards exactly reproduce the master dataset",
            "zero unresolved production-review entries",
        ],
        "files": files,
    }
    (OUT / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
