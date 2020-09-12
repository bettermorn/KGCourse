import certifi
import pyhanlp
import os
import pickle
import urllib3
from urllib.parse import quote, unquote
import re

from SPARQLWrapper import SPARQLWrapper, JSON
from lxml.html import etree


class EntityRecord:
    def __init__(self):
        self.entity_set = dict()

    def add_entity(self, e, t):
        if self.entity_set.__contains__(e) and self.entity_set[e] != "secondary_entity":
            pass
        else:
            self.entity_set[e] = t

    def form_entity_tuples(self):
        ret = []
        for e, t in self.entity_set.items():
            ret.append((f"e:{clean_text(e)}", "r:name", f"\"{e}\""))
            ret.append((f"e:{clean_text(e)}", "r:type", f"\"{t}\""))
        return ret


ER = EntityRecord()
INCRE_PATH = "triples/incremental files"


def clean_text(s):
    # 去掉不是英文也不是中文的奇怪符号
    # 保留？！、；，（）《》“”
    s = re.sub(r"[^\x00-\xff\u4E00-\u9FA5\uff1f\uff01\u3001\uff1b\uff0c\uff08\uff09\u300a\u300b\u201d\u201c]", "", s)
    # 复合的符号
    s = re.sub(r"\+/-", "约", s)
    s = re.sub(r"^~", "约", s)
    s = re.sub(r"\[\d+\]", "", s)
    s = re.sub(r"<>", "、", s)
    # 英文标点
    s = re.sub(r"[(“]", "（", s)
    s = re.sub(r"[)”]", "）", s)
    s = re.sub(r"[.'\"]", "。", s)
    s = re.sub(r"[,;]", "。", s)
    s = re.sub(r"\\", "。", s)
    s = re.sub(r"\?", "？", s)
    s = re.sub(r"[/|]", "、", s)
    s = re.sub(r"[-~]", "至", s)
    # 空白
    s = re.sub(r"\s*", "", s)
    return s


def sep_tag(elems, split_pattern):
    """
    在html元素的字符串中进行切割
    :param elems: html元素
    :param split_pattern: 切割所使用的正则表达式
    :return: list of str, 每个字符串都经过清洗
    """
    ret = [""]
    url_head = "https://asoiaf.huijiwiki.com"
    # e_str = re.split(split_pattern, etree.tostring(elems).decode('utf-8'))
    elems = etree.HTML(etree.tostring(elems).decode('utf-8'))
    for s in elems.xpath("//body/*/text()|//body/*/*"):
        try:
            if isinstance(s, str):
                # 访问到字符串元素
                if not re.fullmatch(r"\s*", s):
                    ret[-1] += clean_text(s)
            else:
                if s.tag == "br":
                    ret.append("")
                elif s.tag == "a":
                    if "new" in s.xpath("@class"):
                        ret[-1] += clean_text("".join(s.xpath(".//text()")))
                    else:
                        ret[-1] += get_header(url_head + s.xpath("@href")[0])
                else:
                    ret[-1] += clean_text("".join(s.xpath(".//text()")))
        except BaseException as e:
            print(f"septag!!!!!exception:{e}")
    # 清理空字符串，分割逗号
    ret_copy = []
    for item in ret:
        if item != "":
            # ret_copy += [*item.split("，")]
            ret_copy.append(item)
    return ret_copy


def dict2file(dict_: dict, filename: str, filetype: int, **kwargs):
    """
    将字典数据写入文件
    :param dict_:
    :param filename:
    :param filetype:
        0: 一行为一项的文本文件
        1: pickle
    :return:
    """
    with open(filename, **kwargs) as f:
        if filetype == 0:
            for key, value in dict_.items():
                f.write(f"{key}: {value}\n")
        elif filetype == 1:
            pickle.dump(dict_, f)


def triple2file(triples, filename, **kwargs):
    with open(filename, **kwargs) as f:
        for s, p, o in triples:
            f.write(f"{s}\t{p}\t{o}.\n")


