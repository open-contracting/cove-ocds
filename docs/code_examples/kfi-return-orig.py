return dict(
    # ...
    total_item_count=len(release_tender_item_ids) + len(release_award_item_ids) + len(release_contract_item_ids),
    tender_item_count=len(release_tender_item_ids),
    award_item_count=len(release_award_item_ids),
    contract_item_count=len(release_contract_item_ids),
    # ...
)
