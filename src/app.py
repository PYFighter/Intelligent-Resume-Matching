import streamlit as st
import pandas as pd
import PyPDF2
from docx import Document
from zhipuai import ZhipuAI
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==================== 页面配置 ====================
st.set_page_config(page_title="智能简历匹配与自动投递系统", layout="wide")
st.title("🤖 智能简历匹配 + 一键自动投递")
st.markdown("上传简历 → AI 匹配岗位 → 一键自动投递（浏览器会自动打开，首次需手动登录猎聘）")

# ==================== 初始化大模型客户端 ====================
API_KEY = ""  #需要输入API_KEY
client = ZhipuAI(api_key=API_KEY)

# ==================== 全国行政区划数据（修正版，直辖市使用正确城市名） ====================
CHINA_REGIONS = {
    "北京市": {
        "北京市": ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区", "通州区", "昌平区", "大兴区", "顺义区", "房山区", "门头沟区", "平谷区", "密云区", "怀柔区", "延庆区"]
    },
    "天津市": {
        "天津市": ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区", "东丽区", "西青区", "津南区", "北辰区", "武清区", "宝坻区", "宁河区", "静海区", "蓟州区"]
    },
    "上海市": {
        "上海市": ["黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区", "松江区", "青浦区", "奉贤区", "崇明区"]
    },
    "重庆市": {
        "重庆市": ["渝中区", "江北区", "沙坪坝区", "九龙坡区", "南岸区", "北碚区", "渝北区", "巴南区", "万州区", "涪陵区", "黔江区", "长寿区", "江津区", "合川区", "永川区", "南川区", "璧山区", "铜梁区", "潼南区", "荣昌区", "开州区", "梁平区", "武隆区"]
    },
    "河北省": {
        "石家庄市": ["长安区", "桥西区", "新华区", "裕华区", "藁城区", "鹿泉区", "栾城区"],
        "唐山市": ["路南区", "路北区", "古冶区", "开平区", "丰南区", "丰润区", "曹妃甸区"],
        "秦皇岛市": ["海港区", "山海关区", "北戴河区", "抚宁区"],
        "邯郸市": ["邯山区", "丛台区", "复兴区", "峰峰矿区", "肥乡区", "永年区"],
        "邢台市": ["襄都区", "信都区", "任泽区", "南和区"],
        "保定市": ["竞秀区", "莲池区", "满城区", "清苑区", "徐水区"],
        "张家口市": ["桥东区", "桥西区", "宣化区", "下花园区", "万全区", "崇礼区"],
        "承德市": ["双桥区", "双滦区", "鹰手营子矿区"],
        "沧州市": ["运河区", "新华区"],
        "廊坊市": ["安次区", "广阳区"],
        "衡水市": ["桃城区", "冀州区"]
    },
    "山西省": {
        "太原市": ["杏花岭区", "小店区", "迎泽区", "尖草坪区", "万柏林区", "晋源区"],
        "大同市": ["平城区", "云冈区", "新荣区", "云州区"],
        "阳泉市": ["城区", "矿区", "郊区"],
        "长治市": ["潞州区", "上党区", "屯留区", "潞城区"],
        "晋城市": ["城区"],
        "朔州市": ["朔城区", "平鲁区"],
        "晋中市": ["榆次区", "太谷区"],
        "运城市": ["盐湖区"],
        "忻州市": ["忻府区"],
        "临汾市": ["尧都区"],
        "吕梁市": ["离石区"]
    },
    "内蒙古自治区": {
        "呼和浩特市": ["新城区", "回民区", "玉泉区", "赛罕区"],
        "包头市": ["昆都仑区", "青山区", "东河区", "九原区", "石拐区"],
        "乌海市": ["海勃湾区", "海南区", "乌达区"],
        "赤峰市": ["红山区", "元宝山区", "松山区"],
        "通辽市": ["科尔沁区"],
        "鄂尔多斯市": ["东胜区", "康巴什区"],
        "呼伦贝尔市": ["海拉尔区"],
        "巴彦淖尔市": ["临河区"],
        "乌兰察布市": ["集宁区"]
    },
    "辽宁省": {
        "沈阳市": ["和平区", "沈河区", "大东区", "皇姑区", "铁西区", "苏家屯区", "浑南区", "沈北新区", "于洪区", "辽中区"],
        "大连市": ["中山区", "西岗区", "沙河口区", "甘井子区", "旅顺口区", "金州区", "普兰店区"],
        "鞍山市": ["铁东区", "铁西区", "立山区", "千山区"],
        "抚顺市": ["新抚区", "望花区", "东洲区", "顺城区"],
        "本溪市": ["平山区", "明山区", "溪湖区", "南芬区"],
        "丹东市": ["元宝区", "振兴区", "振安区"],
        "锦州市": ["古塔区", "凌河区", "太和区"],
        "营口市": ["站前区", "西市区", "鲅鱼圈区", "老边区"],
        "阜新市": ["海州区", "细河区", "太平区"],
        "辽阳市": ["白塔区", "文圣区", "宏伟区", "弓长岭区", "太子河区"],
        "盘锦市": ["双台子区", "兴隆台区", "大洼区"],
        "铁岭市": ["银州区", "清河区"],
        "朝阳市": ["双塔区", "龙城区"],
        "葫芦岛市": ["连山区", "龙港区", "南票区"]
    },
    "吉林省": {
        "长春市": ["南关区", "宽城区", "朝阳区", "二道区", "绿园区", "双阳区", "九台区"],
        "吉林市": ["昌邑区", "龙潭区", "船营区", "丰满区"],
        "四平市": ["铁西区", "铁东区"],
        "辽源市": ["龙山区", "西安区"],
        "通化市": ["东昌区", "二道江区"],
        "白山市": ["浑江区", "江源区"],
        "松原市": ["宁江区"],
        "白城市": ["洮北区"]
    },
    "黑龙江省": {
        "哈尔滨市": ["道里区", "南岗区", "道外区", "平房区", "松北区", "香坊区", "呼兰区", "阿城区", "双城区"],
        "齐齐哈尔市": ["龙沙区", "建华区", "铁锋区", "昂昂溪区", "富拉尔基区", "碾子山区", "梅里斯达斡尔族区"],
        "鸡西市": ["鸡冠区", "恒山区", "滴道区", "梨树区", "城子河区", "麻山区"],
        "鹤岗市": ["向阳区", "工农区", "南山区", "兴安区", "东山区", "兴山区"],
        "双鸭山市": ["尖山区", "岭东区", "四方台区", "宝山区"],
        "大庆市": ["萨尔图区", "龙凤区", "让胡路区", "红岗区", "大同区"],
        "伊春市": ["伊美区", "乌翠区", "友好区", "金林区"],
        "佳木斯市": ["向阳区", "前进区", "东风区", "郊区"],
        "七台河市": ["新兴区", "桃山区", "茄子河区"],
        "牡丹江市": ["东安区", "阳明区", "爱民区", "西安区"],
        "黑河市": ["爱辉区"],
        "绥化市": ["北林区"]
    },
    "江苏省": {
        "南京市": ["玄武区", "秦淮区", "建邺区", "鼓楼区", "浦口区", "栖霞区", "雨花台区", "江宁区", "六合区", "溧水区", "高淳区"],
        "无锡市": ["锡山区", "惠山区", "滨湖区", "梁溪区", "新吴区"],
        "徐州市": ["鼓楼区", "云龙区", "贾汪区", "泉山区", "铜山区"],
        "常州市": ["天宁区", "钟楼区", "新北区", "武进区", "金坛区"],
        "苏州市": ["虎丘区", "吴中区", "相城区", "姑苏区", "吴江区"],
        "南通市": ["崇川区", "港闸区", "通州区", "海门区"],
        "连云港市": ["连云区", "海州区", "赣榆区"],
        "淮安市": ["淮安区", "淮阴区", "清江浦区", "洪泽区"],
        "盐城市": ["亭湖区", "盐都区", "大丰区"],
        "扬州市": ["广陵区", "邗江区", "江都区"],
        "镇江市": ["京口区", "润州区", "丹徒区"],
        "泰州市": ["海陵区", "高港区", "姜堰区"],
        "宿迁市": ["宿城区", "宿豫区"]
    },
    "浙江省": {
        "杭州市": ["上城区", "拱墅区", "西湖区", "滨江区", "萧山区", "余杭区", "富阳区", "临安区", "钱塘区"],
        "宁波市": ["海曙区", "江北区", "北仑区", "镇海区", "鄞州区", "奉化区"],
        "温州市": ["鹿城区", "龙湾区", "瓯海区", "洞头区"],
        "嘉兴市": ["南湖区", "秀洲区"],
        "湖州市": ["吴兴区", "南浔区"],
        "绍兴市": ["越城区", "柯桥区", "上虞区"],
        "金华市": ["婺城区", "金东区"],
        "衢州市": ["柯城区", "衢江区"],
        "舟山市": ["定海区", "普陀区"],
        "台州市": ["椒江区", "黄岩区", "路桥区"],
        "丽水市": ["莲都区"]
    },
    "安徽省": {
        "合肥市": ["瑶海区", "庐阳区", "蜀山区", "包河区"],
        "芜湖市": ["镜湖区", "弋江区", "鸠江区", "三山区"],
        "蚌埠市": ["龙子湖区", "蚌山区", "禹会区", "淮上区"],
        "淮南市": ["大通区", "田家庵区", "谢家集区", "八公山区", "潘集区"],
        "马鞍山市": ["花山区", "雨山区", "博望区"],
        "淮北市": ["相山区", "杜集区", "烈山区"],
        "铜陵市": ["铜官区", "义安区", "郊区"],
        "安庆市": ["迎江区", "大观区", "宜秀区"],
        "黄山市": ["屯溪区", "黄山区", "徽州区"],
        "滁州市": ["琅琊区", "南谯区"],
        "阜阳市": ["颍州区", "颍东区", "颍泉区"],
        "宿州市": ["埇桥区"],
        "六安市": ["金安区", "裕安区", "叶集区"],
        "亳州市": ["谯城区"],
        "池州市": ["贵池区"],
        "宣城市": ["宣州区"]
    },
    "福建省": {
        "福州市": ["鼓楼区", "台江区", "仓山区", "马尾区", "晋安区", "长乐区"],
        "厦门市": ["思明区", "海沧区", "湖里区", "集美区", "同安区", "翔安区"],
        "莆田市": ["城厢区", "涵江区", "荔城区", "秀屿区"],
        "三明市": ["三元区", "沙县区"],
        "泉州市": ["鲤城区", "丰泽区", "洛江区", "泉港区"],
        "漳州市": ["芗城区", "龙文区", "龙海区"],
        "南平市": ["延平区", "建阳区"],
        "龙岩市": ["新罗区", "永定区"],
        "宁德市": ["蕉城区"]
    },
    "江西省": {
        "南昌市": ["东湖区", "西湖区", "青云谱区", "青山湖区", "新建区", "红谷滩区"],
        "景德镇市": ["昌江区", "珠山区"],
        "萍乡市": ["安源区", "湘东区"],
        "九江市": ["濂溪区", "浔阳区", "柴桑区"],
        "新余市": ["渝水区"],
        "鹰潭市": ["月湖区", "余江区"],
        "赣州市": ["章贡区", "南康区", "赣县区"],
        "吉安市": ["吉州区", "青原区"],
        "宜春市": ["袁州区"],
        "抚州市": ["临川区", "东乡区"],
        "上饶市": ["信州区", "广丰区", "广信区"]
    },
    "山东省": {
        "济南市": ["历下区", "市中区", "槐荫区", "天桥区", "历城区", "长清区", "章丘区", "济阳区", "莱芜区", "钢城区"],
        "青岛市": ["市南区", "市北区", "黄岛区", "崂山区", "李沧区", "城阳区", "即墨区"],
        "淄博市": ["淄川区", "张店区", "博山区", "临淄区", "周村区"],
        "枣庄市": ["市中区", "薛城区", "峄城区", "台儿庄区", "山亭区"],
        "东营市": ["东营区", "河口区", "垦利区"],
        "烟台市": ["芝罘区", "福山区", "牟平区", "莱山区", "蓬莱区"],
        "潍坊市": ["潍城区", "寒亭区", "坊子区", "奎文区"],
        "济宁市": ["任城区", "兖州区"],
        "泰安市": ["泰山区", "岱岳区"],
        "威海市": ["环翠区", "文登区"],
        "日照市": ["东港区", "岚山区"],
        "临沂市": ["兰山区", "罗庄区", "河东区"],
        "德州市": ["德城区", "陵城区"],
        "聊城市": ["东昌府区", "茌平区"],
        "滨州市": ["滨城区", "沾化区"],
        "菏泽市": ["牡丹区", "定陶区"]
    },
    "河南省": {
        "郑州市": ["中原区", "二七区", "管城回族区", "金水区", "上街区", "惠济区"],
        "开封市": ["龙亭区", "顺河回族区", "鼓楼区", "禹王台区", "祥符区"],
        "洛阳市": ["老城区", "西工区", "瀍河回族区", "涧西区", "洛龙区"],
        "平顶山市": ["新华区", "卫东区", "石龙区", "湛河区"],
        "安阳市": ["文峰区", "北关区", "殷都区", "龙安区"],
        "鹤壁市": ["鹤山区", "山城区", "淇滨区"],
        "新乡市": ["红旗区", "卫滨区", "凤泉区", "牧野区"],
        "焦作市": ["解放区", "中站区", "马村区", "山阳区"],
        "濮阳市": ["华龙区"],
        "许昌市": ["魏都区", "建安区"],
        "漯河市": ["源汇区", "郾城区", "召陵区"],
        "三门峡市": ["湖滨区", "陕州区"],
        "南阳市": ["宛城区", "卧龙区"],
        "商丘市": ["梁园区", "睢阳区"],
        "信阳市": ["浉河区", "平桥区"],
        "周口市": ["川汇区", "淮阳区"],
        "驻马店市": ["驿城区"]
    },
    "湖北省": {
        "武汉市": ["江岸区", "江汉区", "硚口区", "汉阳区", "武昌区", "青山区", "洪山区", "东西湖区", "汉南区", "蔡甸区", "江夏区", "黄陂区", "新洲区"],
        "黄石市": ["黄石港区", "西塞山区", "下陆区", "铁山区"],
        "十堰市": ["茅箭区", "张湾区", "郧阳区"],
        "宜昌市": ["西陵区", "伍家岗区", "点军区", "猇亭区", "夷陵区"],
        "襄阳市": ["襄城区", "樊城区", "襄州区"],
        "鄂州市": ["梁子湖区", "华容区", "鄂城区"],
        "荆门市": ["东宝区", "掇刀区"],
        "孝感市": ["孝南区"],
        "荆州市": ["沙市区", "荆州区"],
        "黄冈市": ["黄州区"],
        "咸宁市": ["咸安区"],
        "随州市": ["曾都区"]
    },
    "湖南省": {
        "长沙市": ["芙蓉区", "天心区", "岳麓区", "开福区", "雨花区", "望城区"],
        "株洲市": ["荷塘区", "芦淞区", "石峰区", "天元区", "渌口区"],
        "湘潭市": ["雨湖区", "岳塘区"],
        "衡阳市": ["珠晖区", "雁峰区", "石鼓区", "蒸湘区", "南岳区"],
        "邵阳市": ["双清区", "大祥区", "北塔区"],
        "岳阳市": ["岳阳楼区", "云溪区", "君山区"],
        "常德市": ["武陵区", "鼎城区"],
        "张家界市": ["永定区", "武陵源区"],
        "益阳市": ["资阳区", "赫山区"],
        "郴州市": ["北湖区", "苏仙区"],
        "永州市": ["零陵区", "冷水滩区"],
        "怀化市": ["鹤城区"],
        "娄底市": ["娄星区"]
    },
    "广东省": {
        "广州市": ["荔湾区", "越秀区", "海珠区", "天河区", "白云区", "黄埔区", "番禺区", "花都区", "南沙区", "从化区", "增城区"],
        "深圳市": ["罗湖区", "福田区", "南山区", "宝安区", "龙岗区", "盐田区", "龙华区", "坪山区", "光明区"],
        "珠海市": ["香洲区", "斗门区", "金湾区"],
        "汕头市": ["龙湖区", "金平区", "濠江区", "潮阳区", "潮南区", "澄海区"],
        "佛山市": ["禅城区", "南海区", "顺德区", "三水区", "高明区"],
        "江门市": ["蓬江区", "江海区", "新会区"],
        "湛江市": ["赤坎区", "霞山区", "坡头区", "麻章区"],
        "茂名市": ["茂南区", "电白区"],
        "肇庆市": ["端州区", "鼎湖区", "高要区"],
        "惠州市": ["惠城区", "惠阳区"],
        "梅州市": ["梅江区", "梅县区"],
        "汕尾市": ["城区"],
        "河源市": ["源城区"],
        "阳江市": ["江城区", "阳东区"],
        "清远市": ["清城区", "清新区"],
        "东莞市": ["莞城街道", "东城街道", "南城街道", "万江街道", "松山湖"],
        "中山市": ["石岐街道", "东区街道", "西区街道", "南区街道", "火炬开发区"],
        "潮州市": ["湘桥区", "潮安区"],
        "揭阳市": ["榕城区", "揭东区"],
        "云浮市": ["云城区", "云安区"]
    },
    "广西壮族自治区": {
        "南宁市": ["兴宁区", "青秀区", "江南区", "西乡塘区", "良庆区", "邕宁区", "武鸣区"],
        "柳州市": ["城中区", "鱼峰区", "柳南区", "柳北区", "柳江区"],
        "桂林市": ["秀峰区", "叠彩区", "象山区", "七星区", "雁山区", "临桂区"],
        "梧州市": ["万秀区", "长洲区", "龙圩区"],
        "北海市": ["海城区", "银海区", "铁山港区"],
        "防城港市": ["港口区", "防城区"],
        "钦州市": ["钦南区", "钦北区"],
        "贵港市": ["港北区", "港南区", "覃塘区"],
        "玉林市": ["玉州区", "福绵区"],
        "百色市": ["右江区", "田阳区"],
        "贺州市": ["八步区", "平桂区"],
        "河池市": ["金城江区", "宜州区"],
        "来宾市": ["兴宾区"],
        "崇左市": ["江州区"]
    },
    "海南省": {
        "海口市": ["秀英区", "龙华区", "琼山区", "美兰区"],
        "三亚市": ["海棠区", "吉阳区", "天涯区", "崖州区"]
    },
    "四川省": {
        "成都市": ["锦江区", "青羊区", "金牛区", "武侯区", "成华区", "龙泉驿区", "青白江区", "新都区", "温江区", "双流区", "郫都区", "新津区"],
        "自贡市": ["自流井区", "贡井区", "大安区", "沿滩区"],
        "攀枝花市": ["东区", "西区", "仁和区"],
        "泸州市": ["江阳区", "纳溪区", "龙马潭区"],
        "德阳市": ["旌阳区", "罗江区"],
        "绵阳市": ["涪城区", "游仙区", "安州区"],
        "广元市": ["利州区", "昭化区", "朝天区"],
        "遂宁市": ["船山区", "安居区"],
        "内江市": ["市中区", "东兴区"],
        "乐山市": ["市中区", "沙湾区", "五通桥区", "金口河区"],
        "南充市": ["顺庆区", "高坪区", "嘉陵区"],
        "眉山市": ["东坡区", "彭山区"],
        "宜宾市": ["翠屏区", "南溪区", "叙州区"],
        "广安市": ["广安区", "前锋区"],
        "达州市": ["通川区", "达川区"],
        "雅安市": ["雨城区", "名山区"],
        "巴中市": ["巴州区", "恩阳区"],
        "资阳市": ["雁江区"]
    },
    "贵州省": {
        "贵阳市": ["南明区", "云岩区", "花溪区", "乌当区", "白云区", "观山湖区"],
        "六盘水市": ["钟山区", "水城区"],
        "遵义市": ["红花岗区", "汇川区", "播州区"],
        "安顺市": ["西秀区", "平坝区"],
        "毕节市": ["七星关区"],
        "铜仁市": ["碧江区", "万山区"]
    },
    "云南省": {
        "昆明市": ["五华区", "盘龙区", "官渡区", "西山区", "东川区", "呈贡区", "晋宁区"],
        "曲靖市": ["麒麟区", "沾益区", "马龙区"],
        "玉溪市": ["红塔区", "江川区"],
        "保山市": ["隆阳区"],
        "昭通市": ["昭阳区"],
        "丽江市": ["古城区"],
        "普洱市": ["思茅区"],
        "临沧市": ["临翔区"]
    },
    "西藏自治区": {
        "拉萨市": ["城关区", "堆龙德庆区", "达孜区"],
        "日喀则市": ["桑珠孜区"],
        "昌都市": ["卡若区"],
        "林芝市": ["巴宜区"],
        "山南市": ["乃东区"],
        "那曲市": ["色尼区"]
    },
    "陕西省": {
        "西安市": ["新城区", "碑林区", "莲湖区", "灞桥区", "未央区", "雁塔区", "阎良区", "临潼区", "长安区", "高陵区", "鄠邑区"],
        "铜川市": ["王益区", "印台区", "耀州区"],
        "宝鸡市": ["渭滨区", "金台区", "陈仓区", "凤翔区"],
        "咸阳市": ["秦都区", "杨陵区", "渭城区"],
        "渭南市": ["临渭区", "华州区"],
        "延安市": ["宝塔区", "安塞区"],
        "汉中市": ["汉台区", "南郑区"],
        "榆林市": ["榆阳区", "横山区"],
        "安康市": ["汉滨区"],
        "商洛市": ["商州区"]
    },
    "甘肃省": {
        "兰州市": ["城关区", "七里河区", "西固区", "安宁区", "红古区"],
        "嘉峪关市": [],
        "金昌市": ["金川区"],
        "白银市": ["白银区", "平川区"],
        "天水市": ["秦州区", "麦积区"],
        "武威市": ["凉州区"],
        "张掖市": ["甘州区"],
        "平凉市": ["崆峒区"],
        "酒泉市": ["肃州区"],
        "庆阳市": ["西峰区"],
        "定西市": ["安定区"],
        "陇南市": ["武都区"]
    },
    "青海省": {
        "西宁市": ["城东区", "城中区", "城西区", "城北区", "湟中区"],
        "海东市": ["乐都区", "平安区"]
    },
    "宁夏回族自治区": {
        "银川市": ["兴庆区", "西夏区", "金凤区"],
        "石嘴山市": ["大武口区", "惠农区"],
        "吴忠市": ["利通区", "红寺堡区"],
        "固原市": ["原州区"],
        "中卫市": ["沙坡头区"]
    },
    "新疆维吾尔自治区": {
        "乌鲁木齐市": ["天山区", "沙依巴克区", "新市区", "水磨沟区", "头屯河区", "达坂城区", "米东区"],
        "克拉玛依市": ["独山子区", "克拉玛依区", "白碱滩区", "乌尔禾区"],
        "吐鲁番市": ["高昌区"],
        "哈密市": ["伊州区"]
    }
}
PROVINCES = list(CHINA_REGIONS.keys())

