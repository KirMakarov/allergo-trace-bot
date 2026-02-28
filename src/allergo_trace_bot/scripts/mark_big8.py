"""Script to mark Big 8 allergens in the ingredients table.

Big 8 allergens account for 90% of food allergies:
1. Milk/Dairy
2. Eggs
3. Fish
4. Shellfish/Crustaceans
5. Peanuts
6. Tree nuts
7. Wheat/Gluten
8. Soy

Usage:
    python -m src.allergo_trace_bot.scripts.mark_big8

Or from project root:
    uv run python -m allergo_trace_bot.scripts.mark_big8
"""

import asyncio
import re

from sqlalchemy import select, update

from allergo_trace_bot.database.core import AsyncSessionLocal
from allergo_trace_bot.database.models import Ingredient

# Keywords for Big 8 allergens (lowercase for matching)
BIG8_KEYWORDS: dict[str, list[str]] = {
    "Milk/Dairy": [
        "milk",
        "lactose",
        "cheese",
        "cream",
        "yogurt",
        "butter",
        "whey",
        "casein",
        "curd",
        "kefir",
        "buttermilk",
        "custard",
        "pudding",
        "ice cream",
        "ghee",
        "dairy",
    ],
    "Eggs": [
        "egg",
        "eggs",
        "egg white",
        "egg yolk",
        "albumin",
        "globulin",
        "livetin",
        "ovalbumin",
        "ovomucin",
        "ovomucoid",
        "ovovitellin",
        "mayonnaise",
        "meringue",
        "surimi",
    ],
    "Fish": [
        "fish",
        "salmon",
        "tuna",
        "cod",
        "herring",
        "mackerel",
        "trout",
        "barracuda",
        "bass",
        "carp",
        "catfish",
        "anchovy",
        "anchovies",
        "sardine",
        "sardines",
        "flounder",
        "grouper",
        "haddock",
        "hake",
        "halibut",
        "mahi-mahi",
        "perch",
        "pike",
        "pollock",
        "snapper",
        "sole",
        "sturgeon",
        "swordfish",
        "tilapia",
        "walleye",
    ],
    "Crustacean Shellfish": [
        "shellfish",
        "crustacean",
        "shrimp",
        "prawn",
        "crab",
        "crawfish",
        "crayfish",
        "lobster",
        "krill",
        "barnacle",
    ],
    "Peanuts": [
        "peanut",
        "nut",  # Careful with this one, might be too broad if matched loosely
        "groundnut",
        "monkey nut",
        "goober",
        "mixed nuts",
        "peanut butter",
        "peanut oil",
    ],
    "Tree Nuts": [
        "almond",
        "beech nut",
        "brazil nut",
        "butternut",
        "cashew",
        "chestnut",
        "chinquapin",
        "coconut",
        "filbert",
        "hazelnut",
        "hickory nut",
        "lichee nut",
        "macadamia",
        "pecan",
        "pine nut",
        "pistachio",
        "walnut",
        "nut",
        "marzipan",
        "nougat",
        "praline",
        "pesto",
    ],
    "Wheat": [
        "wheat",
        "flour",
        "bread",
        "pasta",
        "spaghetti",
        "macaroni",
        "noodle",
        "couscous",
        "cracker",
        "farina",
        "semolina",
        "spelt",
        "gluten",
        "bulgur",
        "durum",
        "kamut",
        "matzoh",
        "seitan",
        "triticale",
        "bran",
        "germ",
        "starch",
    ],
    "Soy": [
        "soy",
        "soya",
        "soybean",
        "tofu",
        "tempeh",
        "miso",
        "edamame",
        "natto",
        "shoyu",
        "tamari",
        "yuba",
        "teriyaki",
        "okara",
        "lecithin",
    ],
}

# Flatten keywords for matching
ALL_BIG8_KEYWORDS: list[str] = []
for category_keywords in BIG8_KEYWORDS.values():
    ALL_BIG8_KEYWORDS.extend(category_keywords)


def is_big8_ingredient(name: str, aliases: list[str] | None) -> bool:
    """Check if ingredient name or aliases match Big 8 keywords.

    Args:
        name: Ingredient name
        aliases: List of ingredient aliases

    Returns:
        True if ingredient matches any Big 8 keyword
    """
    # Combine name and aliases for checking
    all_names = [name.lower()]
    if aliases:
        all_names.extend(alias.lower() for alias in aliases)

    for text in all_names:
        for keyword in ALL_BIG8_KEYWORDS:
            # Use word boundary matching to avoid false positives
            # e.g., "nut" should not match "donut"
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return False


async def mark_big8_ingredients() -> None:
    """Scan all ingredients and mark Big 8 allergens."""
    print("🔍 Scanning ingredients for Big 8 allergens...")

    async with AsyncSessionLocal() as session:
        # Get all ingredients
        result = await session.execute(select(Ingredient))
        ingredients = result.scalars().all()

        print(f"📦 Found {len(ingredients)} total ingredients")

        marked_count = 0
        marked_ingredients: list[str] = []

        for ingredient in ingredients:
            if is_big8_ingredient(ingredient.name, ingredient.aliases) and not ingredient.is_big8:
                # Update the ingredient
                await session.execute(update(Ingredient).where(Ingredient.id == ingredient.id).values(is_big8=True))
                marked_count += 1
                marked_ingredients.append(ingredient.name)

        await session.commit()

        print(f"\n✅ Marked {marked_count} ingredients as Big 8 allergens:")
        for name in sorted(marked_ingredients):
            print(f"  ⚠️ {name}")

        # Show summary of already marked
        result = await session.execute(select(Ingredient).where(Ingredient.is_big8.is_(True)))
        all_big8 = result.scalars().all()
        print(f"\n📊 Total Big 8 allergens in database: {len(all_big8)}")


async def main() -> None:
    """Main entry point for Big 8 marking script."""
    print("🏷️ Big 8 Allergen Marking Script")
    print("=" * 40)
    await mark_big8_ingredients()
    print("\n🎉 Done!")


if __name__ == "__main__":
    asyncio.run(main())
