"""
Neo Eco Cleaning — Sales Pipeline Manager
============================================
"""
# Re-export from package init for convenience
from sales_pipeline import (
    create_deal,
    update_deal_stage,
    get_deal,
    get_all_deals,
    get_deals_by_stage,
    get_pipeline_view,
    get_pipeline_analytics,
    get_revenue_forecast,
    DEAL_STAGES,
)