# ==================== 数据清洗与解析 ====================
def clean_job_data(df):
    cleaned_rows = []
    for _, row in df.iterrows():
        raw_title = str(row.get('职位', ''))
        pure_title = re.sub(r'^招聘', '', raw_title).strip()
        if ' - ' in pure_title:
            pure_title = pure_title.split(' - ')[0].strip()
        
        salary = str(row.get('薪资', ''))
        if not salary or salary == 'nan':
            raw_company = str(row.get('公司', ''))
            salary_match = re.search(r'(\d+[-~]\d+[kK]?(?:·\d+薪)?)', raw_company)
            if salary_match:
                salary = salary_match.group(1)
            else:
                salary = ''
        
        raw_company = str(row.get('公司', ''))
        location_match = re.search(r'【(.*?)】', raw_company)
        location = location_match.group(1).strip() if location_match else ''
        
        raw_exp_edu = str(row.get('经验/学历', ''))
        exp_edu_clean = re.sub(r'^】?/+', '', raw_exp_edu)
        parts = exp_edu_clean.split('/')
        if len(parts) > 1:
            company = parts[-1].strip()
            exp_edu = '/'.join(parts[:-1]).strip()
        else:
            company = ''
            exp_edu = exp_edu_clean
        
        if not company:
            company = raw_company
            company = re.sub(r'【.*?】', '', company)
            company = re.sub(r'\d+[-~]\d+[kK]?(?:·\d+薪)?', '', company)
            company = company.strip().strip('/')
        
        job_type = '全职'
        if '实习' in exp_edu or '元/天' in salary:
            job_type = '实习'
        elif '兼职' in exp_edu or '兼职' in raw_title:
            job_type = '兼职'
        
        city = ''
        district = ''
        if location:
            parts_loc = location.split('-')
            city = parts_loc[0].strip()
            if len(parts_loc) > 1:
                district = parts_loc[1].strip()
        
        url = str(row.get('URL', ''))
        combined_desc = f"职位名称：{pure_title}\n公司：{company}\n薪资：{salary}\n地点：{location}\n经验/学历要求：{exp_edu}"
        
        cleaned_rows.append({
            '职位': pure_title,
            '公司': company,
            '薪资': salary,
            '地点': location,
            '经验/学历': exp_edu,
            'URL': url,
            'combined_desc': combined_desc,
            'job_type': job_type,
            'city': city,
            'district': district
        })
    return pd.DataFrame(cleaned_rows)

