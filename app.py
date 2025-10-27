# 这是一个示例 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。

import streamlit as st
import pandas as pd #用户进行表格创建和表格数据分析的一个模块
#
st.write("这是我的第一个页面")
#使用pandas创建一个表格，将表格显示在streamlit页面中
table = pd.DataFrame({"第一列":[1,2,3,4,5],"第二列":[6,7,8,9,10]})
st.write(table)

st.write("st.slider()滑块")
#slider参数为滑块自定义名称，返回值为滑动到的数值
num = st.slider("num")
st.write(num, "滑块 is", num*num)



st.write("checkbox()多选框")
# 点击checkbox后返回True，未点击为False

ex1 = st.checkbox("是否显示表格")

if ex1:
    table = pd.DataFrame({"第一列":[1,2,3,4,5],"第二列":[6,7,8,9,10],"第三列":[6,7,8,9,10]})
    st.write(table)
ex2 = st.checkbox("是否显示滑块")
if ex2:
    x = st.slider('x')

# 使用 密码
password = st.text_input("请输入密码",type='password')
if st.button("登录"):
    if password == "123456":
        st.success("登录成功")
    else:
        st.error("登录失败")
# 下拉框
option = st.selectbox(label="请选择性别",options=["男","女"])
st.write("您选择的是",option)

# 侧边栏下拉框
add_selectbox = st.sidebar.selectbox(
    label="sex",
    options=["男","女"]
)
# 获取下拉选项
st.write("获取下拉选项",add_selectbox)

# 侧边栏滑块
add_slider = st.sidebar.slider(
    label="滑块",
    min_value=0,
    max_value=100,
    value=(30,100)
)
# 获取滑块的值
st.write("获取滑块的值",add_slider)

# st.radio 单选按钮
# st.progress 进度条
# 布局
# st.sidebar
# st.columns
# st.tabs
# st.expander
