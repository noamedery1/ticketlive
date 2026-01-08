def _search_offers_logic(match, seller, category, min_price, max_price, min_quantity, max_quantity, keyword, range):
    try:
        # Debugging
        print(f"[SEARCH] Filters: match={match}, seller={seller}, cat={category}, price={min_price}-{max_price}", flush=True)
        
        index_data = load_index()
        # Ensure we have valid sets
        if 'match' not in index_data: index_data['match'] = {}
        if 'seller' not in index_data: index_data['seller'] = {}
        if 'category' not in index_data: index_data['category'] = {}
        if 'offers_by_id' not in index_data: index_data['offers_by_id'] = {}

        candidate_ids = None
        
        # Time range filter
        now = datetime.utcnow()
        if range == '7d':
            cutoff = now - timedelta(days=7)
        elif range == '30d':
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        # --- INDEX FILTERING ---
        used_index = False
        
        # Match Filter
        if match is not None:
            used_index = True
            match_key = str(match)
            # If match key exists, get IDs. If not, we get empty set, which is correct (no results).
            # But we must initialize candidate_ids.
            ids = set(index_data['match'].get(match_key, []))
            if candidate_ids is None:
                candidate_ids = ids
            else:
                candidate_ids &= ids

        # Seller Filter
        if seller:
            used_index = True
            seller_obj = get_seller_by_name(seller)
            if seller_obj:
                seller_id = seller_obj['id']
                ids = set(index_data['seller'].get(seller_id, []))
                if candidate_ids is None:
                    candidate_ids = ids
                else:
                    candidate_ids &= ids
            else:
                # Seller not found -> no results
                candidate_ids = set()
        
        # Category Filter (Skipping index for fuzzy matching capabilities)
        
        # --- FALLBACK ---
        # If candidate_ids IS NONE, it means no index filters were applied -> Search All.
        # If candidate_ids IS EMPTY SET (not None), it means index filters returned 0 results.
        
        if candidate_ids is None:
            # Fallback to all indexed offers
            candidate_ids = set(index_data['offers_by_id'].keys())
            
            # If index is empty/broken, try file scan?
            if not candidate_ids:
                 offer_files = list(BASE_DIR.glob('offers_*.jsonl'))
                 for file_path in offer_files:
                     offers = load_offers_from_file(file_path)
                     for offer in offers:
                         candidate_ids.add(offer.get('id'))

        if not candidate_ids:
             print("[SEARCH] No candidates found.", flush=True)
             return []

        # --- LOAD & FILTER ---
        results = []
        offers_by_id = index_data.get('offers_by_id', {})
        
        # Group by file to minimize IO
        file_groups = {}
        for oid in candidate_ids:
            if oid in offers_by_id:
                fname = offers_by_id[oid]['file']
                if fname not in file_groups: file_groups[fname] = []
                file_groups[fname].append(oid)
        
        print(f"[SEARCH] Scanning {len(file_groups)} files...", flush=True)

        for fname, oids in file_groups.items():
            file_path = BASE_DIR / fname
            if not file_path.exists(): continue
            
            file_offers = load_offers_from_file(file_path)
            target_ids = set(oids)
            
            for offer in file_offers:
                if offer.get('id') not in target_ids:
                    continue
                
                # Time Check
                if 'created_at' in offer:
                    created_at = datetime.fromisoformat(offer['created_at'])
                else:
                    created_at = now
                if cutoff and created_at < cutoff:
                    continue
                
                # Match Check (Robust)
                if match is not None:
                    # Check top level
                    if str(offer.get('match')) == str(match):
                        pass
                    # Check lines
                    else:
                        found_in_lines = False
                        for line in offer.get('lines', []):
                            if str(line.get('match')) == str(match):
                                found_in_lines = True
                                break
                        if not found_in_lines:
                           continue

                # Seller Check
                if seller and str(offer.get('seller', '')).lower() != str(seller).lower():
                    continue

                # Keyword Check
                if keyword and keyword.lower() not in offer.get('raw', '').lower():
                    continue

                # Line Filters (Cat, Price, Qty)
                has_line_filters = (category or min_price is not None or max_price is not None or 
                                    min_quantity is not None or max_quantity is not None)
                
                if has_line_filters:
                    lines = offer.get('lines', [])
                    if not lines: continue
                    
                    line_match = False
                    for line in lines:
                        # Category (Fuzzy)
                        if category:
                            l_cat = str(line.get('category', '')).lower()
                            t_cat = str(category).lower()
                            if t_cat not in l_cat and l_cat not in t_cat:
                                continue
                        
                        # Price
                        price = float(line.get('price', 0))
                        if min_price is not None and price < min_price: continue
                        if max_price is not None and price > max_price: continue
                        
                        # Qty
                        qty = line.get('quantity')
                        if min_quantity is not None and (qty is None or qty < min_quantity): continue
                        if max_quantity is not None and (qty is None or qty > max_quantity): continue
                        
                        line_match = True
                        break
                    
                    if not line_match:
                        continue
                
                results.append(offer)

        print(f"[SEARCH] Found {len(results)} results.", flush=True)
        return results

    except Exception as e:
        print(f'[ERROR] Search Logic: {e}')
        # import traceback
        # traceback.print_exc()
        return []