def sparql_result2file(results, filename, **kwargs):
    triples = [(squeeze_result(result["s"]), squeeze_result(result["p"]), squeeze_result(result["o"]))
               for result in results["results"]["bindings"]]

    with open(filename, mode="w", **kwargs) as f:
        f.write("@prefix r:<http://kg.course/action/>.\n"
                "@prefix e:<http://kg.course/entity/>.\n")

    triple2file(triples, filename, mode="a", **kwargs)


def apply_xpath2url(url: str, xpath: str):
    """
    返回element
    :param url:
    :param xpath:
    :return:
    """
    http = urllib3.PoolManager(ca_certs=certifi.where())
    page = http.request('GET', url).data.decode('utf-8')
    doc = etree.HTML(page)
    if doc is None:
        return None
    else:
        return doc.xpath(xpath)

def apply_xpath2element(elem, xpath: str):
    return elem.xpath(xpath)


def extract_text(elem):
    text = "".join(elem.xpath(".//text()")).strip()
    return text


def get_header(url: str):
    if "#" in url:
        url, loc_id = url.split("#")
        return "".join(apply_xpath2url(url, f"//*[@id='{loc_id}']//text()"))
    else:
        return "".join(apply_xpath2url(url, f"//article//h1//text()"))


def get_index_pages(begin_url: str, n_of_page: int, category: str):
    """
    从begin_url开始获取页面索引
    :param category:
    :param n_of_page:
    :param begin_url:
    :return: dict, key=名称, value=url
    """
    ret = dict()
    url_head = "https://asoiaf.huijiwiki.com"
    url = begin_url
    xpath = ".//div[contains(concat(' ', @class, ' '), concat(' ','mw-category-generated',' '))]" \
            "//div[contains(concat(' ', @id, ' '), concat(' ','mw-pages',' '))]"
    for i in range(n_of_page):
        print(f"{i}-th page, get {category} from {unquote(url)}")
        
        mv_pages = apply_xpath2url(url, xpath)[0]
        names = apply_xpath2element(mv_pages, ".//li//text()")
        urls = apply_xpath2element(mv_pages, ".//li//a/@href")
        for n, u in zip(names, urls):
            print(f"name: {n}, url: {unquote(u)}")
            ret[n] = url_head + u
        try:
            url = url_head + apply_xpath2element(mv_pages, "./a[position()=2]//@href")[0]
        except BaseException as e:
            print(f"indexpages!!!!!exception:{e}")
            break
    print(f"finished, all {len(ret)} {category}")
    return ret


def get_info(name: str, url: str, category_name):
    print("-------1 start get info---------")
    ret = []
    header_xpath = "//*[contains(concat(' ', @id, ' '), concat(' ','firstHeading',' '))]//h1//text()"
    xpathstr = apply_xpath2url(url, header_xpath)
    if xpathstr is None :
        header = ""
    else:    
        header = "".join(xpathstr).strip()
    if header != name:
        with open(os.path.join(INCRE_PATH, "name_mismatch.log"), mode="a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{name}--{header}: {url}\n")
    xpath = "//div[contains(concat(' ', @id, ' '), concat(' ','mw-content-text',' '))]" \
            "//*[contains(@class, 'infobox')]"
    data = apply_xpath2url(url, xpath)
    ER.add_entity(clean_text(name), category_name)
    if data is None:
        data = ""
    for i in data:
        # 获取一个属性
        infobox_labels = i.xpath(".//*[contains(@class, 'infobox-label')]")
        infobox_data = i.xpath(".//*[contains(@class, 'infobox-data')]")
        for p, o in zip(infobox_labels, infobox_data):
            p = "".join(p.xpath(".//text()"))
            o = sep_tag(o, r"<br>|<br/>")
            # 一个属性有多个属性值
            for o_ in o:
                ER.add_entity(clean_text(o_), "secondary_entity")
                ret.append((f"e:{clean_text(name)}", f"r:{clean_text(p)}", f"e:{clean_text(o_)}"))
    print("-------1 end get info---------")
    return ret


