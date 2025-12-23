import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from datetime import datetime
try:
    from pyvirtualdisplay import Display
except ImportError:
    pass

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
DATA_FILE_VIAGOGO = 'prices.json'
GAMES_FILE = 'all_games_to_scrape.json'
ILS_TO_USD = 0.28
# ==========================================

def load_data(file_path):
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except: return []

def append_data(file_path, new_records):
    data = load_data(file_path)
    data.extend(new_records)
    with open(file_path, 'w') as f: json.dump(data, f)

def extract_prices_clean(driver):
    """
    Clean, robust strategy to find 'Category X' labels and fallback to Section Mapping.
    """
    prices = {}
    extraction_start_time = time.time()  # Track total extraction time
    try:
        print("      ➡️ Entering extraction logic...", flush=True)
        # REMOVED: Expensive body.text check that causes Docker CPU hangs
        # We proceed directly to targeted element searches which are lighter.

        # ------------------------------------------------------------------
        # APPROACH 1: "Anchor & Context" (Category Labels)
        # ------------------------------------------------------------------
        category_search_start = time.time()
        for i in range(1, 5):
            cat_name = f"Category {i}"
            
            # Skip if already found
            if cat_name in prices:
                continue
            
            # Check if we're taking too long on category search
            if time.time() - category_search_start > 30:
                print(f"      ⚠️ Category search taking too long, skipping remaining categories")
                break
            
            # Find all elements containing this text - EXPANDED XPATH to include more element types
            xpath_query = f"//div[contains(text(), '{cat_name}')] | //span[contains(text(), '{cat_name}')] | //button[contains(text(), '{cat_name}')] | //a[contains(text(), '{cat_name}')] | //li[contains(text(), '{cat_name}')] | //p[contains(text(), '{cat_name}')] | //label[contains(text(), '{cat_name}')]"
            
            print(f"      ... searching for {cat_name} ...", flush=True)
            try:
                # Add timeout protection for find_elements
                search_start = time.time()
                # Set shorter implicit wait for this search
                original_wait = driver.timeouts.implicit_wait if hasattr(driver.timeouts, 'implicit_wait') else 10
                driver.implicitly_wait(3)  # Reduce wait time for faster failure
                try:
                    anchors = driver.find_elements(By.XPATH, xpath_query)
                finally:
                    driver.implicitly_wait(original_wait)  # Restore original wait
                
                search_time = time.time() - search_start
                if search_time > 5:
                    print(f"      ⚠️ Search took {search_time:.1f}s (slow), limiting results")
                    anchors = anchors[:5]  # Limit to 5 if too slow
                if search_time > 15:
                    print(f"      ⚠️ Search took {search_time:.1f}s (very slow), skipping this category")
                    anchors = []  # Skip if extremely slow
            except Exception as find_err:
                msg = str(find_err).lower()
                if 'crashed' in msg or 'disconnected' in msg:
                    print(f"      🔥 Driver crashed during search: {msg[:50]}")
                    raise find_err
                print(f"      ⚠️ Search error: {msg[:50]}")
                anchors = []
            
            # Fallback for "Cat 1" etc
            if not anchors:
                 try:
                     xpath_short = f"//div[contains(text(), 'Cat {i}')] | //span[contains(text(), 'Cat {i}')] | //button[contains(text(), 'Cat {i}')] | //a[contains(text(), 'Cat {i}')]"
                     search_start = time.time()
                     anchors = driver.find_elements(By.XPATH, xpath_short)
                     search_time = time.time() - search_start
                     if search_time > 5:
                         anchors = anchors[:10]
                 except Exception as find_err:
                     msg = str(find_err).lower()
                     if 'crashed' in msg or 'disconnected' in msg:
                         raise find_err
                     anchors = []
            
            # DEBUG
            if not anchors:
                print(f"      ⚠️ No '{cat_name}' anchors found.")
            else:
                print(f"      Found {len(anchors)} potential anchors for {cat_name}")

            best_price = None
            
            # Limit number of anchors to process (prevent hanging on too many elements)
            max_anchors = 5 if len(anchors) > 5 else len(anchors)
            anchors_to_process = anchors[:max_anchors]
            if len(anchors) > max_anchors:
                print(f"      ⚠️ Limiting to {max_anchors} anchors (found {len(anchors)})")
            
            for anchor_idx, anchor in enumerate(anchors_to_process):
                try:
                    # Check driver health before processing each anchor
                    try:
                        driver.current_url
                    except:
                        print(f"      ⚠️ Driver unhealthy, stopping anchor processing")
                        break
                    
                    container = anchor
                    valid_price = None
                    anchor_start_time = time.time()
                    
                    # Check Anchor, Parent, Grandparent, and siblings (expanded to 4 levels)
                    for level in range(4):
                        # Add timeout protection for text access (can hang in Docker)
                        try:
                            text_start = time.time()
                            txt = container.text.replace('\n', ' ').strip()
                            text_time = time.time() - text_start
                            if text_time > 3:
                                print(f"      ⚠️ Text access took {text_time:.1f}s (slow), skipping level {level}")
                                break  # Skip remaining levels if too slow
                        except Exception as text_err:
                            msg = str(text_err).lower()
                            if 'crashed' in msg or 'disconnected' in msg:
                                raise text_err
                            print(f"      ⚠️ Text access error: {msg[:30]}")
                            break
                        
                        # Skip if text is empty or too short
                        if not txt or len(txt) < 3:
                            try:
                                container = container.find_element(By.XPATH, "..")
                            except:
                                break
                            continue
                        
                        price_matches = re.finditer(r'(?:\$|₪|USD|ILS|NIS)?\s*([\d,]{2,})', txt)
                        min_p = float('inf')
                        found = False
                        
                        for pm in price_matches:
                            try:
                                p_str = pm.group(1)
                                full_match = pm.group(0)
                                val = float(p_str.replace(',', ''))
                                
                                if val < 35: continue 
                                if val > 50000: continue 
                                
                                is_ils = '₪' in full_match or 'ILS' in full_match or 'NIS' in full_match
                                if not is_ils and ('₪' in txt or 'ILS' in txt or 'NIS' in txt): is_ils = True
                                if is_ils: val = round(val * ILS_TO_USD, 2)
                                
                                if val < min_p:
                                    min_p = val
                                    found = True
                            except: pass
                        
                        if found:
                            valid_price = min_p
                            break 
                        
                        # Try parent
                        try: 
                            container = container.find_element(By.XPATH, "..")
                        except: 
                            break

                    if valid_price:
                        if best_price is None or valid_price < best_price:
                            best_price = valid_price
                    
                    anchor_time = time.time() - anchor_start_time
                    if anchor_time > 5:
                        print(f"      ⚠️ Anchor {anchor_idx+1} processing took {anchor_time:.1f}s")
                        # If processing is too slow, break early
                        if anchor_time > 10:
                            print(f"      ⚠️ Stopping anchor processing (too slow)")
                            break
                except Exception as anchor_err:
                    msg = str(anchor_err).lower()
                    if 'crashed' in msg or 'disconnected' in msg:
                        raise anchor_err
                    # Skip individual anchor errors
                    pass
            
            # Fallback: Check aria-label for ALL categories (not just Category 1)
            if not best_price:
                try:
                     # Check driver health before expensive operation
                     try:
                         driver.current_url  # Quick health check
                     except:
                         print(f"      ⚠️ Driver unhealthy, skipping aria-label fallback for {cat_name}")
                         raise Exception("Driver unhealthy")
                     
                     print(f"      🔍 Checking aria-label fallback for {cat_name}...")
                     time.sleep(0.5)  # Small delay to let page stabilize
                     
                     # Add timeout protection for element finding
                     try:
                         # Use shorter timeout for element finding
                         driver.implicitly_wait(2)  # Reduce from 10 to 2 seconds
                         # Add explicit timeout wrapper for find_elements (can hang)
                         start_time = time.time()
                         try:
                             aria_pills = driver.find_elements(By.XPATH, f"//*[@aria-label and contains(@aria-label, '{cat_name}')]")
                             if time.time() - start_time > 5:
                                 print(f"      ⚠️ Aria-label search took {time.time() - start_time:.1f}s, limiting results")
                                 aria_pills = aria_pills[:3]  # Limit if too slow
                         except Exception as find_xpath_err:
                             aria_pills = []
                             if 'crashed' in str(find_xpath_err).lower():
                                 raise find_xpath_err
                         
                         if not aria_pills:
                             # Try short form with timeout
                             try:
                                 start_time = time.time()
                                 aria_pills = driver.find_elements(By.XPATH, f"//*[@aria-label and contains(@aria-label, 'Cat {i}')]")
                                 if time.time() - start_time > 5:
                                     aria_pills = aria_pills[:3]
                             except:
                                 aria_pills = []
                         
                         driver.implicitly_wait(10)  # Restore original timeout
                         if aria_pills:
                             print(f"      Found {len(aria_pills)} aria-label elements for {cat_name}")
                     except Exception as find_err:
                         # Restore timeout even on error
                         try:
                             driver.implicitly_wait(10)
                         except:
                             pass
                         # If finding elements causes crash, skip this fallback
                         msg = str(find_err).lower()
                         if 'crashed' in msg or 'disconnected' in msg or 'target closed' in msg:
                             print(f"      ⚠️ Driver unstable during aria-label search, skipping...")
                             raise find_err  # Re-raise to trigger driver restart
                         aria_pills = []
                     
                     # Limit to first 3 elements to reduce memory pressure
                     for el in aria_pills[:3]:
                         try:
                             # Quick health check before accessing element
                             try:
                                 driver.current_url
                             except:
                                 raise Exception("Driver crashed during element access")
                             
                             txt = el.get_attribute('aria-label')
                             if not txt:
                                 continue
                             m = re.search(r'(?:\$|₪|USD)?\s*([\d,]{2,})', txt)
                             if m:
                                 p = float(m.group(1).replace(',', ''))
                                 if '₪' in txt: p = round(p * ILS_TO_USD, 2)
                                 if p > 35 and p < 50000:
                                     best_price = p
                                     print(f"      ✅ Aria-label fallback found {cat_name}: {best_price}")
                                     break
                         except Exception as el_err:
                             msg = str(el_err).lower()
                             if 'crashed' in msg or 'disconnected' in msg:
                                 raise el_err  # Re-raise critical errors
                             # Skip individual element errors
                             continue
                except Exception as e:
                    msg = str(e).lower()
                    # Re-raise critical errors to trigger driver restart
                    if 'crashed' in msg or 'disconnected' in msg or 'target closed' in msg or 'tab crashed' in msg or 'unhealthy' in msg:
                        print(f"      🔥 Critical error in aria-label fallback: {msg[:50]}")
                        raise e
                    pass

            if best_price:
                prices[cat_name] = best_price
                print(f"      ✅ Found {cat_name}: ${best_price}", flush=True)
            else:
                print(f"      ⚠️ No price found for {cat_name}", flush=True)

        # ------------------------------------------------------------------
        # APPROACH 2: Interactive Section Mapping (Fill in missing categories)
        # ------------------------------------------------------------------
        # Now run section mapping for ANY missing categories (not just when prices is empty)
        series_map = {'1': 'Category 1', '2': 'Category 2', '3': 'Category 3', '4': 'Category 4'}
        
        missing_before_mapping = [cat for cat in ['Category 1', 'Category 2', 'Category 3', 'Category 4'] if cat not in prices]
        if missing_before_mapping:
            print(f"      🔄 Section mapping: Looking for {len(missing_before_mapping)} missing categories...")
        
        for prefix, cat_label in series_map.items():
            # Skip if already found
            if cat_label in prices: 
                continue
            
            print(f"      🔄 Trying section mapping for missing {cat_label}...")
            found_via_section = False
            
            # Check typical sections: 101, 102, 103... (expanded list)
            for suffix in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15']: 
                sec_id = f"{prefix}{suffix}"
                try:
                    # Expanded search for section elements - try multiple patterns
                    xpath_patterns = [
                        f"//div[contains(text(), '{sec_id}')]",
                        f"//span[contains(text(), '{sec_id}')]",
                        f"//button[contains(text(), '{sec_id}')]",
                        f"//a[contains(text(), '{sec_id}')]",
                        f"//*[@data-section='{sec_id}']",
                        f"//*[contains(@class, 'section-{sec_id}')]",
                        f"//*[contains(@id, '{sec_id}')]"
                    ]
                    
                    els = []
                    for pattern in xpath_patterns:
                        try:
                            found = driver.find_elements(By.XPATH, pattern)
                            els.extend(found)
                        except:
                            continue
                    
                    target_el = None
                    for el in els:
                        try:
                            t = el.text.strip()
                            # More flexible matching
                            if sec_id in t or f"Section {sec_id}" in t or f"Sec {sec_id}" in t:
                                if el.is_displayed():
                                    target_el = el
                                    break
                        except:
                            continue
                    
                    if target_el:
                        print(f"      🖱️ Clicking Section {sec_id} to find {cat_label}...")
                        try: 
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_el)
                            time.sleep(0.8)
                            driver.execute_script("arguments[0].click();", target_el)
                            time.sleep(2.5)  # Wait for page to update
                        except Exception as click_err:
                            try:
                                target_el.click()
                                time.sleep(2.5)
                            except:
                                print(f"      ⚠️ Could not click section {sec_id}")
                                continue
                        
                        # Scan body for NEW price - look for prices near the category text
                        try:

                            # Check driver health before reading body
                            try:
                                driver.current_url
                            except:
                                print(f"      ⚠️ Driver unhealthy before reading body, skipping section {sec_id}")
                                continue
                            
                            # Read body text with protection
                            try:
                                driver.implicitly_wait(3)  # Reduce timeout
                                body_txt = driver.find_element(By.TAG_NAME, 'body').text
                                driver.implicitly_wait(10)  # Restore timeout
                            except Exception as body_read_err:
                                try:
                                    driver.implicitly_wait(10)  # Restore timeout
                                except:
                                    pass
                                msg = str(body_read_err).lower()
                                if 'crashed' in msg or 'disconnected' in msg:
                                    print(f"      ⚠️ Driver crashed while reading body, skipping section {sec_id}")
                                    raise body_read_err  # Re-raise to trigger restart
                                print(f"      ⚠️ Could not read body text for section {sec_id}")
                                continue
                            
                            # Look for prices that appear after clicking this section
                            # Try to find prices near "Category X" text in the updated page
                            cat_pattern = rf"Category\s+{prefix}\b"
                            cat_match = re.search(cat_pattern, body_txt, re.IGNORECASE)
                            
                            if cat_match:
                                # Look for prices near this category mention (expanded window)
                                start_pos = cat_match.end()
                                search_window = body_txt[start_pos:start_pos + 800]  # Increased to 800 chars
                                pm = re.findall(r'(?:\$|₪|USD)?\s*([\d,]{2,})', search_window)
                            else:
                                # Fallback: scan all prices and take minimum
                                pm = re.findall(r'(?:\$|₪|USD)?\s*([\d,]{2,})', body_txt)
                            
                            found_p = None
                            curr_min = float('inf')
                            
                            for p_str in pm:
                                try:
                                    v = float(p_str.replace(',', ''))
                                    if v < 35: continue
                                    if v > 50000: continue
                                    if '₪' in body_txt or 'ILS' in body_txt or 'NIS' in body_txt: 
                                        v = round(v * ILS_TO_USD, 2)
                                    if v < curr_min:
                                        curr_min = v
                                        found_p = v
                                except: pass
                                
                            if found_p:
                                prices[cat_label] = found_p
                                print(f"      ✅ Section mapping found {cat_label}: ${found_p}")
                                found_via_section = True
                                break  # Done with this category
                        except Exception as scan_error:
                            print(f"      ⚠️ Error scanning prices after clicking {sec_id}: {scan_error}")
                            pass
                    else:
                        # Try alternative: look for section numbers without prefix
                        if suffix in ['01', '02', '03', '04']:
                            # Try clicking any section that might be category-related
                            try:
                                alt_els = driver.find_elements(By.XPATH, f"//*[contains(text(), 'Section {sec_id}') or contains(text(), 'Sec {sec_id}')]")
                                for alt_el in alt_els[:3]:  # Try first 3 matches
                                    try:
                                        if alt_el.is_displayed():
                                            print(f"      🖱️ Trying alternative section element for {cat_label}...")
                                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", alt_el)
                                            time.sleep(0.8)
                                            driver.execute_script("arguments[0].click();", alt_el)
                                            time.sleep(2.5)
                                            
                                            # Check driver health before reading body
                                            try:
                                                driver.current_url
                                            except:
                                                continue
                                            
                                            # Read body text with protection
                                            try:
                                                driver.implicitly_wait(3)
                                                body_txt = driver.find_element(By.TAG_NAME, 'body').text
                                                driver.implicitly_wait(10)
                                            except Exception as body_err:
                                                try:
                                                    driver.implicitly_wait(10)
                                                except:
                                                    pass
                                                msg = str(body_err).lower()
                                                if 'crashed' in msg or 'disconnected' in msg:
                                                    raise body_err
                                                continue
                                            cat_pattern = rf"Category\s+{prefix}\b"
                                            if re.search(cat_pattern, body_txt, re.IGNORECASE):
                                                pm = re.findall(r'(?:\$|₪|USD)?\s*([\d,]{2,})', body_txt)
                                                found_p = None
                                                curr_min = float('inf')
                                                for p_str in pm:
                                                    try:
                                                        v = float(p_str.replace(',', ''))
                                                        if 35 <= v <= 50000:
                                                            if '₪' in body_txt or 'ILS' in body_txt: 
                                                                v = round(v * ILS_TO_USD, 2)
                                                            if v < curr_min:
                                                                curr_min = v
                                                                found_p = v
                                                    except: pass
                                                if found_p:
                                                    prices[cat_label] = found_p
                                                    print(f"      ✅ Alternative section click found {cat_label}: ${found_p}")
                                                    found_via_section = True
                                                    break
                                    except:
                                        continue
                                if found_via_section:
                                    break
                            except:
                                pass
                except Exception as e:
                    print(f"      ⚠️ Section mapping error for {sec_id}: {str(e)[:50]}")
                    pass
            
            if not found_via_section:
                print(f"      ⚠️ Section mapping did not find {cat_label}")
        
        # ------------------------------------------------------------------
        # APPROACH 3: Comprehensive body text scan for any remaining missing categories
        # ------------------------------------------------------------------
        missing_cats = [cat for cat in ['Category 1', 'Category 2', 'Category 3', 'Category 4'] if cat not in prices]
        if missing_cats:
            # Skip text scan if we already found most categories (to reduce memory pressure)
            if len(prices) >= 2:
                print(f"      ⏭️ Skipping text scan (already found {len(prices)} categories, avoiding memory pressure)")
            else:
                print(f"      🔍 Performing comprehensive text scan for: {', '.join(missing_cats)}...")
                try:
                    # Check driver health before expensive operation
                    try:
                        driver.current_url
                    except:
                        print(f"      ⚠️ Driver unhealthy before text scan, skipping...")
                        raise Exception("Driver unhealthy")
                    
                    # Try to get body text with timeout protection
                    try:
                        driver.implicitly_wait(3)  # Reduce timeout for this operation
                        body_element = driver.find_element(By.TAG_NAME, 'body')
                        body_txt = body_element.text
                        driver.implicitly_wait(10)  # Restore timeout
                    except Exception as body_err:
                        try:
                            driver.implicitly_wait(10)  # Restore timeout even on error
                        except:
                            pass
                        msg = str(body_err).lower()
                        if 'crashed' in msg or 'disconnected' in msg:
                            print(f"      ⚠️ Driver crashed while reading body text, skipping text scan...")
                            raise body_err
                        print(f"      ⚠️ Could not read body text: {msg[:50]}")
                        return prices  # Return what we have
                    
                    # Limit text scan to first 50000 chars to reduce memory usage
                    if len(body_txt) > 50000:
                        body_txt = body_txt[:50000]
                        print(f"      ⚠️ Body text truncated to 50000 chars to reduce memory usage")
                    
                    for cat_label in missing_cats:
                        cat_num = cat_label.split()[-1]
                        # Look for "Category X" followed by prices within reasonable distance
                        pattern = rf"Category\s+{cat_num}\b[^$]*?(?:\$|₪|USD)?\s*([\d,]{{2,}})"
                        matches = re.finditer(pattern, body_txt, re.IGNORECASE | re.DOTALL)
                        
                        best_price = None
                        match_count = 0
                        for match in matches:
                            match_count += 1
                            if match_count > 10:  # Limit matches to prevent excessive processing
                                break
                            try:
                                p_str = match.group(1)
                                val = float(p_str.replace(',', ''))
                                if val < 35 or val > 50000:
                                    continue
                                
                                # Check if ILS currency
                                context = body_txt[max(0, match.start()-50):match.end()+50]
                                if '₪' in context or 'ILS' in context or 'NIS' in context:
                                    val = round(val * ILS_TO_USD, 2)
                                
                                if best_price is None or val < best_price:
                                    best_price = val
                            except:
                                continue
                        
                        if best_price:
                            prices[cat_label] = best_price
                            print(f"      ✅ Text scan found {cat_label}: ${best_price}")
                except Exception as e:
                    msg = str(e).lower()
                    if 'crashed' in msg or 'disconnected' in msg or 'unhealthy' in msg:
                        print(f"      ⚠️ Text scan skipped due to driver instability: {msg[:50]}")
                        # Don't raise - return what we have
                    else:
                        print(f"      ⚠️ Text scan error: {msg[:50]}")

        extraction_total_time = time.time() - extraction_start_time
        if extraction_total_time > 20:
            print(f"      ⚠️ Total extraction took {extraction_total_time:.1f}s")
        print(f"      ✅ Extraction complete: found {len(prices)} categories", flush=True)
        return prices

    except Exception as e:
        extraction_total_time = time.time() - extraction_start_time if 'extraction_start_time' in locals() else 0
        msg = str(e).lower()
        if 'timeout' in msg or 'crashed' in msg or 'disconnected' in msg:
            print(f"      🔥 Critical extraction error after {extraction_total_time:.1f}s: {msg[:50]}")
            raise e  # Propagate critical errors to trigger driver restart
        print(f"      ⚠️ Extract Error after {extraction_total_time:.1f}s: {e}")
        return {}

