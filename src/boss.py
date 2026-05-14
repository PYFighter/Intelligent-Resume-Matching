# 自动化获取boss招聘网的信息
# 引入By Class，辅助元素定位
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from time import sleep
import pandas as pd
import undetected_chromedriver as uc
import random

#BOOS招聘网站
url = "https://www.zhipin.com/shanghai/"
#创建谷歌浏览器
browser = uc.Chrome()
#打开网页
browser.get(url=url)
#等待10秒钟，最好别访问太快
sleep(10)
# 选择搜索框
searching = browser.find_element(By.XPATH,
                                 '//input[@type="text" and @name="query" and @class="ipt-search" and @placeholder="搜索职位、公司"]')
# 输入金融，搜素金融相关的公司
searching.send_keys("金融")
# 点击搜索，通过回车点击
searching.send_keys(Keys.ENTER)
# 等待10秒
sleep(10)
#获取表格数据
#定义一个变量来判断循环的次数
num = 1
#定义一个空数组，后面用来存储数据
pd_lis = []
while True :
    #定位到岗位信息所在的li标签，通过num变量来确认获取哪一行的岗位信息
    mess = f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]'
    li = browser.find_element(By.XPATH,mess)
    # 指定职位等信息
    div_1 = li.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a')
    # 获取职位
    job_title = div_1.find_element(By.XPATH,
                                   f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-title clearfix"]/span[@class="job-name"]').text
    # 获取公司位置
    job_address = div_1.find_element(By.XPATH,
                                     f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-title clearfix"]/span[@class="job-area-wrapper"]/span[@class="job-area"]').text
    # 获取薪资
    salary = div_1.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-info clearfix"]/span[@class="salary"]').text
    # 确认工作经验所属位置
    work_experience = div_1.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-info clearfix"]/ul[@class="tag-list"]')
    # 获取学历和工作经验
    work_experience_lis = work_experience.find_elements(By.TAG_NAME, 'li')
    # 定义一个变量，用来拼接学历和工作经验，因为有的公司有两个信息，有的公司有三个信息，有的公司没有信息
    work_experience = ""
    for we_li in work_experience_lis:
        work_experience = work_experience + we_li.text if work_experience == "" else work_experience + '/' + we_li.text


    # 获取招聘人员加招聘人员职位
    recruiter_position = div_1.find_element(By.XPATH,
                                            f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-info clearfix"]/div[@class="info-public"]').text
    # 获取招聘人员职位
    position = div_1.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/a/div[@class="job-info clearfix"]/div[@class="info-public"]/em').text
    # 将招聘人员加招聘人员职位中剔除招聘人员职位,直接替换成空
    recruiter = recruiter_position.replace(position, "")

    # 指定公司信息
    div_2 = li.find_element(By.XPATH,
                            f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/div[@class="job-card-right"]/div[@class="company-info"]')
    # 公司名称
    company_name = div_2.find_element(By.TAG_NAME, 'h3').text
    # 获取公司类型/融资情况/人员规模
    company_type_ul = div_2.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]/div[@class="job-card-body clearfix"]/div[@class="job-card-right"]/div[@class="company-info"]/ul[@class="company-tag-list"]')
    company_type_lis = company_type_ul.find_elements(By.TAG_NAME, 'li')
    company_join = ""
    for company in company_type_lis:
        #获取公司类型/融资情况/人员规模
        company_join = company_join + company.text if company_join == "" else company_join + '/' + company.text

    # 获取公司对职位的要求ul标签
    company_requirements_ul = li.find_element(By.XPATH,
                                              f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]//div[@class="job-card-footer clearfix"]/ul[@class="tag-list"]')
    # 获取公司对职位的要求li标签
    company_requirements_lis = company_requirements_ul.find_elements(By.TAG_NAME, "li")
    company_requirements = ""
    for company_requirements_li in company_requirements_lis:
        #公司对职位的要
        company_requirements = company_requirements + company_requirements_li.text if company_requirements == "" else company_requirements + '/' + company_requirements_li.text
    # 获取公司福利
    company_benefits = li.find_element(By.XPATH, f'//div[@class="search-job-result"]/ul[@class="job-list-box"]/li[@ka="search_list_{num}"]//div[@class="job-card-footer clearfix"]/div').text
    '''
    job_title 职位 - 
    job_address 公司位置
    salary 薪资 - 
    work_experience 学历工作经验
    recruiter 招聘人
    position 招聘人所属职位
    company_name 公司名称
    company_join 公司类型/融资情况/人员规模
    company_requirements 公司要求
    company_benefits 公司福利
    '''
    pd_lis.append([company_name,job_title,salary, job_address, work_experience, recruiter, position, company_join,
                   company_requirements, company_benefits])
    if num % 30 == 0:
        if num == 300:
            df = pd.DataFrame(data=pd_lis,
                              columns=['公司名称','招聘职位', '薪资区间', '公司位置', '要求的学历/工作经验', '招聘人', '招聘人所属职位',
                                       '公司类型/融资情况/人员规模', '公司要求', '公司福利'])
            df.to_csv('/xxxxx/recruitment.csv')#自己本地的路径
            browser.close()
            browser.quit()
        else :
            #获取a标签下最后一个a标签，那个就是点击下一页
            page = browser.find_elements(By.XPATH,'//div[@class="options-pages"]/a')
            last_page = page[-1]
            #点击下一页
            last_page.click()
    num += 1
    sleep(random.randint(1,15))