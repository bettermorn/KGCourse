# 参考项目
http://openkg.cn/tool/elasticsearch-kbqa  基于elasticsearch的KBQA实现及示例

# 运行软件环境
* Anaconda 3     之spider
* elasticSearch 7.3  
* Python 2.7  注：此代码可做参考，未来可以升级到3.7，因为Python2.7以后不会再被维护。
* django 3.0.3
## Python 依赖库
* django  3.0.3
* jieba   
* pyahocorasick
## 运行步骤
1. 启动Anaconda3， 选中elasticQA环境，打开spider观看代码。以下为进入conda  的命令行方式
```
source ~/.bash_profile  
conda activate elasticQAPy27
```
也可以使用conda的可视化界面 "open terminal"
2. 启动 django  
``` 
cd code/kbdemo
python manage.py runserver
```
3. 启动elasticSearch 
```
cd elasticsearch-7.6.0/bin 
./elasticsearch  
```
* 访问 curl 'http://localhost:9200’  测试是否成功
5. 系统入口
* 访问 http://localhost:8000


#  参考数据及命令
1.新建index('demo')和type('person')
*
`
curl -XPUT 'localhost:9200/demo?include_type_name=true' -H 'Content-Type: application/json' -d'
{
        "mappings": {
        	"person": {
                "properties": {
                    "subj": {"type": "keyword"},
                    "height": {"type": "integer"},
                    "weight": {"type": "integer"},
                    "po":{
                         "type": "nested",
                         "properties":{
                             "pred":{"type":"keyword"},
                             "obj":{"type":"keyword"}
                         }
                    }
                }
            }
       }
}
'
`
返回 {"acknowledged":true,"shards_acknowledged":true,"index":"demo"}  
2.检索知识库

`
curl -XGET 'localhost:9200/demo/person/_search?&pretty' -H 'Content-Type:application/json' -d'
{

  "query":
    { "bool":{
      "must":{ 
        "term":{"subj": "姚明"}
       } 
    }
 } 
 }
'
`
# 3.修改调整过的代码
## 设置文件
* settings.py  ALLOWED_HOSTS = ['localhost', '127.0.0.1']  django 设置文件

## Request 与Response方法
* views.py  增加Content-Type
```
headers = {'Content-type': 'application/json'}
response = requests.get("http://localhost:9200/demo/person/_search", data = query,headers= headers)
```
```
def _search_single_subj(entity_name):       
    if res['hits']['total']['value']== 0:
```
## 文件路径问题
* views.py  写绝对地址
## 优化
### templates 加文字说明
* home.html  
* entity.html
* entity_list.html
* message.html