@st.cache_data
def load_jobs():
    try:
        df_raw = pd.read_csv('liepin_auto_all.csv', encoding='utf-8-sig')
        df_raw = df_raw.dropna(how='all')
        df_clean = clean_job_data(df_raw)
        df_clean = df_clean[df_clean['职位'] != '']
        # 基于URL去重（URL应该是唯一的）
        if 'URL' in df_clean.columns:
            df_clean = df_clean.drop_duplicates(subset=['URL'], keep='first')
        else:
            # 如果URL列缺失，则使用组合列去重
            df_clean = df_clean.drop_duplicates(subset=['职位', '公司', '地点'], keep='first')
        return df_clean
    except Exception as e:
        st.error(f"读取文件失败：{e}")
        return None

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def match_resume_to_job(resume_text, job_title, job_desc, job_salary, job_location, job_exp_edu):
    # 提取公司名（从 combined_desc 中解析）
    try:
        company = job_desc.split('公司：')[1].split('\n')[0] if '公司：' in job_desc else '未知'
    except:
        company = '未知'
    
    prompt = f"""
你是一位温柔、亲切、经验丰富的职业顾问，正在帮助一位求职者（候选人）分析他/她与某个岗位的匹配情况。请用**第二人称“你”**与候选人对话，语气要委婉、鼓励、有人情味，像朋友聊天一样给出真诚的建议，而不是生硬的评价。

岗位信息如下：
- 职位名称：{job_title}
- 公司：{company}
- 薪资范围：{job_salary}
- 工作地点：{job_location}
- 经验/学历要求：{job_exp_edu}
- 岗位描述：{job_desc}

候选人的简历内容：
{resume_text[:2500]}

请你从以下五个维度，以亲切的口吻为候选人分析匹配情况，并给出可操作的改进建议。每个维度都需要给出一个 0–100 的整数分数（可以是 73、86 等非整十数），并附上一段温暖、具体的分析。

**五个维度及权重**：
1. 技能匹配度（权重40%）——你掌握的技能和工具与岗位要求的重合度。
2. 经验匹配度（权重30%）——你的实习/项目/工作经历与岗位要求的匹配程度。
3. 学历/资质匹配度（权重15%）——你的学历、专业、证书等与岗位要求的契合度。
4. 薪资期望匹配度（权重10%）——如果你没有写期望薪资，默认给你80分（表示企业通常可以协商）。
5. 地理位置匹配度（权重5%）——如果你没有写当前城市，默认给你70分（表示愿意考虑异地工作）。

然后计算综合匹配分数（四舍五入取整数）：  
综合分 = 技能分×0.4 + 经验分×0.3 + 学历分×0.15 + 薪资分×0.1 + 地点分×0.05

最后，请严格按照以下格式输出（每行一个部分，不要多输出无关内容）：

技能分：xx | 分析：（以“你”开头，用鼓励的语气分析你的技能优势，指出可以提升的地方）
经验分：xx | 分析：（以“你”开头，分析你的经历亮点和不足）
学历分：xx | 分析：（以“你”开头，分析你的学历是否符合，若不完全符合，如何弥补）
薪资分：xx | 分析：（以“你”开头，分析你的期望与岗位薪资是否匹配）
地点分：xx | 分析：（以“你”开头，分析地点方面的适配情况）
综合分：xx
整体评价：（用两三句温暖的话总结你的优势，以及你和这个岗位的缘分指数）
改进建议：
1. （具体、可操作的建议，以“你可以……”开头）
2. （另一条建议）
3. （可选，第三条建议）

重要提示：
- 所有分数必须是 0-100 之间的整数，可以是任意值，不要只输出整十数。
- 分析的文字要亲切、具体、有鼓励性，比如：“你的Python基础很不错，如果能再熟悉一下Django框架，那就更完美了。”
- 不要输出任何额外的解释或技术性的术语解释，直接按格式输出。
"""
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
        )
        result = response.choices[0].message.content
        
        # ========== 解析各维度分数和综合分 ==========
        import re
        skill_match = re.search(r'技能分[：:]\s*(\d{1,3})', result)
        exp_match = re.search(r'经验分[：:]\s*(\d{1,3})', result)
        edu_match = re.search(r'学历分[：:]\s*(\d{1,3})', result)
        salary_match = re.search(r'薪资分[：:]\s*(\d{1,3})', result)
        loc_match = re.search(r'地点分[：:]\s*(\d{1,3})', result)
        total_match = re.search(r'综合分[：:]\s*(\d{1,3})', result)
        
        skill = int(skill_match.group(1)) if skill_match else 60
        exp = int(exp_match.group(1)) if exp_match else 60
        edu = int(edu_match.group(1)) if edu_match else 60
        sal = int(salary_match.group(1)) if salary_match else 80
        loc = int(loc_match.group(1)) if loc_match else 70
        final_score = int(total_match.group(1)) if total_match else int(round(skill*0.4 + exp*0.3 + edu*0.15 + sal*0.1 + loc*0.05))
        
        # ========== 提取整体评价和改进建议 ==========
        eval_match = re.search(r'整体评价[：:]\s*(.+?)(?=改进建议[：:]|\n\n|$)', result, re.DOTALL)
        overall_eval = eval_match.group(1).strip() if eval_match else "未提供详细评价"
        
        suggest_match = re.search(r'改进建议[：:]\s*(.+?)$', result, re.DOTALL)
        suggestions = suggest_match.group(1).strip() if suggest_match else "暂无具体建议"
        
        # 组合理由（包含整体评价和建议）
        reason = f"{overall_eval}\n\n{suggestions}"
        
        return final_score, reason
    
    except Exception as e:
        return 0, f"匹配过程遇到小问题：{str(e)}，你可以稍后再试～"
    