def _create_chrome_options():
    """Create a fresh ChromeOptions object with all stability flags"""
    options = uc.ChromeOptions()
    # NOTE: When using pyvirtualdisplay / xvfb, we DO NOT use --headless.
    # This makes the browser "think" it is visible, avoiding detection.
    
    # options.add_argument('--headless') # <--- REMOVED for anti-detection
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')
    # Additional stability flags for Docker/server environments
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--disable-hang-monitor')
    options.add_argument('--disable-prompt-on-repost')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    # Memory and performance optimizations
    options.add_argument('--memory-pressure-off')
    # Additional stability flags to prevent crashes
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-translate')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-default-apps')
    options.add_argument('--disable-session-crashed-bubble')
    options.add_argument('--disable-crash-reporter')
    options.add_argument('--disable-breakpad')
    # Memory limits to prevent crashes (V8 heap limit via js-flags)
    options.add_argument('--js-flags=--max-old-space-size=2048')
    # Reduce memory usage
    options.add_argument('--disable-accelerated-2d-canvas')
    options.add_argument('--disable-accelerated-video-decode')
    options.add_argument('--disable-canvas-aa')
    options.add_argument('--disable-2d-canvas-clip-aa')
    options.add_argument('--disable-gl-drawing-for-tests')
    # Additional crash prevention
    options.add_argument('--disable-component-extensions-with-background-pages')
    options.add_argument('--disable-background-downloads')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--disable-domain-reliability')
    options.add_argument('--disable-features=AudioServiceOutOfProcess')
    # options.add_argument('--user-agent=...') # REMOVED: Let UC/Chrome handle this to avoid fingerprint mismatches
    
    # Add persistent profile to build "trust" and avoid repetitive CAPTCHAs
    profile_dir = os.path.join(os.getcwd(), 'chrome_profile_viagogo')
    # options.add_argument(f'--user-data-dir={profile_dir}')
    
    # BLOCK IMAGES to save CPU/Bandwidth
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    options.page_load_strategy = 'eager'
    return options

