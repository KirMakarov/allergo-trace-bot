"""Seed script to populate database with initial global ingredients.

Usage:
    python -m src.allergo_trace_bot.scripts.seed
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from allergo_trace_bot.database import AsyncSessionLocal, Ingredient


async def seed_ingredients() -> None:
    """Load and insert initial global ingredients from JSON file."""
    json_path = Path(__file__).parent / "initial_ingredients.json"

    if not json_path.exists():
        print(f"❌ Error: {json_path} not found!")
        return

    # Load ingredients from JSON
    with open(json_path, encoding="utf-8") as f:
        ingredients_data = json.load(f)

    print(f"📦 Loaded {len(ingredients_data)} ingredients from {json_path}")

    async with AsyncSessionLocal() as session:
        # Check how many global ingredients already exist
        result = await session.execute(select(Ingredient).where(Ingredient.user_id.is_(None)))
        existing = result.scalars().all()
        existing_count = len(existing)

        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing global ingredients in database")
            response = input("Do you want to continue and add new ones? (y/n): ")
            if response.lower() != "y":
                print("❌ Seeding cancelled")
                return

        # Create ingredient objects
        new_ingredients = []
        for item in ingredients_data:
            ingredient = Ingredient(
                name=item["name"],
                category=item["category"],
                aliases=item.get("aliases", []),
                user_id=None,  # Global ingredient
            )
            new_ingredients.append(ingredient)

        # Bulk insert
        session.add_all(new_ingredients)
        await session.commit()

        print(f"✅ Successfully seeded {len(new_ingredients)} global ingredients!")


async def main() -> None:
    """Main entry point for seeding script."""
    print("🌱 Starting database seeding...")
    await seed_ingredients()
    print("🎉 Seeding completed!")


if __name__ == "__main__":
    asyncio.run(main())
