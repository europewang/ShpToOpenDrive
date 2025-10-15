1.本脚本是创建在windows中，PowerShell不支持&&语法，需要分别执行命令
2.conda环境是shp2opendrive，每次记得进入
3.本代码所在路径为：E:\Code\ShpToOpenDrive
4.修改或者新增新的类或者方法之后，将其写入API的md文档中
5.实时更新Readme.md文件
6.提交git时候：更改远程URL为SSH
git remote set-url origin git@github.com:europewang/ShpToOpenDrive.git
git push origin master
7.前端采用苹果风格灰色色调设计的设计语言，以白色、灰色为基调，流畅简洁美观
8.不允许主动提交git，必须我发出了请git上传的命令再上传
9.测试shp2Opendrive最终代码是调用shp2xodr.py，input是在本项目的\data\testODsample\wh2000\Lane.shp，输出文件是一定要放到output中
10.测试shp2Opendrive普通测试代码是在本项目的input是E:\Code\ShpToOpenDrive\data\testODsample\LaneTest.shp，输出文件是一定要放到output中
执行代码方式：python src\shp2xodr.py data\testODsample\LaneTest.shp output\output.xodr
11.完整的测试流程按照shp2opendrive测试之后，再进行opendrive2obj转换
执行代码方式：python src\shp2xodr.py data\testODsample\wh2000\Lane.shp output\output.xodr
12.E:\Code\ShpToOpenDrive\SoftwareCopyright下的所有代码都不要有多余的空行和注释
13.测试道路斜率一致性问题时候，采用用例：
python src\shp2xodr.py data\test_simple\SimpleTest.shp output\simple_test.xodr
使用analyze_slope_consistency.py来看xodr转换的效果怎么样