def get_driver():
    try:
        browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
        driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(3):
            try:
                # Create fresh options object each time to avoid reuse error
                options = _create_chrome_options()
                driver = uc.Chrome(options=options, version_main=None, browser_executable_path=browser_path, driver_executable_path=driver_path)
                # Increased timeout for server environments (Railways can be slower)
                driver.set_page_load_timeout(120)  # Increased from 60 to 120 seconds
                driver.implicitly_wait(10)  # Add implicit wait for element finding
                driver.set_script_timeout(60)  # Set script execution timeout
                return driver
            except OSError as e:
                if 'Text file busy' in str(e):
                    print(f'      ⚠️ Driver file busy (attempt {attempt+1}/3). Waiting...')
                time.sleep(5)
                if attempt == 2: raise e
            except Exception as e:
                error_msg = str(e).lower()
                if 'cannot reuse' in error_msg or 'chromeoptions' in error_msg:
                    # This shouldn't happen now, but if it does, wait and retry
                    print(f'      ⚠️ Options reuse error (attempt {attempt+1}/3). Retrying...')
                    time.sleep(3)
                    continue
                raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}')
        return None

def run_scraper_cycle():
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (CLEAN ANCHOR STRATEGY)...')
    
    # START VIRTUAL DISPLAY IF HEADLESS (DOCKER/LINUX)
    display = None
    if os.environ.get('HEADLESS') == 'true':
        try:
            print("      🖥️ Starting Virtual Display (XVFB)...")
            display = Display(visible=0, size=(1920, 1080))
            display.start()
        except Exception as e:
            print(f"      ⚠️ Failed to start XVFB: {e}")

    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found!')
        if display: display.stop()
        return

    with open(GAMES_FILE, 'r') as games_f: 
        games = json.load(games_f)

    driver = get_driver()
    timestamp = datetime.now().isoformat()
    new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
            # Proactive driver restart every 5 games to prevent memory buildup and crashes
            if i > 1 and i % 5 == 0:
                print(f"      🔄 Proactive driver restart (game {i}/{len(games)})...")
                try: 
                    driver.quit()
                except: 
                    pass
                time.sleep(2)
                driver = get_driver()
                if not driver:
                    print(f"      ❌ Failed to restart driver")
                    break

            if driver is None: driver = get_driver()
            if not driver: continue

            # Check driver health before starting
            try:
                driver.current_url
            except:
                print(f"      ⚠️ Driver unhealthy before match {i}, restarting...")
                try:
                    driver.quit()
                except:
                    pass
                driver = get_driver()
                if not driver:
                    continue

            match_name = game['match_name']
            url = game['url']
            clean_url = url.split('&Currency')[0].split('?Currency')[0]
            target_url = url + ('&Currency=USD' if '?' in url else '?Currency=USD')
            
            print(f'[{i}/{len(games)}] {match_name[:30]}... ', end='', flush=True)
            
            for attempt in range(3):
                try:
                    # Use execute_cdp_cmd for better timeout handling
                    try:
                        driver.set_page_load_timeout(120)
                        driver.get(target_url)
                    except Exception as load_error:
                        # If page load times out, try to continue anyway
                        if 'timeout' in str(load_error).lower():
                            print(f"      ⚠️ Page load timeout, continuing anyway...")
                            try:
                                driver.execute_script("window.stop();")
                            except:
                                pass
                        else:
                            raise load_error
                    
                    # 🛑 FORCE STOP LOADING after 15 seconds to kill heavy JS/Ads (increased from 10)
                    try:
                        time.sleep(15)  # Increased wait time for slower servers
                        driver.execute_script("window.stop();")
                        print("      🛑 Executed window.stop() to clear resources")
                    except Exception: 
                        pass

                    print(f"      🔎 Title: {driver.title}")
                    
                    # Check driver health before expensive extraction
                    try:
                        driver.current_url
                    except:
                        print(f"      ⚠️ Driver unhealthy before extraction, restarting...")
                        raise Exception("Driver unhealthy before extraction")
                    
                    if '502' in driver.title or '403' in driver.title or 'Just a moment' in driver.title:
                        print(f"      ⚠️ Blocked/Error Page detected ('{driver.title}'). waiting...")
                        time.sleep(10)
                    
                    # 1. Try standard extract (Includes Section Fallback) with timeout protection
                    extraction_start = time.time()
                    prices = {}
                    max_extraction_time = 60  # Maximum time for extraction (60 seconds)
                    try:
                        print(f"      🔍 Starting extraction (max {max_extraction_time}s)...")
                        prices = extract_prices_clean(driver)
                        extraction_time = time.time() - extraction_start
                        if extraction_time > 30:
                            print(f"      ⚠️ Extraction took {extraction_time:.1f}s (slow)")
                        print(f"      ✅ Extraction completed in {extraction_time:.1f}s, found {len(prices)} categories")
                    except Exception as extract_err:
                        extraction_time = time.time() - extraction_start
                        msg = str(extract_err).lower()
                        if extraction_time > max_extraction_time:
                            print(f"      ⚠️ Extraction exceeded {max_extraction_time}s timeout ({extraction_time:.1f}s), continuing to next match...")
                            prices = {}  # Return empty, continue to next match
                        elif 'crashed' in msg or 'disconnected' in msg or 'tab crashed' in msg:
                            print(f"      🔥 Critical extraction error after {extraction_time:.1f}s: {msg[:50]}")
                            raise extract_err  # Re-raise to trigger restart
                        else:
                            print(f"      ⚠️ Extraction error after {extraction_time:.1f}s: {msg[:50]}")
                            prices = {}  # Continue with empty prices
                    
                    # Safety check: if extraction took too long but didn't raise error, continue anyway
                    extraction_time = time.time() - extraction_start
                    if extraction_time > max_extraction_time and not prices:
                        print(f"      ⚠️ Extraction took {extraction_time:.1f}s without results, continuing to next match...")
                        prices = {}  # Ensure empty to continue
                    
                    # 2. Interactive: Click "Listings" summary if no data found
                    if not prices:
                        try:
                            listings_clicked = False
                            list_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'listings')]")
                            for le in list_els:
                                if 'ticket' not in le.text.lower() and len(le.text) < 30 and le.is_displayed():
                                     print(f"      🖱️ Clicking Listing Summary: '{le.text}'")
                                     try: driver.execute_script("arguments[0].click();", le)
                                     except: le.click()
                                     time.sleep(3)
                                     listings_clicked = True
                                     break
                            
                            if listings_clicked:
                                print('   🔄 Listings expanded. Retrying extraction...')
                                prices = extract_prices_clean(driver)
                        except: pass

                    if prices:
                        for cat, price in prices.items():
                            new_records_buffer.append({
                                'match_url': clean_url, 'match_name': match_name,
                                'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                            })
                        print(f'✅ Found {json.dumps(prices)}')
                        
                        # SAVE IMMEDIATELY
                        if new_records_buffer:
                             append_data(DATA_FILE_VIAGOGO, new_records_buffer)
                             new_records_buffer = [] 
                        break  # Break from retry loop, continue to next match 
                    else:
                        print('❌ No data found (will retry)...')
                        try:
                            sample_txt = driver.find_element(By.TAG_NAME, 'body').text[:100].replace('\n', ' ')
                            print(f"      [DEBUG BODY]: {sample_txt}...")
                        except: pass
                        
                        # Do NOT break; let it retry naturally
                        if attempt == 2:
                             print("      Giving up on this match.")
                        
                except Exception as e: 
                    msg = str(e).lower()
                    print(f"      ⚠️ Driver Error (attempt {attempt+1}/3): {msg[:100]}")
                    # Handle different types of errors
                    is_critical = False
                    
                    if 'timeout' in msg or 'timed out receiving message from renderer' in msg:
                        print(f"      🔄 Renderer timeout detected, restarting driver...")
                        is_critical = True
                    elif 'tab crashed' in msg or 'session deleted' in msg or 'target closed' in msg:
                        print(f"      🔥 Tab crashed detected, restarting driver...")
                        is_critical = True
                    elif 'chrome not reachable' in msg or 'disconnected' in msg:
                        print(f"      🔥 Chrome disconnected, restarting driver...")
                        is_critical = True
                    elif 'crashed' in msg:
                        print(f"      🔥 Crash detected, restarting driver...")
                        is_critical = True
                    
                    if is_critical:
                        try: 
                            driver.quit()
                        except: 
                            pass
                        time.sleep(5)  # Increased wait time after crash
                        driver = get_driver()
                        if not driver:
                            print(f"      ❌ Failed to restart driver, skipping this match")
                            break  # Break from retry loop, continue to next match
                        time.sleep(5)
                        # Continue to next attempt
                    else:
                        # For non-critical errors, try to continue to next attempt
                        print(f"      ⚠️ Non-critical error, will retry...")
                        if attempt < 2:  # Don't sleep on last attempt
                            time.sleep(2)
                        # Continue to next attempt in the loop
            time.sleep(1) 
        
        time.sleep(1.0)
        
    except Exception as e: print(f'🔥 Error: {e}')
    finally:
        try: driver.quit()
        except: pass
        if display:
            try: display.stop()
            except: pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()