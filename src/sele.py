import csv
import time
import random
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

# ==================== 扩展关键词（150个，多行业覆盖） ====================
KEYWORDS = [
    # IT / 互联网（25个）
    "Python 开发", "Java 开发", "前端开发", "后端开发", "数据分析",
    "产品经理", "UI 设计", "UX 设计", "软件测试", "运维工程师",
    "算法工程师", "网络安全", "嵌入式开发", "游戏开发", "区块链",
    "数据分析师", "大数据开发", "ETL工程师", "技术经理", "架构师",
    "React 开发", "Vue 开发", "Android 开发", "iOS 开发", "Flutter 开发",
    # 金融 / 财会（20个）
    "会计", "财务分析", "审计", "投资经理", "风控",
    "保险", "证券", "银行柜员", "理财顾问", "信贷员",
    "投后管理", "基金经理", "量化分析", "资产评估", "税务专员",
    "金融产品经理", "融资租赁", "担保", "清算", "合规",
    # 市场 / 运营 / 销售（20个）
    "市场营销", "新媒体运营", "电商运营", "销售代表", "客户经理",
    "品牌策划", "商务拓展", "渠道销售", "电话销售", "网络销售",
    "市场调研", "活动策划", "广告投放", "SEM专员", "SEO专员",
    "社群运营", "内容运营", "直播运营", "短视频运营", "公众号运营",
    # 制造 / 工程 / 技术（15个）
    "机械工程师", "电气工程师", "自动化", "质量管理", "生产主管",
    "工艺工程师", "材料工程师", "结构工程师", "模具设计", "CNC编程",
    "机器人工程师", "PLC工程师", "焊接工程师", "涂装工程师", "装配工",
    # 医药 / 健康（10个）
    "医药代表", "临床研究", "护士", "医生", "药剂师",
    "医疗器械销售", "药品注册", "生物工程", "医学编辑", "营养师",
    # 教育 / 培训（10个）
    "教师", "课程顾问", "教务管理", "培训讲师", "在线教育",
    "英语老师", "数学老师", "舞蹈老师", "书法老师", "早教老师",
    # 地产 / 建筑（10个）
    "房地产销售", "工程造价", "土木工程", "室内设计", "施工员",
    "项目经理", "资料员", "安全员", "监理工程师", "规划设计师",
    # 物流 / 供应链（8个）
    "物流专员", "外贸业务员", "采购专员", "仓储管理", "供应链专员",
    "快递员", "货运代理", "报关员",
    # 设计 / 创意（8个）
    "平面设计", "视频剪辑", "文案策划", "原画师", "动画师",
    "视觉设计", "包装设计", "插画师",
    # 人力资源 / 行政 / 法务（10个）
    "人力资源", "行政专员", "法务", "招聘专员", "薪酬福利",
    "员工关系", "行政前台", "文秘", "合同管理", "法务助理",
    # 客服 / 支持（8个）
    "客服专员", "技术支持", "售后工程师", "投诉处理", "在线客服",
    "呼叫中心", "客服主管", "售前支持",
    # 餐饮 / 零售 / 服务业（8个）
    "店长", "厨师", "零售管理", "收银员", "餐厅经理",
    "美容师", "健身教练", "导游",
    # 能源 / 环保（4个）
    "能源管理", "光伏工程师", "环保工程师", "水处理工程师",
    # 传媒 / 广告（4个）
    "记者", "编辑", "广告策划", "媒介专员"
]

MAX_PAGES_PER_KEYWORD = 5          # 每个关键词抓取5页
LIST_PAGE_WAIT = (4, 6)            # 列表页等待范围
DETAIL_PAGE_WAIT = (3, 5)          # 详情页等待范围
BETWEEN_KEYWORDS_WAIT = (8, 12)    # 关键词间等待
BETWEEN_PAGES_WAIT = (3, 5)        # 翻页等待

# ==================== 连接已打开的浏览器 ====================
opt = Options()
opt.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
    driver = webdriver.Chrome(options=opt)
    print(">>> 浏览器连接成功！")
