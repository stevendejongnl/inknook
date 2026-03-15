"""English quotes — international holidays, weather, and weekday quotes."""

from datetime import date, timedelta

from src.services.quotes._utils import easter


def holiday_quote(today: date) -> str | None:
    y = today.year
    e = easter(y)

    holidays: dict[date, str] = {
        date(y, 1, 1):  "A new year — a blank page. Write something good.",
        date(y, 2, 14): "Love is in the small things, not just the grand gestures.",
        date(y, 3, 8):  "The world is richer for the women who shaped it.",
        date(y, 3, 17): "A little luck never hurts. Today seems like a good day for it.",
        date(y, 4, 1):  "Not everything is as it seems. Sometimes that is a gift.",
        date(y, 5, 1):  "Rest is also a form of work. Today, lean into it.",
        date(y, 10, 31):"The dark has its own kind of charm.",
        date(y, 12, 24):"The anticipation is half the magic.",
        date(y, 12, 25):"The best gift is being exactly where you are.",
        date(y, 12, 26):"Two days of stillness. That is a rare thing.",
        date(y, 12, 31):"One more lap around the sun. Not bad at all.",
        # Moveable feasts
        e - timedelta(days=2): "Some days ask for quiet. This is one of them.",
        e:                      "Every spring is a reminder that things come back.",
        e + timedelta(days=1):  "A bonus day of ease. Take it gently.",
        e + timedelta(days=39): "A long weekend is its own small holiday.",
        e + timedelta(days=49): "A pause in the middle of things is a gift.",
        e + timedelta(days=50): "One more day to breathe. Use it well.",
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
            "The sun is generous today — take a little of it with you.",
            "Heat like this asks to be respected. Drink water. Go slow.",
            "A day this bright deserves to be noticed.",
        ])

    if condition in ("sunny", "partlycloudy") and temperature is not None and temperature >= 18:
        return pick([
            "A good day for a slow walk and no particular destination.",
            "The weather is doing its part. The rest is up to you.",
            "Good light makes everything look a little more hopeful.",
        ])

    if condition in ("rainy", "pouring", "lightning-rainy"):
        return pick([
            "Rain clears the air. Sometimes that is enough.",
            "A rainy day has a quietness that is worth sitting with.",
            "The rain has no agenda. Neither do you, for a moment.",
        ])

    if condition in ("snowy", "snowy-rainy"):
        return pick([
            "Snow turns the familiar into something new.",
            "Everything looks softer under snow.",
        ])

    if condition == "lightning":
        return pick([
            "Some days, nature has the last word.",
        ])

    if condition == "fog":
        return pick([
            "On foggy days, the world keeps some things for itself.",
        ])

    if condition in ("windy", "windy-variant"):
        return pick([
            "The wind moves things along. Maybe you can too.",
            "A breezy day — good for clearing the head.",
        ])

    return None


_BY_WEEKDAY: dict[int, list[str]] = {
    0: [  # Monday
        "A quiet start is still a start.",
        "Mondays have a bad reputation they do not deserve.",
        "The week begins. That is already something.",
        "Every week is a fresh attempt. This one too.",
    ],
    1: [  # Tuesday
        "Tuesday is the week finding its footing.",
        "One day in, and still going. That counts.",
        "Tuesdays ask for no special fanfare. Just steady.",
    ],
    2: [  # Wednesday
        "Halfway through. Exactly where you need to be.",
        "Wednesday is a good day to pause and take stock.",
        "The week has rhythm. Today is part of it.",
    ],
    3: [  # Thursday
        "Almost there, without rushing.",
        "Thursday has a quiet confidence about it.",
        "The end of the week is near. Hold the thread.",
    ],
    4: [  # Friday
        "The week taught you something. Carry it lightly.",
        "Friday is a gentle close, not just a finish line.",
        "A week well lived. That is worth something.",
        "The weekend begins at the edges of Friday. Let it.",
    ],
    5: [  # Saturday
        "Rest is not laziness. It is wisdom.",
        "Saturday has no obligations. That is the point.",
        "A day with nowhere to be is a rare gift.",
    ],
    6: [  # Sunday
        "Sunday light is its own kind of soft.",
        "A slow Sunday morning is one of life's small luxuries.",
        "Let Sunday be what it is — unhurried.",
    ],
}


def weekday_quote(today: date) -> str:
    weekday = today.weekday()
    seed = today.isocalendar()[1]
    options = _BY_WEEKDAY.get(weekday, ["Have a wonderful day!"])
    return options[seed % len(options)]
