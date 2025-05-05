
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import random
import re

def scrape_rockefeller_grants(max_pages=5):
    chrome_options = Options()
    
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("WebDriver initialized successfully")
        
        if not os.path.exists("debug_screenshots"):
            os.makedirs("debug_screenshots")
        
        base_url = 'https://www.rockefellerfoundation.org/grants/'
        print(f"Navigating to {base_url}...")
        driver.get(base_url)
        
        print("Waiting for initial page to load...")
        time.sleep(5)
        
        driver.save_screenshot("debug_screenshots/initial_page.png")
        print("Initial page screenshot saved")
        
        all_grants_data = []
        current_page = 1
        
        while current_page <= max_pages:
            print(f"\n--- Processing Page {current_page} ---")
            
            print("Finding grant elements...")
            grant_elements = driver.find_elements(By.TAG_NAME, "article")
            
            print(f"Found {len(grant_elements)} potential grant elements")
            
            page_grants = []
            
            for i, grant_element in enumerate(grant_elements):
                try:
                    grant_info = {}
                    
                    full_text = grant_element.text
                    
                    lines = full_text.split('\n')
                    
                    if len(lines) >= 2:
                        if lines[0].startswith("AWARDED"):
                            grant_info['date'] = lines[0]
                        
                        if len(lines) > 1:
                            grant_info['organization'] = lines[1]
                        
                        if len(lines) > 2 and '$' in lines[2]:
                            grant_info['amount'] = lines[2]
                        
                        if len(lines) > 3:
                            grant_info['description'] = ' '.join(lines[3:])
                    
                    try:
                        link_element = grant_element.find_element(By.TAG_NAME, 'a')
                        grant_info['url'] = link_element.get_attribute('href')
                    except:
                        pass
                    
                    if grant_info:
                        page_grants.append(grant_info)
                        print(f"Processed grant {i+1}: {grant_info.get('date', 'Unknown')}")
                
                except Exception as e:
                    print(f"Error processing grant element {i+1}: {str(e)}")
            
            print(f"Successfully processed {len(page_grants)} grants on page {current_page}")
            all_grants_data.extend(page_grants)
            
            try:
                pagination = driver.find_elements(By.CSS_SELECTOR, ".pagination, .nav-links, nav.pagination")
                
                if pagination:
                    print("Found pagination container")
                    
                    next_page_element = driver.find_element(By.XPATH, "//a[contains(text(), 'Next') or contains(@class, 'next')]")
                    
                    if next_page_element:
                        print(f"Found next page button. Navigating to page {current_page+1}...")
                        
                        driver.save_screenshot(f"debug_screenshots/before_next_click_page{current_page}.png")
                        
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_page_element)
                        time.sleep(2) 
                        
                        driver.save_screenshot(f"debug_screenshots/after_scroll_page{current_page}.png")
                        
                        driver.execute_script("arguments[0].click();", next_page_element)
                        
                        current_page += 1
                        
                        time.sleep(5)
                        
                        driver.save_screenshot(f"debug_screenshots/after_click_page{current_page}.png")
                    else:
                        print("Next button not found. Trying alternative approach...")
                        
                        if "page=" in driver.current_url:
                            current_url = driver.current_url
                            next_url = re.sub(r'page=\d+', f'page={current_page+1}', current_url)
                            print(f"Navigating directly to: {next_url}")
                            driver.get(next_url)
                            current_page += 1
                            time.sleep(5)
                        else:
                            next_url = f"{base_url}?page={current_page+1}"
                            print(f"Trying URL: {next_url}")
                            driver.get(next_url)
                            current_page += 1
                            time.sleep(5)
                            
                            new_grants = driver.find_elements(By.TAG_NAME, "article")
                            if len(new_grants) == 0:
                                print("No grants found on new page. Ending pagination.")
                                break
                else:
                    print("No pagination elements found. Trying direct URL navigation...")
                    
                    if current_page == 1:
                        next_url = f"{base_url}page/2/"
                        print(f"Trying URL: {next_url}")
                        driver.get(next_url)
                        current_page += 1
                        time.sleep(5)
                        
                        new_grants = driver.find_elements(By.TAG_NAME, "article")
                        if len(new_grants) == 0:
                            print("No grants found on new page. Ending pagination.")
                            break
                    else:
                        print("Cannot determine next page URL. Pagination complete.")
                        break
                    
            except Exception as e:
                print(f"Error navigating to next page: {str(e)}")
                driver.save_screenshot(f"debug_screenshots/pagination_error_page{current_page}.png")
                
                try:
                    print("Trying fallback pagination approach...")
                    next_url = f"{base_url}page/{current_page+1}/"
                    print(f"Navigating to: {next_url}")
                    driver.get(next_url)
                    current_page += 1
                    time.sleep(5)
                    
                    new_grants = driver.find_elements(By.TAG_NAME, "article")
                    if len(new_grants) == 0:
                        print("No grants found on new page. Ending pagination.")
                        break
                except:
                    print("All pagination approaches failed. Ending pagination.")
                    break
        
        print(f"\nScraping complete. Saving {len(all_grants_data)} grants to file...")
        with open('grants_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_grants_data, f, indent=4, ensure_ascii=False)
        
        print(f"Data successfully saved to 'grants_data.json'")
        
    except Exception as e:
        print(f"Critical error: {str(e)}")
    
    finally:
        if 'driver' in locals():
            driver.quit()
            print("WebDriver closed")

if __name__ == "__main__":
    scrape_rockefeller_grants(max_pages=5) 