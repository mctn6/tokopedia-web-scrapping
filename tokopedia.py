from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import time
import pandas as pd
import re


def extract_unit(product_name):
    """Extract unit information from product name"""
    pattern = r'\((.*?)\)|\d+\s*(?:ML|Ml|ml|G|g|KG|Kg|kg|GR|Gr|gr|Pcs|PCS|pcs|Pack|PACK|pack|Sachet|SACHET|sachet)+'
    
    matches = re.finditer(pattern, product_name)
    units = []
    clean_name = product_name
    
    for match in matches:
        unit = match.group()
        units.append(unit)
        clean_name = clean_name.replace(unit, '').strip()
    
    unit_info = ' '.join(units).strip('()')
    return clean_name, unit_info

def clean_sales_number(sales_text):
    """Clean sales number by removing '+' and 'terjual'"""
    sales = sales_text.replace('terjual', '').replace('+', '').strip()
    try:
        return int(sales)
    except ValueError:
        return 0

def scroll_to_bottom(driver):
    """Scroll to the bottom of the page to load all products"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

def has_next_page(driver):
    """Check if there's a next page button"""
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "a[data-testid='btnShopProductPageNext']")
        return bool(next_button)
    except NoSuchElementException:
        return False

def get_next_page_url(driver):
    """Get the URL of the next page"""
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "a[data-testid='btnShopProductPageNext']")
        return next_button.get_attribute('href')
    except NoSuchElementException:
        return None

def scrape_page(driver, soup):
    """Scrape product information from a single page"""
    page_data = []
    
    product_containers = soup.find_all("div", class_="css-54k5sq")
    print(f"Found {len(product_containers)} products on this page")
    
    for idx, container in enumerate(product_containers, 1):
        try:
            # Extract product name using more specific selectors
            product_name_elem = container.select_one("div[data-testid='linkProductName']")
            if not product_name_elem:
                product_name_elem = container.select_one(".prd_link-product-name")
                
            product_name = product_name_elem.text.strip() if product_name_elem else "N/A"
            
            # Split product name and unit
            clean_name, unit = extract_unit(product_name)
            
            # Extract product price with more specific selectors
            price_elem = container.select_one("div[data-testid='linkProductPrice']")
            if not price_elem:
                price_elem = container.select_one(".prd_link-product-price")
                
            product_price = price_elem.text.strip() if price_elem else "N/A"
            
            # Extract sales with more specific selectors
            sales_elem = container.select_one("span.prd_label-integrity")
            if not sales_elem:
                sales_elem = container.find("span", text=lambda t: t and 'terjual' in t)
                
            sales = clean_sales_number(sales_elem.text.strip() if sales_elem else "0")
            
            # Add to data list
            page_data.append({
                'Product Name': clean_name,
                'Unit': unit,
                'Price': product_price,
                'Sales': sales
            })
            
            print(f"Scraped product {idx}: {clean_name[:50]}...")
            
        except AttributeError as e:
            print(f"Error extracting product info for item {idx}: {e}")
            continue
    
    return page_data

def scrape_tokopedia(start_url, max_pages=None):
    """Scrape product information from Tokopedia using Firefox with pagination support"""
    all_data = []
    current_url = start_url
    page_num = 1
    
    try:
        options = webdriver.FirefoxOptions()
        options.add_argument("--start-maximized")
        
        driver = webdriver.Firefox(options=options)
        
        while current_url and (max_pages is None or page_num <= max_pages):
            print(f"\nScraping page {page_num}...")
            print(f"URL: {current_url}")
            
            driver.get(current_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "css-54k5sq")))
            
            print("Scrolling page to load all products...")
            scroll_to_bottom(driver)
            
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            page_data = scrape_page(driver, soup)
            all_data.extend(page_data)
            
            if not has_next_page(driver):
                print("No more pages available")
                break
                
            current_url = get_next_page_url(driver)
            page_num += 1
            
            # Add a delay between pages to be respectful to the server
            time.sleep(3)
            
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e
    
    finally:
        driver.quit()
        
    print(f"\nTotal products scraped across all pages: {len(all_data)}")
    return all_data

def save_to_csv(data, filename='tokopedia_products.csv'):
    """Save scraped data to CSV file"""
    if data:
        df = pd.DataFrame(data)
        
        # Clean up price column
        df['Price'] = df['Price'].str.replace('Rp', '').str.replace('.', '').astype(float)
        
        # Sort by sales volume
        df = df.sort_values('Sales', ascending=False)
        
        df.to_csv(filename, index=False)
        print(f"\nData saved to {filename}")
        print("\nAll scraped data:")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df)
        print(f"\nTotal rows in DataFrame: {len(df)}")
    else:
        print("No data to save")

def main():
    # Example usage with pagination
    start_url = ""
    # Set max_pages=None to scrape all pages, or specify a number to limit the pages
    scraped_data = scrape_tokopedia(start_url, max_pages=100)
    save_to_csv(scraped_data)

if __name__ == "__main__":
    main()