except Exception as e:
    print(f">>> 浏览器连接失败：{e}")
    print('请先启动带调试端口的 Chrome：')
    print('& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\chrome_debug"')
    exit()

# ==================== 准备CSV文件 ====================
csv_file = open('liepin_10k.csv', 'w', encoding='utf-8-sig', newline='')
writer = csv.DictWriter(csv_file, fieldnames=[
    '搜索关键词', '职位', '薪资', '公司', '地点', '经验/学历',
    '公司标签', '公司规模', '公司行业', '融资阶段'
])
writer.writeheader()

total_all_jobs = 0

def click_next_page():
    """自动点击下一页，返回是否成功"""
    next_selectors = [
        '.pagination__next',
        '.next-page',
        '.ant-pagination-next',
        '.pagination .next:not(.disabled)',
    ]
    for sel in next_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            class_attr = btn.get_attribute("class") or ""
            aria_label = btn.get_attribute("aria-label") or ""
            if "disabled" in class_attr or "disabled" in aria_label:
                continue
            btn.click()
            return True
        except NoSuchElementException:
            continue
    return False

def fetch_company_detail(detail_url):
    """访问详情页提取公司信息"""
    info = {
        '公司标签': '',
        '公司规模': '',
        '公司行业': '',
        '融资阶段': ''
    }
    try:
        driver.get(detail_url)
        time.sleep(random.uniform(*DETAIL_PAGE_WAIT))
        html = driver.page_source
        if not html:
            return info

        soup = BeautifulSoup(html, 'html.parser')

        tag_container = soup.find('div', class_='company-tags')
        if tag_container:
            tags = [t.get_text(strip=True) for t in tag_container.find_all('span')]
            info['公司标签'] = '/'.join(tags)

        intro_ul = soup.find('ul', class_='new-compintro')
        if intro_ul:
            for li in intro_ul.find_all('li'):
                text = li.get_text(strip=True)
                if '规模' in text or '人数' in text:
                    info['公司规模'] = text.split('：')[-1] if '：' in text else text
                elif '行业' in text:
                    info['公司行业'] = text.split('：')[-1] if '：' in text else text
                elif '融资' in text:
                    info['融资阶段'] = text.split('：')[-1] if '：' in text else text

        if not info['公司行业']:
            industry_ele = soup.find('li', string=lambda s: s and '行业' in s)
            if industry_ele:
                info['公司行业'] = industry_ele.get_text(strip=True).replace('行业：', '')

    except Exception as e:
        print(f"    详情页解析出错 ({detail_url}): {e}")

    return info

# ==================== 主循环 ====================
print("\n>>> 脚本将在5秒后开始全自动抓取，请确保浏览器已登录猎聘。")
print(">>> 预计抓取约1万条数据，耗时可能较长，请耐心等待。")
time.sleep(5)

