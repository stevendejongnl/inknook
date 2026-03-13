"""Nederlandse citaten — feestdagen, weer en dag-van-de-week quotes."""

from datetime import date, timedelta

from src.services.quotes._utils import easter


def holiday_quote(today: date) -> str | None:
    y = today.year
    e = easter(y)

    holidays: dict[date, str] = {
        date(y, 1, 1):  "Gelukkig Nieuwjaar! Een nieuw jaar vol mooie momenten!",
        date(y, 2, 14): "Fijne Valentijnsdag! Jij maakt elke dag bijzonder",
        date(y, 3, 8):  "Happy Women's Day! De wereld is beter met jou erin",
        date(y, 4, 27): "Leve de Koning! Maar jij bent de echte ster thuis",
        date(y, 5, 1):  "Dag van de Arbeid! En vandaag mag je lekker uitrusten",
        date(y, 5, 5):  "Bevrijdingsdag! Vrij om te doen wat je wilt — geniet!",
        date(y, 10, 31):"Boeh! Happy Halloween — jij bent gelukkig niet eng",
        date(y, 11, 11):"Sint Maarten! Zet maar vast een lekker bakje thee klaar",
        date(y, 12, 5): "Sinterklaas is jarig! Wat zit er in jouw schoen?",
        date(y, 12, 24):"Kerstavond! Morgen is het Kerstmis — gezelligheid!",
        date(y, 12, 25):"Eerste Kerstdag! Fijne Kerstdagen aan de liefste thuis",
        date(y, 12, 26):"Tweede Kerstdag! Nog een dag niks moeten — heerlijk",
        date(y, 12, 31):"Oudejaarsavond! Dit jaar was TOP — op naar het volgende!",
        # Beweeglijke feestdagen
        e - timedelta(days=2): "Goede Vrijdag — goed moment voor een goede kop koffie",
        e:                      "Eerste Paasdag! Fijne Paasdagen",
        e + timedelta(days=1):  "Tweede Paasdag! Nog een vrije dag — precies goed",
        e + timedelta(days=39): "Hemelvaartsdag! Lang weekend — enjoy!",
        e + timedelta(days=49): "Eerste Pinksterdag! Fijne Pinksterdagen",
        e + timedelta(days=50): "Tweede Pinksterdag! Nog een vrije dag",
    }

    return holidays.get(today)


def weather_quote(condition: str | None, temperature: float | None, today: date) -> str | None:
    if not condition:
        return None

    seed = today.toordinal()

    def pick(options: list[str]) -> str:
        return options[seed % len(options)]

    if condition == "sunny" and temperature is not None and temperature >= 25:
        return pick([
            "Tropisch warm! IJsje verplicht vandaag",
            "Wat een heerlijke dag — niet binnen blijven!",
            "Zonnebril op en naar buiten, het is prachtig!",
        ])

    if condition in ("sunny", "partlycloudy") and temperature is not None and temperature >= 18:
        return pick([
            "Lekker weer! Mooi om even buiten te zijn",
            "Zonnig en aangenaam — een wandeling is geen straf",
            "Goed weer voor een goed humeur — toevallig?",
        ])

    if condition in ("rainy", "pouring", "lightning-rainy"):
        return pick([
            "Het regent — maar jij maakt de dag zonnig",
            "Regendag! Perfect voor koffie en een goed boek",
            "Het plast buiten — blijf lekker warm binnen",
        ])

    if condition in ("snowy", "snowy-rainy"):
        return pick([
            "Het sneeuwt! Warme chocolademelk is verplicht",
            "Sneeuw! Hopelijk ligt er een warme trui klaar",
        ])

    if condition == "lightning":
        return pick([
            "Onweer! Blijf lekker thuis — het is gezellig",
        ])

    if condition == "fog":
        return pick([
            "Mistig! Rijden met lichten — en neem de tijd",
        ])

    if condition in ("windy", "windy-variant"):
        return pick([
            "Het waait stevig vandaag — houd je hoed vast!",
            "Winderig! Perfect excuus om binnen te blijven",
        ])

    return None


_BY_WEEKDAY: dict[int, list[str]] = {
    0: [  # Maandag
        "Nieuwe week! Jij gaat er vandaag tegenaan",
        "Maandag — de wereld staat te wachten op jou!",
        "Maandag al? Tijd vliegt als je plezier hebt",
        "Nog 4 dagen en dan is het vrijdag — je kan het!",
    ],
    1: [  # Dinsdag
        "Dinsdag! Eén dag verder — je doet het geweldig",
        "De week is al begonnen — dat is alvast iets!",
        "Dinsdag is de nieuwe maandag — maar dan beter",
    ],
    2: [  # Woensdag
        "Halverwege de week! Bijna vrijdag!",
        "Woensdag — eigenlijk al bijna donderdag",
        "Hump day! Het gaat alleen maar beter van hier",
    ],
    3: [  # Donderdag
        "Donderdag! Nog één dag en dan… VRIJDAG!",
        "Pre-vrijdag — de energie zit er al in!",
        "Donderdag: morgen mag je juichen, nu nog even",
    ],
    4: [  # Vrijdag
        "HET IS VRIJDAG!! Verdient een feestje!",
        "Vrijdag! De beste dag van de week — geniet!",
        "TGIF! Jij verdient dit weekend echt",
        "Vrijdag is uitgevonden door iemand die van jou hield",
    ],
    5: [  # Zaterdag
        "Weekend! Lekker niks moeten — of toch van alles",
        "Zaterdag! Een heerlijke dag voor jezelf",
        "Weekend vibes! Geniet van elke minuut",
    ],
    6: [  # Zondag
        "Zondag — de mooiste dag om niks te moeten!",
        "Sunday mood: rustig, lekker, goed",
        "Geniet van je zondag — je bent er klaar voor!",
    ],
}


def weekday_quote(today: date) -> str:
    weekday = today.weekday()
    seed = today.isocalendar()[1]
    options = _BY_WEEKDAY.get(weekday, ["Fijne dag! Je doet het geweldig!"])
    return options[seed % len(options)]