def get_index_main():
    print("------------4 start get index main------------")  
    category_name = "character"
    # 运行此段代码之前，请查看可以访问几页，根据页数确定索引
    character_index = get_index_pages("https://asoiaf.huijiwiki.com/wiki/Category:%E4%BA%BA%E7%89%A9",
                                      3, category_name)
    dict2file(character_index, f"triples/{category_name}_index", 0, mode="w", encoding="utf-8", errors="ignore")
    dict2file(character_index, f"triples/{category_name}_index.pkl", 1, mode="wb")
    category_name = "house"
    house_index = get_index_pages("https://asoiaf.huijiwiki.com/wiki/Category:%E8%B4%B5%E6%97%8F%E5%AE%B6%E6%97%8F",
                                  5, "house")
    dict2file(house_index, f"triples/{category_name}_index", 0, mode="w", encoding="utf-8", errors="ignore")
    dict2file(house_index, f"triples/{category_name}_index.pkl", 1, mode="wb")
    category_name = "castle"
    castle_index = get_index_pages("https://asoiaf.huijiwiki.com/wiki/Category:%E5%9F%8E%E5%A0%A1",
                                   2, category_name)
    dict2file(castle_index, f"triples/{category_name}_index", 0, mode="w", encoding="utf-8", errors="ignore")
    dict2file(castle_index, f"triples/{category_name}_index.pkl", 1, mode="wb")
    print("------------4 end get index main------------")  

def add_index(name, url, category):
    with open(f"triples/{category}_index.pkl", mode="rb") as f:
        name2url = pickle.load(f)
        name2url[name] = url
        dict2file(name2url, f"triples/{category}_index", 0, mode="w", encoding="utf-8", errors="ignore")
        dict2file(name2url, f"triples/{category}_index.pkl", 1, mode="wb")


def get_info_main():
    print("------------5 start get info main------------") 
    with open(os.path.join(INCRE_PATH, "asoiaf.ttl"), mode="w", encoding="utf-8", errors="ignore") as f:
        f.write("@prefix r:<http://kg.course/action/>.\n"
                "@prefix e:<http://kg.course/entity/>.\n")
    category_names = ["character", "house", "castle"]
    # 从pkl文件读取数据
    for c in category_names:
        with open(f"triples/{c}_index.pkl", mode="rb") as f:
            name2url = pickle.load(f)
            for n, u in name2url.items():
                print(f"get {n}'s info")
                kg = get_info(n, u, c)
                if len(kg) < 1:
                    with open(os.path.join(INCRE_PATH, "no_triples.log"), mode="a", encoding="utf-8",
                              errors="ignore") as f:
                        f.write(f"{n}: {u}\n")
                triple2file(kg, os.path.join(INCRE_PATH, "asoiaf.ttl"), mode="a", encoding="utf-8", errors="ignore")
    entities_kg = ER.form_entity_tuples()
    triple2file(entities_kg, os.path.join(INCRE_PATH, "asoiaf.ttl"), mode="a", encoding="utf-8", errors="ignore")
    print("------------5 end get info main------------") 

def squeeze_result(res):
    if res["type"] == "uri":
        tmp_split = res["value"].split("/")
        if tmp_split[-2].strip() == "action":
            return f"r:{tmp_split[-1]}"
        elif tmp_split[-2].strip() == "entity":
            return f"e:{tmp_split[-1]}"
    else:
        return "\"" + res["value"] + "\""


def sparql_add_triple(s, p, o):
    print("-------start insert data to jena-----")
    sparql = SPARQLWrapper("http://localhost:3030/testds/update")
    try:
        sparql.setQuery(
            f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                INSERT DATA {{{s} {p} {o}.}}
            """
        )
        sparql.method = "POST"
        sparql.query()
    except BaseException as e:
        with open(os.path.join(INCRE_PATH, "sparqlerror.log"), mode="a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{e}\n")
    print("-----end insert data to jena----")

def sparql_del_triple(s, p, o):
    print("-------start delete data to jena-----")
    sparql = SPARQLWrapper("http://localhost:3030/testds/update")
    try:
        sparql.setQuery(
            f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                DELETE WHERE{{{s} {p} {o}.}}
            """
        )
        sparql.method = "POST"
        sparql.query()
    except BaseException as e:
        with open(os.path.join(INCRE_PATH, "sparqlerror.log"), mode="a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{e}\n")
    print("-------end delete data to jena-----")

