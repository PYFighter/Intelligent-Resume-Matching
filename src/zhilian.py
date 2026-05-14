import csv
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

# ==================== 配置区 ====================
KEYWORDS = [
    "Python 开发", "Java 开发", "前端开发", "数据分析", "产品经理",
    "UI 设计", "软件测试", "运维工程师", "算法工程师", "网络安全",
    "销售代表", "客户经理", "市场营销", "品牌策划", "商务拓展",
    "渠道销售", "电话销售", "外贸业务员", "行政专员", "人力资源",
    "会计", "财务分析", "出纳", "招聘专员", "培训专员", "总裁助理",
    "投资经理", "风控", "保险顾问", "证券分析师", "理财顾问",
    "医药代表", "护士", "医生", "药剂师", "临床研究", "教师",
    "课程顾问", "教务管理", "培训讲师", "留学顾问", "物流专员",
    "采购专员", "仓储管理", "供应链专员", "平面设计", "新媒体运营",
    "文案策划", "视频剪辑", "室内设计", "法务", "翻译", "房地产销售",
    "物业管理", "客服专员"
]
MAX_PAGES_PER_KEYWORD = 2          # 每个关键词抓取页数（可调整）
PAGE_LOAD_WAIT = (5, 8)            # 页面加载等待范围（秒）
BETWEEN_KEYWORDS_WAIT = (5, 8)     # 关键词切换等待范围
BETWEEN_PAGES_WAIT = (3, 5)        # 翻页等待范围

CSV_FILE = 'zhaopin_auto_all.csv'
FIELD_NAMES = ['搜索关键词', '职位', '薪资', '公司', '地点', '经验/学历', 'URL']

# ==================== 浏览器连接 ====================
def get_selenium_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=opts)
        print(">>> 成功连接到已有浏览器会话！")
        return driver
    except Exception as e:
        print(f">>> 连接失败：{e}，将启动新浏览器，请手动登录...")
        user_data_dir = "C:\\selenium_profile_zhaopin"
        opts = Options()
        opts.add_argument(f"--user-data-dir={user_data_dir}")
        driver = webdriver.Chrome(options=opts)
        input(">>> 登录智联招聘后按回车继续...")
        return driver

# ==================== 翻页功能（修复版） ====================
def click_next_page(driver):
    """点击下一页按钮，返回是否成功"""
    # 优先匹配智联招聘的 .soupager__btn 且未禁用
    try:
        # 等待下一页按钮可点击（排除禁用状态）
        next_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.soupager__btn:not(.soupager__btn--disable)"))
        )
        if "下一页" in next_btn.text:
            next_btn.click()
            time.sleep(random.uniform(3, 5))
            return True
    except (TimeoutException, NoSuchElementException):
        pass
    
    # 备选选择器（兼容其他可能）
    next_selectors = [
        "a.soupager__btn",
        ".pagination__next a",
        "a[aria-label='下一页']",
        "a.next",
        "li.pagination-item-next a",
        "button.pagination__next"
    ]
    for selector in next_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            class_attr = btn.get_attribute("class") or ""
            if "disabled" in class_attr or "soupager__btn--disable" in class_attr:
                continue
            btn.click()
            time.sleep(random.uniform(2, 4))
            return True
        except:
            continue
    return False

