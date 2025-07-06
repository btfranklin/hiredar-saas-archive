# Constants related to recruiter credit costs and credit bundles.

# Credit cost per action
RESUME_PROCESSING_CREDIT_COST: int = 1
CANDIDATE_OUTREACH_CREDIT_COST: int = 2
SHORTLIST_EXPORT_CREDIT_COST: int = 5

# Mapping of credit bundles to their USD prices
CREDIT_BUNDLES: dict[int, int] = {
    100: 5,  # 100 credits cost $5
    500: 20,  # 500 credits cost $20
    1000: 35,  # 1000 credits cost $35 – best deal
}

# Which bundle should be highlighted as the best deal in the UI
BEST_DEAL_CREDITS: int = 1000