def sparql_get_all_entity(category=None):
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    if category:
        sparql.setQuery(
            f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                SELECT DISTINCT ?s
                WHERE {{
                    ?s r:type "{category}".
                }}
            """
        )
    else:
        sparql.setQuery(
            f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                SELECT DISTINCT ?s
                WHERE {{
                    ?s r:name ?o.
                }}
            """
        )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return [squeeze_result(r["s"]) for r in results["results"]["bindings"]]


def sparql_get_name(e):
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                SELECT DISTINCT ?o
                WHERE {{
                    {e} r:name ?o.
                }}
            """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results["results"]["bindings"][0]["o"]["value"]


def sparql_get_representation(e):
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        f"""
            PREFIX	r:	<http://kg.course/action/>
            PREFIX	e:	<http://kg.course/entity/>
            SELECT DISTINCT ?o
            WHERE{{
                {{{e} r:name ?o}}
                UNION{{{e} r:别名 ?o}}
                UNION{{{e} r:名 ?o}}
            }}
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return [squeeze_result(r["o"]) for r in results["results"]["bindings"]]


def eliminate_entity(e):
    name = sparql_get_name(e)
    print(f"eliminating {name}...")
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        f"""
            PREFIX	r:	<http://kg.course/action/>
            PREFIX	e:	<http://kg.course/entity/>
            SELECT DISTINCT ?s ?r
            WHERE {{
                ?s ?r {e}.
            }}
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    for result in results["results"]["bindings"]:
        s = squeeze_result(result["s"])
        r = squeeze_result(result["r"])
        sparql_del_triple(s, r, e)
        sparql_add_triple(s, r, f"\"{name}\"")
    sparql_del_triple(e, "r:name", "?o")
    sparql_del_triple(e, "r:type", "?o")


def sparql_all2file():
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        """
        PREFIX	r:	<http://kg.course/action/>
        PREFIX	e:	<http://kg.course/entity/>
        SELECT DISTINCT ?s ?p ?o
        WHERE {
            ?s ?p ?o.
        }
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    sparql_result2file(results, os.path.join(INCRE_PATH, "asoif.ttl"), encoding="utf-8", errors="ignore")


def clean_triples():
    """
    需要先使用get_info_main抓取三元组, 并启动fuseki服务器载入
    去掉secondary entity
    :return:
    """
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        """
        PREFIX	r:	<http://kg.course/action/>
        PREFIX	e:	<http://kg.course/entity/>
        SELECT DISTINCT ?s
        WHERE {
            ?s r:type "secondary_entity".
        }
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    for result in results["results"]["bindings"]:
        eliminate_entity(squeeze_result(result["s"]))

    sparql_all2file()


def get_all_literal(filename, **kwargs):
    
    print("--------2 start get all iteral--------------")
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        """
        PREFIX	r:	<http://kg.course/action/>
        PREFIX	e:	<http://kg.course/entity/>
        SELECT DISTINCT ?o
        WHERE {
            ?s ?r ?o.
            MINUS {?s r:type ?o}
            FILTER isLiteral(?o)
        }
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    literals = [result["o"]["value"] for result in results["results"]["bindings"]]
    with open(filename, **kwargs) as f:
        for l in literals:
            f.write(f"{l}\n")
    print("--------2 end get all iteral--------------")

