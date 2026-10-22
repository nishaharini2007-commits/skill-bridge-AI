import os
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.industry_portal import IndustryCompanyDetails
from app.main import Industry, User, hash_password


def bootstrap_tcs():
    email = os.getenv("TCS_INDUSTRY_EMAIL", "").strip().lower()
    password = os.getenv("TCS_INDUSTRY_PASSWORD", "")
    if not email or not password:
        raise ValueError("Set TCS_INDUSTRY_EMAIL and TCS_INDUSTRY_PASSWORD before running this command.")
    if len(password) < 8 or len(password) > 128:
        raise ValueError("TCS_INDUSTRY_PASSWORD must be between 8 and 128 characters.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_tcs = db.scalar(select(Industry).where(Industry.company_name.ilike("TCS%")))
        user = db.scalar(select(User).where(User.email == email))
        if existing_tcs is not None:
            if existing_tcs.user.email != email:
                raise ValueError("A TCS company profile is already associated with a different account.")
            return "TCS account is already configured."
        if user is not None and user.role != "industry":
            raise ValueError("The configured email belongs to a non-Industry account.")

        if user is None:
            user = User(
                name="TCS — Tata Consultancy Services",
                email=email,
                password_hash=hash_password(password),
                role="industry",
            )
            db.add(user)
            db.flush()
        elif user.industry is not None and user.industry.company_name.casefold() != "tcs":
            raise ValueError("The configured Industry account already belongs to another company.")

        industry = user.industry or Industry(
            user_id=user.id,
            company_name="TCS — Tata Consultancy Services",
            industry_type="Information Technology",
            description="",
        )
        if user.industry is None:
            db.add(industry)
            db.flush()
        details = db.get(IndustryCompanyDetails, industry.id)
        if details is None:
            db.add(IndustryCompanyDetails(industry_id=industry.id))
        db.commit()
        return "TCS Industry account configured. Credentials were not displayed."
    finally:
        db.close()


if __name__ == "__main__":
    try:
        print(bootstrap_tcs())
    except ValueError as error:
        print(f"TCS provisioning failed: {error}", file=sys.stderr)
        sys.exit(1)