def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def auto_apply_job(job_url):
    driver = get_selenium_driver()
    if driver is None:
        return False, "浏览器启动失败"
    try:
        driver.get(job_url)
        time.sleep(5)
        if "login" in driver.current_url.lower():
            driver.quit()
            return False, "需要登录，请在浏览器中完成登录后再次点击投递按钮"
        
        apply_selectors = [
            "//button[contains(text(),'立即申请')]",
            "//a[contains(text(),'立即申请')]",
            "//span[contains(text(),'立即申请')]",
            ".btn-apply",
            ".apply-btn",
            ".job-operation__apply"
        ]
        apply_btn = None
        for selector in apply_selectors:
            try:
                if selector.startswith("//"):
                    apply_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    apply_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                if apply_btn:
                    break
            except:
                continue
        
        if apply_btn:
            apply_btn.click()
            time.sleep(2)
            return True, "已点击「立即申请」，请手动确认后续弹窗（如有）"
        else:
            return False, "未找到「立即申请」按钮"
    except Exception as e:
        return False, f"投递出错：{str(e)}"
    finally:
        driver.quit()

# ==================== 主界面 ====================
uploaded_file = st.file_uploader("📄 上传简历 (PDF 或 Word)", type=["pdf", "docx"])

if uploaded_file:
    if uploaded_file.name.endswith('.pdf'):
        resume_text = extract_text_from_pdf(uploaded_file)
    else:
        resume_text = extract_text_from_docx(uploaded_file)
    
    if not resume_text.strip():
        st.error("无法从简历中提取文本，请确保文件为文字版（非扫描图片）")
        st.stop()
    
    st.success(f"简历解析成功，共 {len(resume_text)} 字符")
    
    jobs_df = load_jobs()
    if jobs_df is None or jobs_df.empty:
        st.stop()
    
    # ==================== 侧边栏筛选（修复地点匹配） ====================
    with st.sidebar:
        st.header("岗位筛选")
        
        keyword = st.text_input("职位必须包含的关键词", placeholder="例如：Python", value="")
        min_salary = st.number_input("最低月薪(k)", min_value=0, value=0, step=1)
        job_type_filter = st.radio("工作类型", options=["全部", "实习", "全职", "兼职"], horizontal=True)
        
        st.subheader("工作地点")
        selected_province = st.selectbox("省份", options=["全部"] + PROVINCES)
        
        if selected_province != "全部":
            cities = list(CHINA_REGIONS[selected_province].keys())
            city_options = ["全部"] + cities
        else:
            city_options = ["全部"]
        selected_city = st.selectbox("城市", options=city_options)
        
        if selected_province != "全部" and selected_city != "全部":
            districts = CHINA_REGIONS[selected_province].get(selected_city, [])
            district_options = ["全部"] + districts
        else:
            district_options = ["全部"]
        selected_district = st.selectbox("区/县", options=district_options)
        
        custom_city = st.text_input("自定义城市（如未找到所需城市）", placeholder="例如：雄安新区")
        custom_desc = st.text_input("自定义关键词（在职位、公司、经验/学历中搜索）", placeholder="例如：大模型", value="")
    
    # 应用筛选
    filtered_df = jobs_df.copy()
    
    if keyword:
        filtered_df = filtered_df[filtered_df['职位'].str.contains(keyword, case=False, na=False)]
    
    if min_salary > 0:
        def get_min_salary(s):
            nums = re.findall(r'(\d+)', str(s))
            return int(nums[0]) if nums else 0
        filtered_df['_min'] = filtered_df['薪资'].apply(get_min_salary)
        filtered_df = filtered_df[filtered_df['_min'] >= min_salary]
    
    if job_type_filter != "全部":
        filtered_df = filtered_df[filtered_df['job_type'] == job_type_filter]
    
    # ========== 改进的地点匹配逻辑（模糊匹配） ==========
    def match_location(row_location, province, city, district, custom_city):
        if not row_location:
            return False
        if custom_city:
            return custom_city in row_location
        # 如果省份为"全部"，则不过滤地点
        if province == "全部":
            return True
        # 清理省份名称中的后缀（省、市、自治区）
        province_clean = province.replace("省", "").replace("市", "").replace("自治区", "").replace("壮族", "").replace("回族", "").replace("维吾尔", "")
        # 检查省份是否出现在地点中
        if province_clean not in row_location and province not in row_location:
            return False
        # 如果城市为"全部"，则只匹配省份
        if city == "全部":
            return True
        city_clean = city.replace("市", "")
        if city_clean not in row_location and city not in row_location:
            return False
        # 如果区县为"全部"，则只匹配省份和城市
        if district == "全部":
            return True
        if district not in row_location:
            return False
        return True
    
    location_mask = filtered_df['地点'].apply(
        lambda loc: match_location(loc, selected_province, selected_city, selected_district, custom_city)
    )
    filtered_df = filtered_df[location_mask]
    
    if custom_desc:
        mask = (
            filtered_df['职位'].str.contains(custom_desc, case=False, na=False) |
            filtered_df['公司'].str.contains(custom_desc, case=False, na=False) |
            filtered_df['经验/学历'].str.contains(custom_desc, case=False, na=False) |
            filtered_df['combined_desc'].str.contains(custom_desc, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    
    st.write(f"筛选后共 **{len(filtered_df)}** 个岗位")
    
    if len(filtered_df) == 0:
        st.warning("没有符合筛选条件的岗位，请放宽筛选条件（例如地点选择更宽泛）")
        st.stop()
    
    num_match = st.slider("选择进行 AI 匹配的岗位数量", 1, min(50, len(filtered_df)), 10)
    jobs_to_match = filtered_df.head(num_match)
    
    if st.button("🚀 开始 AI 匹配", use_container_width=True):
        results = []
        progress = st.progress(0)
        for i, (idx, row) in enumerate(jobs_to_match.iterrows()):
            score, reason = match_resume_to_job(
                resume_text,
                row['职位'],
                row['combined_desc'],
                row['薪资'],
                row['地点'],
                row['经验/学历']
            )
            results.append({
                "职位": row['职位'],
                "公司": row['公司'],
                "薪资": row['薪资'],
                "地点": row['地点'] if row['地点'] else "未提供",
                "经验/学历": row['经验/学历'],
                "URL": row.get('URL', ''),
                "匹配分数": score,
                "匹配理由": reason
            })
            progress.progress((i+1)/num_match)
        
        st.session_state['match_results'] = pd.DataFrame(results)
        st.success("匹配完成！")
    
    if 'match_results' in st.session_state:
        results_df = st.session_state['match_results'].sort_values("匹配分数", ascending=False)
        st.subheader("📊 匹配结果（按匹配度排序）")
        
        for idx, row in results_df.iterrows():
            with st.expander(f"【{row['匹配分数']}分】{row['职位']} - {row['公司']}"):
                st.write(f"**公司**：{row['公司']}")
                st.write(f"**薪资**：{row['薪资']}")
                st.write(f"**地点**：{row['地点']}")
                st.write(f"**经验/学历**：{row['经验/学历']}")
                st.write(f"**匹配理由**：{row['匹配理由']}")
                
                if pd.notna(row['URL']) and row['URL']:
                    if st.button(f"📤 一键自动投递", key=f"apply_{idx}"):
                        with st.spinner(f"正在自动投递 {row['职位']} ..."):
                            success, msg = auto_apply_job(row['URL'])
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                else:
                    st.warning("该岗位缺少投递链接，无法自动投递")
else:
    st.info("请上传简历文件开始使用")