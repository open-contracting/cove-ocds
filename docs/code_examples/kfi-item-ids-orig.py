tender_items = tender.get('items', [])
for item in tender_items:
	item_id = item.get('id')
	if item_id and release_id:
		release_tender_item_ids.add((ocid, release_id, item_id))
		get_item_scheme(item)
