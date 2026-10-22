import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal, engine
from .industry_portal import IndustryDemoDirectoryCompany


DEMO_DIRECTORY_COMPANIES = (
    {
        "key": "tcs",
        "name": "Tata Consultancy Services (TCS)",
        "category": "Information Technology",
        "description": "Sample profile representing IT services and consulting. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.tcs.com",
        "logo": "TCS",
    },
    {
        "key": "amazon",
        "name": "Amazon",
        "category": "Technology and E-commerce",
        "description": "Sample profile representing online retail, cloud, and digital services. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.amazon.com",
        "logo": "AMZ",
    },
    {
        "key": "infosys",
        "name": "Infosys",
        "category": "Information Technology",
        "description": "Sample profile representing IT consulting and digital services. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.infosys.com",
        "logo": "INF",
    },
    {
        "key": "microsoft",
        "name": "Microsoft",
        "category": "Software and Cloud Technology",
        "description": "Sample profile representing software, cloud, and productivity services. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.microsoft.com",
        "logo": "MS",
    },
    {
        "key": "wipro",
        "name": "Wipro",
        "category": "Information Technology",
        "description": "Sample profile representing IT consulting and technology services. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.wipro.com",
        "logo": "WIP",
    },
    {
        "key": "accenture",
        "name": "Accenture",
        "category": "Professional Services and Technology",
        "description": "Sample profile representing consulting and technology services. Demo data only; not a registered employer, partner, or endorsement.",
        "website": "https://www.accenture.com",
        "logo": "ACC",
    },
)


def seed_demo_company_directory(db: Session) -> int:
    IndustryDemoDirectoryCompany.__table__.create(bind=db.get_bind(), checkfirst=True)
    added = 0
    try:
        for company in DEMO_DIRECTORY_COMPANIES:
            existing_key = db.get(IndustryDemoDirectoryCompany, company["key"])
            if existing_key is not None:
                continue
            existing_name = db.scalar(
                select(IndustryDemoDirectoryCompany).where(
                    IndustryDemoDirectoryCompany.company_name.ilike(company["name"])
                )
            )
            if existing_name is not None:
                continue
            db.add(IndustryDemoDirectoryCompany(
                company_key=company["key"],
                company_name=company["name"],
                category=company["category"],
                description=company["description"],
                website=company["website"],
                logo_text=company["logo"],
                demo_label="DEMO COMPANY",
            ))
            added += 1
        db.commit()
        return added
    except Exception:
        db.rollback()
        raise


def main() -> int:
    db = SessionLocal()
    try:
        count = seed_demo_company_directory(db)
        print(f"Demo company directory seed complete: {count} company profiles added.")
        return 0
    except IntegrityError:
        print("Demo company directory seed failed because a database constraint was not satisfied.", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