for keyword_idx, keyword in enumerate(KEYWORDS, 1):
    print("\n" + "=" * 50)
    print(f">>> [{keyword_idx}/{len(KEYWORDS)}] 正在处理：{keyword}")
    print("=" * 50)

    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}"
    driver.get(search_url)
    time.sleep(random.uniform(*LIST_PAGE_WAIT))

    if keyword_idx == 1:
        print(">>> 首次运行，请确认已登录。10秒后自动开始...")
        time.sleep(10)

    keyword_job_count = 0
    jobs_data = []

    # ---- 列表页抓取 ----
    for page_num in range(1, MAX_PAGES_PER_KEYWORD + 1):
        print(f"  [第 {page_num} 页] 抓取列表...", end="", flush=True)
        time.sleep(random.uniform(*LIST_PAGE_WAIT))

        html = driver.page_source
        if not html:
            print(" ❌ 页面源码获取失败")
            break

        soup = BeautifulSoup(html, 'html.parser')
        job_cards = []
        card_selectors = [
            ('div', 'job-card-item'),
            ('li', 'job-list-item'),
            ('div', 'job-recommend-card'),
            ('div', 'job-search-card'),
            ('div', 'job-card'),
        ]
        for tag, class_name in card_selectors:
            job_cards = soup.find_all(tag, class_=lambda x: x and class_name in x if x else False)
            if job_cards:
                break

        if not job_cards:
            print(" ⚠️ 未找到卡片，跳过本页")
            break

        page_count = 0
        for card in job_cards:
            try:
                a_tag = card.find('a', href=True)
                detail_link = urljoin("https://www.liepin.com", a_tag['href']) if a_tag else ""

                job_elem = card.find('div', class_='ellipsis-1', title=True)
                if not job_elem:
                    job_elem = card.find('div', title=True)
                job_name = job_elem.get('title', '').strip() if job_elem else ''
                if not job_name and job_elem:
                    job_name = job_elem.get_text(strip=True)
                if not job_name:
                    continue

                location = ''
                loc_spans = card.find_all('span', class_='ellipsis-1')
                for span in loc_spans:
                    text = span.get_text(strip=True)
                    if '【' in text and '】' in text:
                        location = text.replace('【', '').replace('】', '').strip()
                        break

                salary = ''
                all_spans = card.find_all('span')
                for span in all_spans:
                    text = span.get_text(strip=True)
                    if text and any(ch.isdigit() for ch in text) and ('k' in text.lower() or '薪' in text):
                        salary = text
                        break

                company = ''
                company_elem = card.find(['a', 'span', 'div'], class_=lambda x: x and any(k in x for k in ['company-name', 'company', 'corp-name']))
                if not company_elem:
                    company_elem = card.find('a', href=True)
                company = company_elem.get_text(strip=True) if company_elem else ''

                exp_req = ''
                tag_texts = []
                for span in all_spans:
                    cls = span.get('class', [])
                    if cls and any('_' in c and any(ch.isdigit() for ch in c) for c in cls):
                        text = span.get_text(strip=True)
                        if text and text != salary and text != location and '【' not in text and text != company:
                            tag_texts.append(text)
                if tag_texts:
                    unique_tags = list(dict.fromkeys(tag_texts))
                    exp_req = '/'.join(unique_tags)

                jobs_data.append({
                    '搜索关键词': keyword,
                    '职位': job_name,
                    '薪资': salary,
                    '公司': company,
                    '地点': location,
                    '经验/学历': exp_req,
                    'detail_url': detail_link
                })
                page_count += 1
            except:
                continue

        keyword_job_count += page_count
        print(f" 获取 {page_count} 条")

        if page_num == MAX_PAGES_PER_KEYWORD:
            break
        if not click_next_page():
            print("  没有下一页了，提前结束")
            break
        time.sleep(random.uniform(*BETWEEN_PAGES_WAIT))

    # ---- 补充公司详情 ----
    print(f"    开始补充 {len(jobs_data)} 条职位的公司详情...")
    for idx, job in enumerate(jobs_data, 1):
        detail_url = job.pop('detail_url', '')
        if not detail_url:
            continue
        print(f"    [{idx}/{len(jobs_data)}] {job['职位'][:20]}...", end="", flush=True)
        company_info = fetch_company_detail(detail_url)
        job.update(company_info)
        writer.writerow(job)
        print(" ✓")
        time.sleep(random.uniform(1.5, 3))

    total_all_jobs += keyword_job_count
    print(f">>> 关键词 '{keyword}' 完成，共 {keyword_job_count} 条。累计 {total_all_jobs} 条。")

    if keyword_idx < len(KEYWORDS):
        wait = random.uniform(*BETWEEN_KEYWORDS_WAIT)
        print(f">>> 休息 {wait:.1f} 秒后继续...")
        time.sleep(wait)

csv_file.close()
print("\n" + "=" * 50)
print(f">>> 🎉 全自动抓取完成！总计 {total_all_jobs} 条数据，保存于 liepin_10k.csv")
print("=" * 50)