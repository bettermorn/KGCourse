# 参考项目
http://openkg.cn/tool/elasticsearch-kbqa  基于elasticsearch的KBQA实现及示例

# 运行软件环境
* elasticSearch 7.3
* Python 2.7
## Python 依赖库
* django
* jieba
* pyahocorasick

#  参考文件
1.新建index('demo')和type('person')
*
`curl -XPUT 'localhost:9200/demo?pretty' -H 'Content-Type: application/json' -d'
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
