"""Run the Budget Manager web app."""
import sys
from web.app import create_app
from web.models import db, CategoryGroup
from web.seed import seed_database

app = create_app()

if __name__ == "__main__":
    # Seed if DB is empty
    with app.app_context():
        if CategoryGroup.query.count() == 0:
            print("Empty database detected — seeding with initial data...")
            seed_database()
            print("Done!")

    if "--seed" in sys.argv:
        with app.app_context():
            db.drop_all()
            db.create_all()
            seed_database()
            print("Database reset and seeded.")
    else:
        app.run(debug=True, port=5001)
