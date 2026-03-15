"""Nederlandse citaten — feestdagen, weer en dag-van-de-week quotes."""

from datetime import date, timedelta

from src.services.quotes._utils import easter


def holiday_quote(today: date) -> str | None:
    y = today.year
    e = easter(y)

    holidays: dict[date, str] = {
        date(y, 1, 1):  "Een nieuw jaar, een leeg blad. Schrijf iets moois.",
        date(y, 2, 14): "Liefde zit in de kleine dingen, niet alleen de grote gebaren.",
        date(y, 3, 8):  "De wereld is gevormd door vrouwen die durfden.",
        date(y, 4, 27): "Oranje kent geen peil — en dat is precies wat het zo leuk maakt.",
        date(y, 5, 1):  "Rust is ook een vorm van doen. Vandaag mag dat.",
        date(y, 5, 5):  "Vrijheid is iets om stil bij te staan, niet alleen te vieren.",
        date(y, 10, 31):"Het donker heeft zijn eigen soort charme.",
        date(y, 11, 11):"Sint Maarten — een kaarsje brandt het verst als je het deelt.",
        date(y, 12, 5): "Niet alles hoeft een groot gebaar te zijn. Soms is een klein gedicht genoeg.",
        date(y, 12, 24):"De verwachting is al de helft van de magie.",
        date(y, 12, 25):"Het mooiste cadeau is er gewoon zijn.",
        date(y, 12, 26):"Twee dagen stilte. Dat is een zeldzaam ding.",
        date(y, 12, 31):"Nog een rondje om de zon. Niet slecht.",
        # Beweeglijke feestdagen
        e - timedelta(days=2): "Sommige dagen vragen om rust. Dit is er een van.",
        e:                      "Elke lente herinnert eraan dat dingen terugkomen.",
        e + timedelta(days=1):  "Een extra dag om rustig te zijn. Neem hem mee.",
        e + timedelta(days=39): "Een lang weekend is zijn eigen kleine vakantie.",
        e + timedelta(days=49): "Even pauzeren middenin alles is een cadeau.",
        e + timedelta(days=50): "Nog een dag om adem te halen. Gebruik hem goed.",
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
            "De zon is vandaag gul. Neem er wat van mee.",
            "Zulk weer vraagt om respect. Drink water. Doe rustig.",
            "Een dag zo helder verdient even stilgestaan te worden.",
        ])

    if condition in ("sunny", "partlycloudy") and temperature is not None and temperature >= 18:
        return pick([
            "Een goede dag voor een langzame wandeling zonder doel.",
            "Het weer doet zijn deel. De rest is aan jou.",
            "Goed licht maakt alles een beetje hoopvoller.",
        ])

    if condition in ("rainy", "pouring", "lightning-rainy"):
        return pick([
            "Regen zuivert de lucht. Soms is dat genoeg.",
            "Een regendag heeft een stilte die de moeite waard is.",
            "De regen heeft geen agenda. Jij ook niet, even.",
        ])

    if condition in ("snowy", "snowy-rainy"):
        return pick([
            "Sneeuw maakt het vertrouwde even nieuw.",
            "Alles ziet er zachter uit onder sneeuw.",
        ])

    if condition == "lightning":
        return pick([
            "Soms heeft de natuur het laatste woord.",
        ])

    if condition == "fog":
        return pick([
            "Op mistige dagen houdt de wereld wat voor zichzelf.",
        ])

    if condition in ("windy", "windy-variant"):
        return pick([
            "De wind brengt dingen in beweging. Misschien jij ook.",
            "Een winderige dag — goed voor het hoofd leegblazen.",
        ])

    return None


_BY_WEEKDAY: dict[int, list[str]] = {
    0: [  # Maandag
        "Een rustig begin is ook een begin.",
        "Maandag heeft een slechte reputatie die het niet verdient.",
        "De week begint. Dat is al iets.",
        "Elke week is een nieuwe poging. Deze ook.",
    ],
    1: [  # Dinsdag
        "Dinsdag is de week die zijn draai vindt.",
        "Een dag verder, en nog steeds bezig. Dat telt.",
        "Dinsdag vraagt om geen bijzonder feestje. Gewoon door.",
    ],
    2: [  # Woensdag
        "Halverwege. Precies waar je moet zijn.",
        "Woensdag is een goede dag om even stil te staan.",
        "De week heeft zijn ritme. Vandaag hoort daarbij.",
    ],
    3: [  # Donderdag
        "Bijna, zonder te haasten.",
        "Donderdag heeft een rustige zekerheid.",
        "Het einde van de week is nabij. Houd de draad vast.",
    ],
    4: [  # Vrijdag
        "De week heeft je iets geleerd. Draag het licht.",
        "Vrijdag is een zachte afsluiting, geen finish.",
        "Een week goed geleefd. Dat is wat waard.",
        "Het weekend begint aan de randen van vrijdag. Laat het.",
    ],
    5: [  # Zaterdag
        "Rust is geen luiheid. Het is wijsheid.",
        "Zaterdag heeft geen verplichtingen. Dat is het punt.",
        "Een dag zonder agenda is een zeldzaam cadeau.",
    ],
    6: [  # Zondag
        "Zondagslicht heeft zijn eigen soort zachtheid.",
        "Een langzame zondagochtend is een van de kleine luxes.",
        "Laat zondag zijn wat het is — rustig.",
    ],
}


def weekday_quote(today: date) -> str:
    weekday = today.weekday()
    seed = today.isocalendar()[1]
    options = _BY_WEEKDAY.get(weekday, ["Een goede dag begint gewoon met beginnen."])
    return options[seed % len(options)]