def add_firstname_last_name():
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        """
        PREFIX	r:	<http://kg.course/action/>
        PREFIX	e:	<http://kg.course/entity/>
        SELECT DISTINCT ?s ?o
        WHERE {
            ?s r:name ?o.
            FILTER EXISTS{?s r:type "character"}
        }
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]
    for result in results:
        s = squeeze_result(result["s"])
        o = result["o"]["value"]
        print(s, o)
        name_list = o.split("·")
        sparql_add_triple(s, "r:名", "\"" + name_list[0] + "\"")
        if len(name_list) > 1:
            sparql_add_triple(s, "r:姓", "\"" + name_list[1] + "\"")


def match_literal(entity, word):
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        f"""
            PREFIX	r:	<http://kg.course/action/>
            PREFIX	e:	<http://kg.course/entity/>
            SELECT DISTINCT ?s ?r ?o
            WHERE {{
                ?s ?r ?o.
                MINUS {{?s r:type ?o}}
                MINUS {{?s r:name ?o}}
                MINUS {{?s r:名 ?o}}
                MINUS {{?s r:别名 ?o}}
                MINUS {{{entity} ?r ?o}}
                FILTER regex(str(?r), "继承|继任|父亲|母亲|子嗣|兄弟姐妹")
                FILTER regex(?o, "^{word}$")
            }}
            """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return [(squeeze_result(result["s"]),
             squeeze_result(result["r"]),
             squeeze_result(result["o"]))
            for result in results["results"]["bindings"]]


def refine_literals():
    """
    把可以对应实体的literal找出来
    :return:
    """
    print("------------3 start refine literals------------")
    entities = sparql_get_all_entity("character")
    print("------------3 end refine literals------------")  
    for i, e in enumerate(entities):
        alias = sparql_get_representation(e)
        for a in alias:
            a = a.strip("\"")
            matched_triple = match_literal(e, f"{a}.*")
            for t in matched_triple:
                print("用实体", e, f"替换掉", t, f"中的{t[2]}?({i}/{len(entities)})")
                input_signal = input()
                if input_signal == "":
                    print("------------3 end refine literals------------")  
                    pass
                else:
                    sparql_add_triple(t[0], t[1], e)
                    sparql_del_triple(t[0], t[1], t[2])
            print("------------3 end refine literals------------")        
     
     

def to_simplified_chinese(in_filename, out_filename):
    with open(out_filename, mode="w", encoding="utf-8", errors="ignore") as outfile:
        with open(in_filename, mode="r", encoding="utf-8", errors="ignore") as infile:
            for l in infile.readlines():
                outfile.write(pyhanlp.HanLP.convertToSimplifiedChinese(l))


def change_relation_name(original_rname, changed_rname):
    """
    把原来称为original_rname的关系改为changed_rname
    :param original_rname:
    :param changed_rname:
    :return:
    """
    sparql = SPARQLWrapper("http://localhost:3030/testds/sparql")
    sparql.setQuery(
        f"""
            PREFIX	r:	<http://kg.course/action/>
            PREFIX	e:	<http://kg.course/entity/>
            SELECT DISTINCT *
            WHERE {{
                ?s {original_rname} ?o.
            }}
        """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    sparql = SPARQLWrapper("http://localhost:3030/testds/update")
    try:
        sparql.setQuery(
            f"""
                PREFIX	r:	<http://kg.course/action/>
                PREFIX	e:	<http://kg.course/entity/>
                DELETE WHERE{{?s {original_rname} ?o.}}
            """
        )
        sparql.method = "POST"
        sparql.query()
    except BaseException as e:
        with open(os.path.join(INCRE_PATH, "sparqlerror.log"), mode="a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{e}\n")
    for r in results["results"]["bindings"]:
        sparql_add_triple(squeeze_result(r["s"]), changed_rname, squeeze_result(r["o"]))


if __name__ == "__main__":
    #get_info("艾德·史塔克", "https://asoiaf.huijiwiki.com/wiki/%E8%89%BE%E5%BE%B7%C2%B7%E5%8F%B2%E5%A1%94%E5%85%8B", "character")
    #get_info("阿大克·汉博利", "https://asoiaf.huijiwiki.com/wiki/%E9%98%BF%E5%A4%A7%E5%85%8B%C2%B7%E6%B1%89%E5%8D%9A%E5%88%A9", "character")
    #get_all_literal("literal_vocabulary", mode="w", encoding="utf-8", errors="ignore")
    #refine_literals()
    #get_index_main()
    #get_info_main()
    #to_simplified_chinese("triples/incremental files/asoiaf.ttl", "triples/incremental files/asoiaf-s.ttl")
    # # 启动fuseki,上传ttl文件，运行下面文件
    # clean_triples()
    # add_firstname_last_name()
    # change_relation_name("r:王后", "r:配偶")
    # change_relation_name("r:丈夫", "r:配偶")
    # change_relation_name("r:继承者", "r:继承人")
    # change_relation_name("r:信仰", "r:宗教")
    # change_relation_name("r:家传武器", "r:祖传武器")
    # change_relation_name("r:文化", "r:种族")
    sparql_all2file()
    pass
