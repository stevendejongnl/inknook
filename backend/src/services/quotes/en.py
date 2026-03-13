"""English quotes — international holidays, weather, and weekday quotes."""

from datetime import date, timedelta

from src.services.quotes._utils import easter


def holiday_quote(today: date) -> str | None:
    y = today.year
    e = easter(y)

    holidays: dict[date, str] = {
        date(y, 1, 1):  "Happy New Year! A fresh start full of possibilities!",
        date(y, 2, 14): "Happy Valentine's Day! You make every day special",
        date(y, 3, 8):  "Happy International Women's Day! The world is better with you in it",
        date(y, 3, 17): "Happy St. Patrick's Day! May the luck be with you today",
        date(y, 4, 1):  "April Fools'! Don't believe everything you read today",
        date(y, 5, 1):  "Labour Day! A great day to... rest",
        date(y, 10, 31):"Happy Halloween! You're the least scary thing around",
        date(y, 12, 24):"Christmas Eve! The excitement is real",
        date(y, 12, 25):"Merry Christmas! Wishing you a lovely day",
        date(y, 12, 26):"Boxing Day! A bonus holiday — enjoy every minute",
        date(y, 12, 31):"New Year's Eve! What a year — here's to the next one!",
        # Moveable feasts
        e - timedelta(days=2): "Good Friday — a good day for a good cup of coffee",
        e:                      "Happy Easter! Hope your day is egg-cellent",
        e + timedelta(days=1):  "Easter Monday! A bonus day off — you earned it",
        e + timedelta(days=39): "Ascension Day! Long weekend incoming",
        e + timedelta(days=49): "Whit Sunday! Enjoy the long weekend",
        e + timedelta(days=50): "Whit Monday! One more free day — make the most of it",
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
            "Gorgeous day! Get outside and soak it up",
            "It's scorching! Ice cream is basically required today",
            "Perfect beach weather — or at least garden weather!",
        ])

    if condition in ("sunny", "partlycloudy") and temperature is not None and temperature >= 18:
        return pick([
            "What a lovely day! A walk would be perfect",
            "Beautiful weather — no excuses to stay inside",
            "Good weather for a good mood",
        ])

    if condition in ("rainy", "pouring", "lightning-rainy"):
        return pick([
            "Rainy day — ideal excuse for tea and a book",
            "It's pouring! Perfect for staying cozy inside",
            "Wet outside, warm inside — sounds like a plan",
        ])

    if condition in ("snowy", "snowy-rainy"):
        return pick([
            "Snow day! Hot chocolate is absolutely mandatory",
            "It's snowing! Hope there's a warm blanket nearby",
        ])

    if condition == "lightning":
        return pick([
            "Storm incoming! Stay cozy indoors",
        ])

    if condition == "fog":
        return pick([
            "Foggy morning — take it slow today",
        ])

    if condition in ("windy", "windy-variant"):
        return pick([
            "Hold onto your hat — it's breezy out there!",
            "Windy day! Perfect excuse to stay in",
        ])

    return None


_BY_WEEKDAY: dict[int, list[str]] = {
    0: [  # Monday
        "New week, new adventures! You've got this",
        "Monday again? Time flies when you're having fun",
        "The week is young — and so are you!",
        "Four more days until Friday — let's go!",
    ],
    1: [  # Tuesday
        "Tuesday! One day down, already winning",
        "Two days in — you're crushing it!",
        "Tuesday is just Monday's cooler sibling",
    ],
    2: [  # Wednesday
        "Hump day! Downhill from here",
        "Wednesday — basically Friday-eve-eve",
        "Halfway there! You're doing great",
    ],
    3: [  # Thursday
        "Almost Friday! One more sleep...",
        "Thursday: the pre-pre-weekend has arrived",
        "So close to Friday you can almost taste it",
    ],
    4: [  # Friday
        "IT'S FRIDAY!! You made it!",
        "TGIF! You absolutely deserve this weekend",
        "Friday! The best invention of the week",
        "The weekend called — it's on its way!",
    ],
    5: [  # Saturday
        "Weekend! Do whatever you want — you earned it",
        "Saturday vibes: no alarm, no rush, no problem",
        "It's Saturday — the world is your oyster",
    ],
    6: [  # Sunday
        "Sunday: the original lazy day",
        "Soak up Sunday — tomorrow is another story",
        "Sunday mode: ON. Enjoy every minute",
    ],
}


def weekday_quote(today: date) -> str:
    weekday = today.weekday()
    seed = today.isocalendar()[1]
    options = _BY_WEEKDAY.get(weekday, ["Have a wonderful day!"])
    return options[seed % len(options)]
