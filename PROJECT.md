这是一个类agent的任务处理流程
**主要任务**
通过中国气象局官方的公布数据、天气预警信息等获得当天的天气预警和实况等信息，通过ocr等识别方法，爬取或识别对应的文字信息，通过api连接到云ai平台，使用模型总结，并给出对应省份的气象信息，具体的总结见**总结要求**。爬取的网站见**网站**。使用的ai模型网站、token和模型见**模型配置**。需要让他总结出整理成表格，每行为省份，每列为未来第n天的日期，表中为具体的天气信息，如大风、台风，沙尘，降雪等，具体的实例图见./example.jpg，最终输出为markdown格式到当前文件夹，命名为{当前日期}.md。需要作为python脚本运行，可以用conda建立一个单独的环境。并且给出环境依赖、能够定时运行。


**总结要求**
从上述中央气象台网页爬取文字信息。如果爬取的信息是当天刚刚发布的，那么就整理汇总信息。
筛选出山东、湖北、安徽、山西、、河北、辽宁、河南、黑龙江、甘肃、陕西、宁夏、广东、江西、广、贵州地区发生大风、台风，沙尘，降雪，大雨以上级别的信息。


**网站**
天气公报：https://www.nmc.cn/publish/weather-bulletin/index.htm
每日天气提示：https://www.nmc.cn/publish/weatherperday/index.htm
重要天气提示：https://www.nmc.cn/publish/news/weather_new.html
中期天气：https://www.nmc.cn/publish/bulletin/mid-range.htm
台风预警：https://www.nmc.cn/publish/typhoon/warning_index.html

**模型配置**
base_url=https://api.deepseek.com
模型型号为deepseek-reasoner
token==<YOUR_TOKEN>