# ==================== 卡片解析（获取公司名） ====================
def parse_job_card(card_soup, keyword, driver):
    # 职位名称
    job_elem = card_soup.select_one('a.jobinfo__name')
    if not job_elem:
        return None
    job_name = job_elem.get_text(strip=True)
    if not job_name:
        return None

    # 薪资
    salary_elem = card_soup.select_one('p.jobinfo__salary')
    salary = salary_elem.get_text(strip=True) if salary_elem else ''

    # 地点、经验/学历
    location = ''
    exp_edu = ''
    other_items = card_soup.select('.jobinfo__other-info-item')
    for item in other_items:
        text = item.get_text(strip=True)
        if '·' in text and not any(k in text for k in ['经验', '学历', '年']):
            location = text
        elif any(k in text for k in ['经验', '学历', '年', '本科', '大专', '硕士', '不限']):
            if exp_edu:
                exp_edu += '/' + text
            else:
                exp_edu = text

    if not exp_edu:
        tags = card_soup.select('.joblist-box__item-tag')
        for tag in tags:
            txt = tag.get_text(strip=True)
            if any(k in txt for k in ['经验', '学历', '本科', '大专', '硕士', '不限']):
                exp_edu = txt
                break

    # 岗位URL
    job_url = ''
    href = job_elem.get('href')
    if href:
        if href.startswith('//'):
            job_url = 'https:' + href
        elif href.startswith('/'):
            job_url = 'https://sou.zhaopin.com' + href
        else:
            job_url = href

    # 获取公司名（在当前窗口跳转）
    company = ''
    if job_url:
        original_url = driver.current_url
        try:
            driver.get(job_url)
            time.sleep(random.uniform(2, 4))
            selectors = [
                ".company-name a",
                ".company-name",
                ".company-title",
                "h2.company-name",
                ".company-info a",
                ".job-header__company a"
            ]
            for sel in selectors:
                try:
                    company_elem = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    company = company_elem.get_text(strip=True)
                    if company:
                        break
                except:
                    continue
            if not company:
                page_source = driver.page_source
                match = re.search(r'([\u4e00-\u9fa5]{2,30}(?:有限公司|公司|集团|股份))', page_source)
                if match:
                    company = match.group(1)
        except Exception as e:
            print(f"      警告：获取公司名失败 - {job_url}，错误：{e}")
        finally:
            driver.get(original_url)
            time.sleep(random.uniform(2, 3))

    return {
        '搜索关键词': keyword,
        '职位': job_name,
        '薪资': salary,
        '公司': company,
        '地点': location,
        '经验/学历': exp_edu,
        'URL': job_url
    }

# ==================== 主爬取函数 ====================
def scrape_zhaopin():
    driver = get_selenium_driver()
    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()

    total = 0
    for idx, keyword in enumerate(KEYWORDS, 1):
        print(f"\n>>> [{idx}/{len(KEYWORDS)}] 关键词：{keyword}")
        search_url = f"https://sou.zhaopin.com/jobs/searchresult.ashx?kw={keyword}&sm=0"
        driver.get(search_url)
        time.sleep(random.uniform(*PAGE_LOAD_WAIT))

        for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
            print(f"  第 {page} 页 ...")
            # 确保在列表页
            if "searchresult" not in driver.current_url:
                driver.get(search_url)
                time.sleep(random.uniform(*PAGE_LOAD_WAIT))

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('div.joblist-box__item')
            if not cards:
                print("      未找到职位卡片，跳过本页")
                break

            page_count = 0
            for card in cards:
                try:
                    job_data = parse_job_card(card, keyword, driver)
                    if job_data and job_data['职位']:
                        with open(CSV_FILE, 'a', encoding='utf-8-sig', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
                            writer.writerow(job_data)
                        page_count += 1
                        print(f"        已抓取：{job_data['职位']} | 公司：{job_data['公司']}")
                except Exception as e:
                    print(f"      处理卡片时出错：{e}")
                    continue
                time.sleep(random.uniform(1, 2))

            print(f"      本页抓取 {page_count} 条")
            total += page_count

            if page == MAX_PAGES_PER_KEYWORD:
                break
            if not click_next_page(driver):
                print("      没有下一页或翻页失败，提前结束")
                break
            time.sleep(random.uniform(*BETWEEN_PAGES_WAIT))

        if idx < len(KEYWORDS):
            wait = random.uniform(*BETWEEN_KEYWORDS_WAIT)
            print(f"休息 {wait:.1f} 秒...")
            time.sleep(wait)

    driver.quit()
    print(f"\n完成！共抓取 {total} 条，保存至 {CSV_FILE}")

if __name__ == "__main__":
    scrape_zhaopin()